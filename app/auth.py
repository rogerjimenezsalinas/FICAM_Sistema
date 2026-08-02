import os
import bcrypt
import jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.database import get_db

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "ficam-clave-por-defecto-CAMBIAR-en-produccion-2026")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "12"))

if SECRET_KEY == "ficam-clave-por-defecto-CAMBIAR-en-produccion-2026":
    print("⚠️  JWT_SECRET_KEY no configurada: usando clave por defecto (insegura). "
          "Define la variable de entorno JWT_SECRET_KEY en Render.")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def crear_token(usuario_id: int, username: str, rol: str) -> str:
    payload = {
        "sub": str(usuario_id),
        "username": username,
        "rol": rol,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    from app.models import Usuario
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "No autenticado: falta el token de acceso")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "La sesión expiró, vuelve a iniciar sesión")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Token inválido")
    usuario = db.query(Usuario).filter(Usuario.id == int(payload["sub"])).first()
    if not usuario or not usuario.activo:
        raise HTTPException(401, "Usuario no válido o desactivado")
    return usuario


def requiere_admin(usuario=Depends(get_current_user)):
    if usuario.rol != "admin":
        raise HTTPException(403, "Esta acción requiere rol de administrador")
    return usuario
