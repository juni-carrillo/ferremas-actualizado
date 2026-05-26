from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.database.database import get_db
from backend.models.models import (
    Pedido, ItemPedido, Producto, Usuario,
    RolUsuario, EstadoPedido, EstadoPago, MetodoPago
)
from backend.schemas.schemas import PedidoCreate, PedidoUpdate, PedidoResponse
from backend.services.auth_service import get_current_user, require_roles
from backend.services import email_service
import asyncio

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


def _get_pedido_or_404(pedido_id: int, db: Session) -> Pedido:
    p = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return p


# ─── CLIENTE: crear pedido ────────────────────────────────────────────────────
@router.post("", response_model=PedidoResponse, status_code=201)
def crear_pedido(
    data: PedidoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(RolUsuario.cliente)),
):
    if not data.items:
        raise HTTPException(status_code=400, detail="El pedido debe tener al menos un producto")

    total = 0.0
    items_db = []
    for item in data.items:
        producto = db.query(Producto).filter(Producto.id == item.producto_id, Producto.activo == True).first()
        if not producto:
            raise HTTPException(status_code=404, detail=f"Producto {item.producto_id} no encontrado")
        if producto.stock < item.cantidad:
            raise HTTPException(status_code=400, detail=f"Stock insuficiente para '{producto.nombre}'")
        total += producto.precio * item.cantidad
        items_db.append(ItemPedido(
            producto_id=producto.id,
            cantidad=item.cantidad,
            precio_unitario=producto.precio,
        ))
        producto.stock -= item.cantidad  # reservar stock

    # Descuento automático por más de 4 artículos (clientes suscritos)
    total_items = sum(i.cantidad for i in data.items)
    if total_items > 4 and current_user.suscrito_noticias:
        total *= 0.95  # 5 % de descuento

    pedido = Pedido(
        cliente_id=current_user.id,
        tipo_entrega=data.tipo_entrega,
        metodo_pago=data.metodo_pago,
        direccion_entrega=data.direccion_entrega,
        total=round(total, 2),
        moneda=data.moneda,
        notas=data.notas,
    )
    db.add(pedido)
    db.flush()  # obtener id antes de confirmar

    for item in items_db:
        item.pedido_id = pedido.id
        db.add(item)

    db.commit()
    db.refresh(pedido)

    # Enviar email de confirmación (sin bloquear la respuesta)
    try:
        items_email = [
            {"nombre": it.producto.nombre, "cantidad": it.cantidad, "precio_unitario": it.precio_unitario}
            for it in pedido.items
        ]
        asyncio.create_task(email_service.enviar_confirmacion_pedido(
            email_cliente=current_user.email,
            nombre_cliente=current_user.nombre,
            pedido_id=pedido.id,
            items=items_email,
            total=pedido.total,
            tipo_entrega=pedido.tipo_entrega.value,
            metodo_pago=pedido.metodo_pago.value,
            direccion=pedido.direccion_entrega,
        ))
    except Exception as e:
        print(f"[Email] No se pudo enviar confirmación: {e}")

    return pedido


# ─── CLIENTE: mis pedidos ─────────────────────────────────────────────────────
@router.get("/mis-pedidos", response_model=List[PedidoResponse])
def mis_pedidos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles(RolUsuario.cliente)),
):
    return db.query(Pedido).filter(Pedido.cliente_id == current_user.id).all()


# ─── VENDEDOR: ver todos los pedidos y aprobar/rechazar ──────────────────────
@router.get("/todos", response_model=List[PedidoResponse])
def listar_todos(
    db: Session = Depends(get_db),
    _=Depends(require_roles(RolUsuario.vendedor, RolUsuario.administrador, RolUsuario.bodeguero, RolUsuario.contador)),
):
    return db.query(Pedido).order_by(Pedido.fecha_creacion.desc()).all()


@router.put("/{pedido_id}/aprobar")
def aprobar_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_roles(RolUsuario.vendedor)),
):
    pedido = _get_pedido_or_404(pedido_id, db)
    if pedido.estado != EstadoPedido.pendiente:
        raise HTTPException(status_code=400, detail="Solo se pueden aprobar pedidos pendientes")
    pedido.estado = EstadoPedido.aprobado
    db.commit()
    try:
        asyncio.create_task(email_service.enviar_actualizacion_estado(
            email_cliente=pedido.cliente.email, nombre_cliente=pedido.cliente.nombre,
            pedido_id=pedido_id, nuevo_estado="aprobado", total=pedido.total))
    except Exception: pass
    return {"mensaje": "Pedido aprobado", "pedido_id": pedido_id}


@router.put("/{pedido_id}/rechazar")
def rechazar_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_roles(RolUsuario.vendedor)),
):
    pedido = _get_pedido_or_404(pedido_id, db)
    if pedido.estado not in [EstadoPedido.pendiente, EstadoPedido.aprobado]:
        raise HTTPException(status_code=400, detail="No se puede rechazar este pedido en su estado actual")
    # Devolver stock
    for item in pedido.items:
        item.producto.stock += item.cantidad
    pedido.estado = EstadoPedido.rechazado
    db.commit()
    return {"mensaje": "Pedido rechazado y stock restaurado", "pedido_id": pedido_id}


# ─── BODEGUERO: preparar y marcar como listo ─────────────────────────────────
@router.put("/{pedido_id}/preparar")
def preparar_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_roles(RolUsuario.bodeguero)),
):
    pedido = _get_pedido_or_404(pedido_id, db)
    if pedido.estado != EstadoPedido.aprobado:
        raise HTTPException(status_code=400, detail="Solo se pueden preparar pedidos aprobados")
    pedido.estado = EstadoPedido.preparando
    db.commit()
    return {"mensaje": "Pedido en preparación", "pedido_id": pedido_id}


@router.put("/{pedido_id}/listo")
def marcar_listo(
    pedido_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_roles(RolUsuario.bodeguero)),
):
    pedido = _get_pedido_or_404(pedido_id, db)
    if pedido.estado != EstadoPedido.preparando:
        raise HTTPException(status_code=400, detail="El pedido debe estar en preparación")
    pedido.estado = EstadoPedido.listo
    db.commit()
    return {"mensaje": "Pedido listo para entrega/despacho", "pedido_id": pedido_id}


# ─── CONTADOR / VENDEDOR: confirmar entrega ───────────────────────────────────
@router.put("/{pedido_id}/entregar")
def confirmar_entrega(
    pedido_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_roles(RolUsuario.contador, RolUsuario.vendedor)),
):
    pedido = _get_pedido_or_404(pedido_id, db)
    if pedido.estado != EstadoPedido.listo:
        raise HTTPException(status_code=400, detail="El pedido debe estar listo para marcar como entregado")
    pedido.estado = EstadoPedido.entregado
    db.commit()
    try:
        asyncio.create_task(email_service.enviar_actualizacion_estado(
            email_cliente=pedido.cliente.email, nombre_cliente=pedido.cliente.nombre,
            pedido_id=pedido_id, nuevo_estado="entregado", total=pedido.total))
    except Exception: pass
    return {"mensaje": "Entrega registrada correctamente", "pedido_id": pedido_id}


@router.get("/{pedido_id}", response_model=PedidoResponse)
def obtener_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    pedido = _get_pedido_or_404(pedido_id, db)
    # Clientes solo ven sus propios pedidos
    if current_user.rol == RolUsuario.cliente and pedido.cliente_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    return pedido
