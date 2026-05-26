"""
Servicio de correo electrónico – FERREMAS
Usa Gmail SMTP con contraseña de aplicación (App Password).

Pasos para activarlo:
  1. Ve a myaccount.google.com → Seguridad → Verificación en dos pasos (actívala)
  2. Luego: myaccount.google.com → Seguridad → Contraseñas de aplicaciones
  3. Crea una contraseña para "Correo" / "Windows" y cópiala aquí abajo.
"""
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import List

# ── CONFIGURACIÓN – edita estos valores ──────────────────────────────────────
GMAIL_USER     = "tu_correo@gmail.com"          # ← tu Gmail
GMAIL_APP_PASS = "xxxx xxxx xxxx xxxx"           # ← contraseña de aplicación (16 chars)
NOMBRE_REMITENTE = "FERREMAS Tienda"
# ─────────────────────────────────────────────────────────────────────────────


async def _enviar(destinatario: str, asunto: str, html: str) -> bool:
    """Envía un email HTML de forma asíncrona. Retorna True si tuvo éxito."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"]    = f"{NOMBRE_REMITENTE} <{GMAIL_USER}>"
    msg["To"]      = destinatario
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        await aiosmtplib.send(
            msg,
            hostname="smtp.gmail.com",
            port=587,
            start_tls=True,
            username=GMAIL_USER,
            password=GMAIL_APP_PASS,
        )
        print(f"[Email] ✅ Enviado a {destinatario}: {asunto}")
        return True
    except Exception as e:
        print(f"[Email] ❌ Error enviando a {destinatario}: {e}")
        return False


# ── PLANTILLA BASE ────────────────────────────────────────────────────────────

def _base_template(contenido: str) -> str:
    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:'Segoe UI',Arial,sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:30px 0">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:12px;overflow:hidden;
                    box-shadow:0 4px 20px rgba(0,0,0,0.10);max-width:600px;width:100%">

        <!-- HEADER -->
        <tr>
          <td style="background:linear-gradient(135deg,#1a1a2e 0%,#e65c00 100%);
                     padding:32px 40px;text-align:center">
            <h1 style="margin:0;color:#ffffff;font-size:28px;letter-spacing:2px">
              FERRE<span style="color:#f9a825">MAS</span>
            </h1>
            <p style="margin:6px 0 0;color:#ffcca0;font-size:13px">
              Ferretería y Construcción · Santiago, Chile
            </p>
          </td>
        </tr>

        <!-- CONTENIDO -->
        <tr>
          <td style="padding:36px 40px">
            {contenido}
          </td>
        </tr>

        <!-- FOOTER -->
        <tr>
          <td style="background:#f8f8f8;padding:20px 40px;text-align:center;
                     border-top:1px solid #eeeeee">
            <p style="margin:0;color:#999;font-size:12px">
              © {datetime.now().year} FERREMAS · Santiago, Chile<br>
              Este correo fue enviado automáticamente, por favor no respondas a este mensaje.<br>
              <a href="mailto:contacto@ferremas.cl"
                 style="color:#e65c00;text-decoration:none">contacto@ferremas.cl</a>
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


# ── EMAIL 1: CONFIRMACIÓN DE PEDIDO ──────────────────────────────────────────

async def enviar_confirmacion_pedido(
    email_cliente: str,
    nombre_cliente: str,
    pedido_id: int,
    items: list,           # lista de dicts {nombre, cantidad, precio_unitario}
    total: float,
    tipo_entrega: str,
    metodo_pago: str,
    direccion: str = None,
) -> bool:

    metodo_label = {
        "debito": "Débito (Webpay)", "credito": "Crédito (Webpay)",
        "transferencia": "Transferencia bancaria"
    }.get(metodo_pago, metodo_pago)

    entrega_label = {
        "retiro_tienda": "🏪 Retiro en tienda",
        "despacho_domicilio": "🚚 Despacho a domicilio"
    }.get(tipo_entrega, tipo_entrega)

    filas_items = "".join([
        f"""<tr>
          <td style="padding:10px 12px;border-bottom:1px solid #f0f0f0;color:#333">{i['nombre']}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #f0f0f0;text-align:center;color:#555">{i['cantidad']}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #f0f0f0;text-align:right;
                     color:#e65c00;font-weight:600">${i['precio_unitario']*i['cantidad']:,.0f} CLP</td>
        </tr>"""
        for i in items
    ])

    direccion_html = f"""
      <tr>
        <td style="padding:8px 0;color:#666;font-size:14px">📍 Dirección</td>
        <td style="padding:8px 0;color:#333;font-size:14px;font-weight:600">{direccion}</td>
      </tr>""" if direccion else ""

    transferencia_html = """
      <div style="background:#fff8e1;border-left:4px solid #f9a825;padding:16px 20px;
                  border-radius:0 8px 8px 0;margin-top:20px">
        <p style="margin:0 0 8px;font-weight:700;color:#e65c00">⚠️ Recuerda completar tu transferencia</p>
        <p style="margin:0;font-size:13px;color:#555">
          Banco de Chile · Cta. Corriente Nº 00-123-45678-09<br>
          RUT: 76.543.210-K · FERREMAS Ltda.<br>
          Envía el comprobante a: <strong>pagos@ferremas.cl</strong>
        </p>
      </div>""" if metodo_pago == "transferencia" else ""

    contenido = f"""
      <h2 style="margin:0 0 4px;color:#1a1a2e;font-size:22px">¡Gracias por tu pedido, {nombre_cliente}! 🎉</h2>
      <p style="margin:0 0 24px;color:#888;font-size:14px">
        Tu pedido fue recibido y está siendo procesado.
      </p>

      <!-- Badge pedido -->
      <div style="background:#fff4ee;border:2px solid #e65c00;border-radius:10px;
                  padding:16px 24px;margin-bottom:24px;text-align:center">
        <span style="color:#888;font-size:13px">Número de pedido</span><br>
        <span style="font-size:32px;font-weight:800;color:#e65c00">#{pedido_id}</span>
      </div>

      <!-- Detalles del pedido -->
      <table width="100%" cellpadding="0" cellspacing="0"
             style="margin-bottom:20px;border-radius:8px;overflow:hidden;
                    border:1px solid #eeeeee">
        <tr style="background:#f8f8f8">
          <th style="padding:10px 12px;text-align:left;color:#555;font-size:13px">Producto</th>
          <th style="padding:10px 12px;text-align:center;color:#555;font-size:13px">Cant.</th>
          <th style="padding:10px 12px;text-align:right;color:#555;font-size:13px">Subtotal</th>
        </tr>
        {filas_items}
        <tr style="background:#fff4ee">
          <td colspan="2" style="padding:12px;font-weight:700;color:#1a1a2e;font-size:15px">Total</td>
          <td style="padding:12px;text-align:right;font-weight:800;color:#e65c00;font-size:18px">
            ${total:,.0f} CLP
          </td>
        </tr>
      </table>

      <!-- Info entrega y pago -->
      <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px">
        <tr>
          <td style="padding:8px 0;color:#666;font-size:14px;width:140px">🚚 Entrega</td>
          <td style="padding:8px 0;color:#333;font-size:14px;font-weight:600">{entrega_label}</td>
        </tr>
        <tr>
          <td style="padding:8px 0;color:#666;font-size:14px">💳 Pago</td>
          <td style="padding:8px 0;color:#333;font-size:14px;font-weight:600">{metodo_label}</td>
        </tr>
        {direccion_html}
      </table>

      {transferencia_html}

      <div style="background:#f0f9f0;border-radius:8px;padding:16px 20px;margin-top:20px">
        <p style="margin:0;color:#2e7d32;font-size:14px">
          📬 Te notificaremos cuando tu pedido cambie de estado.<br>
          Si tienes dudas escríbenos a
          <a href="mailto:contacto@ferremas.cl" style="color:#e65c00">contacto@ferremas.cl</a>
        </p>
      </div>"""

    return await _enviar(
        email_cliente,
        f"✅ Pedido #{pedido_id} confirmado – FERREMAS",
        _base_template(contenido)
    )


# ── EMAIL 2: CAMBIO DE ESTADO DEL PEDIDO ─────────────────────────────────────

async def enviar_actualizacion_estado(
    email_cliente: str,
    nombre_cliente: str,
    pedido_id: int,
    nuevo_estado: str,
    total: float,
) -> bool:

    estados = {
        "aprobado":   ("✅", "#2e7d32", "¡Tu pedido fue aprobado!", "Nuestro equipo ya está preparando tus productos."),
        "rechazado":  ("❌", "#c62828", "Tu pedido fue rechazado",  "Lo sentimos, hubo un problema con tu pedido. Contáctanos para más información."),
        "preparando": ("📦", "#1565c0", "Preparando tu pedido",     "El bodeguero ya está preparando tus productos."),
        "listo":      ("🎯", "#6a1b9a", "¡Tu pedido está listo!",   "Tu pedido está listo para retiro o despacho."),
        "entregado":  ("🎉", "#2e7d32", "¡Pedido entregado!",       "Tu pedido fue entregado exitosamente. ¡Gracias por comprar en FERREMAS!"),
    }
    icono, color, titulo, desc = estados.get(nuevo_estado, ("ℹ️", "#555", f"Estado: {nuevo_estado}", ""))

    contenido = f"""
      <div style="text-align:center;padding:10px 0 28px">
        <span style="font-size:56px">{icono}</span>
        <h2 style="margin:12px 0 6px;color:{color};font-size:22px">{titulo}</h2>
        <p style="margin:0;color:#888;font-size:14px">{desc}</p>
      </div>

      <div style="background:#f8f8f8;border-radius:10px;padding:20px 24px;text-align:center">
        <span style="color:#888;font-size:13px">Pedido</span><br>
        <span style="font-size:28px;font-weight:800;color:#e65c00">#{pedido_id}</span><br>
        <span style="color:#555;font-size:15px;font-weight:600">${total:,.0f} CLP</span>
      </div>

      <p style="margin:24px 0 0;color:#555;font-size:14px;text-align:center">
        Hola <strong>{nombre_cliente}</strong>, el estado de tu pedido ha sido actualizado.<br>
        Si tienes preguntas, contáctanos en
        <a href="mailto:contacto@ferremas.cl" style="color:#e65c00">contacto@ferremas.cl</a>
      </p>"""

    return await _enviar(
        email_cliente,
        f"{icono} Pedido #{pedido_id} – {titulo} | FERREMAS",
        _base_template(contenido)
    )


# ── EMAIL 3: REGISTRO DE USUARIO ─────────────────────────────────────────────

async def enviar_bienvenida(email: str, nombre: str) -> bool:
    contenido = f"""
      <div style="text-align:center;padding:10px 0 28px">
        <span style="font-size:56px">🎉</span>
        <h2 style="margin:12px 0 6px;color:#1a1a2e;font-size:24px">¡Bienvenido/a, {nombre}!</h2>
        <p style="margin:0;color:#888;font-size:14px">Tu cuenta en FERREMAS fue creada exitosamente.</p>
      </div>

      <div style="background:#fff4ee;border-radius:10px;padding:20px 24px;margin-bottom:20px">
        <h3 style="margin:0 0 12px;color:#e65c00;font-size:16px">¿Qué puedes hacer ahora?</h3>
        <p style="margin:6px 0;color:#555;font-size:14px">🔨 Explorar nuestro catálogo completo de productos</p>
        <p style="margin:6px 0;color:#555;font-size:14px">🛒 Comprar con débito, crédito o transferencia</p>
        <p style="margin:6px 0;color:#555;font-size:14px">🚚 Elegir retiro en tienda o despacho a domicilio</p>
        <p style="margin:6px 0;color:#555;font-size:14px">💱 Ver precios en USD, EUR y GBP en tiempo real</p>
      </div>

      <div style="text-align:center">
        <a href="http://localhost:8000"
           style="display:inline-block;background:#e65c00;color:#ffffff;text-decoration:none;
                  padding:14px 32px;border-radius:8px;font-weight:700;font-size:15px">
          Ir a la tienda →
        </a>
      </div>"""

    return await _enviar(email, "🔨 ¡Bienvenido/a a FERREMAS!", _base_template(contenido))
