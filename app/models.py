from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class Carrera(Base):
    __tablename__ = "carreras"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), unique=True, nullable=False)
    codigo = Column(String(10), unique=True, nullable=False)
    activa = Column(Boolean, default=True)
    materias = relationship("Materia", back_populates="carrera")
    estudiantes = relationship("Estudiante", back_populates="carrera")

class Materia(Base):
    __tablename__ = "materias"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    codigo = Column(String(10), unique=True, nullable=False)
    creditos = Column(Integer, default=4)
    semestre = Column(Integer, nullable=False)
    carrera_id = Column(Integer, ForeignKey("carreras.id"), nullable=False)
    carrera = relationship("Carrera", back_populates="materias")
    inscripciones = relationship("Inscripcion", back_populates="materia")
    asistencias = relationship("Asistencia", back_populates="materia")
    trabajos = relationship("Trabajo", back_populates="materia")

class Estudiante(Base):
    __tablename__ = "estudiantes"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    codigo = Column(String(20), unique=True, nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    semestre_actual = Column(Integer, default=1)
    carrera_id = Column(Integer, ForeignKey("carreras.id"), nullable=False)
    activo = Column(Boolean, default=True)
    carrera = relationship("Carrera", back_populates="estudiantes")
    inscripciones = relationship("Inscripcion", back_populates="estudiante")
    asistencias = relationship("Asistencia", back_populates="estudiante")
    calificaciones = relationship("Calificacion", back_populates="estudiante")

class Inscripcion(Base):
    __tablename__ = "inscripciones"
    __table_args__ = (UniqueConstraint("estudiante_id", "materia_id", "semestre", name="uq_inscripcion"),)
    id = Column(Integer, primary_key=True, index=True)
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"), nullable=False)
    materia_id = Column(Integer, ForeignKey("materias.id"), nullable=False)
    semestre = Column(String(10), nullable=False)  # ej: "2024-I"
    fecha_inscripcion = Column(DateTime, default=datetime.utcnow)
    activa = Column(Boolean, default=True)
    estudiante = relationship("Estudiante", back_populates="inscripciones")
    materia = relationship("Materia", back_populates="inscripciones")

class Asistencia(Base):
    __tablename__ = "asistencias"
    __table_args__ = (UniqueConstraint("estudiante_id", "materia_id", "fecha", name="uq_asistencia"),)
    id = Column(Integer, primary_key=True, index=True)
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"), nullable=False)
    materia_id = Column(Integer, ForeignKey("materias.id"), nullable=False)
    fecha = Column(Date, nullable=False)
    presente = Column(Boolean, default=True)
    observacion = Column(String(200))
    estudiante = relationship("Estudiante", back_populates="asistencias")
    materia = relationship("Materia", back_populates="asistencias")

class Trabajo(Base):
    __tablename__ = "trabajos"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(200), nullable=False)
    descripcion = Column(Text)
    materia_id = Column(Integer, ForeignKey("materias.id"), nullable=False)
    fecha_entrega = Column(Date, nullable=False)
    puntaje_maximo = Column(Float, default=100.0)
    tipo = Column(String(50), default="tarea")  # tarea, proyecto, examen, practica
    materia = relationship("Materia", back_populates="trabajos")
    calificaciones = relationship("Calificacion", back_populates="trabajo")

class Calificacion(Base):
    __tablename__ = "calificaciones"
    __table_args__ = (UniqueConstraint("estudiante_id", "trabajo_id", name="uq_calificacion"),)
    id = Column(Integer, primary_key=True, index=True)
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"), nullable=False)
    trabajo_id = Column(Integer, ForeignKey("trabajos.id"), nullable=False)
    puntaje = Column(Float, nullable=False)
    fecha_registro = Column(DateTime, default=datetime.utcnow)
    comentario = Column(String(300))
    estudiante = relationship("Estudiante", back_populates="calificaciones")
    trabajo = relationship("Trabajo", back_populates="calificaciones")
