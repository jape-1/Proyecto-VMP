"""Prueba de integración con el detector real (marcada `lenta`).

No corre por defecto (`addopts = -m 'not lenta'`). Para ejecutarla hace falta:
1. el servicio de IA levantado (`ia_service`, con `best.pt`) en `IA_URL`;
2. el backend apuntando a él: `IA_MODO=http IA_URL=http://localhost:8001`;
3. una foto de un scooter o bicicleta en `tests/fixtures/`.

    pytest -m lenta tests/test_ia_real.py

Si no hay servicio o foto, la prueba se **omite** en vez de fallar: así queda
declarado en el README lo que no se pudo probar todavía.
"""

from pathlib import Path

import httpx
import pytest

from app.core.config import settings
from app.ia.cliente import ClienteIAHTTP

FIXTURES = Path(__file__).parent / "fixtures"

pytestmark = pytest.mark.lenta


def _imagen_de_prueba() -> Path | None:
    for nombre in ("scooter.jpg", "bicicleta.jpg", "scooter.png", "bicicleta.png"):
        ruta = FIXTURES / nombre
        if ruta.is_file():
            return ruta
    return None


@pytest.fixture(scope="module")
def detector():
    try:
        respuesta = httpx.get(f"{settings.ia_url.rstrip('/')}/v1/salud", timeout=3)
        respuesta.raise_for_status()
    except httpx.HTTPError as exc:
        pytest.skip(f"El servicio de IA no responde en {settings.ia_url}: {exc}")
    return ClienteIAHTTP()


def test_detector_real_reconoce_el_vehiculo(detector):
    imagen = _imagen_de_prueba()
    if imagen is None:
        pytest.skip(f"Falta una foto de ejemplo en {FIXTURES} (scooter.jpg o bicicleta.jpg).")

    resultado = detector.validar_ingreso(
        imagen.read_bytes(), "image/jpeg", ["scooter_electrico", "bicicleta"], imagen.name
    )
    assert resultado.detecciones, "El detector no encontró ningún vehículo en la foto."
    mejor = resultado.mejor
    assert mejor is not None
    assert mejor.clase in {"scooter", "bicicleta"}
    assert 0.0 <= mejor.confianza <= 1.0
    assert resultado.modelo_version, "El servicio debe informar la versión del modelo."


def test_detector_real_salud(detector):
    estado = detector.salud()
    assert estado["disponible"] is True


def test_detector_real_devuelve_la_semejanza_con_la_referencia(detector):
    """La misma foto como captura y como referencia: semejanza casi 1 (docs/26 §7.6)."""
    from app.core.enums import MAPA_CLASE_A_TIPOS
    from app.ia.cliente import Referencia

    imagen = _imagen_de_prueba()
    if imagen is None:
        pytest.skip(f"Falta una foto de ejemplo en {FIXTURES} (scooter.jpg o bicicleta.jpg).")
    contenido = imagen.read_bytes()
    clase = "bicicleta" if "bicicleta" in imagen.name else "scooter"
    tipo = MAPA_CLASE_A_TIPOS[clase][0].value

    resultado = detector.validar_ingreso(
        contenido, "image/jpeg", [tipo], imagen.name, [Referencia(41, tipo, contenido)]
    )
    assert resultado.comparador_version, "El servicio debe informar la versión del comparador."
    semejanzas = [s for d in resultado.detecciones for s in d.semejanzas]
    assert semejanzas, "El servicio no devolvió ninguna semejanza."
    assert {s.id_vehiculo for s in semejanzas} == {41}
    assert max(s.semejanza for s in semejanzas) > 0.99
