"""
Integración con Webpay Plus de Transbank.
En modo sandbox (desarrollo) no se requieren credenciales reales.
Para producción: obtener API Key y Commerce Code en https://www.transbank.cl/
"""
import httpx
import uuid
from typing import Optional

# ── Configuración Sandbox ──────────────────────────────────────────────────
WEBPAY_BASE_URL = "https://webpay3gint.transbank.cl"  # ambiente integración
COMMERCE_CODE = "597055555532"                          # código comercio sandbox
API_KEY = "579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C"  # key sandbox
RETURN_URL = "http://localhost:8000/api/pagos/webpay/retorno"


HEADERS = {
    "Tbk-Api-Key-Id": COMMERCE_CODE,
    "Tbk-Api-Key-Secret": API_KEY,
    "Content-Type": "application/json",
}


async def iniciar_transaccion(monto: float, pedido_id: int) -> dict:
    """
    Inicia una transacción Webpay Plus.
    Retorna la URL de pago y el token para redirigir al cliente.
    """
    buy_order = f"FERREMAS-{pedido_id}-{uuid.uuid4().hex[:6].upper()}"
    session_id = f"SES-{pedido_id}"

    payload = {
        "buy_order": buy_order,
        "session_id": session_id,
        "amount": int(monto),
        "return_url": RETURN_URL,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{WEBPAY_BASE_URL}/rswebpaytransaction/api/webpay/v1.2/transactions",
                headers=HEADERS,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "token": data["token"],
                "url_pago": data["url"],
                "buy_order": buy_order,
            }
    except Exception as e:
        print(f"[Webpay] Error al iniciar transacción: {e}")
        raise


async def confirmar_transaccion(token: str) -> dict:
    """
    Confirma una transacción Webpay luego de que el cliente completa el pago.
    Retorna el resultado con estado de autorización.
    """
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.put(
                f"{WEBPAY_BASE_URL}/rswebpaytransaction/api/webpay/v1.2/transactions/{token}",
                headers=HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()
            # response_code == 0 → transacción aprobada
            aprobada = data.get("response_code") == 0
            return {
                "aprobada": aprobada,
                "response_code": data.get("response_code"),
                "authorization_code": data.get("authorization_code"),
                "amount": data.get("amount"),
                "buy_order": data.get("buy_order"),
                "card_detail": data.get("card_detail"),
            }
    except Exception as e:
        print(f"[Webpay] Error al confirmar transacción: {e}")
        raise
