from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.models import Carrera, Materia, Estudiante, Inscripcion, Asistencia, Trabajo, Calificacion
import json, csv, io
from datetime import datetime

router_backup = APIRouter(prefix="/backup", tags=["Backup"])

def serialize(obj):
    if isinstance(obj, (datetime,)): return obj.isoformat()
    from datetime import date
    if isinstance(obj, date): return obj.isoformat()
    return str(obj)

@router_backup.get("/json")
def backup_json(db: Session = Depends(get_db)):
    """Descarga backup completo en JSON"""
    data = {
        "generado": datetime.utcnow().isoformat(),
        "version": "1.0",
        "carreras": [
            {"id": c.id, "nombre": c.nombre, "codigo": c.codigo, "activa": c.activa}
            for c in db.query(Carrera).all()
        ],
        "materias": [
            {"id": m.id, "nombre": m.nombre, "codigo": m.codigo,
             "creditos": m.creditos, "semestre": m.semestre, "carrera_id": m.carrera_id}
            for m in db.query(Materia).all()
        ],
        "estudiantes": [
            {"id": e.id, "nombre": e.nombre, "apellido": e.apellido,
             "codigo": e.codigo, "email": e.email, "semestre_actual": e.semestre_actual,
             "activo": e.activo, "carrera_ids": [c.id for c in e.carreras]}
            for e in db.query(Estudiante).all()
        ],
        "inscripciones": [
            {"id": i.id, "estudiante_id": i.estudiante_id, "materia_id": i.materia_id,
             "semestre": i.semestre, "activa": i.activa,
             "fecha_inscripcion": serialize(i.fecha_inscripcion)}
            for i in db.query(Inscripcion).all()
        ],
        "asistencias": [
            {"id": a.id, "estudiante_id": a.estudiante_id, "materia_id": a.materia_id,
             "fecha": serialize(a.fecha), "presente": a.presente, "observacion": a.observacion}
            for a in db.query(Asistencia).all()
        ],
        "trabajos": [
            {"id": t.id, "titulo": t.titulo, "descripcion": t.descripcion,
             "materia_id": t.materia_id, "fecha_entrega": serialize(t.fecha_entrega),
             "puntaje_maximo": t.puntaje_maximo, "tipo": t.tipo}
            for t in db.query(Trabajo).all()
        ],
        "calificaciones": [
            {"id": c.id, "estudiante_id": c.estudiante_id, "trabajo_id": c.trabajo_id,
             "puntaje": c.puntaje, "comentario": c.comentario,
             "fecha_registro": serialize(c.fecha_registro)}
            for c in db.query(Calificacion).all()
        ],
    }
    nombre = f"ficam_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    content = json.dumps(data, ensure_ascii=False, indent=2)
    return StreamingResponse(
        iter([content]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={nombre}"}
    )

@router_backup.get("/csv/{tabla}")
def backup_csv(tabla: str, db: Session = Depends(get_db)):
    """Descarga una tabla específica en CSV"""
    tablas_validas = {
        "estudiantes": (Estudiante, ["id","codigo","nombre","apellido","email","semestre_actual","activo"]),
        "materias": (Materia, ["id","codigo","nombre","creditos","semestre","carrera_id"]),
        "carreras": (Carrera, ["id","codigo","nombre","activa"]),
        "inscripciones": (Inscripcion, ["id","estudiante_id","materia_id","semestre","activa"]),
        "asistencias": (Asistencia, ["id","estudiante_id","materia_id","fecha","presente","observacion"]),
        "calificaciones": (Calificacion, ["id","estudiante_id","trabajo_id","puntaje","comentario"]),
    }
    if tabla not in tablas_validas:
        return JSONResponse({"error": f"Tabla '{tabla}' no válida"}, status_code=400)

    modelo, campos = tablas_validas[tabla]
    registros = db.query(modelo).all()

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=campos)
    writer.writeheader()
    for r in registros:
        writer.writerow({c: serialize(getattr(r, c, "")) for c in campos})

    nombre = f"ficam_{tabla}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={nombre}"}
    )

@router_backup.get("/estadisticas")
def estadisticas_backup(db: Session = Depends(get_db)):
    """Resumen de registros por tabla"""
    return {
        "carreras": db.query(Carrera).count(),
        "materias": db.query(Materia).count(),
        "estudiantes": db.query(Estudiante).filter(Estudiante.activo == True).count(),
        "inscripciones": db.query(Inscripcion).filter(Inscripcion.activa == True).count(),
        "asistencias": db.query(Asistencia).count(),
        "trabajos": db.query(Trabajo).count(),
        "calificaciones": db.query(Calificacion).count(),
        "ultima_actualizacion": datetime.utcnow().isoformat()
    }
