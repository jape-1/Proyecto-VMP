"""Errores uniformes de la API: `{codigo, mensaje, detalle, request_id}` (docs/07 §1)."""

import logging
import uuid
from contextvars import ContextVar
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

request_id_actual: ContextVar[str] = ContextVar("request_id", default="")


class ErrorNegocio(Exception):
    """Error con un código estable que el frontend traduce a un mensaje."""

    def __init__(
        self,
        codigo: str,
        mensaje: str,
        status_code: int = 409,
        detalle: dict[str, Any] | list[Any] | None = None,
    ) -> None:
        self.codigo = codigo
        self.mensaje = mensaje
        self.status_code = status_code
        self.detalle = detalle or {}
        super().__init__(mensaje)


def _cuerpo(codigo: str, mensaje: str, detalle: Any = None) -> dict[str, Any]:
    return {
        "codigo": codigo,
        "mensaje": mensaje,
        "detalle": detalle or {},
        "request_id": request_id_actual.get(),
    }


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ErrorNegocio)
    async def _error_negocio(_: Request, exc: ErrorNegocio) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_cuerpo(exc.codigo, exc.mensaje, exc.detalle),
        )

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
        errores = [
            {"campo": ".".join(str(p) for p in e.get("loc", [])), "mensaje": e.get("msg", "")}
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=_cuerpo("DATOS_INVALIDOS", "Los datos enviados no son válidos.", errores),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        mensaje = str(exc.detail) if exc.detail else "Error HTTP"
        return JSONResponse(
            status_code=exc.status_code,
            content=_cuerpo(f"HTTP_{exc.status_code}", mensaje),
        )

    @app.exception_handler(Exception)
    async def _inesperado(request: Request, exc: Exception) -> JSONResponse:
        # Sin datos personales en el log: solo ruta y tipo de error.
        logger.exception(
            "Error no controlado en %s %s (%s)",
            request.method,
            request.url.path,
            type(exc).__name__,
        )
        return JSONResponse(
            status_code=500,
            content=_cuerpo("ERROR_INTERNO", "Ocurrió un error inesperado."),
        )


def nuevo_request_id() -> str:
    return uuid.uuid4().hex
