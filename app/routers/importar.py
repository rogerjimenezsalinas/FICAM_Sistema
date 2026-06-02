from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Estudiante, Carrera, Materia, Inscripcion
import csv
import io

router_importar = APIRouter(prefix="/importar", tags=["Importación"])

@router_importar.post("/estudiantes")
async def importar_estudiantes(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Importa estudiantes desde CSV con columnas:
    nombre, apellido, codigo, semestre_actual, carrera_codigo, materia_codigo (opcional), semestre_inscripcion (opcional)
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Solo se aceptan archivos .csv")

    contenido = await file.read()
    texto = contenido.decode("utf-8-sig")  # utf-8-sig maneja BOM de Excel
    reader = csv.DictReader(io.StringIO(texto))

    # Normalizar nombres de columnas (quitar espacios, minúsculas)
    def norm(d):
        return {k.strip().lower(): v.strip() for k, v in d.items()}

    resultados = {"creados": 0, "actualizados": 0, "inscritos": 0, "errores": []}

    for i, row in enumerate(reader, start=2):  # fila 2 = primera de datos
        row = norm(row)
        try:
            # Validar campos obligatorios
            for campo in ["nombre", "apellido", "codigo", "carrera_codigo"]:
                if not row.get(campo):
                    raise ValueError(f"Campo '{campo}' vacío")

            # Buscar carrera
            carrera = db.query(Carrera).filter(
                Carrera.codigo == row["carrera_codigo"].upper()
            ).first()
            if not carrera:
                raise ValueError(f"Carrera '{row['carrera_codigo']}' no existe")

            # Generar email si no viene
            email = row.get("email") or f"{row['codigo'].lower()}@ficam.edu.bo"

            # Crear o actualizar estudiante
            est = db.query(Estudiante).filter(Estudiante.codigo == row["codigo"]).first()
            if est:
                est.nombre = row["nombre"].title()
                est.apellido = row["apellido"].title()
                est.semestre_actual = int(row.get("semestre_actual") or 1)
                est.carrera_id = carrera.id
                est.activo = True
                resultados["actualizados"] += 1
            else:
                est = Estudiante(
                    nombre=row["nombre"].title(),
                    apellido=row["apellido"].title(),
                    codigo=row["codigo"],
                    email=email,
                    semestre_actual=int(row.get("semestre_actual") or 1),
                    carrera_id=carrera.id,
                    activo=True
                )
                db.add(est)
                db.flush()  # obtener el id sin commit
                resultados["creados"] += 1

            # Inscripción opcional
            mat_cod = row.get("materia_codigo", "").strip()
            sem_insc = row.get("semestre_inscripcion", "").strip()
            if mat_cod and sem_insc:
                materia = db.query(Materia).filter(
                    Materia.codigo == mat_cod.upper()
                ).first()
                if not materia:
                    raise ValueError(f"Materia '{mat_cod}' no existe")
                existe = db.query(Inscripcion).filter(
                    Inscripcion.estudiante_id == est.id,
                    Inscripcion.materia_id == materia.id,
                    Inscripcion.semestre == sem_insc
                ).first()
                if not existe:
                    insc = Inscripcion(
                        estudiante_id=est.id,
                        materia_id=materia.id,
                        semestre=sem_insc
                    )
                    db.add(insc)
                    resultados["inscritos"] += 1

        except Exception as e:
            resultados["errores"].append({"fila": i, "error": str(e), "datos": row})

    db.commit()
    return resultados


@router_importar.get("/plantilla")
def descargar_plantilla():
    """Retorna una plantilla CSV de ejemplo"""
    from fastapi.responses import Response
    plantilla = (
        "nombre,apellido,codigo,semestre_actual,carrera_codigo,materia_codigo,semestre_inscripcion\n"
        "Ana,Mamani,20240001,1,IM,AL101,2024-I\n"
        "Luis,Quispe,20240002,3,IMT,ED101,2024-I\n"
        "Maria,Flores,20240003,5,IB,BM201,2024-I\n"
    )
    return Response(
        content=plantilla,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=plantilla_estudiantes.csv"}
    )
