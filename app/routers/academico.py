from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Carrera, Materia, Estudiante, Inscripcion, estudiante_carrera
from app.schemas import (CarreraCreate, CarreraOut, MateriaCreate, MateriaOut,
                          EstudianteCreate, EstudianteOut, InscripcionCreate, InscripcionOut,
                          InscripcionUpdate)
from typing import List

# ── CARRERAS ──────────────────────────────────────────────
router_carreras = APIRouter(prefix="/carreras", tags=["Carreras"])

@router_carreras.get("/", response_model=List[CarreraOut])
def listar_carreras(db: Session = Depends(get_db)):
    return db.query(Carrera).all()

@router_carreras.post("/", response_model=CarreraOut)
def crear_carrera(data: CarreraCreate, db: Session = Depends(get_db)):
    c = Carrera(**data.model_dump())
    db.add(c); db.commit(); db.refresh(c); return c

@router_carreras.put("/{id}", response_model=CarreraOut)
def actualizar_carrera(id: int, data: CarreraCreate, db: Session = Depends(get_db)):
    c = db.query(Carrera).filter(Carrera.id == id).first()
    if not c: raise HTTPException(404, "Carrera no encontrada")
    for k, v in data.model_dump().items(): setattr(c, k, v)
    db.commit(); db.refresh(c); return c

@router_carreras.delete("/{id}")
def eliminar_carrera(id: int, db: Session = Depends(get_db)):
    c = db.query(Carrera).filter(Carrera.id == id).first()
    if not c: raise HTTPException(404, "Carrera no encontrada")
    db.delete(c); db.commit()
    return {"ok": True}

# ── MATERIAS ──────────────────────────────────────────────
router_materias = APIRouter(prefix="/materias", tags=["Materias"])

@router_materias.get("/", response_model=List[MateriaOut])
def listar_materias(carrera_id: int = None, db: Session = Depends(get_db)):
    q = db.query(Materia)
    if carrera_id: q = q.filter(Materia.carrera_id == carrera_id)
    return q.all()

@router_materias.post("/", response_model=MateriaOut)
def crear_materia(data: MateriaCreate, db: Session = Depends(get_db)):
    m = Materia(**data.model_dump())
    db.add(m); db.commit(); db.refresh(m); return m

@router_materias.put("/{id}", response_model=MateriaOut)
def actualizar_materia(id: int, data: MateriaCreate, db: Session = Depends(get_db)):
    m = db.query(Materia).filter(Materia.id == id).first()
    if not m: raise HTTPException(404, "Materia no encontrada")
    for k, v in data.model_dump().items(): setattr(m, k, v)
    db.commit(); db.refresh(m); return m

@router_materias.delete("/{id}")
def eliminar_materia(id: int, db: Session = Depends(get_db)):
    m = db.query(Materia).filter(Materia.id == id).first()
    if not m: raise HTTPException(404, "Materia no encontrada")
    db.delete(m); db.commit()
    return {"ok": True}

# ── ESTUDIANTES ───────────────────────────────────────────
router_estudiantes = APIRouter(prefix="/estudiantes", tags=["Estudiantes"])

@router_estudiantes.get("/", response_model=List[EstudianteOut])
def listar_estudiantes(carrera_id: int = None, activo: bool = True, db: Session = Depends(get_db)):
    q = db.query(Estudiante).filter(Estudiante.activo == activo)
    if carrera_id:
        q = q.filter(Estudiante.carreras.any(Carrera.id == carrera_id))
    return q.all()

@router_estudiantes.post("/", response_model=EstudianteOut)
def crear_estudiante(data: EstudianteCreate, db: Session = Depends(get_db)):
    carrera_ids = data.carrera_ids
    est_data = data.model_dump(exclude={"carrera_ids"})
    e = Estudiante(**est_data)
    if carrera_ids:
        carreras = db.query(Carrera).filter(Carrera.id.in_(carrera_ids)).all()
        e.carreras = carreras
    db.add(e); db.commit(); db.refresh(e); return e

@router_estudiantes.put("/{id}", response_model=EstudianteOut)
def actualizar_estudiante(id: int, data: EstudianteCreate, db: Session = Depends(get_db)):
    e = db.query(Estudiante).filter(Estudiante.id == id).first()
    if not e: raise HTTPException(404, "Estudiante no encontrado")
    carrera_ids = data.carrera_ids
    for k, v in data.model_dump(exclude={"carrera_ids"}).items(): setattr(e, k, v)
    if carrera_ids is not None:
        e.carreras = db.query(Carrera).filter(Carrera.id.in_(carrera_ids)).all()
    db.commit(); db.refresh(e); return e

@router_estudiantes.delete("/{id}")
def eliminar_estudiante(id: int, db: Session = Depends(get_db)):
    e = db.query(Estudiante).filter(Estudiante.id == id).first()
    if not e: raise HTTPException(404, "Estudiante no encontrado")
    e.activo = False; db.commit()
    return {"ok": True}

# ── INSCRIPCIONES ─────────────────────────────────────────
router_inscripciones = APIRouter(prefix="/inscripciones", tags=["Inscripciones"])

@router_inscripciones.get("/", response_model=List[InscripcionOut])
def listar_inscripciones(materia_id: int = None, gestion_id: int = None, semestre: str = None,
                          estudiante_id: int = None, estado: str = None, db: Session = Depends(get_db)):
    q = db.query(Inscripcion).filter(Inscripcion.activa == True)
    if materia_id: q = q.filter(Inscripcion.materia_id == materia_id)
    if gestion_id: q = q.filter(Inscripcion.gestion_id == gestion_id)
    if semestre: q = q.filter(Inscripcion.semestre == semestre)  # compat: filtrar por texto histórico
    if estudiante_id: q = q.filter(Inscripcion.estudiante_id == estudiante_id)
    if estado: q = q.filter(Inscripcion.estado == estado)
    return q.all()

@router_inscripciones.post("/", response_model=InscripcionOut)
def inscribir(data: InscripcionCreate, db: Session = Depends(get_db)):
    from app.models import Gestion
    existe = db.query(Inscripcion).filter(
        Inscripcion.estudiante_id == data.estudiante_id,
        Inscripcion.materia_id == data.materia_id,
        Inscripcion.gestion_id == data.gestion_id
    ).first()
    if existe: raise HTTPException(400, "Estudiante ya inscrito en esta materia para esta gestión")
    gestion = db.query(Gestion).filter(Gestion.id == data.gestion_id).first()
    if not gestion: raise HTTPException(400, "Gestión no válida")
    i = Inscripcion(**data.model_dump(), semestre=gestion.codigo)
    db.add(i); db.commit(); db.refresh(i); return i

@router_inscripciones.put("/{id}", response_model=InscripcionOut)
def actualizar_inscripcion(id: int, data: InscripcionUpdate, db: Session = Depends(get_db)):
    """Cambiar estado (cursando/aprobado/reprobado/retirado), marcar repitente, o registrar nota final."""
    i = db.query(Inscripcion).filter(Inscripcion.id == id).first()
    if not i: raise HTTPException(404, "Inscripción no encontrada")
    for k, v in data.model_dump(exclude_unset=True).items(): setattr(i, k, v)
    db.commit(); db.refresh(i); return i

@router_inscripciones.delete("/{id}")
def dar_baja(id: int, db: Session = Depends(get_db)):
    i = db.query(Inscripcion).filter(Inscripcion.id == id).first()
    if not i: raise HTTPException(404, "Inscripción no encontrada")
    i.activa = False
    i.estado = "retirado"
    db.commit()
    return {"ok": True}
