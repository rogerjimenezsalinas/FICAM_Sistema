from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from app.database import init_db, SessionLocal
from app.routers.academico import router_carreras, router_materias, router_estudiantes, router_inscripciones
from app.routers.gestion import router_asistencia, router_trabajos, router_calificaciones, router_estadisticas
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Cargar datos de prueba solo si está habilitado
    if os.getenv("SEED_DATA", "true").lower() == "true":
        from app.seed import seed
        db = SessionLocal()
        try:
            seed(db)
        finally:
            db.close()
    yield

app = FastAPI(
    title="FICAM — Sistema Académico",
    version="1.0.0",
    lifespan=lifespan
)

# API routes
app.include_router(router_carreras, prefix="/api")
app.include_router(router_materias, prefix="/api")
app.include_router(router_estudiantes, prefix="/api")
app.include_router(router_inscripciones, prefix="/api")
app.include_router(router_asistencia, prefix="/api")
app.include_router(router_trabajos, prefix="/api")
app.include_router(router_calificaciones, prefix="/api")
app.include_router(router_estadisticas, prefix="/api")

# Servir frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.get("/health")
async def health():
    return {"status": "ok", "app": "FICAM Sistema Académico"}
