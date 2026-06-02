"""Datos de prueba para inicializar la base de datos"""
from datetime import date, timedelta
import random

def seed(db):
    from app.models import Carrera, Materia, Estudiante, Inscripcion, Asistencia, Trabajo, Calificacion

    if db.query(Carrera).count() > 0:
        return  # ya tiene datos

    # Carreras
    carreras = [
        Carrera(nombre="Ingeniería Mecánica", codigo="IM", activa=True),
        Carrera(nombre="Ingeniería Mecatrónica", codigo="IMT", activa=True),
        Carrera(nombre="Ingeniería Biomédica", codigo="IB", activa=True),
    ]
    db.add_all(carreras); db.commit()
    for c in carreras: db.refresh(c)

    # Materias
    materias_data = [
        ("Álgebra Lineal", "AL101", 4, 1, carreras[0].id),
        ("Termodinámica", "TD201", 5, 3, carreras[0].id),
        ("Resistencia de Materiales", "RM301", 5, 4, carreras[0].id),
        ("Electrónica Digital", "ED101", 4, 2, carreras[1].id),
        ("Control Automático", "CA301", 5, 5, carreras[1].id),
        ("Biomecánica", "BM201", 4, 3, carreras[2].id),
        ("Señales Biomédicas", "SB301", 4, 5, carreras[2].id),
    ]
    materias = []
    for nm, cd, cr, sm, cid in materias_data:
        m = Materia(nombre=nm, codigo=cd, creditos=cr, semestre=sm, carrera_id=cid)
        db.add(m); db.commit(); db.refresh(m)
        materias.append(m)

    # Estudiantes
    nombres = ["Ana","Luis","María","Carlos","Sofía","Diego","Valentina","Andrés","Paula","Jorge"]
    apellidos = ["Mamani","Quispe","Flores","Condori","Gutierrez","Tarqui","Vargas","Limachi","Chávez","Rojas"]
    estudiantes = []
    for i, (n, a) in enumerate(zip(nombres, apellidos)):
        car = carreras[i % 3]
        e = Estudiante(nombre=n, apellido=a, codigo=f"2024{i+1:04d}",
                       email=f"{n.lower()}.{a.lower()}@ficam.edu.bo",
                       semestre_actual=(i % 6) + 1, carrera_id=car.id)
        db.add(e); db.commit(); db.refresh(e)
        estudiantes.append(e)

    # Inscripciones (cada estudiante en 2-3 materias)
    semestre = "2024-I"
    inscripciones = []
    for est in estudiantes:
        mats_carrera = [m for m in materias if m.carrera_id == est.carrera_id]
        for mat in mats_carrera[:2]:
            insc = Inscripcion(estudiante_id=est.id, materia_id=mat.id, semestre=semestre)
            db.add(insc)
            inscripciones.append((est, mat))
    db.commit()

    # Asistencia (últimas 4 semanas, lunes y miércoles)
    hoy = date.today()
    fechas_clase = []
    for semana in range(4):
        lunes = hoy - timedelta(days=hoy.weekday() + 7 * semana)
        fechas_clase.append(lunes)
        fechas_clase.append(lunes + timedelta(days=2))

    for est, mat in inscripciones:
        for fecha in fechas_clase:
            presente = random.random() > 0.15  # 85% asistencia
            a = Asistencia(estudiante_id=est.id, materia_id=mat.id,
                           fecha=fecha, presente=presente)
            db.add(a)
    db.commit()

    # Trabajos (2-3 por materia)
    tipos = ["tarea", "proyecto", "examen", "practica"]
    trabajos = []
    for mat in materias:
        for j in range(3):
            t = Trabajo(
                titulo=f"{['Tarea','Proyecto','Examen'][j]} {j+1} - {mat.nombre}",
                descripcion=f"Actividad evaluativa de {mat.nombre}",
                materia_id=mat.id,
                fecha_entrega=hoy - timedelta(days=j*14),
                puntaje_maximo=100.0,
                tipo=tipos[j % len(tipos)]
            )
            db.add(t); db.commit(); db.refresh(t)
            trabajos.append(t)

    # Calificaciones
    for trabajo in trabajos:
        inscritos = [(e, m) for e, m in inscripciones if m.id == trabajo.materia_id]
        for est, _ in inscritos:
            if random.random() > 0.1:  # 90% entrega
                puntaje = round(random.gauss(72, 15), 1)
                puntaje = max(0, min(100, puntaje))
                c = Calificacion(estudiante_id=est.id, trabajo_id=trabajo.id, puntaje=puntaje)
                db.add(c)
    db.commit()
    print("✅ Datos de prueba cargados correctamente")
