import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ficam.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _col_existe(conn, tabla, col):
    r = conn.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name=:t AND column_name=:c"
    ), {"t": tabla, "c": col})
    return r.fetchone() is not None

def _tabla_existe(conn, tabla):
    r = conn.execute(text(
        "SELECT table_name FROM information_schema.tables WHERE table_name=:t"
    ), {"t": tabla})
    return r.fetchone() is not None

def _migrar_gestiones(conn):
    """Introduce el concepto de Gestión Académica (período: '1/2026', '2/2026', ...)
    en bases de datos que ya tenían datos con el modelo v2 anterior (sin gestiones)."""
    # 1) Agregar columna gestion_id (nullable por ahora) a las tablas que dependen de un período
    for tabla in ("inscripciones", "trabajos", "asistencias"):
        if _tabla_existe(conn, tabla) and not _col_existe(conn, tabla, "gestion_id"):
            conn.execute(text(f"ALTER TABLE {tabla} ADD COLUMN gestion_id INTEGER"))
            conn.commit()
            print(f"✅ Migración: columna 'gestion_id' agregada a {tabla}")

    # 2) Nuevas columnas de estado del cursante en inscripciones
    for col, tipo in [("estado", "VARCHAR(15) DEFAULT 'cursando'"),
                       ("repitente", "BOOLEAN DEFAULT false"),
                       ("nota_final", "FLOAT")]:
        if _tabla_existe(conn, "inscripciones") and not _col_existe(conn, "inscripciones", col):
            conn.execute(text(f"ALTER TABLE inscripciones ADD COLUMN {col} {tipo}"))
            conn.commit()
            print(f"✅ Migración: columna '{col}' agregada a inscripciones")

    # 3) Backfill: si hay filas con gestion_id NULL, se necesita al menos una Gestion
    if not _tabla_existe(conn, "gestiones"):
        return  # create_all la creará después; el backfill se completa en el próximo arranque

    pendientes = 0
    for tabla in ("inscripciones", "trabajos", "asistencias"):
        if _tabla_existe(conn, tabla):
            r = conn.execute(text(f"SELECT count(*) FROM {tabla} WHERE gestion_id IS NULL"))
            pendientes += r.scalar() or 0
    if pendientes == 0:
        return

    # Determinar/crear la gestión por defecto para los datos históricos
    r = conn.execute(text("SELECT id FROM gestiones ORDER BY id LIMIT 1"))
    row = r.fetchone()
    if row:
        gestion_default_id = row[0]
    else:
        # Si las inscripciones antiguas tenían un único valor de 'semestre', se usa como código
        codigo = "1/2026"
        if _col_existe(conn, "inscripciones", "semestre"):
            r = conn.execute(text("SELECT DISTINCT semestre FROM inscripciones WHERE semestre IS NOT NULL"))
            valores = [x[0] for x in r.fetchall() if x[0]]
            if len(valores) == 1:
                codigo = valores[0]
        conn.execute(text(
            "INSERT INTO gestiones (codigo, nombre, activa, cerrada) VALUES (:c, :n, true, false)"
        ), {"c": codigo, "n": f"Migración de datos previos ({codigo})"})
        conn.commit()
        r = conn.execute(text("SELECT id FROM gestiones WHERE codigo=:c"), {"c": codigo})
        gestion_default_id = r.fetchone()[0]
        print(f"✅ Migración: gestión '{codigo}' creada para datos históricos")

    for tabla in ("inscripciones", "trabajos", "asistencias"):
        if _tabla_existe(conn, tabla):
            conn.execute(text(f"UPDATE {tabla} SET gestion_id=:g WHERE gestion_id IS NULL"), {"g": gestion_default_id})
    conn.commit()
    print("✅ Migración: registros históricos asignados a la gestión por defecto")

    # 4) Restricciones únicas correctas (por gestión, no por texto de semestre/fecha suelta)
    try:
        conn.execute(text("ALTER TABLE inscripciones DROP CONSTRAINT IF EXISTS uq_inscripcion"))
        conn.execute(text(
            "ALTER TABLE inscripciones ADD CONSTRAINT uq_inscripcion UNIQUE (estudiante_id, materia_id, gestion_id)"))
        conn.execute(text("ALTER TABLE asistencias DROP CONSTRAINT IF EXISTS uq_asistencia"))
        conn.execute(text(
            "ALTER TABLE asistencias ADD CONSTRAINT uq_asistencia UNIQUE (estudiante_id, materia_id, gestion_id, fecha)"))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Info migración (constraints): {e}")

def _crear_admin_inicial():
    """Si la tabla de usuarios está vacía, crea el administrador inicial.
    Configurable vía variables de entorno ADMIN_USERNAME / ADMIN_PASSWORD."""
    from app.models import Usuario
    from app.auth import hash_password
    db = SessionLocal()
    try:
        if db.query(Usuario).count() > 0:
            return
        username = os.getenv("ADMIN_USERNAME", "admin").strip().lower()
        password = os.getenv("ADMIN_PASSWORD")
        usando_default = password is None
        if usando_default:
            password = "FICAM2026!"
        admin = Usuario(username=username, password_hash=hash_password(password),
                         nombre_completo="Administrador", rol="admin", activo=True)
        db.add(admin); db.commit()
        print(f"✅ Usuario administrador inicial creado: '{username}'")
        if usando_default:
            print(f"⚠️  ADMIN_PASSWORD no estaba configurada — se usó la contraseña por defecto '{password}'. "
                  f"Inicia sesión y cámbiala de inmediato en Mi Cuenta.")
    except Exception as e:
        db.rollback()
        print(f"Info migración (admin inicial): {e}")
    finally:
        db.close()

def init_db():
    # Migraciones automáticas para PostgreSQL
    try:
        with engine.connect() as conn:
            if "sqlite" not in DATABASE_URL:
                # Eliminar carrera_id legado v1
                if _col_existe(conn, "estudiantes", "carrera_id"):
                    conn.execute(text("ALTER TABLE estudiantes DROP COLUMN IF EXISTS carrera_id"))
                    conn.commit()
                    print("✅ Migración: carrera_id eliminado")

                # Agregar campos nuevos si no existen
                nuevas_columnas = [
                    ("celular", "VARCHAR(20)"),
                    ("carnet", "VARCHAR(20)"),
                    ("correo_electronico", "VARCHAR(150)"),
                ]
                for col, tipo in nuevas_columnas:
                    if not _col_existe(conn, "estudiantes", col):
                        conn.execute(text(f"ALTER TABLE estudiantes ADD COLUMN {col} {tipo}"))
                        conn.commit()
                        print(f"✅ Migración: columna '{col}' agregada")
    except Exception as e:
        print(f"Info migración: {e}")

    # Crea tablas nuevas (incluye 'gestiones') antes del backfill de gestion_id
    Base.metadata.create_all(bind=engine)

    if "sqlite" not in DATABASE_URL:
        try:
            with engine.connect() as conn:
                _migrar_gestiones(conn)
        except Exception as e:
            print(f"Info migración (gestiones): {e}")

    _crear_admin_inicial()
