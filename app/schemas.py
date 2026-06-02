from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime

# ── CARRERA ──────────────────────────────────────────────
class CarreraBase(BaseModel):
    nombre: str
    codigo: str
    activa: bool = True

class CarreraCreate(CarreraBase): pass
class CarreraOut(CarreraBase):
    id: int
    class Config: from_attributes = True

# ── MATERIA ───────────────────────────────────────────────
class MateriaBase(BaseModel):
    nombre: str
    codigo: str
    creditos: int = 4
    semestre: int
    carrera_id: int

class MateriaCreate(MateriaBase): pass
class MateriaOut(MateriaBase):
    id: int
    carrera: Optional[CarreraOut] = None
    class Config: from_attributes = True

# ── ESTUDIANTE ────────────────────────────────────────────
class EstudianteBase(BaseModel):
    nombre: str
    apellido: str
    codigo: str
    email: str
    semestre_actual: int = 1
    carrera_id: int
    activo: bool = True

class EstudianteCreate(EstudianteBase): pass
class EstudianteOut(EstudianteBase):
    id: int
    carrera: Optional[CarreraOut] = None
    class Config: from_attributes = True

# ── INSCRIPCION ───────────────────────────────────────────
class InscripcionCreate(BaseModel):
    estudiante_id: int
    materia_id: int
    semestre: str

class InscripcionOut(BaseModel):
    id: int
    estudiante_id: int
    materia_id: int
    semestre: str
    activa: bool
    estudiante: Optional[EstudianteOut] = None
    materia: Optional[MateriaOut] = None
    class Config: from_attributes = True

# ── ASISTENCIA ────────────────────────────────────────────
class AsistenciaCreate(BaseModel):
    estudiante_id: int
    materia_id: int
    fecha: date
    presente: bool = True
    observacion: Optional[str] = None

class AsistenciaOut(AsistenciaCreate):
    id: int
    class Config: from_attributes = True

class AsistenciaMasiva(BaseModel):
    materia_id: int
    fecha: date
    registros: List[dict]  # [{estudiante_id, presente, observacion}]

# ── TRABAJO ───────────────────────────────────────────────
class TrabajoCreate(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    materia_id: int
    fecha_entrega: date
    puntaje_maximo: float = 100.0
    tipo: str = "tarea"

class TrabajoOut(TrabajoCreate):
    id: int
    materia: Optional[MateriaOut] = None
    class Config: from_attributes = True

# ── CALIFICACION ──────────────────────────────────────────
class CalificacionCreate(BaseModel):
    estudiante_id: int
    trabajo_id: int
    puntaje: float
    comentario: Optional[str] = None

class CalificacionOut(CalificacionCreate):
    id: int
    fecha_registro: datetime
    class Config: from_attributes = True

# ── ESTADÍSTICAS ──────────────────────────────────────────
class EstadisticaEstudiante(BaseModel):
    estudiante_id: int
    nombre_completo: str
    materia: str
    semestre: str
    total_clases: int
    presentes: int
    porcentaje_asistencia: float
    trabajos_entregados: int
    promedio_calificaciones: float
