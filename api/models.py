from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import ForeignKey
from sqlalchemy import UniqueConstraint

from sqlalchemy.orm import relationship

from .database import Base


class Estudiante(Base):

    __tablename__ = "estudiantes"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    nombre = Column(
        String(100),
        nullable=False
    )

    correo = Column(
        String(100),
        unique=True,
        nullable=False
    )

    matriculas = relationship(
        "Matricula",
        back_populates="estudiante"
    )


class Asignatura(Base):

    __tablename__ = "asignaturas"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    codigo = Column(
        String(20),
        unique=True,
        nullable=False
    )

    nombre = Column(
        String(100),
        nullable=False
    )

    cupos = Column(
        Integer,
        nullable=False
    )

    cupos_disponibles = Column(
        Integer,
        nullable=False
    )

    matriculas = relationship(
        "Matricula",
        back_populates="asignatura"
    )


class Matricula(Base):

    __tablename__ = "matriculas"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    estudiante_id = Column(
        Integer,
        ForeignKey("estudiantes.id"),
        nullable=False
    )

    asignatura_id = Column(
        Integer,
        ForeignKey("asignaturas.id"),
        nullable=False
    )

    estudiante = relationship(
        "Estudiante",
        back_populates="matriculas"
    )

    asignatura = relationship(
        "Asignatura",
        back_populates="matriculas"
    )

    __table_args__ = (
        UniqueConstraint(
            "estudiante_id",
            "asignatura_id"
        ),
    )