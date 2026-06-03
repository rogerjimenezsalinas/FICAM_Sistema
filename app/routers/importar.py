from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Estudiante, Carrera, Materia, Inscripcion
import csv, io, re

router_importar = APIRouter(prefix="/importar", tags=["Importación"])

def limpiar_nombre(texto):
    """Elimina números de CI pegados al nombre: 'Kevin Anderson -69674727' → 'Kevin Anderson'"""
    return re.sub(r'\s*-?\d{6,}', '', texto).strip()

@router_importar.post("/estudiantes")
async def importar_estudiantes(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Solo se aceptan archivos .csv")
    contenido = await file.read()
    # Intentar UTF-8 con BOM, luego latin-1
    try:
        texto = contenido.decode("utf-8-sig")
    except:
        texto = contenido.decode("latin-1")

    reader = csv.DictReader(io.StringIO(texto))
    def norm(d): return {k.strip().lower().replace(' ','_'): v.strip() for k, v in d.items() if k}

    resultados = {"creados": 0, "actualizados": 0, "inscritos": 0, "errores": []}

    for i, row in enumerate(reader, start=2):
        row = norm(row)
        try:
            # Limpiar nombre y apellido (quita CI pegados)
            nombre = limpiar_nombre(row.get("nombre",""))
            apellido = limpiar_nombre(row.get("apellido",""))
            codigo = row.get("codigo","").strip()

            if not nombre: raise ValueError("Campo 'nombre' vacío")
            if not apellido: raise ValueError("Campo 'apellido' vacío")
            if not codigo: raise ValueError("Campo 'codigo' vacío")

            # Carreras (acepta "IB" o "IM,IB")
            carrera_codigos = [x.strip().upper() for x in row.get("carrera_codigo","").split(",") if x.strip()]
            carreras = []
            for cod in carrera_codigos:
                c = db.query(Carrera).filter(Carrera.codigo == cod).first()
                if not c: raise ValueError(f"Carrera '{cod}' no existe en el sistema")
                carreras.append(c)

            email = row.get("email","").strip() or f"{codigo.lower()}@ficam.edu.bo"

            est = db.query(Estudiante).filter(Estudiante.codigo == codigo).first()
            if est:
                est.nombre = nombre.title()
                est.apellido = apellido.title()
                est.semestre_actual = int(row.get("semestre_actual") or 1)
                est.activo = True
                if row.get("celular","").strip(): est.celular = row["celular"].strip()
                if row.get("carnet","").strip(): est.carnet = row["carnet"].strip()
                if row.get("correo_electronico","").strip(): est.correo_electronico = row["correo_electronico"].strip()
                for car in carreras:
                    if car not in est.carreras: est.carreras.append(car)
                resultados["actualizados"] += 1
            else:
                est = Estudiante(
                    nombre=nombre.title(), apellido=apellido.title(),
                    codigo=codigo, email=email,
                    celular=row.get("celular","").strip() or None,
                    carnet=row.get("carnet","").strip() or None,
                    correo_electronico=row.get("correo_electronico","").strip() or None,
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

            db.commit()  # commit por fila para evitar rollback total

        except Exception as e:
            db.rollback()
            resultados["errores"].append({"fila": i, "error": str(e),
                "datos": f"{row.get('nombre','')} {row.get('apellido','')} / {row.get('codigo','')}"})

    return resultados

@router_importar.get("/plantilla")
def descargar_plantilla():
    plantilla = (
        "nombre,apellido,codigo,semestre_actual,carrera_codigo,celular,carnet,correo_electronico,materia_codigo,semestre_inscripcion\n"
        "Ana,Mamani,20240001,1,IM,70012345,9876543,ana.mamani@gmail.com,AL101,2024-I\n"
        "Luis,Quispe,20240002,3,IMT,70098765,1234567,luis.quispe@gmail.com,ED101,2024-I\n"
        "Maria,Flores,20240003,5,IB,,,maria@gmail.com,BM201,2024-I\n"
        "Pedro,Ticona,20240004,2,\"IM,IB\",,,,\n"
    )
    return Response(content=plantilla, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=plantilla_estudiantes.csv"})
