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

def init_db():
    # Migraciones automáticas para PostgreSQL
    try:
        with engine.connect() as conn:
            if "sqlite" not in DATABASE_URL:
                # Eliminar carrera_id legado v1
                r = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='estudiantes' AND column_name='carrera_id'"))
                if r.fetchone():
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
                    r = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='estudiantes' AND column_name='{col}'"))
                    if not r.fetchone():
                        conn.execute(text(f"ALTER TABLE estudiantes ADD COLUMN {col} {tipo}"))
                        conn.commit()
                        print(f"✅ Migración: columna '{col}' agregada")
    except Exception as e:
        print(f"Info migración: {e}")

    Base.metadata.create_all(bind=engine)
