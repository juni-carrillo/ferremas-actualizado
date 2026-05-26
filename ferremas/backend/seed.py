"""
Script para poblar la base de datos con datos iniciales de FERREMAS.
Ejecutar una sola vez con: python -m backend.seed
"""
from backend.database.database import SessionLocal, engine
from backend.models.models import Base, Usuario, Categoria, Producto, RolUsuario
from backend.services.auth_service import hash_password

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Evitar duplicados
    if db.query(Usuario).first():
        print("La base de datos ya tiene datos. Seed omitido.")
        db.close()
        return

    print("Creando datos iniciales...")

    # ── Usuarios ─────────────────────────────────────────────────────────────
    usuarios = [
        Usuario(nombre="Admin Principal", email="admin@ferremas.cl", rut="12345678-9",
                password_hash=hash_password("12345678-9"), rol=RolUsuario.administrador, primer_login=True),
        Usuario(nombre="Carlos Vendedor", email="vendedor@ferremas.cl", rut="11111111-1",
                password_hash=hash_password("11111111-1"), rol=RolUsuario.vendedor, primer_login=True),
        Usuario(nombre="Pedro Bodeguero", email="bodega@ferremas.cl", rut="22222222-2",
                password_hash=hash_password("22222222-2"), rol=RolUsuario.bodeguero, primer_login=True),
        Usuario(nombre="Ana Contadora", email="contador@ferremas.cl", rut="33333333-3",
                password_hash=hash_password("33333333-3"), rol=RolUsuario.contador, primer_login=True),
        Usuario(nombre="Juan Cliente", email="cliente@test.cl", rut="44444444-4",
                password_hash=hash_password("cliente123"), rol=RolUsuario.cliente,
                primer_login=False, suscrito_noticias=True),
    ]
    db.add_all(usuarios)
    db.flush()

    # ── Categorías ────────────────────────────────────────────────────────────
    cats = {
        "Herramientas Manuales": Categoria(nombre="Herramientas Manuales", descripcion="Martillos, destornilladores, llaves y más"),
        "Herramientas Eléctricas": Categoria(nombre="Herramientas Eléctricas", descripcion="Taladros, sierras, lijadoras"),
        "Materiales de Construcción": Categoria(nombre="Materiales de Construcción", descripcion="Cemento, arena, ladrillos, pinturas"),
        "Equipos de Seguridad": Categoria(nombre="Equipos de Seguridad", descripcion="Cascos, guantes, lentes"),
        "Tornillos y Anclajes": Categoria(nombre="Tornillos y Anclajes", descripcion="Fijaciones y adhesivos"),
        "Equipos de Medición": Categoria(nombre="Equipos de Medición", descripcion="Metros, niveles, escuadras"),
    }
    for c in cats.values():
        db.add(c)
    db.flush()

    # ── Productos ─────────────────────────────────────────────────────────────
    productos = [
        # Herramientas Manuales
        Producto(codigo_ferremas="FER-10001", codigo_marca="STA-MART-500", nombre="Martillo Stanley 500g",
                 marca="Stanley", precio=12990, stock=45, categoria_id=cats["Herramientas Manuales"].id),
        Producto(codigo_ferremas="FER-10002", codigo_marca="STA-DEST-PH2", nombre="Destornillador Phillips Stanley",
                 marca="Stanley", precio=4990, stock=80, categoria_id=cats["Herramientas Manuales"].id),
        Producto(codigo_ferremas="FER-10003", codigo_marca="STA-LLA-12", nombre="Llave Ajustable 12'' Stanley",
                 marca="Stanley", precio=9990, stock=30, categoria_id=cats["Herramientas Manuales"].id),
        # Herramientas Eléctricas
        Producto(codigo_ferremas="FER-20001", codigo_marca="BOS-GSB-13", nombre="Taladro Percutor Bosch GSB 13 RE",
                 marca="Bosch", precio=89990, stock=15, categoria_id=cats["Herramientas Eléctricas"].id),
        Producto(codigo_ferremas="FER-20002", codigo_marca="MAK-HS6600", nombre="Sierra Circular Makita HS6600",
                 marca="Makita", precio=149990, stock=8, categoria_id=cats["Herramientas Eléctricas"].id),
        Producto(codigo_ferremas="FER-20003", codigo_marca="BOS-GEX-125", nombre="Lijadora Orbital Bosch GEX 125",
                 marca="Bosch", precio=64990, stock=12, categoria_id=cats["Herramientas Eléctricas"].id),
        # Materiales de Construcción
        Producto(codigo_ferremas="FER-30001", codigo_marca="SKA-CEM-42", nombre="Cemento Sika 42.5 kg",
                 marca="Sika", precio=7990, stock=200, categoria_id=cats["Materiales de Construcción"].id),
        Producto(codigo_ferremas="FER-30002", codigo_marca="SKA-IMP-5L", nombre="Impermeabilizante Sika 5L",
                 marca="Sika", precio=19990, stock=50, categoria_id=cats["Materiales de Construcción"].id),
        Producto(codigo_ferremas="FER-30003", codigo_marca="SUP-PINT-BLANC-4L", nombre="Pintura Látex Blanco 4L Superplast",
                 marca="Superplast", precio=12990, stock=75, categoria_id=cats["Materiales de Construcción"].id),
        # Equipos de Seguridad
        Producto(codigo_ferremas="FER-40001", codigo_marca="3M-CASC-E1", nombre="Casco de Seguridad 3M E1",
                 marca="3M", precio=8990, stock=60, categoria_id=cats["Equipos de Seguridad"].id),
        Producto(codigo_ferremas="FER-40002", codigo_marca="3M-GLOV-NIT", nombre="Guantes Nitrilo 3M (par)",
                 marca="3M", precio=2490, stock=150, categoria_id=cats["Equipos de Seguridad"].id),
        # Tornillos
        Producto(codigo_ferremas="FER-50001", codigo_marca="STA-TORN-100", nombre="Tornillos autorroscantes 100 un.",
                 marca="Stanley", precio=3490, stock=300, categoria_id=cats["Tornillos y Anclajes"].id),
        # Medición
        Producto(codigo_ferremas="FER-60001", codigo_marca="BOS-GLM-50", nombre="Medidor Láser Bosch GLM 50",
                 marca="Bosch", precio=54990, stock=20, categoria_id=cats["Equipos de Medición"].id),
    ]
    db.add_all(productos)
    db.commit()
    print(f"✅ Seed completado: {len(usuarios)} usuarios, {len(cats)} categorías, {len(productos)} productos.")
    db.close()


if __name__ == "__main__":
    seed()
