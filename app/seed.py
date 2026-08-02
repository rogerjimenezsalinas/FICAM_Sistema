from datetime import date, timedelta
import random

def seed(db):
    from app.models import Carrera, Materia, Estudiante, Inscripcion, Asistencia, Trabajo, Calificacion, Gestion
    if db.query(Carrera).count() > 0:
        return

    gestion = Gestion(codigo="1/2026", nombre="Enero - Junio 2026", activa=True)
    db.add(gestion); db.commit(); db.refresh(gestion)

    carreras = [
        Carrera(nombre="Ingeniería Mecánica", codigo="IM"),
        Carrera(nombre="Ingeniería Mecatrónica", codigo="IMT"),
        Carrera(nombre="Ingeniería Biomédica", codigo="IB"),
    ]
    db.add_all(carreras); db.commit()
    for c in carreras: db.refresh(c)

    materias_data = [
        ("Álgebra Lineal","AL101",4,1,carreras[0].id),
        ("Termodinámica","TD201",5,3,carreras[0].id),
        ("Electrónica Digital","ED101",4,2,carreras[1].id),
        ("Control Automático","CA301",5,5,carreras[1].id),
        ("Biomecánica","BM201",4,3,carreras[2].id),
    ]
    materias = []
    for nm,cd,cr,sm,cid in materias_data:
        m = Materia(nombre=nm,codigo=cd,creditos=cr,semestre=sm,carrera_id=cid)
        db.add(m); db.commit(); db.refresh(m); materias.append(m)

    nombres = ["Ana","Luis","María","Carlos","Sofía","Diego","Valentina","Andrés","Paula","Jorge"]
    apellidos = ["Mamani","Quispe","Flores","Condori","Gutierrez","Tarqui","Vargas","Limachi","Chávez","Rojas"]
    estudiantes = []
    for i,(n,a) in enumerate(zip(nombres,apellidos)):
        car = carreras[i%3]
        e = Estudiante(nombre=n,apellido=a,codigo=f"2024{i+1:04d}",
                       email=f"{n.lower()}.{a.lower()}@ficam.edu.bo",
                       semestre_actual=(i%6)+1,activo=True)
        e.carreras = [car]
        db.add(e); db.commit(); db.refresh(e); estudiantes.append(e)

    inscripciones = []
    for est in estudiantes:
        mats = [m for m in materias if m.carrera_id == est.carreras[0].id][:2]
        for mat in mats:
            insc = Inscripcion(estudiante_id=est.id,materia_id=mat.id,gestion_id=gestion.id,
                                semestre=gestion.codigo,estado="cursando")
            db.add(insc); inscripciones.append((est,mat))
    db.commit()

    hoy = date.today()
    fechas = [hoy-timedelta(days=hoy.weekday()+7*s+d) for s in range(4) for d in [0,2]]
    for est,mat in inscripciones:
        for fecha in fechas:
            db.add(Asistencia(estudiante_id=est.id,materia_id=mat.id,gestion_id=gestion.id,
                               fecha=fecha,presente=random.random()>0.15))
    db.commit()

    trabajos = []
    for mat in materias:
        for j in range(3):
            t = Trabajo(titulo=f"{'Tarea Proyecto Examen'.split()[j]} {j+1} - {mat.nombre}",
                       materia_id=mat.id,gestion_id=gestion.id,fecha_entrega=hoy-timedelta(days=j*14),
                       puntaje_maximo=100.0,tipo=['tarea','proyecto','examen'][j])
            db.add(t); db.commit(); db.refresh(t); trabajos.append(t)

    for trab in trabajos:
        inscritos = [(e,m) for e,m in inscripciones if m.id==trab.materia_id]
        for est,_ in inscritos:
            if random.random()>0.1:
                db.add(Calificacion(estudiante_id=est.id,trabajo_id=trab.id,
                                    puntaje=round(max(0,min(100,random.gauss(72,15))),1)))
    db.commit()
    print("✅ Datos de prueba cargados")
