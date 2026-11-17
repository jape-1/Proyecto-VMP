"""Tercera comprobación del ingreso: semejanza con la foto registrada (docs/26 §3 y §7).

El doble de la IA deduce todo del nombre del archivo de la captura:
«distinto» -> semejanza baja; «ultimo» -> se parece más al último vehículo
registrado; «ajeno» -> además del vehículo del usuario hay un scooter de otra persona.
"""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.estacionamiento.models import EventoDeteccionIA
from tests.conftest import API, imagen_png


def _ingresar(cliente: TestClient, guardia: dict, token: str, archivo: str) -> dict:
    lectura = cliente.post(f"{API}/acceso/qr", json={"token": token}, headers=guardia)
    assert lectura.status_code == 200, lectura.text
    id_sesion = lectura.json()["id_sesion"]
    captura = cliente.post(
        f"{API}/acceso/{id_sesion}/captura",
        files={"archivo": (archivo, imagen_png(), "image/png")},
        headers=guardia,
    )
    assert captura.status_code == 202, captura.text
    return cliente.get(f"{API}/acceso/{id_sesion}", headers=guardia).json()


def test_clase_correcta_y_semejanza_alta_valida(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr, db: Session
):
    _, ids = preparar_usuario(vehiculos=({"tipo_vmp": "scooter_electrico"},))
    estado = _ingresar(cliente, token_guardia(), token_qr(), "scooter.png")

    assert estado["estado"] == "validado"
    assert estado["id_vehiculo_reconocido"] == ids[0]
    assert estado["semejanza"] == 0.85
    assert estado["id_vehiculo_mas_parecido"] == ids[0]
    assert estado["detecciones"][0]["semejanzas"] == [{"id_vehiculo": ids[0], "semejanza": 0.85}]

    # La semejanza queda en la evidencia (RF17).
    evento = db.scalar(select(EventoDeteccionIA))
    assert evento.detecciones["semejanza"] == 0.85


def test_clase_correcta_y_semejanza_baja_va_a_verificar(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr
):
    _, ids = preparar_usuario(vehiculos=({"tipo_vmp": "scooter_electrico"},))
    estado = _ingresar(cliente, token_guardia(), token_qr(), "scooter_distinto.png")

    assert estado["estado"] == "verificar"
    assert estado["motivo"] == "SEMEJANZA_BAJA"
    assert estado["id_vehiculo_reconocido"] is None
    assert estado["semejanza"] == 0.2
    assert estado["id_vehiculo_mas_parecido"] == ids[0]
    assert estado["puede_decidir"] is True


def test_con_dos_vehiculos_de_la_misma_clase_elige_el_mas_parecido(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr
):
    _, ids = preparar_usuario(
        vehiculos=(
            {"marca": "Xiaomi", "archivo": "scooter1.png"},
            {"marca": "Segway", "archivo": "scooter2.png"},
        )
    )
    estado = _ingresar(cliente, token_guardia(), token_qr(), "scooter_ultimo.png")

    assert estado["estado"] == "validado"
    assert estado["id_vehiculo_reconocido"] == ids[1]
    assert estado["semejanza"] == 0.9


def test_vehiculo_sin_foto_de_referencia_va_a_verificar(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr
):
    cabeceras, _ = preparar_usuario()
    creado = cliente.post(
        f"{API}/usuarios/me/vehiculos",
        json={"tipo_vmp": "scooter_electrico", "marca": "Xiaomi", "color": "negro"},
        headers=cabeceras,
    )
    assert creado.status_code == 201, creado.text
    estado = _ingresar(cliente, token_guardia(), token_qr(), "scooter.png")

    assert estado["estado"] == "verificar"
    assert estado["motivo"] == "SIN_REFERENCIA_COMPARABLE"
    assert estado["semejanza"] is None


def test_un_vehiculo_ajeno_en_la_foto_no_provoca_rechazo(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr
):
    # Hallazgo 4: en la foto hay un scooter ajeno (0.95) y la bicicleta del usuario (0.80).
    _, ids = preparar_usuario(
        vehiculos=({"tipo_vmp": "bicicleta", "marca": "Trek", "archivo": "bicicleta.png"},)
    )
    estado = _ingresar(cliente, token_guardia(), token_qr(), "ajeno.png")

    assert estado["estado"] == "validado"
    assert estado["id_vehiculo_reconocido"] == ids[0]
    assert estado["confianza"] == 0.8


def test_clase_que_no_corresponde_rechaza_aunque_no_haya_semejanza(
    cliente: TestClient, preparar_usuario, token_guardia, token_qr
):
    preparar_usuario(
        vehiculos=({"tipo_vmp": "bicicleta", "marca": "Trek", "archivo": "bicicleta.png"},)
    )
    estado = _ingresar(cliente, token_guardia(), token_qr(), "scooter.png")

    assert estado["estado"] == "rechazado"
    assert estado["motivo"] == "VEHICULO_NO_COINCIDE"
    assert estado["semejanza"] is None
