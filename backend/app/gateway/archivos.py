"""Entrega de imágenes con URL firmada y caducidad corta (docs/07 §4).

Nunca se sirve una imagen sin firma válida: la base solo guarda la clave
(`capturas/2026/11/15/abc.jpg`), y el frontend recibe
`/api/v1/archivos/<clave>?e=<epoch>&s=<hmac>`.
"""

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from app.core.errors import ErrorNegocio
from app.core.security import firma_valida
from app.core.storage import ruta_de

router = APIRouter(prefix="/archivos", tags=["Archivos"])


@router.get(
    "/{clave:path}",
    summary="Descarga una imagen con URL firmada",
    response_class=FileResponse,
)
def obtener_archivo(
    clave: str,
    e: int = Query(..., description="Expiración en segundos epoch"),
    s: str = Query(..., description="Firma HMAC de la clave y la expiración"),
) -> FileResponse:
    if not firma_valida(clave, e, s):
        raise ErrorNegocio(
            "ARCHIVO_NO_ENCONTRADO",
            "El enlace de la imagen venció o no es válido.",
            404,
        )
    destino = ruta_de(clave)
    return FileResponse(
        destino,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "private, max-age=300",
            "X-Content-Type-Options": "nosniff",
        },
    )
