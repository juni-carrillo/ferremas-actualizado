from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.database.database import get_db
from backend.models.models import Usuario, RolUsuario
from backend.schemas.schemas import UsuarioCreate, UsuarioResponse
from backend.services.auth_service import hash_password, require_roles

router = APIRouter(prefix="/admin", tags=["Administración"])

SOLO_ADMIN = Depends(require_roles(RolUsuario.administrador))


@router.get("/usuarios", response_model=List[UsuarioResponse])
def listar_usuarios(db: Session = Depends(get_db), _=SOLO_ADMIN):
    return db.query(Usuario).all()


@router.post("/usuarios", response_model=UsuarioResponse, status_code=201)
def crear_usuario_interno(
    data: UsuarioCreate,
    db: Session = Depends(get_db),
    _=SOLO_ADMIN,
):
    """
    El administrador crea cuentas para vendedores, bodegueros y contadores.
    La contraseña inicial es el RUT del usuario (deben cambiarla en primer login).
    """
    if data.rol == RolUsuario.cliente:
        raise HTTPException(status_code=400, detail="Use el endpoint público /auth/registro para clientes")
    if db.query(Usuario).filter(Usuario.email == data.email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    usuario = Usuario(
        nombre=data.nombre,
        email=data.email,
        rut=data.rut,
        password_hash=hash_password(data.password),
        rol=data.rol,
        primer_login=True,  # deberá cambiar contraseña
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.put("/usuarios/{usuario_id}/desactivar")
def desactivar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    _=SOLO_ADMIN,
):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    usuario.activo = False
    db.commit()
    return {"mensaje": f"Usuario {usuario.nombre} desactivado"}


@router.get("/reportes/ventas")
def reporte_ventas(db: Session = Depends(get_db), _=SOLO_ADMIN):
    """Reporte básico de ventas para administradores."""
    from backend.models.models import Pedido, EstadoPedido
    from sqlalchemy import func

    total_pedidos = db.query(func.count(Pedido.id)).scalar()
    pedidos_entregados = db.query(func.count(Pedido.id)).filter(
        Pedido.estado == EstadoPedido.entregado
    ).scalar()
    ingresos_totales = db.query(func.sum(Pedido.total)).filter(
        Pedido.estado == EstadoPedido.entregado
    ).scalar() or 0

    return {
        "total_pedidos": total_pedidos,
        "pedidos_entregados": pedidos_entregados,
        "pedidos_pendientes": total_pedidos - pedidos_entregados,
        "ingresos_totales_clp": round(ingresos_totales, 2),
    }
