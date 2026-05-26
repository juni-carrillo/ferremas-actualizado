from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime
from backend.database.database import get_db
from backend.models.models import Pedido, Pago, RolUsuario, EstadoPago, MetodoPago
from backend.schemas.schemas import (
    ConfirmarTransferenciaRequest, DatosTransferenciaRequest, PagoResponse
)
from backend.services.auth_service import get_current_user, require_roles
from backend.services import webpay_service

router = APIRouter(prefix="/pagos", tags=["Pagos"])


# ─── WEBPAY: iniciar transacción ─────────────────────────────────────────────
@router.post("/webpay/iniciar/{pedido_id}")
async def iniciar_pago_webpay(
    pedido_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(RolUsuario.cliente)),
):
    pedido = db.query(Pedido).filter(
        Pedido.id == pedido_id, Pedido.cliente_id == current_user.id
    ).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if pedido.metodo_pago not in [MetodoPago.debito, MetodoPago.credito]:
        raise HTTPException(status_code=400, detail="Este pedido no es de tipo tarjeta")

    # Si ya hay un pago previo pendiente con token, reutilizarlo
    pago_existente = db.query(Pago).filter(Pago.pedido_id == pedido_id).first()
    if pago_existente and pago_existente.estado == EstadoPago.confirmado:
        raise HTTPException(status_code=400, detail="Este pedido ya fue pagado")

    resultado = await webpay_service.iniciar_transaccion(pedido.total, pedido.id)

    if pago_existente:
        pago_existente.token_webpay = resultado["token"]
    else:
        pago = Pago(
            pedido_id=pedido.id,
            metodo=pedido.metodo_pago,
            monto=pedido.total,
            token_webpay=resultado["token"],
        )
        db.add(pago)
    db.commit()

    return {
        "url_pago": resultado["url_pago"],
        "token": resultado["token"],
    }


# ─── WEBPAY: retorno tras el pago (Transbank redirige aquí) ──────────────────
@router.get("/webpay/retorno", response_class=HTMLResponse)
async def retorno_webpay(token_ws: str = None, TBK_TOKEN: str = None, db: Session = Depends(get_db)):
    """
    Transbank redirige al usuario aquí luego de completar (o cancelar) el pago.
    Responde con una página HTML que muestra el resultado y redirige al frontend.
    """
    # Si el usuario canceló en Webpay, Transbank envía TBK_TOKEN en lugar de token_ws
    token = token_ws or TBK_TOKEN
    cancelado = TBK_TOKEN and not token_ws

    if cancelado or not token:
        return _html_resultado(
            exito=False,
            titulo="Pago cancelado",
            mensaje="Cancelaste el proceso de pago. Tu pedido sigue pendiente.",
            redirect="/?pago=cancelado"
        )

    pago = db.query(Pago).filter(Pago.token_webpay == token).first()
    if not pago:
        return _html_resultado(
            exito=False,
            titulo="Error",
            mensaje="No se encontró la transacción. Contacta a soporte.",
            redirect="/?pago=error"
        )

    try:
        resultado = await webpay_service.confirmar_transaccion(token)
    except Exception as e:
        return _html_resultado(
            exito=False,
            titulo="Error al confirmar pago",
            mensaje=str(e),
            redirect="/?pago=error"
        )

    if resultado["aprobada"]:
        pago.estado = EstadoPago.confirmado
        pago.fecha_pago = datetime.utcnow()
        pago.pedido.estado_pago = EstadoPago.confirmado
        db.commit()
        return _html_resultado(
            exito=True,
            titulo="¡Pago aprobado!",
            mensaje=f"Tu pago de ${resultado['amount']:,.0f} fue procesado exitosamente.<br>"
                    f"Código de autorización: <strong>{resultado['authorization_code']}</strong>",
            redirect="/?pago=ok"
        )
    else:
        pago.estado = EstadoPago.rechazado
        pago.pedido.estado_pago = EstadoPago.rechazado
        db.commit()
        return _html_resultado(
            exito=False,
            titulo="Pago rechazado",
            mensaje="La transacción fue rechazada por Webpay. Intenta con otra tarjeta.",
            redirect="/?pago=error"
        )


def _html_resultado(exito: bool, titulo: str, mensaje: str, redirect: str) -> str:
    color = "#2e7d32" if exito else "#c62828"
    icono = "✅" if exito else "❌"
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{titulo} – FERREMAS</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Segoe UI', sans-serif; background: #f5f5f5;
            display: flex; align-items: center; justify-content: center; min-height: 100vh; }}
    .card {{ background: #fff; border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,.12);
             padding: 3rem 2rem; max-width: 460px; width: 90%; text-align: center; }}
    .icon {{ font-size: 4rem; margin-bottom: 1rem; }}
    h1 {{ color: {color}; margin-bottom: 1rem; }}
    p {{ color: #555; line-height: 1.6; margin-bottom: 1.5rem; }}
    .progress {{ height: 4px; background: #eee; border-radius: 2px; overflow: hidden; margin-top: 1rem; }}
    .progress-bar {{ height: 100%; background: {color}; animation: fill 4s linear forwards; }}
    @keyframes fill {{ from {{ width: 0 }} to {{ width: 100% }} }}
    small {{ color: #999; font-size: 0.8rem; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">{icono}</div>
    <h1>{titulo}</h1>
    <p>{mensaje}</p>
    <small>Redirigiendo en 4 segundos...</small>
    <div class="progress"><div class="progress-bar"></div></div>
  </div>
  <script>setTimeout(() => window.location.href = window.location.origin + "{redirect}", 4000);</script>
</body>
</html>"""


# ─── TRANSFERENCIA: cliente registra su transferencia ────────────────────────
@router.post("/transferencia/registrar")
def registrar_transferencia(
    data: DatosTransferenciaRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(RolUsuario.cliente)),
):
    """
    El cliente registra los datos de su transferencia bancaria.
    Queda en estado 'pendiente' hasta que el contador la confirme.
    """
    pedido = db.query(Pedido).filter(
        Pedido.id == data.pedido_id, Pedido.cliente_id == current_user.id
    ).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if pedido.metodo_pago != MetodoPago.transferencia:
        raise HTTPException(status_code=400, detail="El pedido no es de tipo transferencia")

    pago_existente = db.query(Pago).filter(Pago.pedido_id == data.pedido_id).first()
    if pago_existente and pago_existente.estado == EstadoPago.confirmado:
        raise HTTPException(status_code=400, detail="Este pedido ya fue pagado")

    notas = (f"Titular: {data.nombre_titular} | RUT: {data.rut_titular} | "
             f"Banco: {data.banco_origen} | Email: {data.email_notificacion}")

    if pago_existente:
        pago_existente.comprobante = data.numero_comprobante
        pago_existente.estado = EstadoPago.pendiente
    else:
        pago = Pago(
            pedido_id=pedido.id,
            metodo=MetodoPago.transferencia,
            monto=pedido.total,
            comprobante=data.numero_comprobante,
            estado=EstadoPago.pendiente,
        )
        db.add(pago)

    pedido.notas = (pedido.notas or "") + f"\n[TRANSFERENCIA] {notas}"
    db.commit()

    return {
        "mensaje": "Transferencia registrada. El contador verificará el pago en breve.",
        "pedido_id": data.pedido_id,
        "comprobante": data.numero_comprobante,
        "monto_esperado": pedido.total,
    }


# ─── TRANSFERENCIA: contador confirma ────────────────────────────────────────
@router.post("/transferencia/confirmar")
def confirmar_transferencia(
    data: ConfirmarTransferenciaRequest,
    db: Session = Depends(get_db),
    _=Depends(require_roles(RolUsuario.contador)),
):
    pedido = db.query(Pedido).filter(Pedido.id == data.pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    pago = db.query(Pago).filter(Pago.pedido_id == data.pedido_id).first()
    if not pago:
        pago = Pago(pedido_id=pedido.id, metodo=MetodoPago.transferencia, monto=pedido.total)
        db.add(pago)

    pago.estado = EstadoPago.confirmado
    pago.comprobante = data.comprobante
    pago.fecha_pago = datetime.utcnow()
    pedido.estado_pago = EstadoPago.confirmado
    db.commit()
    db.refresh(pago)
    return {"mensaje": "Transferencia confirmada", "comprobante": data.comprobante}


# ─── DATOS BANCARIOS FERREMAS (para mostrar al cliente) ──────────────────────
@router.get("/transferencia/datos-banco")
def datos_banco():
    """Retorna los datos bancarios de FERREMAS para que el cliente realice la transferencia."""
    return {
        "banco": "Banco de Chile",
        "tipo_cuenta": "Cuenta Corriente",
        "numero_cuenta": "00-123-45678-09",
        "rut_empresa": "76.543.210-K",
        "nombre_empresa": "FERREMAS Ltda.",
        "email_comprobante": "pagos@ferremas.cl",
        "instrucciones": "Transferir el monto exacto e indicar el número de pedido en el comentario.",
    }


# ─── CONSULTAR PAGO ──────────────────────────────────────────────────────────
@router.get("/{pedido_id}", response_model=PagoResponse)
def obtener_pago(
    pedido_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_roles(RolUsuario.contador, RolUsuario.administrador, RolUsuario.vendedor)),
):
    pago = db.query(Pago).filter(Pago.pedido_id == pedido_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado para este pedido")
    return pago
