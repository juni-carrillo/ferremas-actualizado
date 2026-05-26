from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from backend.database.database import get_db
from backend.models.models import Producto, Categoria, RolUsuario
from backend.schemas.schemas import (
    ProductoCreate, ProductoUpdate, ProductoResponse, ProductoAPIResponse,
    CategoriaCreate, CategoriaResponse
)
from backend.services.auth_service import get_current_user, require_roles

router = APIRouter(prefix="/productos", tags=["Productos"])


# ─── CATEGORÍAS ─────────────────────────────────────────────────────────────
@router.get("/categorias", response_model=List[CategoriaResponse])
def listar_categorias(db: Session = Depends(get_db)):
    return db.query(Categoria).all()


@router.post("/categorias", response_model=CategoriaResponse, status_code=201)
def crear_categoria(
    data: CategoriaCreate,
    db: Session = Depends(get_db),
    _=Depends(require_roles(RolUsuario.administrador)),
):
    cat = Categoria(**data.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


# ─── CATÁLOGO PÚBLICO ────────────────────────────────────────────────────────
@router.get("", response_model=List[ProductoResponse])
def listar_productos(
    categoria_id: Optional[int] = Query(None),
    marca: Optional[str] = Query(None),
    busqueda: Optional[str] = Query(None),
    solo_disponibles: bool = Query(True),
    db: Session = Depends(get_db),
):
    q = db.query(Producto).filter(Producto.activo == True)
    if solo_disponibles:
        q = q.filter(Producto.stock > 0)
    if categoria_id:
        q = q.filter(Producto.categoria_id == categoria_id)
    if marca:
        q = q.filter(Producto.marca.ilike(f"%{marca}%"))
    if busqueda:
        q = q.filter(Producto.nombre.ilike(f"%{busqueda}%"))
    return q.all()


@router.get("/{producto_id}", response_model=ProductoResponse)
def obtener_producto(producto_id: int, db: Session = Depends(get_db)):
    p = db.query(Producto).filter(Producto.id == producto_id, Producto.activo == True).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return p


# ─── API PÚBLICA (formato especificado en el caso) ───────────────────────────
@router.get("/api/detalle/{codigo}", response_model=ProductoAPIResponse, tags=["API Pública"])
def detalle_api_publico(codigo: str, db: Session = Depends(get_db)):
    """
    Endpoint público para consulta externa de productos.
    Retorna el formato JSON especificado en el enunciado del caso FERREMAS.
    """
    p = db.query(Producto).filter(
        Producto.codigo_ferremas == codigo, Producto.activo == True
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return ProductoAPIResponse(
        codigo_producto=p.codigo_ferremas,
        marca=p.marca,
        codigo=p.codigo_marca,
        nombre=p.nombre,
        precio=[{"fecha": datetime.now().isoformat(), "valor": p.precio}],
        stock=p.stock,
        categoria=p.categoria.nombre,
    )


@router.get("/api/catalogo", response_model=List[ProductoAPIResponse], tags=["API Pública"])
def catalogo_api_publico(db: Session = Depends(get_db)):
    """Listado completo de productos para consumo externo (otras tiendas / sucursales)."""
    productos = db.query(Producto).filter(Producto.activo == True).all()
    return [
        ProductoAPIResponse(
            codigo_producto=p.codigo_ferremas,
            marca=p.marca,
            codigo=p.codigo_marca,
            nombre=p.nombre,
            precio=[{"fecha": datetime.now().isoformat(), "valor": p.precio}],
            stock=p.stock,
            categoria=p.categoria.nombre,
        )
        for p in productos
    ]


# ─── GESTIÓN (admin / vendedor / bodeguero) ──────────────────────────────────
@router.post("/", response_model=ProductoResponse, status_code=201)
def crear_producto(
    data: ProductoCreate,
    db: Session = Depends(get_db),
    _=Depends(require_roles(RolUsuario.administrador, RolUsuario.vendedor)),
):
    if db.query(Producto).filter(Producto.codigo_ferremas == data.codigo_ferremas).first():
        raise HTTPException(status_code=400, detail="El código de producto ya existe")
    p = Producto(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.put("/{producto_id}", response_model=ProductoResponse)
def actualizar_producto(
    producto_id: int,
    data: ProductoUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_roles(RolUsuario.administrador, RolUsuario.vendedor, RolUsuario.bodeguero)),
):
    p = db.query(Producto).filter(Producto.id == producto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(p, campo, valor)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/{producto_id}")
def eliminar_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_roles(RolUsuario.administrador)),
):
    p = db.query(Producto).filter(Producto.id == producto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    p.activo = False  # soft delete
    db.commit()
    return {"mensaje": "Producto desactivado correctamente"}
