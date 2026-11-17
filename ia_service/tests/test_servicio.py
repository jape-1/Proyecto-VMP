"""Lógica de comparación con dobles (docs/26 §4 y §7). No carga modelos."""

import pytest
from PIL import Image

from app.comparador import coseno, recortar
from app.servicio import Referencia, ServicioIA
from tests.conftest import imagen_de_color

ROJO, ROJO_OSCURO, NARANJA = (220, 30, 30), (120, 16, 16), (230, 150, 20)
VERDE, GRIS = (30, 200, 30), (128, 128, 128)


def test_coseno_de_un_vector_consigo_mismo_es_uno():
    assert coseno([0.6, 0.8], [0.6, 0.8]) == pytest.approx(1.0)
    assert coseno([1.0, 0.0], [0.0, 1.0]) == 0.0
    # Nunca sale del rango [0, 1], aunque los vectores apunten en sentidos opuestos.
    assert coseno([1.0, 0.0], [-1.0, 0.0]) == 0.0


def test_recortar_devuelve_la_zona_de_la_caja():
    imagen = Image.new("RGB", (200, 100), (0, 0, 0))
    recorte = recortar(imagen, [0.5, 0.0, 1.0, 1.0], margen=0.0)
    assert recorte.size == (100, 100)


def test_recortar_una_caja_degenerada_devuelve_la_imagen_completa():
    imagen = Image.new("RGB", (200, 100), (0, 0, 0))
    assert recortar(imagen, [0.5, 0.5, 0.5, 0.5]).size == (200, 100)


def test_misma_foto_como_captura_y_referencia_da_semejanza_uno(servicio: ServicioIA):
    foto = imagen_de_color(ROJO)
    detecciones = servicio.validar(foto, [Referencia(7, "scooter_electrico", foto)])

    assert len(detecciones) == 1
    assert detecciones[0].clase == "scooter"
    assert detecciones[0].semejanzas[0].id_vehiculo == 7
    assert detecciones[0].semejanzas[0].semejanza == pytest.approx(1.0, abs=1e-3)


def test_devuelve_una_semejanza_por_cada_referencia_compatible(servicio: ServicioIA):
    captura = imagen_de_color(ROJO)
    referencias = [
        Referencia(1, "scooter_electrico", imagen_de_color(NARANJA)),
        Referencia(2, "scooter_electrico", imagen_de_color(ROJO_OSCURO)),
    ]
    semejanzas = {
        s.id_vehiculo: s.semejanza for s in servicio.validar(captura, referencias)[0].semejanzas
    }

    assert set(semejanzas) == {1, 2}
    # El rojo oscuro es el mismo tono que la captura; el naranja no.
    assert semejanzas[2] > semejanzas[1]


def test_no_compara_con_referencias_de_otro_tipo(servicio: ServicioIA):
    captura = imagen_de_color(ROJO)  # scooter
    referencias = [Referencia(5, "bicicleta", imagen_de_color(VERDE))]
    assert servicio.validar(captura, referencias)[0].semejanzas == []


def test_referencia_sin_vehiculo_no_es_comparable(servicio: ServicioIA):
    captura = imagen_de_color(ROJO)
    referencias = [Referencia(5, "scooter_electrico", imagen_de_color(GRIS))]
    assert servicio.validar(captura, referencias)[0].semejanzas == []


def test_referencia_cuya_foto_muestra_otra_clase_no_es_comparable(servicio: ServicioIA):
    # Registrada como scooter, pero en su foto el detector ve una bicicleta.
    captura = imagen_de_color(ROJO)
    referencias = [Referencia(5, "scooter_electrico", imagen_de_color(VERDE))]
    assert servicio.validar(captura, referencias)[0].semejanzas == []


def test_captura_sin_vehiculo_no_devuelve_detecciones(servicio: ServicioIA):
    assert servicio.validar(imagen_de_color(GRIS), []) == []


def test_vector_de_referencia_se_calcula_una_vez_por_foto(servicio):
    """En video en vivo llegan las mismas referencias en cada cuadro."""
    llamadas = []
    original = servicio._calcular_vector_de_referencia

    def contar(referencia):
        llamadas.append(referencia.id_vehiculo)
        return original(referencia)

    servicio._calcular_vector_de_referencia = contar
    foto = imagen_de_color(NARANJA)
    referencia = Referencia(1, "scooter_electrico", imagen_de_color(NARANJA), huella="abc")
    primera = servicio.validar(foto, [referencia])
    segunda = servicio.validar(foto, [referencia])
    assert llamadas == [1]
    assert primera[0].semejanzas == segunda[0].semejanzas

    # Otra foto (otra huella) sí se calcula.
    servicio.validar(
        foto, [Referencia(1, "scooter_electrico", imagen_de_color(ROJO_OSCURO), "def")]
    )
    assert llamadas == [1, 1]
