from fastapi import FastAPI
from fastapi import Depends
from fastapi import HTTPException

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
    version="1.0"
)

#Endpoint 1- estado de la API
@app.get("/")
def inicio():

    return {
        "mensaje": "API de matrícula funcionando",
        "estado": "activo"
    }


# Endpoint 2 - crear estudiante

@app.post("/estudiantes")
def crear_estudiante(
    estudiante: schemas.EstudianteCreate,
    db: Session = Depends(get_db)
):

    nuevo = models.Estudiante(
        nombre=estudiante.nombre,
        correo=estudiante.correo
    )

    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    return nuevo



# Endpoint 3 - Consultar estudiantes


@app.get("/estudiantes")
def listar_estudiantes(
    db: Session = Depends(get_db)
):

    return db.query(
        models.Estudiante
    ).all()



# Endpoint 4 - crear asignatura


@app.post("/asignaturas")
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
    db.commit()
    db.refresh(nueva)

    return nueva



# Endpoint 5 - Consultar asignaturas


@app.get("/asignaturas")
def listar_asignaturas(
    db: Session = Depends(get_db)
):

    return db.query(
        models.Asignatura
    ).all()



# Endpoint 6 - Realizar matrícula


@app.post("/matriculas")
def matricular(
    matricula: schemas.MatriculaCreate,
    db: Session = Depends(get_db)
):

    # Buscar estudiante
    estudiante = db.query(
        models.Estudiante
    ).filter(
        models.Estudiante.id == matricula.estudiante_id
    ).first()

    if not estudiante:

        raise HTTPException(
            status_code=404,
            detail="Estudiante no encontrado"
        )


    # Buscar asignatura
    asignatura = db.query(
        models.Asignatura
    ).filter(
        models.Asignatura.id == matricula.asignatura_id
    ).first()

    if not asignatura:

        raise HTTPException(
            status_code=404,
            detail="Asignatura no encontrada"
        )


    # Verificar cupos
    if asignatura.cupos_disponibles <= 0:

        raise HTTPException(
            status_code=400,
            detail="No hay cupos disponibles"
        )


    # Crear matrícula
    nueva = models.Matricula(
        estudiante_id=matricula.estudiante_id,
        asignatura_id=matricula.asignatura_id
    )

    # Reducir cupo
    asignatura.cupos_disponibles -= 1

    db.add(nueva)
    db.commit()
    db.refresh(nueva)

    return nueva