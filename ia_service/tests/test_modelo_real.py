"""Prueba de humo con los modelos reales: `pytest -m lenta`.

Necesita `pesos/E2-3clases-best.pt` y fotos en `tests/fixtures/` (ninguno está en
Git). Si falta algo, las pruebas se omiten.

OJO: esto **no mide** el modelo. Solo comprueba que carga y responde con la forma
esperada. Las métricas salen del cuaderno de Colab (`resultados/`), y el umbral de
semejanza se mide con fotos propias (docs/26 §5).
"""

import math
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import settings

pytestmark = pytest.mark.lenta

FIXTURES = Path(__file__).parent / "fixtures"
CLASE_DE = {"scooter": "scooter", "bicicleta": "bicicleta", "moto": "moto_electrica"}
TIPO_DE = {"scooter": "scooter_electrico", "bicicleta": "bicicleta", "moto": "moto_electrica"}


def _foto(nombre: str) -> Path:
    ruta = FIXTURES / nombre
    if not ruta.is_file():
        pytest.skip(f"Falta la foto de ejemplo {ruta.name} (tests/fixtures no está en Git).")
    return ruta


@pytest.fixture(scope="module")
def servicio_real():
    if not settings.modelo_path.is_file():
        pytest.skip(f"Faltan los pesos del detector: {settings.modelo_path}")
    from app.main import obtener_servicio

    return obtener_servicio()


def test_el_detector_tiene_las_tres_clases(servicio_real):
    assert servicio_real.detector.clases == ["scooter", "bicicleta", "moto_electrica"]


@pytest.mark.parametrize("prefijo", ["scooter", "bicicleta", "moto"])
def test_detecta_la_clase_de_la_foto_de_ejemplo(servicio_real, prefijo):
    detecciones = servicio_real.detectar(Image.open(_foto(f"{prefijo}-1.jpg")).convert("RGB"))
    assert detecciones, "no detectó ningún vehículo"
    assert detecciones[0].clase == CLASE_DE[prefijo]
    assert 0 < detecciones[0].confianza <= 1
    assert all(0 <= v <= 1 for v in detecciones[0].caja)


def test_el_vector_tiene_norma_uno(servicio_real):
    vector = servicio_real.vectorizador.vector(Image.open(_foto("scooter-1.jpg")).convert("RGB"))
    assert math.sqrt(sum(v * v for v in vector)) == pytest.approx(1.0, abs=1e-4)


def test_la_misma_foto_contra_si_misma_da_semejanza_casi_uno(servicio_real):
    from app.servicio import Referencia

    foto = Image.open(_foto("scooter-1.jpg")).convert("RGB")
    detecciones = servicio_real.validar(foto, [Referencia(1, "scooter_electrico", foto)])
    assert detecciones[0].semejanzas[0].semejanza == pytest.approx(1.0, abs=1e-3)


def test_api_completa_con_los_modelos_reales(servicio_real):
    from app.main import app

    captura = _foto("bicicleta-1.jpg").read_bytes()
    otra = _foto("bicicleta-2.jpg").read_bytes()
    with TestClient(app) as cliente:
        salud = cliente.get("/v1/salud").json()
        respuesta = cliente.post(
            "/v1/validar",
            files=[
                ("imagen", ("captura.jpg", captura, "image/jpeg")),
                ("referencias", ("ref-1.jpg", captura, "image/jpeg")),
                ("referencias", ("ref-2.jpg", otra, "image/jpeg")),
            ],
            data={
                "referencias_meta": '[{"id_vehiculo": 1, "tipo_vmp": "bicicleta"},'
                ' {"id_vehiculo": 2, "tipo_vmp": "bicicleta"}]'
            },
        )
    assert salud["clases"] == ["scooter", "bicicleta", "moto_electrica"]
    assert respuesta.status_code == 200, respuesta.text
    semejanzas = {
        s["id_vehiculo"]: s["semejanza"] for s in respuesta.json()["detecciones"][0]["semejanzas"]
    }
    # La misma foto se parece más a sí misma que a la de otra bicicleta.
    assert semejanzas[1] > 0.99
    if 2 in semejanzas:
        assert semejanzas[2] < semejanzas[1]
