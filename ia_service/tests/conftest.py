"""Dobles para probar el servicio sin cargar los modelos reales.

- `DetectorFalso`: «ve» un vehículo según el color dominante de la imagen
  (rojo -> scooter, verde -> bicicleta, azul -> moto_electrica, gris -> nada).
- `VectorizadorFalso`: el vector es el color medio de la imagen, normalizado.
"""

import io
import math
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageStat

from app.detector import Deteccion
from app.main import _servicio, app
from app.servicio import ServicioIA

CAJA = [0.25, 0.25, 0.75, 0.75]


def imagen_de_color(color: tuple[int, int, int], lado: int = 64) -> Image.Image:
    return Image.new("RGB", (lado, lado), color)


def a_png(imagen: Image.Image) -> bytes:
    buffer = io.BytesIO()
    imagen.save(buffer, format="PNG")
    return buffer.getvalue()


class DetectorFalso:
    clases = ["scooter", "bicicleta", "moto_electrica"]

    def detectar(self, imagen: Image.Image) -> list[Deteccion]:
        r, g, b = ImageStat.Stat(imagen).mean[:3]
        if max(r, g, b) - min(r, g, b) < 30:  # gris: no hay vehículo
            return []
        clase = self.clases[[r, g, b].index(max(r, g, b))]
        return [Deteccion(clase, 0.9, CAJA)]


class VectorizadorFalso:
    version = "falso-color-medio"

    def vector(self, imagen: Image.Image) -> list[float]:
        medias = ImageStat.Stat(imagen.convert("RGB")).mean[:3]
        norma = math.sqrt(sum(m * m for m in medias)) or 1.0
        return [m / norma for m in medias]


@pytest.fixture
def servicio() -> ServicioIA:
    return ServicioIA(DetectorFalso(), VectorizadorFalso())


@pytest.fixture
def cliente(servicio: ServicioIA) -> Iterator[TestClient]:
    app.dependency_overrides[_servicio] = lambda: servicio
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
