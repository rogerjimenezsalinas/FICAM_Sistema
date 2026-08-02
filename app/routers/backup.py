from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db, engine
from app.models import Carrera, Materia, Estudiante, Inscripcion, Asistencia, Trabajo, Calificacion, Gestion, Usuario, estudiante_carrera
from app.auth import requiere_admin
import json, csv, io
from datetime import datetime

router_backup = APIRouter(prefix="/backup", tags=["Backup"])

def serialize(obj):
    if isinstance(obj, (datetime,)): return obj.isoformat()
    from datetime import date
    if isinstance(obj, date): return obj.isoformat()
    return str(obj)

@router_backup.get("/json")
def backup_json(gestion_id: int = None, db: Session = Depends(get_db)):
    """Descarga backup completo en JSON. Si se pasa gestion_id, restringe inscripciones/
    asistencias/trabajos/calificaciones a esa gestión (útil para archivar un semestre cerrado),
    conservando siempre el catálogo completo de carreras/materias/estudiantes/gestiones."""
    q_insc = db.query(Inscripcion)
    q_trab = db.query(Trabajo)
    q_asis = db.query(Asistencia)
    if gestion_id:
        q_insc = q_insc.filter(Inscripcion.gestion_id == gestion_id)
        q_trab = q_trab.filter(Trabajo.gestion_id == gestion_id)
        q_asis = q_asis.filter(Asistencia.gestion_id == gestion_id)
    trabajo_ids = [t.id for t in q_trab.all()] if gestion_id else None

    data = {
        "generado": datetime.utcnow().isoformat(),
        "version": "2.0",
        "gestion_id_filtro": gestion_id,
        "gestiones": [
            {"id": g.id, "codigo": g.codigo, "nombre": g.nombre,
             "fecha_inicio": serialize(g.fecha_inicio) if g.fecha_inicio else None,
             "fecha_fin": serialize(g.fecha_fin) if g.fecha_fin else None,
             "activa": g.activa, "cerrada": g.cerrada}
            for g in db.query(Gestion).all()
        ],
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
             "codigo": e.codigo, "email": e.email, "celular": e.celular, "carnet": e.carnet,
             "correo_electronico": e.correo_electronico, "semestre_actual": e.semestre_actual,
             "activo": e.activo, "carrera_ids": [c.id for c in e.carreras]}
            for e in db.query(Estudiante).all()
        ],
        "inscripciones": [
            {"id": i.id, "estudiante_id": i.estudiante_id, "materia_id": i.materia_id,
             "gestion_id": i.gestion_id, "semestre": i.semestre, "activa": i.activa,
             "estado": i.estado, "repitente": i.repitente, "nota_final": i.nota_final,
             "fecha_inscripcion": serialize(i.fecha_inscripcion)}
            for i in q_insc.all()
        ],
        "asistencias": [
            {"id": a.id, "estudiante_id": a.estudiante_id, "materia_id": a.materia_id,
             "gestion_id": a.gestion_id, "fecha": serialize(a.fecha), "presente": a.presente,
             "observacion": a.observacion}
            for a in q_asis.all()
        ],
        "trabajos": [
            {"id": t.id, "titulo": t.titulo, "descripcion": t.descripcion,
             "materia_id": t.materia_id, "gestion_id": t.gestion_id,
             "fecha_entrega": serialize(t.fecha_entrega),
             "puntaje_maximo": t.puntaje_maximo, "tipo": t.tipo}
            for t in q_trab.all()
        ],
        "calificaciones": [
            {"id": c.id, "estudiante_id": c.estudiante_id, "trabajo_id": c.trabajo_id,
             "puntaje": c.puntaje, "comentario": c.comentario,
             "fecha_registro": serialize(c.fecha_registro)}
            for c in db.query(Calificacion).filter(
                Calificacion.trabajo_id.in_(trabajo_ids) if trabajo_ids is not None else True
            ).all()
        ],
    }
    sufijo = f"_gestion{gestion_id}" if gestion_id else ""
    nombre = f"ficam_backup{sufijo}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    content = json.dumps(data, ensure_ascii=False, indent=2)
    return StreamingResponse(
        iter([content]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={nombre}"}
    )


@router_backup.post("/restore")
async def restore_json(file: UploadFile = File(...), confirmar: bool = False, db: Session = Depends(get_db),
                        _admin: Usuario = Depends(requiere_admin)):
    """Restaura el sistema completo desde un backup JSON generado por /backup/json.
    ⚠️ DESTRUCTIVO: borra todos los datos actuales antes de restaurar. Requiere confirmar=true.
    No acepta backups parciales (con gestion_id_filtro) para evitar restaurar un sistema incompleto."""
    if not confirmar:
        raise HTTPException(400, "Debes confirmar esta operación (confirmar=true) — borrará todos los datos actuales")
    if not file.filename.endswith(".json"):
        raise HTTPException(400, "Solo se aceptan archivos .json")

    contenido = await file.read()
    try:
        data = json.loads(contenido.decode("utf-8-sig"))
    except Exception as e:
        raise HTTPException(400, f"El archivo no es un JSON válido: {e}")

    if data.get("gestion_id_filtro"):
        raise HTTPException(400, "Este backup está filtrado por una sola gestión; no se puede usar para restaurar el sistema completo")

    requeridas = ["carreras", "materias", "estudiantes", "inscripciones", "asistencias", "trabajos", "calificaciones"]
    faltantes = [k for k in requeridas if k not in data]
    if faltantes:
        raise HTTPException(400, f"El backup no tiene las claves esperadas: {faltantes}")

    def fecha(v):
        from datetime import date
        return date.fromisoformat(v) if v else None
    def fechahora(v):
        return datetime.fromisoformat(v) if v else None

    try:
        # Borrar todo en orden seguro por dependencias (hijos primero)
        db.query(Calificacion).delete()
        db.query(Asistencia).delete()
        db.query(Trabajo).delete()
        db.query(Inscripcion).delete()
        db.execute(estudiante_carrera.delete())
        db.query(Estudiante).delete()
        db.query(Materia).delete()
        db.query(Carrera).delete()
        db.query(Gestion).delete()
        db.commit()

        # Restaurar preservando IDs originales (para no romper las relaciones)
        for g in data.get("gestiones", []):
            db.add(Gestion(id=g["id"], codigo=g["codigo"], nombre=g.get("nombre"),
                            fecha_inicio=fecha(g.get("fecha_inicio")), fecha_fin=fecha(g.get("fecha_fin")),
                            activa=g.get("activa", False), cerrada=g.get("cerrada", False)))
        db.commit()

        for c in data["carreras"]:
            db.add(Carrera(id=c["id"], nombre=c["nombre"], codigo=c["codigo"], activa=c.get("activa", True)))
        db.commit()

        for m in data["materias"]:
            db.add(Materia(id=m["id"], nombre=m["nombre"], codigo=m["codigo"], creditos=m.get("creditos", 4),
                            semestre=m["semestre"], carrera_id=m["carrera_id"]))
        db.commit()

        for e in data["estudiantes"]:
            est = Estudiante(id=e["id"], nombre=e["nombre"], apellido=e["apellido"], codigo=e["codigo"],
                              email=e["email"], celular=e.get("celular"), carnet=e.get("carnet"),
                              correo_electronico=e.get("correo_electronico"),
                              semestre_actual=e.get("semestre_actual", 1), activo=e.get("activo", True))
            db.add(est); db.flush()
            if e.get("carrera_ids"):
                est.carreras = db.query(Carrera).filter(Carrera.id.in_(e["carrera_ids"])).all()
        db.commit()

        for i in data["inscripciones"]:
            db.add(Inscripcion(id=i["id"], estudiante_id=i["estudiante_id"], materia_id=i["materia_id"],
                                gestion_id=i.get("gestion_id"), semestre=i.get("semestre"),
                                activa=i.get("activa", True), estado=i.get("estado", "cursando"),
                                repitente=i.get("repitente", False), nota_final=i.get("nota_final"),
                                fecha_inscripcion=fechahora(i.get("fecha_inscripcion")) or datetime.utcnow()))
        db.commit()

        for t in data["trabajos"]:
            db.add(Trabajo(id=t["id"], titulo=t["titulo"], descripcion=t.get("descripcion"),
                            materia_id=t["materia_id"], gestion_id=t.get("gestion_id"),
                            fecha_entrega=fecha(t["fecha_entrega"]),
                            puntaje_maximo=t.get("puntaje_maximo", 100.0), tipo=t.get("tipo", "tarea")))
        db.commit()

        for a in data["asistencias"]:
            db.add(Asistencia(id=a["id"], estudiante_id=a["estudiante_id"], materia_id=a["materia_id"],
                               gestion_id=a.get("gestion_id"), fecha=fecha(a["fecha"]),
                               presente=a.get("presente", True), observacion=a.get("observacion")))
        db.commit()

        for c in data["calificaciones"]:
            db.add(Calificacion(id=c["id"], estudiante_id=c["estudiante_id"], trabajo_id=c["trabajo_id"],
                                 puntaje=c["puntaje"], comentario=c.get("comentario"),
                                 fecha_registro=fechahora(c.get("fecha_registro")) or datetime.utcnow()))
        db.commit()

        # Reajustar las secuencias de autoincremento de Postgres para que sigan después del máximo id restaurado
        if "sqlite" not in str(engine.url):
            for tabla in ["gestiones", "carreras", "materias", "estudiantes", "inscripciones",
                          "trabajos", "asistencias", "calificaciones"]:
                db.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{tabla}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {tabla}), 1))"
                ))
            db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Error al restaurar: {e}")

    return {
        "ok": True,
        "restaurado": {k: len(data.get(k, [])) for k in
                        ["gestiones","carreras","materias","estudiantes","inscripciones","trabajos","asistencias","calificaciones"]}
    }

@router_backup.get("/csv/{tabla}")
def backup_csv(tabla: str, db: Session = Depends(get_db)):
    """Descarga una tabla específica en CSV"""
    tablas_validas = {
        "estudiantes": (Estudiante, ["id","codigo","nombre","apellido","email","celular","carnet","correo_electronico","semestre_actual","activo"]),
        "materias": (Materia, ["id","codigo","nombre","creditos","semestre","carrera_id"]),
        "carreras": (Carrera, ["id","codigo","nombre","activa"]),
        "gestiones": (Gestion, ["id","codigo","nombre","fecha_inicio","fecha_fin","activa","cerrada"]),
        "inscripciones": (Inscripcion, ["id","estudiante_id","materia_id","gestion_id","semestre","activa","estado","repitente","nota_final"]),
        "asistencias": (Asistencia, ["id","estudiante_id","materia_id","gestion_id","fecha","presente","observacion"]),
        "trabajos": (Trabajo, ["id","titulo","materia_id","gestion_id","fecha_entrega","puntaje_maximo","tipo"]),
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
        "gestiones": db.query(Gestion).count(),
        "carreras": db.query(Carrera).count(),
        "materias": db.query(Materia).count(),
        "estudiantes": db.query(Estudiante).filter(Estudiante.activo == True).count(),
        "inscripciones": db.query(Inscripcion).filter(Inscripcion.activa == True).count(),
        "asistencias": db.query(Asistencia).count(),
        "trabajos": db.query(Trabajo).count(),
        "calificaciones": db.query(Calificacion).count(),
        "ultima_actualizacion": datetime.utcnow().isoformat()
    }
