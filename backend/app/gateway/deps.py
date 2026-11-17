"""API Gateway interno: autenticación y autorización por rol (docs/10 §2)."""

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.enums import EstadoActivo, RolPersonal
from app.core.errors import ErrorNegocio
from app.core.security import decodificar_token
from app.modules.administracion.models import PersonalSeguridad
from app.modules.identidad.models import UsuarioUTP

esquema_portador = HTTPBearer(auto_error=False, description="JWT entregado por /dev/sesion/*")

ROL_USUARIO = "usuario"


def _claims(credenciales: HTTPAuthorizationCredentials | None) -> dict:
    if credenciales is None:
        raise ErrorNegocio("SIN_TOKEN", "Falta el encabezado Authorization: Bearer.", 401)
    return decodificar_token(credenciales.credentials)


def usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_portador),
    db: Session = Depends(get_db),
) -> UsuarioUTP:
    claims = _claims(credenciales)
    if claims.get("rol") != ROL_USUARIO:
        raise ErrorNegocio(
            "SIN_PERMISO",
            "Esta operación es solo para usuarios UTP.",
            403,
        )
    usuario = db.get(UsuarioUTP, int(claims["sub"]))
    if usuario is None:
        raise ErrorNegocio("TOKEN_INVALIDO", "La sesión ya no es válida.", 401)
    return usuario


def personal_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_portador),
    db: Session = Depends(get_db),
) -> PersonalSeguridad:
    claims = _claims(credenciales)
    if claims.get("rol") not in (RolPersonal.seguridad.value, RolPersonal.administrador.value):
        raise ErrorNegocio(
            "SIN_PERMISO",
            "Esta operación es solo para personal de seguridad.",
            403,
        )
    personal = db.get(PersonalSeguridad, int(claims["sub"]))
    if personal is None or personal.estado != EstadoActivo.activo:
        raise ErrorNegocio("TOKEN_INVALIDO", "La sesión ya no es válida.", 401)
    return personal


def _claims_eventos(request: Request, credenciales: HTTPAuthorizationCredentials | None) -> dict:
    """Igual que `_claims`, pero admite `?token=` para el SSE.

    `EventSource` del navegador no puede enviar el encabezado `Authorization`,
    así que el token viaja como parámetro. El servidor no lo registra en logs.
    """
    if credenciales is not None:
        return decodificar_token(credenciales.credentials)
    token = request.query_params.get("token")
    if not token:
        raise ErrorNegocio(
            "SIN_TOKEN",
            "Falta el token: usa Authorization: Bearer o ?token= en el stream.",
            401,
        )
    return decodificar_token(token)


def personal_actual_eventos(
    request: Request,
    credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_portador),
) -> int:
    """Personal autenticado para el SSE. Devuelve solo el id (la sesión se cierra aparte).

    Las dependencias con `yield` se cierran *antes* de enviar el stream en FastAPI,
    así que el generador del SSE abre su propia conexión a la base.
    """
    claims = _claims_eventos(request, credenciales)
    if claims.get("rol") not in (RolPersonal.seguridad.value, RolPersonal.administrador.value):
        raise ErrorNegocio("SIN_PERMISO", "Esta operación es solo para personal de seguridad.", 403)
    return int(claims["sub"])


def requiere_roles(*roles: RolPersonal):
    """Dependencia para exigir un rol concreto del personal."""

    def _verificar(personal: PersonalSeguridad = Depends(personal_actual)) -> PersonalSeguridad:
        if personal.rol not in roles:
            raise ErrorNegocio(
                "SIN_PERMISO",
                "Tu rol no tiene permiso para esta operación.",
                403,
                {"roles_permitidos": [r.value for r in roles]},
            )
        return personal

    return _verificar
