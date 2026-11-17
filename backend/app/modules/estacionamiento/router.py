"""Endpoints del punto de acceso (tablet del guardia): HU07–HU12."""

import logging
import time
from collections.abc import Iterator

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, get_db
from app.core.enums import EstadoValidacion, RolPersonal
from app.core.errors import ErrorNegocio
from app.gateway.deps import personal_actual_eventos, requiere_roles
from app.modules.administracion.models import PersonalSeguridad
from app.modules.estacionamiento import service
from app.modules.estacionamiento.schemas import (
    AccesoQRIn,
    AccesoQROut,
    CapturaOut,
    CuadroOut,
    DecisionIn,
    EspaciosOut,
    SesionEstadoOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/acceso", tags=["Guardia"])

ROLES_ACCESO = requiere_roles(RolPersonal.seguridad, RolPersonal.administrador)

# El SSE consulta la base cada segundo y se corta solo: el frontend reconecta.
INTERVALO_SSE_SEG = 1.0
LATIDO_SSE_SEG = 15.0
MAX_SSE_SEG = 180.0


@router.post(
    "/qr",
    response_model=AccesoQROut,
    status_code=status.HTTP_200_OK,
    summary="Lee el QR y abre la sesión de ingreso (HU07/HU08)",
)
def leer_qr(
    datos: AccesoQRIn,
    db: Session = Depends(get_db),
    personal: PersonalSeguridad = Depends(ROLES_ACCESO),
) -> AccesoQROut:
    """Valida el token, consulta el Conector UTP y crea la sesión en `pendiente`.

    Los intentos con QR inválido, vencido o revocado quedan registrados en
    `intento_lectura_qr` (docs/18 §7.5) con un fragmento del hash, nunca el token.
    """
    return service.crear_sesion(db, datos.token, personal.id_personal)


@router.post(
    "/{id_sesion}/captura",
    response_model=CapturaOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Sube la foto del vehículo y lanza la IA (HU09)",
)
def subir_captura(
    id_sesion: int,
    tareas: BackgroundTasks,
    archivo: UploadFile = File(..., description="JPG o PNG, máximo 5 MB"),
    db: Session = Depends(get_db),
    personal: PersonalSeguridad = Depends(ROLES_ACCESO),
) -> CapturaOut:
    """Responde 202 de inmediato; la IA corre en segundo plano.

    El guardia consulta `GET /acceso/{id_sesion}` (o el stream) para el resultado.
    """
    contenido = archivo.file.read()
    key = service.registrar_captura(
        db,
        id_sesion,
        contenido,
        archivo.content_type,
        archivo.filename or "captura.jpg",
    )
    tareas.add_task(service.procesar_captura_ia, id_sesion, key, archivo.filename or "")
    return CapturaOut(
        id_sesion=id_sesion,
        estado=EstadoValidacion.pendiente,
        mensaje=service.MENSAJES[EstadoValidacion.pendiente],
    )


@router.post(
    "/{id_sesion}/cuadro",
    response_model=CuadroOut,
    summary="Analiza un cuadro del video en vivo, sin guardarlo",
)
def analizar_cuadro(
    id_sesion: int,
    archivo: UploadFile = File(..., description="Cuadro del video, JPG"),
    db: Session = Depends(get_db),
    personal: PersonalSeguridad = Depends(ROLES_ACCESO),
) -> CuadroOut:
    """Responde con lo que la IA ve en este cuadro y el veredicto que tendría.

    No cambia la sesión ni guarda la imagen. La decisión oficial, con evidencia,
    se toma al enviar el cuadro elegido a `/captura`.
    """
    return service.analizar_cuadro(
        db,
        id_sesion,
        archivo.file.read(),
        archivo.content_type,
        archivo.filename or "cuadro.jpg",
    )


@router.get(
    "/{id_sesion}",
    response_model=SesionEstadoOut,
    summary="Estado del ingreso: pendiente, validado, verificar o rechazado (HU10/HU11)",
)
def estado_sesion(
    id_sesion: int,
    db: Session = Depends(get_db),
    personal: PersonalSeguridad = Depends(ROLES_ACCESO),
) -> SesionEstadoOut:
    return service.obtener_estado(db, id_sesion)


@router.get(
    "/{id_sesion}/stream",
    summary="Stream SSE con el resultado de la IA (HU11/HU12)",
    response_class=StreamingResponse,
)
def stream_sesion(
    id_sesion: int,
    _personal: int = Depends(personal_actual_eventos),
) -> StreamingResponse:
    """Server-Sent Events: empuja el estado cuando cambia.

    Autenticación: `Authorization: Bearer …` o `?token=…` (limitación de
    `EventSource`). Emite `event: estado` con el mismo JSON que `GET /{id}` y un
    comentario de latido cada 15 s. Se cierra al llegar a un estado que ya no
    cambia solo (validado / rechazado) o al agotar el tiempo máximo.
    """
    return StreamingResponse(
        _eventos(id_sesion),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _eventos(id_sesion: int) -> Iterator[str]:
    inicio = time.monotonic()
    ultimo_json: str | None = None
    ultimo_latido = inicio

    # Comprobación inicial sin base de datos abierta de más: el generador abre y
    # cierra su propia sesión (las dependencias con `yield` ya no están vivas aquí).
    db = SessionLocal()
    try:
        estado = service.obtener_estado(db, id_sesion)
        ultimo_json = estado.model_dump_json()
        yield f"event: estado\ndata: {ultimo_json}\n\n"
        if _estado_terminal(estado):
            return
    finally:
        db.close()

    while time.monotonic() - inicio < MAX_SSE_SEG:
        time.sleep(INTERVALO_SSE_SEG)
        db = SessionLocal()
        try:
            estado = service.obtener_estado(db, id_sesion)
            payload = estado.model_dump_json()
            if payload != ultimo_json:
                ultimo_json = payload
                yield f"event: estado\ndata: {payload}\n\n"
            if _estado_terminal(estado):
                return
        except ErrorNegocio:
            yield 'event: error\ndata: {"codigo": "SESION_NO_ENCONTRADA"}\n\n'
            return
        finally:
            db.close()

        if time.monotonic() - ultimo_latido >= LATIDO_SSE_SEG:
            ultimo_latido = time.monotonic()
            yield ": latido\n\n"

    yield 'event: fin\ndata: {"motivo": "tiempo_maximo"}\n\n'


def _estado_terminal(estado: SesionEstadoOut) -> bool:
    if estado.estado in (EstadoValidacion.validado, EstadoValidacion.rechazado):
        return True
    return False


@router.post(
    "/{id_sesion}/decision",
    response_model=SesionEstadoOut,
    summary="Aprueba o rechaza manualmente (HU12)",
)
def decidir_sesion(
    id_sesion: int,
    datos: DecisionIn,
    db: Session = Depends(get_db),
    personal: PersonalSeguridad = Depends(ROLES_ACCESO),
) -> SesionEstadoOut:
    """La IA nunca cierra un rechazo: lo cierra una persona, y queda registrado."""
    return service.decidir(db, id_sesion, personal.id_personal, datos)


@router.post(
    "/{id_sesion}/cancelar",
    response_model=SesionEstadoOut,
    summary="Cancela un ingreso a medias (HU07)",
)
def cancelar_sesion(
    id_sesion: int,
    db: Session = Depends(get_db),
    personal: PersonalSeguridad = Depends(ROLES_ACCESO),
) -> SesionEstadoOut:
    return service.cancelar(db, id_sesion)


# ---------------------------------------------------------------------
# Espacios (HU17 básico, 17-nov-2026): solo seguridad y administración (RF21)
# ---------------------------------------------------------------------
router_espacios = APIRouter(prefix="/espacios", tags=["Espacios"])


@router_espacios.get(
    "",
    response_model=EspaciosOut,
    summary="Espacios libres y ocupados por zona, con quién ocupa cada uno",
)
def listar_espacios(
    db: Session = Depends(get_db),
    personal: PersonalSeguridad = Depends(ROLES_ACCESO),
) -> EspaciosOut:
    return service.resumen_espacios(db)


@router_espacios.post(
    "/{id_espacio}/liberar",
    response_model=EspaciosOut,
    summary="Registra la salida del vehículo de ese espacio y lo deja libre",
)
def liberar_espacio(
    id_espacio: int,
    db: Session = Depends(get_db),
    personal: PersonalSeguridad = Depends(ROLES_ACCESO),
) -> EspaciosOut:
    """Mientras no haya cámaras de casillas (HU15), la salida la marca el guardia."""
    return service.liberar_espacio(db, id_espacio)
