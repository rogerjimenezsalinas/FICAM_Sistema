from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.database import get_db
from app.models import Asistencia, Trabajo, Calificacion, Inscripcion, Estudiante, Materia
from app.schemas import (AsistenciaCreate, AsistenciaOut, AsistenciaMasiva,
                          TrabajoCreate, TrabajoOut, CalificacionCreate, CalificacionOut)
from typing import List
from datetime import date

# ── ASISTENCIA ────────────────────────────────────────────
router_asistencia = APIRouter(prefix="/asistencia", tags=["Asistencia"])

@router_asistencia.get("/", response_model=List[AsistenciaOut])
def listar_asistencia(materia_id: int = None, estudiante_id: int = None,
                       fecha: date = None, db: Session = Depends(get_db)):
    q = db.query(Asistencia)
    if materia_id: q = q.filter(Asistencia.materia_id == materia_id)
    if estudiante_id: q = q.filter(Asistencia.estudiante_id == estudiante_id)
    if fecha: q = q.filter(Asistencia.fecha == fecha)
    return q.order_by(Asistencia.fecha.desc()).all()

@router_asistencia.post("/", response_model=AsistenciaOut)
def registrar_asistencia(data: AsistenciaCreate, db: Session = Depends(get_db)):
    existe = db.query(Asistencia).filter(
        Asistencia.estudiante_id == data.estudiante_id,
        Asistencia.materia_id == data.materia_id,
        Asistencia.fecha == data.fecha
    ).first()
    if existe:
        for k, v in data.model_dump().items(): setattr(existe, k, v)
        db.commit(); db.refresh(existe); return existe
    a = Asistencia(**data.model_dump())
    db.add(a); db.commit(); db.refresh(a); return a

@router_asistencia.post("/masiva")
def asistencia_masiva(data: AsistenciaMasiva, db: Session = Depends(get_db)):
    registrados = 0
    for r in data.registros:
        existe = db.query(Asistencia).filter(
            Asistencia.estudiante_id == r["estudiante_id"],
            Asistencia.materia_id == data.materia_id,
            Asistencia.fecha == data.fecha
        ).first()
        if existe:
            existe.presente = r.get("presente", True)
            existe.observacion = r.get("observacion")
        else:
            a = Asistencia(
                estudiante_id=r["estudiante_id"],
                materia_id=data.materia_id,
                fecha=data.fecha,
                presente=r.get("presente", True),
                observacion=r.get("observacion")
            )
            db.add(a)
        registrados += 1
    db.commit()
    return {"registrados": registrados}

@router_asistencia.get("/resumen/{materia_id}")
def resumen_asistencia(materia_id: int, semestre: str = None, db: Session = Depends(get_db)):
    from sqlalchemy import Integer as SAInteger
    q = db.query(
        Estudiante.id,
        Estudiante.nombre,
        Estudiante.apellido,
        Estudiante.codigo,
        func.count(Asistencia.id).label("total"),
        func.sum(func.cast(Asistencia.presente, SAInteger)).label("presentes")
    ).join(Asistencia, Asistencia.estudiante_id == Estudiante.id)\
     .filter(Asistencia.materia_id == materia_id)\
     .group_by(Estudiante.id, Estudiante.nombre, Estudiante.apellido, Estudiante.codigo)

    resultados = []
    for row in q.all():
        total = row.total or 0
        presentes = row.presentes or 0
        resultados.append({
            "estudiante_id": row.id,
            "nombre": f"{row.nombre} {row.apellido}",
            "codigo": row.codigo,
            "total_clases": total,
            "presentes": presentes,
            "ausentes": total - presentes,
            "porcentaje": round((presentes / total * 100) if total > 0 else 0, 1)
        })
    return sorted(resultados, key=lambda x: x["porcentaje"], reverse=True)

# ── TRABAJOS ──────────────────────────────────────────────
router_trabajos = APIRouter(prefix="/trabajos", tags=["Trabajos"])

@router_trabajos.get("/", response_model=List[TrabajoOut])
def listar_trabajos(materia_id: int = None, db: Session = Depends(get_db)):
    q = db.query(Trabajo)
    if materia_id: q = q.filter(Trabajo.materia_id == materia_id)
    return q.order_by(Trabajo.fecha_entrega.desc()).all()

@router_trabajos.post("/", response_model=TrabajoOut)
def crear_trabajo(data: TrabajoCreate, db: Session = Depends(get_db)):
    t = Trabajo(**data.model_dump())
    db.add(t); db.commit(); db.refresh(t); return t

@router_trabajos.put("/{id}", response_model=TrabajoOut)
def actualizar_trabajo(id: int, data: TrabajoCreate, db: Session = Depends(get_db)):
    t = db.query(Trabajo).filter(Trabajo.id == id).first()
    if not t: raise HTTPException(404, "Trabajo no encontrado")
    for k, v in data.model_dump().items(): setattr(t, k, v)
    db.commit(); db.refresh(t); return t

@router_trabajos.delete("/{id}")
def eliminar_trabajo(id: int, db: Session = Depends(get_db)):
    t = db.query(Trabajo).filter(Trabajo.id == id).first()
    if not t: raise HTTPException(404, "Trabajo no encontrado")
    db.delete(t); db.commit(); return {"ok": True}

# ── CALIFICACIONES ────────────────────────────────────────
router_calificaciones = APIRouter(prefix="/calificaciones", tags=["Calificaciones"])

@router_calificaciones.get("/", response_model=List[CalificacionOut])
def listar_calificaciones(trabajo_id: int = None, estudiante_id: int = None,
                           db: Session = Depends(get_db)):
    q = db.query(Calificacion)
    if trabajo_id: q = q.filter(Calificacion.trabajo_id == trabajo_id)
    if estudiante_id: q = q.filter(Calificacion.estudiante_id == estudiante_id)
    return q.all()

@router_calificaciones.post("/", response_model=CalificacionOut)
def registrar_calificacion(data: CalificacionCreate, db: Session = Depends(get_db)):
    existe = db.query(Calificacion).filter(
        Calificacion.estudiante_id == data.estudiante_id,
        Calificacion.trabajo_id == data.trabajo_id
    ).first()
    if existe:
        existe.puntaje = data.puntaje
        existe.comentario = data.comentario
        db.commit(); db.refresh(existe); return existe
    c = Calificacion(**data.model_dump())
    db.add(c); db.commit(); db.refresh(c); return c

@router_calificaciones.post("/masiva")
def calificaciones_masivas(trabajo_id: int, calificaciones: List[dict], db: Session = Depends(get_db)):
    registradas = 0
    for cal in calificaciones:
        existe = db.query(Calificacion).filter(
            Calificacion.estudiante_id == cal["estudiante_id"],
            Calificacion.trabajo_id == trabajo_id
        ).first()
        if existe:
            existe.puntaje = cal["puntaje"]
            existe.comentario = cal.get("comentario")
        else:
            c = Calificacion(estudiante_id=cal["estudiante_id"], trabajo_id=trabajo_id,
                             puntaje=cal["puntaje"], comentario=cal.get("comentario"))
            db.add(c)
        registradas += 1
    db.commit()
    return {"registradas": registradas}

# ── ESTADÍSTICAS ──────────────────────────────────────────
router_estadisticas = APIRouter(prefix="/estadisticas", tags=["Estadísticas"])

@router_estadisticas.get("/materia/{materia_id}")
def stats_materia(materia_id: int, db: Session = Depends(get_db)):
    materia = db.query(Materia).filter(Materia.id == materia_id).first()
    if not materia: raise HTTPException(404, "Materia no encontrada")

    inscritos = db.query(Inscripcion).filter(
        Inscripcion.materia_id == materia_id, Inscripcion.activa == True).count()
    trabajos = db.query(Trabajo).filter(Trabajo.materia_id == materia_id).all()
    total_trabajos = len(trabajos)

    # Promedio general de calificaciones
    promedios = []
    for t in trabajos:
        cals = db.query(Calificacion).filter(Calificacion.trabajo_id == t.id).all()
        if cals:
            avg = sum(c.puntaje for c in cals) / len(cals)
            promedios.append({"trabajo": t.titulo, "tipo": t.tipo, "promedio": round(avg, 1),
                              "entregados": len(cals), "total_inscritos": inscritos})

    # Asistencia general
    total_reg = db.query(Asistencia).filter(Asistencia.materia_id == materia_id).count()
    presentes = db.query(Asistencia).filter(
        Asistencia.materia_id == materia_id, Asistencia.presente == True).count()

    return {
        "materia": materia.nombre,
        "codigo": materia.codigo,
        "inscritos": inscritos,
        "total_trabajos": total_trabajos,
        "trabajos_detalle": promedios,
        "total_registros_asistencia": total_reg,
        "porcentaje_asistencia_global": round((presentes / total_reg * 100) if total_reg > 0 else 0, 1)
    }

@router_estadisticas.get("/estudiante/{estudiante_id}")
def stats_estudiante(estudiante_id: int, db: Session = Depends(get_db)):
    est = db.query(Estudiante).filter(Estudiante.id == estudiante_id).first()
    if not est: raise HTTPException(404, "Estudiante no encontrado")

    inscripciones = db.query(Inscripcion).filter(
        Inscripcion.estudiante_id == estudiante_id, Inscripcion.activa == True).all()

    resumen = []
    for insc in inscripciones:
        total_cls = db.query(Asistencia).filter(
            Asistencia.materia_id == insc.materia_id,
            Asistencia.estudiante_id == estudiante_id).count()
        presentes = db.query(Asistencia).filter(
            Asistencia.materia_id == insc.materia_id,
            Asistencia.estudiante_id == estudiante_id,
            Asistencia.presente == True).count()
        cals = db.query(Calificacion).join(Trabajo).filter(
            Trabajo.materia_id == insc.materia_id,
            Calificacion.estudiante_id == estudiante_id).all()
        promedio = round(sum(c.puntaje for c in cals) / len(cals), 1) if cals else 0

        resumen.append({
            "materia_id": insc.materia_id,
            "materia": insc.materia.nombre if insc.materia else "",
            "semestre": insc.semestre,
            "asistencia_pct": round((presentes / total_cls * 100) if total_cls > 0 else 0, 1),
            "trabajos_calificados": len(cals),
            "promedio": promedio
        })

    return {
        "estudiante": f"{est.nombre} {est.apellido}",
        "codigo": est.codigo,
        "carrera": est.carrera.nombre if est.carrera else "",
        "materias": resumen
    }

@router_estadisticas.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    from app.models import Carrera
    return {
        "total_estudiantes": db.query(Estudiante).filter(Estudiante.activo == True).count(),
        "total_materias": db.query(Materia).count(),
        "total_carreras": db.query(Carrera).count(),
        "total_inscripciones": db.query(Inscripcion).filter(Inscripcion.activa == True).count(),
        "total_trabajos": db.query(Trabajo).count(),
        "total_calificaciones": db.query(Calificacion).count(),
        "total_asistencias": db.query(Asistencia).count(),
    }
