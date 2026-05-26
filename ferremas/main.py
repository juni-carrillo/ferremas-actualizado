from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
import os

from backend.database.database import engine
from backend.models.models import Base
from backend.routers import auth, productos, pedidos, pagos, admin
from backend.routers.extras import router_divisas, router_contacto

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FERREMAS API",
    description="Plataforma de comercio electrónico FERREMAS",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers API
app.include_router(auth.router,        prefix="/api")
app.include_router(productos.router,   prefix="/api")
app.include_router(pedidos.router,     prefix="/api")
app.include_router(pagos.router,       prefix="/api")
app.include_router(admin.router,       prefix="/api")
app.include_router(router_divisas,     prefix="/api")
app.include_router(router_contacto,    prefix="/api")

# Archivos estáticos (CSS, JS) — con middleware anti-caché
frontend_path = os.path.join(os.path.dirname(__file__), "frontend", "static")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.middleware("http")
async def no_cache_static(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
    return response

INDEX = os.path.join(os.path.dirname(__file__), "frontend", "templates", "index.html")

@app.get("/", include_in_schema=False)
def root(request: Request):
    """
    Sirve el index.html para cualquier query string (ej: /?pago=ok, /?pago=cancelado).
    Los query params los lee el JS del frontend con URLSearchParams.
    """
    return FileResponse(
        INDEX,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
            "Content-Security-Policy": "upgrade-insecure-requests",
        }
    )

@app.get("/health", tags=["Sistema"])
def health():
    return {"estado": "ok", "servicio": "FERREMAS API", "version": "1.0.0"}
