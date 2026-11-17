"""Configuración de las pruebas.

Importante: las variables de entorno se fijan **antes** de importar `app`,
porque `settings` y el `engine` se construyen al importar el módulo.

Las pruebas usan la base `vmp_test`, que se recrea con `alembic upgrade head`
en cada corrida. La IA se sustituye por el stub (`IA_MODO=stub`), así que no
dependen del modelo real.
"""

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

MEDIA_TMP = Path(tempfile.mkdtemp(prefix="vmp-media-test-"))

# La base de pruebas se RECREA en cada corrida (DROP SCHEMA): nunca apuntar a una base con datos.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://postgres:admin@localhost:5432/vmp_test"
)
os.environ["ENTORNO"] = "test"
os.environ["IA_MODO"] = "stub"
os.environ["JWT_SECRETO"] = "secreto-jwt-de-pruebas-con-mas-de-32-bytes"
os.environ["QR_SECRETO"] = "secreto-qr-de-pruebas-con-mas-de-32-bytes"
os.environ["MEDIA_SECRETO"] = "secreto-media-de-pruebas-con-mas-de-32-by"
os.environ["MEDIA_ROOT"] = str(MEDIA_TMP)
os.environ["IA_UMBRAL_VALIDADO"] = "0.60"
os.environ["IA_UMBRAL_SEMEJANZA"] = "0.70"
os.environ["DB_ECHO"] = "false"

import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from alembic import command  # noqa: E402
from app.core.db import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402

API = "/api/v1"

TABLAS = (
    "notificacion",
    "reporte_piloto",
    "incidencia",
    "evento_deteccion_ia",
    "intento_lectura_qr",
    "sesion_estacionamiento",
    "espacio_estacionamiento",
    "zona_estacionamiento",
    "codigo_qr",
    "vehiculo_vmp",
    "sincronizacion_utp",
    "usuario_utp",
    "personal_seguridad",
)


def _recrear_esquema() -> None:
    with engine.begin() as conexion:
        conexion.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conexion.execute(text("CREATE SCHEMA public"))
    configuracion = Config(str(BASE_DIR / "alembic.ini"))
    configuracion.set_main_option("script_location", str(BASE_DIR / "alembic"))
    command.upgrade(configuracion, "head")


@pytest.fixture(scope="session", autouse=True)
def esquema() -> Iterator[None]:
    """Esquema limpio una vez por corrida (Alembic, no `create_all`)."""
    _recrear_esquema()
    yield


@pytest.fixture(autouse=True)
def limpiar() -> Iterator[None]:
    with engine.begin() as conexion:
        conexion.execute(text(f"TRUNCATE {', '.join(TABLAS)} RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture(autouse=True)
def personal_de_prueba(limpiar) -> Iterator[None]:
    """Dos guardias activos por prueba: las rutas de `/dev/sesion/guardia/*` los necesitan."""
    from app.core.enums import RolPersonal, TurnoPersonal
    from app.modules.administracion.models import PersonalSeguridad

    sesion = SessionLocal()
    try:
        sesion.add_all(
            [
                PersonalSeguridad(
                    nombres="Carlos",
                    apellidos="Quispe Mamani",
                    usuario_acceso="guardia.tarde",
                    contrasena_hash="x",
                    turno=TurnoPersonal.tarde,
                    rol=RolPersonal.seguridad,
                ),
                PersonalSeguridad(
                    nombres="Jefe",
                    apellidos="de Seguridad",
                    usuario_acceso="admin.seguridad",
                    contrasena_hash="x",
                    turno=TurnoPersonal.manana,
                    rol=RolPersonal.administrador,
                ),
            ]
        )
        sesion.commit()
    finally:
        sesion.close()
    yield


@pytest.fixture
def db() -> Iterator[Session]:
    sesion = SessionLocal()
    try:
        yield sesion
    finally:
        sesion.close()


@pytest.fixture
def cliente() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------
def imagen_png(lado: int = 320) -> bytes:
    """Imagen válida (>= 200 px) para las pruebas de subida."""
    from io import BytesIO

    buffer = BytesIO()
    Image.new("RGB", (lado, lado), (90, 120, 160)).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def png() -> bytes:
    return imagen_png()


@pytest.fixture
def token_usuario(cliente: TestClient):
    """Devuelve una función `token(codigo_utp)` que ya viene autenticada."""

    def _token(codigo_utp: str = "U90000001") -> dict[str, str]:
        respuesta = cliente.post(f"{API}/dev/sesion/usuario/{codigo_utp}")
        assert respuesta.status_code == 200, respuesta.text
        return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}

    return _token


@pytest.fixture
def token_guardia(cliente: TestClient):
    def _token(usuario_acceso: str = "guardia.tarde") -> dict[str, str]:
        respuesta = cliente.post(f"{API}/dev/sesion/guardia/{usuario_acceso}")
        assert respuesta.status_code == 200, respuesta.text
        return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}

    return _token


@pytest.fixture
def preparar_usuario(cliente: TestClient, token_usuario):
    """Perfil con consentimiento + N vehículos con foto. Devuelve (cabeceras, ids)."""

    def _preparar(
        codigo_utp: str = "U90000001",
        vehiculos: tuple[dict, ...] = (),
        con_consentimiento: bool = True,
    ) -> tuple[dict[str, str], list[int]]:
        cabeceras = token_usuario(codigo_utp)
        if con_consentimiento:
            respuesta = cliente.put(
                f"{API}/usuarios/me/perfil",
                json={"acepta_tratamiento_datos": True, "version_consentimiento": "2026-11"},
                headers=cabeceras,
            )
            assert respuesta.status_code == 200, respuesta.text

        ids: list[int] = []
        for datos in vehiculos:
            respuesta = cliente.post(
                f"{API}/usuarios/me/vehiculos",
                json={
                    "tipo_vmp": datos.get("tipo_vmp", "scooter_electrico"),
                    "marca": datos.get("marca", "Xiaomi"),
                    "modelo": datos.get("modelo", "Mi 3"),
                    "color": datos.get("color", "negro"),
                    "caracteristica_distintiva": datos.get("caracteristica_distintiva"),
                },
                headers=cabeceras,
            )
            assert respuesta.status_code == 201, respuesta.text
            id_vehiculo = respuesta.json()["id_vehiculo"]
            ids.append(id_vehiculo)

            respuesta = cliente.post(
                f"{API}/usuarios/me/vehiculos/{id_vehiculo}/foto",
                files={"archivo": (datos.get("archivo", "scooter.png"), imagen_png(), "image/png")},
                headers=cabeceras,
            )
            assert respuesta.status_code == 200, respuesta.text

        return cabeceras, ids

    return _preparar


@pytest.fixture
def token_qr(db: Session):
    """Token real del QR de un usuario (caja blanca: la API solo devuelve el PNG)."""
    from app.modules.identidad import service

    def _token(codigo_utp: str = "U90000001") -> str:
        usuario = service.sincronizar_usuario(db, codigo_utp)
        qr = service.obtener_qr(db, usuario)
        return service.token_de_qr(qr)

    return _token
