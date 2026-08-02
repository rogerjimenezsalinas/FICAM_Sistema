from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import Gestion, Inscripcion, Estudiante, Materia, Usuario
from app.schemas import GestionCreate, GestionOut
from app.auth import requiere_admin

router_gestiones = APIRouter(prefix="/gestiones", tags=["Gestiones Académicas"])


@router_gestiones.get("/", response_model=List[GestionOut])
def listar_gestiones(db: Session = Depends(get_db)):
    return db.query(Gestion).order_by(Gestion.codigo.desc()).all()


@router_gestiones.get("/actual", response_model=Optional[GestionOut])
def gestion_actual(db: Session = Depends(get_db)):
    """Devuelve la gestión marcada como activa (la que usa la UI por defecto)."""
    return db.query(Gestion).filter(Gestion.activa == True).first()


@router_gestiones.post("/", response_model=GestionOut)
def crear_gestion(data: GestionCreate, db: Session = Depends(get_db)):
    existe = db.query(Gestion).filter(Gestion.codigo == data.codigo).first()
    if existe:
        raise HTTPException(400, f"Ya existe una gestión con el código '{data.codigo}'")
    g = Gestion(**data.model_dump())
    db.add(g); db.commit(); db.refresh(g)
    return g


@router_gestiones.put("/{id}", response_model=GestionOut)
def actualizar_gestion(id: int, data: GestionCreate, db: Session = Depends(get_db)):
    g = db.query(Gestion).filter(Gestion.id == id).first()
    if not g: raise HTTPException(404, "Gestión no encontrada")
    for k, v in data.model_dump().items(): setattr(g, k, v)
    db.commit(); db.refresh(g)
    return g


@router_gestiones.post("/{id}/activar", response_model=GestionOut)
def activar_gestion(id: int, db: Session = Depends(get_db)):
    """Marca esta gestión como la activa (usada por defecto en toda la UI) y desactiva las demás."""
    g = db.query(Gestion).filter(Gestion.id == id).first()
    if not g: raise HTTPException(404, "Gestión no encontrada")
    db.query(Gestion).update({Gestion.activa: False})
    g.activa = True
    db.commit(); db.refresh(g)
    return g


@router_gestiones.delete("/{id}")
def eliminar_gestion(id: int, db: Session = Depends(get_db), _admin: Usuario = Depends(requiere_admin)):
    g = db.query(Gestion).filter(Gestion.id == id).first()
    if not g: raise HTTPException(404, "Gestión no encontrada")
    if g.inscripciones or g.trabajos or g.asistencias:
        raise HTTPException(400, "No se puede eliminar: esta gestión tiene inscripciones, trabajos o asistencias registradas")
    db.delete(g); db.commit()
    return {"ok": True}


@router_gestiones.get("/{id}/resumen")
def resumen_gestion(id: int, db: Session = Depends(get_db)):
    """Conteo de inscripciones por estado, útil antes de cerrar una gestión."""
    g = db.query(Gestion).filter(Gestion.id == id).first()
    if not g: raise HTTPException(404, "Gestión no encontrada")
    inscripciones = db.query(Inscripcion).filter(Inscripcion.gestion_id == id, Inscripcion.activa == True).all()
    conteo = {"cursando": 0, "aprobado": 0, "reprobado": 0, "retirado": 0}
    for i in inscripciones:
        conteo[i.estado] = conteo.get(i.estado, 0) + 1
    return {"gestion": g.codigo, "total_inscripciones": len(inscripciones), "por_estado": conteo}


@router_gestiones.get("/{origen_id}/repitentes-preview")
def preview_repitentes(origen_id: int, destino_id: int, db: Session = Depends(get_db)):
    """Lista quiénes se trasladarían como repitentes de origen_id -> destino_id, sin ejecutar el traslado."""
    reprobados = db.query(Inscripcion).filter(
        Inscripcion.gestion_id == origen_id, Inscripcion.estado == "reprobado", Inscripcion.activa == True
    ).all()
    resultado = []
    for i in reprobados:
        ya_en_destino = db.query(Inscripcion).filter(
            Inscripcion.gestion_id == destino_id,
            Inscripcion.estudiante_id == i.estudiante_id,
            Inscripcion.materia_id == i.materia_id
        ).first()
        resultado.append({
            "estudiante_id": i.estudiante_id,
            "estudiante": f"{i.estudiante.apellido}, {i.estudiante.nombre}" if i.estudiante else "",
            "codigo": i.estudiante.codigo if i.estudiante else "",
            "materia_id": i.materia_id,
            "materia": i.materia.nombre if i.materia else "",
            "ya_inscrito_en_destino": ya_en_destino is not None
        })
    return sorted(resultado, key=lambda x: x["estudiante"].lower())


@router_gestiones.post("/{origen_id}/promover/{destino_id}")
def promover_repitentes(origen_id: int, destino_id: int, db: Session = Depends(get_db),
                         _admin: Usuario = Depends(requiere_admin)):
    """Traslada automáticamente a la gestión destino a todos los estudiantes 'reprobado' en la gestión
    origen, como repitentes de la misma materia. Los 'aprobado' y 'retirado' NO se trasladan
    (correctamente salen de la lista de esa materia). Es idempotente: no duplica si ya se corrió antes."""
    origen = db.query(Gestion).filter(Gestion.id == origen_id).first()
    destino = db.query(Gestion).filter(Gestion.id == destino_id).first()
    if not origen or not destino:
        raise HTTPException(404, "Gestión de origen o destino no encontrada")

    reprobados = db.query(Inscripcion).filter(
        Inscripcion.gestion_id == origen_id, Inscripcion.estado == "reprobado", Inscripcion.activa == True
    ).all()

    trasladados, ya_existian = 0, 0
    for i in reprobados:
        existe = db.query(Inscripcion).filter(
            Inscripcion.gestion_id == destino_id,
            Inscripcion.estudiante_id == i.estudiante_id,
            Inscripcion.materia_id == i.materia_id
        ).first()
        if existe:
            ya_existian += 1
            continue
        nueva = Inscripcion(
            estudiante_id=i.estudiante_id, materia_id=i.materia_id, gestion_id=destino_id,
            semestre=destino.codigo, estado="cursando", repitente=True, activa=True
        )
        db.add(nueva)
        trasladados += 1
    db.commit()
    return {
        "gestion_origen": origen.codigo, "gestion_destino": destino.codigo,
        "repitentes_trasladados": trasladados, "ya_existian_en_destino": ya_existian
    }
