"""Contrato HTTP (docs/IA-CONTRATO.md §3). Con dobles: no carga modelos."""

import json

from fastapi.testclient import TestClient

from tests.conftest import a_png, imagen_de_color

ROJO, VERDE, GRIS = (220, 30, 30), (30, 200, 30), (128, 128, 128)


def _png(color) -> tuple[str, bytes, str]:
    return ("foto.png", a_png(imagen_de_color(color)), "image/png")


def test_salud_informa_clases_y_versiones(cliente: TestClient):
    cuerpo = cliente.get("/v1/salud").json()
    assert cuerpo["estado"] == "ok"
    assert cuerpo["clases"] == ["scooter", "bicicleta", "moto_electrica"]
    assert cuerpo["modelo_version"]
    assert cuerpo["comparador_version"] == "falso-color-medio"


def test_validar_devuelve_detecciones_con_semejanzas(cliente: TestClient):
    respuesta = cliente.post(
        "/v1/validar",
        files=[("imagen", _png(ROJO)), ("referencias", _png(ROJO)), ("referencias", _png(VERDE))],
        data={
            "tipos_esperados": json.dumps(["scooter_electrico", "bicicleta"]),
            "referencias_meta": json.dumps(
                [
                    {"id_vehiculo": 12, "tipo_vmp": "scooter_electrico"},
                    {"id_vehiculo": 13, "tipo_vmp": "bicicleta"},
                ]
            ),
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"detecciones", "modelo_version", "comparador_version", "ms"}
    (deteccion,) = cuerpo["detecciones"]
    assert deteccion["clase"] == "scooter"
    assert 0 <= deteccion["confianza"] <= 1
    assert len(deteccion["caja"]) == 4
    # Solo la referencia del tipo compatible (el scooter 12).
    assert [s["id_vehiculo"] for s in deteccion["semejanzas"]] == [12]
    assert deteccion["semejanzas"][0]["semejanza"] > 0.99


def test_validar_sin_referencias_es_valido(cliente: TestClient):
    respuesta = cliente.post("/v1/validar", files=[("imagen", _png(ROJO))])
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["detecciones"][0]["semejanzas"] == []


def test_validar_sin_vehiculo_devuelve_lista_vacia(cliente: TestClient):
    respuesta = cliente.post("/v1/validar", files=[("imagen", _png(GRIS))])
    assert respuesta.status_code == 200
    assert respuesta.json()["detecciones"] == []


def test_validar_rechaza_meta_que_no_corresponde_a_los_archivos(cliente: TestClient):
    respuesta = cliente.post(
        "/v1/validar",
        files=[("imagen", _png(ROJO)), ("referencias", _png(ROJO))],
        data={"referencias_meta": "[]"},
    )
    assert respuesta.status_code == 422


def test_un_archivo_que_no_es_imagen_responde_error_y_no_200(cliente: TestClient):
    respuesta = cliente.post(
        "/v1/validar", files=[("imagen", ("nota.png", b"esto no es una imagen", "image/png"))]
    )
    assert respuesta.status_code == 422


def test_validar_foto_referencia_tiene_la_misma_forma(cliente: TestClient):
    respuesta = cliente.post("/v1/validar-foto-referencia", files=[("imagen", _png(VERDE))])
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["detecciones"][0]["clase"] == "bicicleta"
    assert "modelo_version" in cuerpo and "ms" in cuerpo
