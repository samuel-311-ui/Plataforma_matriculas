from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import Field


class EstudianteCreate(BaseModel):

    nombre: str
    correo: EmailStr


class EstudianteResponse(BaseModel):

    id: int
    nombre: str
    correo: str

    class Config:
        from_attributes = True


class AsignaturaCreate(BaseModel):

    codigo: str
    nombre: str
    cupos: int = Field(gt=0)


class AsignaturaResponse(BaseModel):

    id: int
    codigo: str
    nombre: str
    cupos: int
    cupos_disponibles: int

    class Config:
        from_attributes = True


class MatriculaCreate(BaseModel):

    estudiante_id: int
    asignatura_id: int


class MatriculaResponse(BaseModel):

    id: int
    estudiante_id: int
    asignatura_id: int

    class Config:
        from_attributes = True