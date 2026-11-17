"""Punto de entrada del backend: la app FastAPI que levanta uvicorn.

Arranque en desarrollo:
    uvicorn app.main:app --reload
"""

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.errors import (
    nuevo_request_id,
    registrar_manejadores,
    request_id_actual,
)
from app.core.logging import configurar_logs
from app.gateway.archivos import router as router_archivos
from app.ia.cliente import obtener_cliente_ia
from app.modules.estacionamiento.router import router as router_acceso
from app.modules.estacionamiento.router import router_espacios
from app.modules.identidad.router import router as router_usuarios

logger = logging.getLogger(__name__)

DESCRIPCION = """\
Backend del **servicio de estacionamiento de VMP** (UTP Torre Arequipa), avance 1.

Cubre dos flujos:
- **Usuario**: perfil con consentimiento, hasta 3 VMP con foto de referencia y su código QR.
- **Guardia**: lectura del QR, captura de la foto, resultado del detector y decisión manual.

El detector de IA es un servicio aparte; aquí solo se consume por HTTP.
El backend decide los permisos, nunca el detector. Ver `docs/IA-CONTRATO.md`.
"""


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configurar_logs()
    settings.media_root.mkdir(parents=True, exist_ok=True)
    (settings.media_root / "referencias").mkdir(exist_ok=True)
    (settings.media_root / "capturas").mkdir(exist_ok=True)
    logger.info(
        "Backend listo | entorno=%s | ia=%s | media=%s",
        settings.entorno,
        settings.ia_modo,
        settings.media_root,
    )
    yield


app = FastAPI(
    title=settings.app_nombre,
    version=settings.app_version,
    description=DESCRIPCION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origenes_cors,
    allow_origin_regex=settings.regex_cors,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-Id"],
)


@app.middleware("http")
async def contexto_peticion(request: Request, call_next):
    """Asigna `request_id` a cada petición y lo devuelve en la cabecera."""
    request_id = request.headers.get("X-Request-Id") or nuevo_request_id()
    testigo = request_id_actual.set(request_id)
    inicio = time.perf_counter()
    try:
        respuesta = await call_next(request)
    finally:
        request_id_actual.reset(testigo)
    respuesta.headers["X-Request-Id"] = request_id
    duracion_ms = (time.perf_counter() - inicio) * 1000
    # Sin query string ni cuerpo: puede llevar tokens.
    logger.info(
        "%s %s -> %s (%.0f ms)",
        request.method,
        request.url.path,
        respuesta.status_code,
        duracion_ms,
    )
    return respuesta


registrar_manejadores(app)

# --- Rutas de negocio --------------------------------------------------
app.include_router(router_usuarios, prefix=settings.api_prefijo)
app.include_router(router_acceso, prefix=settings.api_prefijo)
app.include_router(router_espacios, prefix=settings.api_prefijo)
app.include_router(router_archivos, prefix=settings.api_prefijo)

if settings.es_dev:  # dev | test; nunca en prod
    from app.gateway.dev import router as router_dev

    app.include_router(router_dev, prefix=settings.api_prefijo)
    logger.info("Rutas /dev/* habilitadas (ENTORNO=%s)", settings.entorno)


# --- Salud -------------------------------------------------------------
@app.get("/salud", tags=["Comunes"], summary="Estado del backend y del detector")
def salud() -> dict:
    """Comprueba también la base de datos y el servicio de IA.

    El estado de la IA se informa, pero su caída **no** tumba el backend: el
    flujo del guardia sigue con decisión manual (docs/18 §7.7).
    """
    from sqlalchemy import text

    from app.core.db import engine

    base = "ok"
    try:
        with engine.connect() as conexion:
            conexion.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - queremos reportar cualquier fallo
        base = f"error: {type(exc).__name__}"

    return {
        "estado": "ok",
        "app": settings.app_nombre,
        "version": settings.app_version,
        "entorno": settings.entorno,
        "base_datos": base,
        "ia": obtener_cliente_ia().salud(),
    }


@app.get("/", include_in_schema=False)
def raiz() -> RedirectResponse:
    return RedirectResponse("/docs")
