from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from backend.models.models import RolUsuario, EstadoPedido, TipoEntrega, MetodoPago, EstadoPago


# ─── USUARIO ────────────────────────────────────────────────────────────────
class UsuarioBase(BaseModel):
    nombre: str
    email: EmailStr
    rut: Optional[str] = None
    rol: RolUsuario = RolUsuario.cliente
    suscrito_noticias: bool = False

class UsuarioCreate(UsuarioBase):
    password: str

class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    suscrito_noticias: Optional[bool] = None

class UsuarioResponse(UsuarioBase):
    id: int
    activo: bool
    primer_login: bool
    fecha_creacion: datetime

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    rol: str
    nombre: str
    primer_login: bool


# ─── CATEGORÍA ──────────────────────────────────────────────────────────────
class CategoriaBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None

class CategoriaCreate(CategoriaBase):
    pass

class CategoriaResponse(CategoriaBase):
    id: int

    class Config:
        from_attributes = True


# ─── PRODUCTO ───────────────────────────────────────────────────────────────
class ProductoBase(BaseModel):
    codigo_ferremas: str
    codigo_marca: Optional[str] = None
    nombre: str
    descripcion: Optional[str] = None
    marca: str
    precio: float = Field(gt=0)
    stock: int = Field(ge=0)
    categoria_id: int

class ProductoCreate(ProductoBase):
    pass

class ProductoUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    precio: Optional[float] = None
    stock: Optional[int] = None
    activo: Optional[bool] = None

class ProductoResponse(ProductoBase):
    id: int
    activo: bool
    fecha_actualizacion: datetime
    categoria: CategoriaResponse

    class Config:
        from_attributes = True

class ProductoAPIResponse(BaseModel):
    """Estructura de respuesta pública de la API (formato solicitado en el caso)"""
    codigo_producto: str
    marca: str
    codigo: Optional[str]
    nombre: str
    precio: List[dict]
    stock: int
    categoria: str


# ─── PEDIDO ─────────────────────────────────────────────────────────────────
class ItemPedidoCreate(BaseModel):
    producto_id: int
    cantidad: int = Field(gt=0)

class ItemPedidoResponse(BaseModel):
    id: int
    producto_id: int
    cantidad: int
    precio_unitario: float
    producto: ProductoResponse

    class Config:
        from_attributes = True

class PedidoCreate(BaseModel):
    tipo_entrega: TipoEntrega
    metodo_pago: MetodoPago
    direccion_entrega: Optional[str] = None
    items: List[ItemPedidoCreate]
    moneda: str = "CLP"
    notas: Optional[str] = None

class PedidoUpdate(BaseModel):
    estado: Optional[EstadoPedido] = None
    estado_pago: Optional[EstadoPago] = None
    notas: Optional[str] = None

class PedidoResponse(BaseModel):
    id: int
    cliente_id: int
    estado: EstadoPedido
    tipo_entrega: TipoEntrega
    metodo_pago: MetodoPago
    estado_pago: EstadoPago
    direccion_entrega: Optional[str]
    total: float
    moneda: str
    notas: Optional[str]
    fecha_creacion: datetime
    items: List[ItemPedidoResponse]

    class Config:
        from_attributes = True


# ─── PAGO ───────────────────────────────────────────────────────────────────
class PagoCreate(BaseModel):
    pedido_id: int
    metodo: MetodoPago
    monto: float

class DatosTransferenciaRequest(BaseModel):
    """Datos que el cliente envía al registrar su transferencia."""
    pedido_id: int
    nombre_titular: str
    rut_titular: str
    banco_origen: str
    numero_comprobante: str
    email_notificacion: str

class ConfirmarTransferenciaRequest(BaseModel):
    """Usado por el contador para confirmar una transferencia recibida."""
    pedido_id: int
    comprobante: str

class PagoResponse(BaseModel):
    id: int
    pedido_id: int
    metodo: MetodoPago
    estado: EstadoPago
    monto: float
    token_webpay: Optional[str]
    comprobante: Optional[str]
    fecha_pago: Optional[datetime]

    class Config:
        from_attributes = True


# ─── CONTACTO ───────────────────────────────────────────────────────────────
class ContactoCreate(BaseModel):
    nombre: str
    email: EmailStr
    asunto: str
    mensaje: str

class ContactoResponse(BaseModel):
    id: int
    nombre: str
    email: str
    asunto: str
    mensaje: str
    atendido: bool
    fecha: datetime

    class Config:
        from_attributes = True


# ─── DIVISAS ────────────────────────────────────────────────────────────────
class ConversionDivisaResponse(BaseModel):
    moneda_origen: str
    moneda_destino: str = "CLP"
    valor_unitario: float
    monto_original: float
    monto_convertido: float
    fecha: str
