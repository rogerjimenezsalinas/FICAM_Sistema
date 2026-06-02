# FICAM — Sistema Académico

Sistema de gestión académica para la Facultad de Ingeniería.

## Módulos
- Gestión de carreras y materias
- Registro de estudiantes e inscripciones por semestre
- Control de asistencia (individual y masiva)
- Registro de trabajos y calificaciones
- Estadísticas por materia y por estudiante

## Despliegue en Railway

### 1. Subir a GitHub
```bash
git init
git add .
git commit -m "Sistema FICAM v1.0"
git remote add origin https://github.com/TU_USUARIO/ficam.git
git push -u origin main
```

### 2. Desplegar en Railway
1. Ir a https://railway.app y crear cuenta con GitHub
2. Clic en "New Project" → "Deploy from GitHub repo"
3. Seleccionar el repositorio `ficam`
4. Railway detecta el Dockerfile automáticamente

### 3. Agregar PostgreSQL
1. En el proyecto Railway → "Add Service" → "PostgreSQL"
2. Railway automáticamente crea la variable DATABASE_URL
3. El sistema la detecta y usa PostgreSQL en vez de SQLite

### 4. Variables de entorno (opcionales)
- `SEED_DATA=false` → desactiva los datos de prueba en producción
- `DATABASE_URL` → se configura automáticamente con PostgreSQL de Railway

## Desarrollo local
```bash
pip install -r requirements.txt
uvicorn main:app --reload
# Abrir http://localhost:8000
```
