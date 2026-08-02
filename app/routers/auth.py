from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Usuario
from app.schemas import LoginRequest, TokenResponse, UsuarioCreate, UsuarioUpdate, UsuarioOut, CambiarClave
from app.auth import hash_password, verify_password, crear_token, get_current_user, requiere_admin

router_auth = APIRouter(prefix="/auth", tags=["Autenticación"])


@router_auth.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    username = data.username.strip().lower()
    usuario = db.query(Usuario).filter(Usuario.username == username).first()
    if not usuario or not usuario.activo or not verify_password(data.password, usuario.password_hash):
        raise HTTPException(401, "Usuario o contraseña incorrectos")
    token = crear_token(usuario.id, usuario.username, usuario.rol)
    return {"access_token": token, "token_type": "bearer", "usuario": usuario}


@router_auth.get("/me", response_model=UsuarioOut)
def me(usuario: Usuario = Depends(get_current_user)):
    return usuario


@router_auth.post("/cambiar-clave")
def cambiar_clave(data: CambiarClave, usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.password_actual is not None and not verify_password(data.password_actual, usuario.password_hash):
        raise HTTPException(400, "La contraseña actual no es correcta")
    if len(data.password_nueva) < 6:
        raise HTTPException(400, "La nueva contraseña debe tener al menos 6 caracteres")
    usuario.password_hash = hash_password(data.password_nueva)
    db.commit()
    return {"ok": True}


# ── Gestión de usuarios (solo administradores) ─────────────
@router_auth.get("/usuarios", response_model=List[UsuarioOut])
def listar_usuarios(db: Session = Depends(get_db), _admin: Usuario = Depends(requiere_admin)):
    return db.query(Usuario).order_by(Usuario.username).all()


@router_auth.post("/usuarios", response_model=UsuarioOut)
def crear_usuario(data: UsuarioCreate, db: Session = Depends(get_db), _admin: Usuario = Depends(requiere_admin)):
    username = data.username.strip().lower()
    if not username:
        raise HTTPException(400, "El nombre de usuario no puede estar vacío")
    if db.query(Usuario).filter(Usuario.username == username).first():
        raise HTTPException(400, f"El usuario '{username}' ya existe")
    if len(data.password) < 6:
        raise HTTPException(400, "La contraseña debe tener al menos 6 caracteres")
    if data.rol not in ("admin", "docente"):
        raise HTTPException(400, "Rol no válido")
    u = Usuario(username=username, password_hash=hash_password(data.password),
                nombre_completo=data.nombre_completo, rol=data.rol, activo=data.activo)
    db.add(u); db.commit(); db.refresh(u)
    return u


@router_auth.put("/usuarios/{id}", response_model=UsuarioOut)
def actualizar_usuario(id: int, data: UsuarioUpdate, db: Session = Depends(get_db),
                        admin: Usuario = Depends(requiere_admin)):
    u = db.query(Usuario).filter(Usuario.id == id).first()
    if not u: raise HTTPException(404, "Usuario no encontrado")
    if u.id == admin.id and data.activo is False:
        raise HTTPException(400, "No puedes desactivar tu propia cuenta")
    if u.id == admin.id and data.rol != "admin":
        raise HTTPException(400, "No puedes quitarte tu propio rol de administrador")
    u.nombre_completo = data.nombre_completo
    u.rol = data.rol
    u.activo = data.activo
    db.commit(); db.refresh(u)
    return u


@router_auth.post("/usuarios/{id}/resetear-clave")
def resetear_clave(id: int, data: dict, db: Session = Depends(get_db), _admin: Usuario = Depends(requiere_admin)):
    u = db.query(Usuario).filter(Usuario.id == id).first()
    if not u: raise HTTPException(404, "Usuario no encontrado")
    nueva = (data or {}).get("password_nueva", "")
    if len(nueva) < 6:
        raise HTTPException(400, "La contraseña debe tener al menos 6 caracteres")
    u.password_hash = hash_password(nueva)
    db.commit()
    return {"ok": True}


@router_auth.delete("/usuarios/{id}")
def eliminar_usuario(id: int, db: Session = Depends(get_db), admin: Usuario = Depends(requiere_admin)):
    if id == admin.id:
        raise HTTPException(400, "No puedes eliminar tu propia cuenta")
    u = db.query(Usuario).filter(Usuario.id == id).first()
    if not u: raise HTTPException(404, "Usuario no encontrado")
    db.delete(u); db.commit()
    return {"ok": True}
