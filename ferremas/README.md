# FERREMAS – Plataforma de Comercio Electrónico
**Asignatura:** ASY5131 – Integración de Plataformas  
**Stack:** Python · FastAPI · SQLite · HTML/CSS/JS

---

## 📁 Estructura del proyecto

```
ferremas/
├── main.py                     # Punto de entrada principal
├── requirements.txt
├── backend/
│   ├── database/
│   │   └── database.py         # Conexión SQLite + SQLAlchemy
│   ├── models/
│   │   └── models.py           # Tablas de la BD (ORM)
│   ├── schemas/
│   │   └── schemas.py          # Validación de datos (Pydantic)
│   ├── routers/
│   │   ├── auth.py             # Login, registro, cambio de contraseña
│   │   ├── productos.py        # Catálogo + API pública externa
│   │   ├── pedidos.py          # Flujo completo de pedidos por rol
│   │   ├── pagos.py            # Webpay + transferencias
│   │   ├── admin.py            # Gestión usuarios + reportes
│   │   └── extras.py           # Divisas (Banco Central) + Contacto
│   ├── services/
│   │   ├── auth_service.py     # JWT, hashing, control de roles
│   │   ├── webpay_service.py   # Integración Transbank Webpay Plus
│   │   └── divisa_service.py   # Integración API Banco Central Chile
│   └── seed.py                 # Datos iniciales de prueba
└── frontend/
    ├── templates/
    │   └── index.html          # SPA principal
    └── static/
        ├── css/styles.css
        └── js/app.js
```

---

## ⚙️ Instalación y ejecución

### 1. Crear entorno virtual (recomendado)
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Poblar la base de datos con datos de prueba
```bash
python -m backend.seed
```

### 4. Ejecutar el servidor
```bash
uvicorn main:app --reload
```

### 5. Abrir en el navegador
| URL | Descripción |
|-----|-------------|
| http://localhost:8000 | Frontend FERREMAS |
| http://localhost:8000/docs | Documentación Swagger (Postman alternativo) |
| http://localhost:8000/redoc | Documentación ReDoc |

---

## 👥 Cuentas de prueba

| Rol | Email | Contraseña |
|-----|-------|------------|
| Administrador | admin@ferremas.cl | 12345678-9 |
| Vendedor | vendedor@ferremas.cl | 11111111-1 |
| Bodeguero | bodega@ferremas.cl | 22222222-2 |
| Contador | contador@ferremas.cl | 33333333-3 |
| Cliente | cliente@test.cl | cliente123 |

> ⚠️ Los usuarios internos (admin, vendedor, bodeguero, contador) deben cambiar su contraseña en el primer inicio de sesión.

---

## 🔗 APIs externas integradas

### Webpay Plus (Transbank)
- Ambiente: **Sandbox (integración)**
- Endpoint: `POST /api/pagos/webpay/iniciar/{pedido_id}`
- Retorno: `GET /api/pagos/webpay/retorno?token_ws=...`
- Documentación oficial: https://www.transbankdevelopers.cl/

### Banco Central de Chile – Tipo de cambio
- Endpoint: `GET /api/divisas/convertir?monto=100&moneda=USD`
- Endpoint: `GET /api/divisas/tipos-cambio`
- ⚠️ Requiere credenciales: editar `backend/services/divisa_service.py`
  - Registrarse en: https://si3.bcentral.cl/estadisticas/
  - En desarrollo usa valores de fallback automáticamente.

---

## 🏛️ Arquitectura por capas

```
┌─────────────────────────────────────────────┐
│              CAPA DE PRESENTACIÓN            │
│         HTML · CSS · JavaScript              │
├─────────────────────────────────────────────┤
│              CAPA DE NEGOCIO                 │
│    FastAPI Routers + Services (Python)       │
│    Auth · Pedidos · Pagos · Divisas          │
├─────────────────────────────────────────────┤
│              CAPA DE DATOS                   │
│    SQLAlchemy ORM → SQLite (o MySQL)         │
│    Modelos: Usuario, Producto, Pedido, Pago  │
└─────────────────────────────────────────────┘
          ↕ APIs externas
    Webpay (Transbank) · Banco Central
```

---

## 📋 Endpoints principales de la API pública

```
GET  /api/productos/api/catalogo          → catálogo completo (consumo externo)
GET  /api/productos/api/detalle/{codigo}  → detalle de un producto
GET  /api/divisas/convertir               → conversión de divisas
GET  /api/divisas/tipos-cambio            → tipos de cambio vigentes
POST /api/contacto                        → formulario de contacto
```

---

## 🗄️ Migración a MySQL (para entrega final)

Cambiar en `backend/database/database.py`:
```python
# SQLite (desarrollo)
DATABASE_URL = "sqlite:///./ferremas.db"

# MySQL (producción)
DATABASE_URL = "mysql+pymysql://usuario:password@localhost:3306/ferremas"
```
Instalar driver: `pip install pymysql`
