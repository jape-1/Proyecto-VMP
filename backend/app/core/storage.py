"""Almacenamiento de imágenes en disco local (docs/18 §3), con URLs firmadas."""

import io
from pathlib import Path
from uuid import uuid4

from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.core.errors import ErrorNegocio

FORMATOS_ACEPTADOS = {"JPEG", "PNG"}
MIME_ACEPTADOS = {"image/jpeg", "image/jpg", "image/png"}
LADO_MINIMO = 200
LADO_MAXIMO = 1280


def normalizar_imagen(contenido: bytes, content_type: str | None) -> bytes:
    """Valida tipo/tamaño real y re-codifica a JPEG (descarta EXIF, GPS incluido)."""
    if content_type and content_type.split(";")[0].strip().lower() not in MIME_ACEPTADOS:
        raise ErrorNegocio("FOTO_INVALIDA", "Solo se aceptan imágenes JPG o PNG.", 422)

    if not contenido:
        raise ErrorNegocio("FOTO_INVALIDA", "La imagen está vacía.", 422)

    if len(contenido) > settings.foto_max_mb * 1024 * 1024:
        raise ErrorNegocio(
            "FOTO_INVALIDA",
            f"La imagen supera el máximo de {settings.foto_max_mb} MB.",
            422,
            {"max_mb": settings.foto_max_mb},
        )

    try:
        with Image.open(io.BytesIO(contenido)) as imagen:
            formato = imagen.format
            imagen.load()
            if formato not in FORMATOS_ACEPTADOS:
                raise ErrorNegocio("FOTO_INVALIDA", "Solo se aceptan imágenes JPG o PNG.", 422)
            if imagen.width < LADO_MINIMO or imagen.height < LADO_MINIMO:
                raise ErrorNegocio(
                    "FOTO_INVALIDA",
                    "La imagen es demasiado pequeña.",
                    422,
                    {"minimo_px": LADO_MINIMO},
                )
            rgb = imagen.convert("RGB")
            rgb.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
            salida = io.BytesIO()
            rgb.save(salida, format="JPEG", quality=85, optimize=True)
            return salida.getvalue()
    except ErrorNegocio:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ErrorNegocio("FOTO_INVALIDA", "El archivo no es una imagen válida.", 422) from exc


def guardar_imagen(contenido: bytes, carpeta: str) -> str:
    """Guarda la imagen y devuelve su clave relativa (lo único que va a la BD)."""
    nombre = f"{uuid4().hex}.jpg"
    key = f"{carpeta.strip('/')}/{nombre}"
    destino = settings.media_root / key
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(contenido)
    return key


def ruta_de(key: str) -> Path:
    raiz = settings.media_root.resolve()
    destino = (raiz / key).resolve()
    if not destino.is_relative_to(raiz) or not destino.is_file():
        raise ErrorNegocio("ARCHIVO_NO_ENCONTRADO", "La imagen no existe.", 404)
    return destino


def url_de(key: str | None) -> str | None:
    if not key:
        return None
    from app.core.security import url_firmada

    return url_firmada(key)
