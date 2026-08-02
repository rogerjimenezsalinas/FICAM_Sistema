from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime

class CarreraBase(BaseModel):
    nombre: str
    codigo: str
    activa: bool = True

class CarreraCreate(CarreraBase): pass
class CarreraOut(CarreraBase):
    id: int
    class Config: from_attributes = True

class LoginRequest(BaseModel):
    username: str
    password: str

class UsuarioBase(BaseModel):
    nombre_completo: Optional[str] = None
    rol: str = "docente"
    activo: bool = True

class UsuarioCreate(UsuarioBase):
    username: str
    password: str

class UsuarioUpdate(UsuarioBase): pass

class UsuarioOut(UsuarioBase):
    id: int
    username: str
    class Config: from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut

class CambiarClave(BaseModel):
    password_actual: Optional[str] = None
    password_nueva: str

class GestionBase(BaseModel):
    codigo: str
    nombre: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    activa: bool = False
    cerrada: bool = False

class GestionCreate(GestionBase): pass
class GestionOut(GestionBase):
    id: int
    class Config: from_attributes = True

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

class EstudianteBase(BaseModel):
    nombre: str
    apellido: str
    codigo: str
    email: str
    celular: Optional[str] = None
    carnet: Optional[str] = None
    correo_electronico: Optional[str] = None
    semestre_actual: int = 1
    activo: bool = True

class EstudianteCreate(EstudianteBase):
    carrera_ids: List[int] = []

class EstudianteOut(EstudianteBase):
    id: int
    carreras: List[CarreraOut] = []
    class Config: from_attributes = True

class InscripcionCreate(BaseModel):
    estudiante_id: int
    materia_id: int
    gestion_id: int
    estado: str = "cursando"
    repitente: bool = False

class InscripcionUpdate(BaseModel):
    estado: Optional[str] = None
    repitente: Optional[bool] = None
    nota_final: Optional[float] = None
    activa: Optional[bool] = None

class InscripcionOut(BaseModel):
    id: int
    estudiante_id: int
    materia_id: int
    gestion_id: int
    semestre: Optional[str] = None
    activa: bool
    estado: str
    repitente: bool
    nota_final: Optional[float] = None
    estudiante: Optional[EstudianteOut] = None
    materia: Optional[MateriaOut] = None
    gestion: Optional[GestionOut] = None
    class Config: from_attributes = True

class AsistenciaCreate(BaseModel):
    estudiante_id: int
    materia_id: int
    gestion_id: int
    fecha: date
    presente: bool = True
    observacion: Optional[str] = None

class AsistenciaOut(AsistenciaCreate):
    id: int
    class Config: from_attributes = True

class TrabajoCreate(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    materia_id: int
    gestion_id: int
    fecha_entrega: date
    puntaje_maximo: float = 100.0
    tipo: str = "tarea"

class TrabajoOut(TrabajoCreate):
    id: int
    materia: Optional[MateriaOut] = None
    gestion: Optional[GestionOut] = None
    class Config: from_attributes = True

class CalificacionCreate(BaseModel):
    estudiante_id: int
    trabajo_id: int
    puntaje: float
    comentario: Optional[str] = None

class CalificacionOut(CalificacionCreate):
    id: int
    fecha_registro: datetime
    class Config: from_attributes = True

class AsistenciaMasiva(BaseModel):
    materia_id: int
    gestion_id: int
    fecha: date
    registros: List[dict]
