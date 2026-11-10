import logging
import time
from typing import Optional

from fastapi import FastAPI
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import Base
from .database import engine
from .database import get_db

from . import models
from . import schemas


Base.metadata.create_all(
    bind=engine
)


app = FastAPI(
    title="Plataforma de Matrícula",
    description="API REST para el sistema de matrícula académica",
    version="1.1"
)


# Métricas: una línea por petición en stdout (visible con `docker logs`).
# Formato: METRICA,<método>,<ruta>,<status>,<duración_ms>
# Estos datos sirven para estimar tiempos de servicio y tasas de llegada
# al calibrar el modelo de simulación (SimPy).
logger = logging.getLogger("uvicorn.error")


@app.middleware("http")
async def medir_tiempo(request: Request, call_next):

    inicio = time.perf_counter()
    response = await call_next(request)
    duracion_ms = (time.perf_counter() - inicio) * 1000

    response.headers["X-Process-Time-ms"] = f"{duracion_ms:.2f}"

    logger.info(
        "METRICA,%s,%s,%s,%.2f",
        request.method,
        request.url.path,
        response.status_code,
        duracion_ms
    )

    return response


# Endpoint 1 - estado de la API
@app.get("/")
def inicio():

    return {
        "mensaje": "API de matrícula funcionando",
        "estado": "activo"
    }


# Endpoint extra - salud (verifica conexión con la base de datos)
@app.get("/health")
def health(db: Session = Depends(get_db)):

    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Base de datos no disponible"
        )

    return {"estado": "ok"}


# ---------------------------------------------------------------
# Estudiantes
# ---------------------------------------------------------------

# Endpoint 2 - crear estudiante
@app.post("/estudiantes", response_model=schemas.EstudianteResponse)
def crear_estudiante(
    estudiante: schemas.EstudianteCreate,
    db: Session = Depends(get_db)
):

    nuevo = models.Estudiante(
        nombre=estudiante.nombre,
        correo=estudiante.correo
    )

    db.add(nuevo)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ya existe un estudiante con ese correo"
        )

    db.refresh(nuevo)

    return nuevo


# Endpoint 3 - consultar estudiantes
@app.get("/estudiantes", response_model=list[schemas.EstudianteResponse])
def listar_estudiantes(
    skip: int = 0,
    limit: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db)
):

    consulta = db.query(
        models.Estudiante
    ).order_by(
        models.Estudiante.id
    ).offset(skip)

    if limit is not None:
        consulta = consulta.limit(limit)

    return consulta.all()


# ---------------------------------------------------------------
# Asignaturas
# ---------------------------------------------------------------

# Endpoint 4 - crear asignatura
@app.post("/asignaturas", response_model=schemas.AsignaturaResponse)
def crear_asignatura(
    asignatura: schemas.AsignaturaCreate,
    db: Session = Depends(get_db)
):

    nueva = models.Asignatura(
        codigo=asignatura.codigo,
        nombre=asignatura.nombre,
        cupos=asignatura.cupos,
        cupos_disponibles=asignatura.cupos
    )

    db.add(nueva)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ya existe una asignatura con ese código"
        )

    db.refresh(nueva)

    return nueva


# Endpoint 5 - consultar asignaturas
@app.get("/asignaturas", response_model=list[schemas.AsignaturaResponse])
def listar_asignaturas(
    skip: int = 0,
    limit: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db)
):

    consulta = db.query(
        models.Asignatura
    ).order_by(
        models.Asignatura.id
    ).offset(skip)

    if limit is not None:
        consulta = consulta.limit(limit)

    return consulta.all()


# ---------------------------------------------------------------
# Matrículas
# ---------------------------------------------------------------

# Endpoint 6 - realizar matrícula
@app.post(
    "/matriculas",
    response_model=schemas.MatriculaResponse,
    summary="Matriculas"
)
def matricular(
    matricula: schemas.MatriculaCreate,
    db: Session = Depends(get_db)
):

    # Buscar estudiante
    estudiante = db.get(models.Estudiante, matricula.estudiante_id)

    if not estudiante:
        raise HTTPException(
            status_code=404,
            detail="Estudiante no encontrado"
        )

    # Buscar asignatura
    asignatura = db.get(models.Asignatura, matricula.asignatura_id)

    if not asignatura:
        raise HTTPException(
            status_code=404,
            detail="Asignatura no encontrada"
        )

    # Reducir cupo de forma atómica: el UPDATE solo afecta la fila si
    # todavía quedan cupos. Así dos solicitudes simultáneas nunca
    # sobrepasan el cupo (a diferencia de leer, restar y guardar).
    actualizadas = db.query(
        models.Asignatura
    ).filter(
        models.Asignatura.id == matricula.asignatura_id,
        models.Asignatura.cupos_disponibles > 0
    ).update(
        {models.Asignatura.cupos_disponibles:
         models.Asignatura.cupos_disponibles - 1},
        synchronize_session=False
    )

    if actualizadas == 0:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="No hay cupos disponibles"
        )

    # Crear matrícula (la restricción UNIQUE evita duplicados)
    nueva = models.Matricula(
        estudiante_id=matricula.estudiante_id,
        asignatura_id=matricula.asignatura_id
    )

    db.add(nueva)

    try:
        db.commit()
    except IntegrityError:
        # Se revierte también el descuento de cupo
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="El estudiante ya está matriculado en esta asignatura"
        )

    db.refresh(nueva)

    return nueva


# Endpoint 7 - consultar matrículas (con filtros opcionales)
@app.get(
    "/matriculas",
    response_model=list[schemas.MatriculaResponse],
    summary="Matriculas"
)
def listar_matriculas(
    estudiante_id: Optional[int] = None,
    asignatura_id: Optional[int] = None,
    skip: int = 0,
    limit: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db)
):

    consulta = db.query(models.Matricula)

    if estudiante_id is not None:
        consulta = consulta.filter(
            models.Matricula.estudiante_id == estudiante_id
        )

    if asignatura_id is not None:
        consulta = consulta.filter(
            models.Matricula.asignatura_id == asignatura_id
        )

    consulta = consulta.order_by(
        models.Matricula.id
    ).offset(skip)

    # Sin límite explícito se devuelven todas las matrículas
    if limit is not None:
        consulta = consulta.limit(limit)

    return consulta.all()


# Endpoint 8 - cancelar matrícula (libera el cupo)
@app.delete(
    "/matriculas",
    summary="Cancelar matricula con id"
)
def cancelar_matricula(
    matricula_id: int,
    db: Session = Depends(get_db)
):

    matricula = db.get(models.Matricula, matricula_id)

    if not matricula:
        raise HTTPException(
            status_code=404,
            detail="Matrícula no encontrada"
        )

    db.query(
        models.Asignatura
    ).filter(
        models.Asignatura.id == matricula.asignatura_id
    ).update(
        {models.Asignatura.cupos_disponibles:
         models.Asignatura.cupos_disponibles + 1},
        synchronize_session=False
    )

    db.delete(matricula)
    db.commit()

    return {"mensaje": "Matrícula cancelada"}
