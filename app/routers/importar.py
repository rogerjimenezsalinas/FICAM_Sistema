from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Estudiante, Carrera, Materia, Inscripcion
import csv, io

router_importar = APIRouter(prefix="/importar", tags=["Importación"])

@router_importar.post("/estudiantes")
async def importar_estudiantes(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Solo se aceptan archivos .csv")
    contenido = await file.read()
    texto = contenido.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(texto))

    def norm(d): return {k.strip().lower(): v.strip() for k, v in d.items()}
    resultados = {"creados": 0, "actualizados": 0, "inscritos": 0, "errores": []}

    for i, row in enumerate(reader, start=2):
        row = norm(row)
        try:
            for campo in ["nombre", "apellido", "codigo"]:
                if not row.get(campo): raise ValueError(f"Campo '{campo}' vacío")

            # Carreras (puede venir como "IM" o "IM,IMT")
            carrera_codigos = [x.strip().upper() for x in row.get("carrera_codigo","").split(",") if x.strip()]
            carreras = []
            for cod in carrera_codigos:
                c = db.query(Carrera).filter(Carrera.codigo == cod).first()
                if not c: raise ValueError(f"Carrera '{cod}' no existe")
                carreras.append(c)

            email = row.get("email") or f"{row['codigo'].lower()}@ficam.edu.bo"
            est = db.query(Estudiante).filter(Estudiante.codigo == row["codigo"]).first()
            if est:
                est.nombre = row["nombre"].title()
                est.apellido = row["apellido"].title()
                est.semestre_actual = int(row.get("semestre_actual") or 1)
                est.activo = True
                if carreras:
                    # Agregar carreras sin duplicar
                    for car in carreras:
                        if car not in est.carreras: est.carreras.append(car)
                resultados["actualizados"] += 1
            else:
                est = Estudiante(
                    nombre=row["nombre"].title(), apellido=row["apellido"].title(),
                    codigo=row["codigo"], email=email,
                    semestre_actual=int(row.get("semestre_actual") or 1), activo=True
                )
                est.carreras = carreras
                db.add(est)
                db.flush()
                resultados["creados"] += 1

            # Inscripción opcional
            mat_cod = row.get("materia_codigo","").strip()
            sem_insc = row.get("semestre_inscripcion","").strip()
            if mat_cod and sem_insc:
                materia = db.query(Materia).filter(Materia.codigo == mat_cod.upper()).first()
                if not materia: raise ValueError(f"Materia '{mat_cod}' no existe")
                existe = db.query(Inscripcion).filter(
                    Inscripcion.estudiante_id == est.id,
                    Inscripcion.materia_id == materia.id,
                    Inscripcion.semestre == sem_insc
                ).first()
                if not existe:
                    db.add(Inscripcion(estudiante_id=est.id, materia_id=materia.id, semestre=sem_insc))
                    resultados["inscritos"] += 1
        except Exception as e:
            resultados["errores"].append({"fila": i, "error": str(e), "datos": dict(row)})

    db.commit()
    return resultados

@router_importar.get("/plantilla")
def descargar_plantilla():
    plantilla = (
        "nombre,apellido,codigo,semestre_actual,carrera_codigo,materia_codigo,semestre_inscripcion\n"
        "Ana,Mamani,20240001,1,IM,AL101,2024-I\n"
        "Luis,Quispe,20240002,3,IMT,ED101,2024-I\n"
        "Maria,Flores,20240003,5,IB,BM201,2024-I\n"
        "Pedro,Ticona,20240004,2,\"IM,IB\",,\n"
    )
    return Response(content=plantilla, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=plantilla_estudiantes.csv"})
