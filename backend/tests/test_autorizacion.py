"""Autorización por rol y salud del servicio (docs/18 §7.6)."""

from fastapi.testclient import TestClient

from tests.conftest import API


def test_sin_token_da_401(cliente: TestClient):
    respuesta = cliente.get(f"{API}/usuarios/me")
    assert respuesta.status_code == 401
    cuerpo = respuesta.json()
    assert cuerpo["codigo"] == "SIN_TOKEN"
    assert cuerpo["request_id"]


def test_token_basura_da_401(cliente: TestClient):
    respuesta = cliente.get(f"{API}/usuarios/me", headers={"Authorization": "Bearer no.es.un.jwt"})
    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "TOKEN_INVALIDO"


def test_usuario_no_puede_usar_rutas_del_guardia(cliente: TestClient, token_usuario):
    cabeceras = token_usuario()
    respuesta = cliente.post(
        f"{API}/acceso/qr", json={"token": "vmp1_" + "a" * 43}, headers=cabeceras
    )
    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "SIN_PERMISO"

    estado = cliente.get(f"{API}/acceso/1", headers=cabeceras)
    assert estado.status_code == 403

    decision = cliente.post(
        f"{API}/acceso/1/decision", json={"decision": "rechazar"}, headers=cabeceras
    )
    assert decision.status_code == 403


def test_guardia_no_puede_usar_rutas_del_usuario(cliente: TestClient, token_guardia):
    cabeceras = token_guardia()
    for metodo, ruta in (
        ("get", f"{API}/usuarios/me"),
        ("get", f"{API}/usuarios/me/vehiculos"),
        ("get", f"{API}/usuarios/me/qr"),
    ):
        respuesta = getattr(cliente, metodo)(ruta, headers=cabeceras)
        assert respuesta.status_code == 403, (ruta, respuesta.status_code)
        assert respuesta.json()["codigo"] == "SIN_PERMISO"


def test_salud_informa_estado_de_ia(cliente: TestClient):
    respuesta = cliente.get("/salud")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "ok"
    assert cuerpo["base_datos"] == "ok"
    assert cuerpo["ia"]["disponible"] is True
    assert respuesta.headers["X-Request-Id"]


def test_request_id_se_respeta_si_viene(cliente: TestClient):
    respuesta = cliente.get("/salud", headers={"X-Request-Id": "abc123"})
    assert respuesta.headers["X-Request-Id"] == "abc123"


def test_rutas_dev_ocultas_fuera_de_dev(monkeypatch):
    """Con ENTORNO=prod las rutas /dev/* no están registradas."""
    import importlib

    from app.core.config import settings

    monkeypatch.setattr(settings, "entorno", "prod")
    modulo = importlib.reload(importlib.import_module("app.main"))
    rutas = set(modulo.app.openapi()["paths"])
    assert not any(ruta.startswith(f"{API}/dev") for ruta in rutas)
    monkeypatch.undo()
    importlib.reload(importlib.import_module("app.main"))
