from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database.database import get_db
from backend.models.models import Usuario, RolUsuario
from backend.schemas.schemas import UsuarioCreate, UsuarioResponse, LoginRequest, TokenResponse, UsuarioUpdate
from backend.services import email_service
import asyncio
from backend.services.auth_service import (
    hash_password, verify_password, create_access_token, get_current_user
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/registro", response_model=UsuarioResponse, status_code=201)
def registrar_cliente(data: UsuarioCreate, db: Session = Depends(get_db)):
    """Registro público solo para clientes."""
    if db.query(Usuario).filter(Usuario.email == data.email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    usuario = Usuario(
        nombre=data.nombre,
        email=data.email,
        rut=data.rut,
        password_hash=hash_password(data.password),
        rol=RolUsuario.cliente,
        primer_login=False,
        suscrito_noticias=data.suscrito_noticias,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    try:
        asyncio.create_task(email_service.enviar_bienvenida(usuario.email, usuario.nombre))
    except Exception: pass
    return usuario


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == data.email).first()
    if not usuario or not verify_password(data.password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    if not usuario.activo:
        raise HTTPException(status_code=403, detail="Usuario desactivado")
    token = create_access_token({"sub": str(usuario.id), "rol": usuario.rol.value})
    return TokenResponse(
        access_token=token,
        rol=usuario.rol.value,
        nombre=usuario.nombre,
        primer_login=usuario.primer_login,
    )


@router.put("/cambiar-password")
def cambiar_password(
    data: UsuarioUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not data.password:
        raise HTTPException(status_code=400, detail="Se requiere nueva contraseña")
    current_user.password_hash = hash_password(data.password)
    current_user.primer_login = False
    db.commit()
    return {"mensaje": "Contraseña actualizada correctamente"}


@router.get("/perfil", response_model=UsuarioResponse)
def perfil(current_user: Usuario = Depends(get_current_user)):
    return current_user
