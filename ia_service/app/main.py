"""API del servicio de IA. Contrato: docs/IA-CONTRATO.md y docs/26 §4.

Si algo falla se responde con un código HTTP de error (nunca 200 con un mensaje):
el backend lo trata como «IA no disponible» y el guardia decide a mano.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import time
from functools import lru_cache
from typing import Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from app.config import settings
from app.servicio import Referencia, ServicioIA

logger = logging.getLogger(__name__)

MAX_REFERENCIAS = 3

app = FastAPI(title="VMP · Servicio de IA", version="0.1.0")


@lru_cache
def obtener_servicio() -> ServicioIA:
    """Carga los modelos una sola vez, en la primera petición."""
    from app.comparador import VectorizadorTorchvision
    from app.detector import DetectorYOLO

    detector = DetectorYOLO(
        settings.modelo_path,
        imgsz=settings.imgsz,
        device=settings.device,
        confianza_minima=settings.confianza_minima,
        max_detecciones=settings.max_detecciones,
    )
    vectorizador = VectorizadorTorchvision(settings.comparador_modelo, settings.device)
    return ServicioIA(detector, vectorizador, settings.margen_recorte)


def _servicio() -> ServicioIA:
    try:
        return obtener_servicio()
    except Exception as exc:  # pesos ausentes, sin memoria, etc.
        logger.exception("No se pudieron cargar los modelos")
        raise HTTPException(503, f"Modelos no disponibles: {type(exc).__name__}") from exc


def _abrir_con_huella(archivo: UploadFile) -> tuple[Image.Image, str]:
    datos = archivo.file.read()
    try:
        imagen = Image.open(io.BytesIO(datos))
        imagen.load()
        return imagen.convert("RGB"), hashlib.sha256(datos).hexdigest()
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(422, f"«{archivo.filename}» no es una imagen válida.") from exc


def _abrir(archivo: UploadFile) -> Image.Image:
    return _abrir_con_huella(archivo)[0]


def _referencia(meta: dict, archivo: UploadFile) -> Referencia:
    imagen, huella = _abrir_con_huella(archivo)
    return Referencia(int(meta["id_vehiculo"]), str(meta["tipo_vmp"]), imagen, huella)


@app.get("/v1/salud")
def salud(servicio: ServicioIA = Depends(_servicio)) -> dict[str, Any]:
    return {
        "estado": "ok",
        "modelo_version": settings.modelo_version,
        "clases": servicio.detector.clases,
        "comparador_version": servicio.vectorizador.version,
        "device": settings.device,
    }


@app.post("/v1/validar")
def validar(
    imagen: UploadFile = File(...),
    tipos_esperados: str = Form("[]"),  # informativo: la correspondencia la hace el backend
    referencias: list[UploadFile] = File(default=[]),
    referencias_meta: str = Form("[]"),
    servicio: ServicioIA = Depends(_servicio),
) -> dict[str, Any]:
    inicio = time.perf_counter()
    try:
        meta = json.loads(referencias_meta)
        if not isinstance(meta, list):
            raise ValueError("referencias_meta no es una lista")
        lista = [_referencia(m, archivo) for m, archivo in zip(meta, referencias, strict=True)]
    except HTTPException:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            422, "`referencias_meta` debe traer un elemento por cada archivo de `referencias`."
        ) from exc
    if len(lista) > MAX_REFERENCIAS:
        raise HTTPException(422, f"Se admiten como máximo {MAX_REFERENCIAS} referencias.")

    comparadas = servicio.validar(_abrir(imagen), lista)
    return {
        "detecciones": [
            {
                "clase": d.clase,
                "confianza": round(d.confianza, 4),
                "caja": d.caja,
                "semejanzas": [
                    {"id_vehiculo": s.id_vehiculo, "semejanza": s.semejanza} for s in d.semejanzas
                ],
            }
            for d in comparadas
        ],
        "modelo_version": settings.modelo_version,
        "comparador_version": servicio.vectorizador.version,
        "ms": int((time.perf_counter() - inicio) * 1000),
    }


@app.post("/v1/validar-foto-referencia")
def validar_foto_referencia(
    imagen: UploadFile = File(...),
    servicio: ServicioIA = Depends(_servicio),
) -> dict[str, Any]:
    inicio = time.perf_counter()
    detecciones = servicio.detectar(_abrir(imagen))
    return {
        "detecciones": [
            {"clase": d.clase, "confianza": round(d.confianza, 4), "caja": d.caja}
            for d in detecciones
        ],
        "modelo_version": settings.modelo_version,
        "ms": int((time.perf_counter() - inicio) * 1000),
    }
