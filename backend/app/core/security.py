"""Seguridad: JWT, contraseñas, hash de tokens y URLs firmadas.

Reglas del proyecto (docs/10): nunca se guarda ni se registra un token o una
contraseña en claro. El QR guarda un token opaco y en la base solo su hash.
"""

import base64
import hashlib
import hmac
import secrets
import time
from typing import Any

import bcrypt
import jwt

from app.core.config import settings
from app.core.errors import ErrorNegocio

PREFIJO_TOKEN_QR = "vmp1_"


# --- Contraseñas ------------------------------------------------------
def hash_password(password: str) -> str:
    # bcrypt solo considera los primeros 72 bytes
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt(rounds=12)).decode()


def verificar_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], password_hash.encode())
    except ValueError:
        return False


# --- JWT --------------------------------------------------------------
def crear_token(*, sub: int, rol: str) -> tuple[str, int]:
    expira_en = settings.jwt_expira_min * 60
    ahora = int(time.time())
    payload = {"sub": str(sub), "rol": rol, "iat": ahora, "exp": ahora + expira_en}
    return jwt.encode(payload, settings.jwt_secreto, algorithm=settings.jwt_algoritmo), expira_en


def decodificar_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secreto, algorithms=[settings.jwt_algoritmo])
    except jwt.ExpiredSignatureError as exc:
        raise ErrorNegocio("TOKEN_EXPIRADO", "La sesión expiró.", 401) from exc
    except jwt.PyJWTError as exc:
        raise ErrorNegocio("TOKEN_INVALIDO", "Token inválido.", 401) from exc


# --- Tokens opacos (QR) ----------------------------------------------
def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generar_token_qr(id_qr: int, id_usuario_utp: int) -> str:
    """Token determinista derivado de `id_qr` + `id_usuario_utp`.

    Así el QR se puede volver a dibujar cuando el usuario lo pide (HU06) sin
    guardar el token en claro: en la base solo queda `token_hash`. Sin el
    secreto del servidor el token es indistinguible de uno aleatorio.
    """
    mensaje = f"{id_qr}:{id_usuario_utp}".encode()
    firma = hmac.new(settings.qr_secreto.encode(), mensaje, hashlib.sha256).digest()
    cuerpo = base64.urlsafe_b64encode(firma).decode().rstrip("=")
    return f"{PREFIJO_TOKEN_QR}{cuerpo}"


def es_token_qr(token: str) -> bool:
    return token.startswith(PREFIJO_TOKEN_QR) and len(token) > len(PREFIJO_TOKEN_QR) + 20


def token_para_log(token: str) -> str:
    """Fragmento no reversible para poder auditar un intento sin guardar el token."""
    return hashlib.sha256(token.encode()).hexdigest()[:12]


def nuevo_secreto(n_bytes: int = 32) -> str:
    return secrets.token_urlsafe(n_bytes)


# --- URLs firmadas de imágenes ---------------------------------------
def _firma_media(key: str, expira: int) -> str:
    mensaje = f"media|{key}|{expira}".encode()
    return hmac.new(settings.media_secreto.encode(), mensaje, hashlib.sha256).hexdigest()


def url_firmada(key: str) -> str:
    expira = int(time.time()) + settings.media_url_expira_seg
    firma = _firma_media(key, expira)
    return f"{settings.api_prefijo}/archivos/{key}?e={expira}&s={firma}"


def firma_valida(key: str, expira: int, firma: str) -> bool:
    if expira < int(time.time()):
        return False
    return hmac.compare_digest(_firma_media(key, expira), firma)
