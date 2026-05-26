from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from backend.database.database import Base


class RolUsuario(str, enum.Enum):
    cliente = "cliente"
    administrador = "administrador"
    vendedor = "vendedor"
    bodeguero = "bodeguero"
    contador = "contador"


class EstadoPedido(str, enum.Enum):
    pendiente = "pendiente"
    aprobado = "aprobado"
    rechazado = "rechazado"
    preparando = "preparando"
    listo = "listo"
    entregado = "entregado"


class TipoEntrega(str, enum.Enum):
    retiro_tienda = "retiro_tienda"
    despacho_domicilio = "despacho_domicilio"


class MetodoPago(str, enum.Enum):
    debito = "debito"
    credito = "credito"
    transferencia = "transferencia"


class EstadoPago(str, enum.Enum):
    pendiente = "pendiente"
    confirmado = "confirmado"
    rechazado = "rechazado"


# ─── USUARIO ────────────────────────────────────────────────────────────────
class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    rut = Column(String(12), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    rol = Column(Enum(RolUsuario), default=RolUsuario.cliente, nullable=False)
    primer_login = Column(Boolean, default=True)   # fuerza cambio de contraseña
    activo = Column(Boolean, default=True)
    suscrito_noticias = Column(Boolean, default=False)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())

    pedidos = relationship("Pedido", back_populates="cliente")


# ─── CATEGORÍA ──────────────────────────────────────────────────────────────
class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=True)

    productos = relationship("Producto", back_populates="categoria")


# ─── PRODUCTO ───────────────────────────────────────────────────────────────
class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    codigo_ferremas = Column(String(20), unique=True, nullable=False, index=True)
    codigo_marca = Column(String(30), nullable=True)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(Text, nullable=True)
    marca = Column(String(80), nullable=False)
    precio = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    categoria_id = Column(Integer, ForeignKey("categorias.id"), nullable=False)
    activo = Column(Boolean, default=True)
    fecha_actualizacion = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    categoria = relationship("Categoria", back_populates="productos")
    items_pedido = relationship("ItemPedido", back_populates="producto")


# ─── PEDIDO ─────────────────────────────────────────────────────────────────
class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    estado = Column(Enum(EstadoPedido), default=EstadoPedido.pendiente)
    tipo_entrega = Column(Enum(TipoEntrega), nullable=False)
    metodo_pago = Column(Enum(MetodoPago), nullable=False)
    estado_pago = Column(Enum(EstadoPago), default=EstadoPago.pendiente)
    direccion_entrega = Column(String(300), nullable=True)
    total = Column(Float, nullable=False, default=0)
    moneda = Column(String(10), default="CLP")
    notas = Column(Text, nullable=True)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    cliente = relationship("Usuario", back_populates="pedidos")
    items = relationship("ItemPedido", back_populates="pedido")
    pago = relationship("Pago", back_populates="pedido", uselist=False)


# ─── ITEM DE PEDIDO ─────────────────────────────────────────────────────────
class ItemPedido(Base):
    __tablename__ = "items_pedido"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Float, nullable=False)

    pedido = relationship("Pedido", back_populates="items")
    producto = relationship("Producto", back_populates="items_pedido")


# ─── PAGO ───────────────────────────────────────────────────────────────────
class Pago(Base):
    __tablename__ = "pagos"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), unique=True, nullable=False)
    metodo = Column(Enum(MetodoPago), nullable=False)
    estado = Column(Enum(EstadoPago), default=EstadoPago.pendiente)
    monto = Column(Float, nullable=False)
    token_webpay = Column(String(200), nullable=True)     # token de transacción Webpay
    comprobante = Column(String(200), nullable=True)      # número de comprobante transferencia
    fecha_pago = Column(DateTime(timezone=True), nullable=True)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())

    pedido = relationship("Pedido", back_populates="pago")


# ─── CONTACTO ───────────────────────────────────────────────────────────────
class MensajeContacto(Base):
    __tablename__ = "mensajes_contacto"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False)
    asunto = Column(String(200), nullable=False)
    mensaje = Column(Text, nullable=False)
    atendido = Column(Boolean, default=False)
    fecha = Column(DateTime(timezone=True), server_default=func.now())
