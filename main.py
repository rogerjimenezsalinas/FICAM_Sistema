from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from app.database import init_db, SessionLocal
from app.routers.academico import router_carreras, router_materias, router_estudiantes, router_inscripciones
from app.routers.gestion import router_asistencia, router_trabajos, router_calificaciones, router_estadisticas
from app.routers.gestiones import router_gestiones
from app.routers.importar import router_importar
from app.routers.backup import router_backup
from app.routers.auth import router_auth
from app.auth import get_current_user
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if os.getenv("SEED_DATA", "true").lower() == "true":
        from app.seed import seed
        db = SessionLocal()
        try: seed(db)
        finally: db.close()
    yield

app = FastAPI(title="FICAM — Sistema Académico", version="2.0.0", lifespan=lifespan)

app.include_router(router_auth, prefix="/api")

for router in [router_carreras, router_materias, router_estudiantes, router_inscripciones,
               router_gestiones,
               router_asistencia, router_trabajos, router_calificaciones, router_estadisticas,
               router_importar, router_backup]:
    app.include_router(router, prefix="/api", dependencies=[Depends(get_current_user)])

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root(): return FileResponse("static/index.html")

@app.get("/health")
async def health(): return {"status": "ok", "version": "2.0"}
