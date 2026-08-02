from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, Text, ForeignKey, UniqueConstraint, Table
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

# Tabla intermedia: un estudiante puede pertenecer a varias carreras
estudiante_carrera = Table(
    "estudiante_carrera", Base.metadata,
    Column("estudiante_id", Integer, ForeignKey("estudiantes.id", ondelete="CASCADE"), primary_key=True),
    Column("carrera_id", Integer, ForeignKey("carreras.id", ondelete="CASCADE"), primary_key=True)
)

class Gestion(Base):
    """Período académico (ej: '1/2026' = enero-junio, '2/2026' = julio-diciembre).
    Las materias son fijas; lo que cambia gestión a gestión es quién las cursa."""
    __tablename__ = "gestiones"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(20), unique=True, nullable=False)   # "1/2026"
    nombre = Column(String(100), nullable=True)                # "Enero - Junio 2026"
    fecha_inicio = Column(Date, nullable=True)
    fecha_fin = Column(Date, nullable=True)
    activa = Column(Boolean, default=False)   # gestión vigente por defecto en la UI
    cerrada = Column(Boolean, default=False)  # ya se hizo el cierre/promoción, no admite más cambios
    inscripciones = relationship("Inscripcion", back_populates="gestion")
    trabajos = relationship("Trabajo", back_populates="gestion")
    asistencias = relationship("Asistencia", back_populates="gestion")

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    nombre_completo = Column(String(150), nullable=True)
    rol = Column(String(20), default="docente")   # admin | docente
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)


class Carrera(Base):
    __tablename__ = "carreras"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), unique=True, nullable=False)
    codigo = Column(String(10), unique=True, nullable=False)
    activa = Column(Boolean, default=True)
    materias = relationship("Materia", back_populates="carrera", cascade="all, delete-orphan")
    estudiantes = relationship("Estudiante", secondary=estudiante_carrera, back_populates="carreras")

class Materia(Base):
    __tablename__ = "materias"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    codigo = Column(String(10), unique=True, nullable=False)
    creditos = Column(Integer, default=4)
    semestre = Column(Integer, nullable=False)
    carrera_id = Column(Integer, ForeignKey("carreras.id"), nullable=False)
    carrera = relationship("Carrera", back_populates="materias")
    inscripciones = relationship("Inscripcion", back_populates="materia", cascade="all, delete-orphan")
    asistencias = relationship("Asistencia", back_populates="materia", cascade="all, delete-orphan")
    trabajos = relationship("Trabajo", back_populates="materia", cascade="all, delete-orphan")

class Estudiante(Base):
    __tablename__ = "estudiantes"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    codigo = Column(String(20), unique=True, nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    celular = Column(String(20), nullable=True)
    carnet = Column(String(20), nullable=True)
    correo_electronico = Column(String(150), nullable=True)
    semestre_actual = Column(Integer, default=1)
    activo = Column(Boolean, default=True)
    # Relación muchos a muchos con carreras
    carreras = relationship("Carrera", secondary=estudiante_carrera, back_populates="estudiantes")
    inscripciones = relationship("Inscripcion", back_populates="estudiante", cascade="all, delete-orphan")
    asistencias = relationship("Asistencia", back_populates="estudiante", cascade="all, delete-orphan")
    calificaciones = relationship("Calificacion", back_populates="estudiante", cascade="all, delete-orphan")

class Inscripcion(Base):
    __tablename__ = "inscripciones"
    __table_args__ = (UniqueConstraint("estudiante_id", "materia_id", "gestion_id", name="uq_inscripcion"),)
    id = Column(Integer, primary_key=True, index=True)
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id", ondelete="CASCADE"), nullable=False)
    materia_id = Column(Integer, ForeignKey("materias.id", ondelete="CASCADE"), nullable=False)
    gestion_id = Column(Integer, ForeignKey("gestiones.id", ondelete="CASCADE"), nullable=False)
    semestre = Column(String(10), nullable=True)  # heredado v2, se mantiene en sincronía con gestion.codigo
    fecha_inscripcion = Column(DateTime, default=datetime.utcnow)
    activa = Column(Boolean, default=True)
    # estado del cursante en ESTA gestión para ESTA materia
    estado = Column(String(15), default="cursando")   # cursando | aprobado | reprobado | retirado
    repitente = Column(Boolean, default=False)        # ya cursó esta materia antes y reprobó
    nota_final = Column(Float, nullable=True)
    estudiante = relationship("Estudiante", back_populates="inscripciones")
    materia = relationship("Materia", back_populates="inscripciones")
    gestion = relationship("Gestion", back_populates="inscripciones")

class Asistencia(Base):
    __tablename__ = "asistencias"
    __table_args__ = (UniqueConstraint("estudiante_id", "materia_id", "gestion_id", "fecha", name="uq_asistencia"),)
    id = Column(Integer, primary_key=True, index=True)
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id", ondelete="CASCADE"), nullable=False)
    materia_id = Column(Integer, ForeignKey("materias.id", ondelete="CASCADE"), nullable=False)
    gestion_id = Column(Integer, ForeignKey("gestiones.id", ondelete="CASCADE"), nullable=False)
    fecha = Column(Date, nullable=False)
    presente = Column(Boolean, default=True)
    observacion = Column(String(200))
    estudiante = relationship("Estudiante", back_populates="asistencias")
    materia = relationship("Materia", back_populates="asistencias")
    gestion = relationship("Gestion", back_populates="asistencias")

class Trabajo(Base):
    __tablename__ = "trabajos"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(200), nullable=False)
    descripcion = Column(Text)
    materia_id = Column(Integer, ForeignKey("materias.id", ondelete="CASCADE"), nullable=False)
    gestion_id = Column(Integer, ForeignKey("gestiones.id", ondelete="CASCADE"), nullable=False)
    fecha_entrega = Column(Date, nullable=False)
    puntaje_maximo = Column(Float, default=100.0)
    tipo = Column(String(50), default="tarea")
    materia = relationship("Materia", back_populates="trabajos")
    gestion = relationship("Gestion", back_populates="trabajos")
    calificaciones = relationship("Calificacion", back_populates="trabajo", cascade="all, delete-orphan")

class Calificacion(Base):
    __tablename__ = "calificaciones"
    __table_args__ = (UniqueConstraint("estudiante_id", "trabajo_id", name="uq_calificacion"),)
    id = Column(Integer, primary_key=True, index=True)
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id", ondelete="CASCADE"), nullable=False)
    trabajo_id = Column(Integer, ForeignKey("trabajos.id", ondelete="CASCADE"), nullable=False)
    puntaje = Column(Float, nullable=False)
    fecha_registro = Column(DateTime, default=datetime.utcnow)
    comentario = Column(String(300))
    estudiante = relationship("Estudiante", back_populates="calificaciones")
    trabajo = relationship("Trabajo", back_populates="calificaciones")
