"""Une detector y comparador. No conoce usuarios ni decide nada (docs/IA-CONTRATO.md §1)."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field

from PIL import Image

from app.comparador import Vectorizador, coseno, recortar
from app.detector import Deteccion, Detector

# Clase del detector -> tipos de VMP del backend. Debe coincidir con
# `MAPA_CLASE_A_TIPOS` de backend/app/core/enums.py.
TIPOS_POR_CLASE: dict[str, tuple[str, ...]] = {
    "scooter": ("scooter_electrico",),
    "bicicleta": ("bicicleta", "bicicleta_electrica"),
    "moto_electrica": ("moto_electrica",),
}


@dataclass
class Referencia:
    id_vehiculo: int
    tipo_vmp: str
    imagen: Image.Image
    # Huella de los bytes de la foto. Con ella se reutiliza el vector ya calculado:
    # en video en vivo llegan las mismas referencias varias veces por segundo.
    huella: str | None = None


@dataclass
class Semejanza:
    id_vehiculo: int
    semejanza: float


@dataclass
class DeteccionComparada:
    clase: str
    confianza: float
    caja: list[float]
    semejanzas: list[Semejanza] = field(default_factory=list)


class ServicioIA:
    def __init__(
        self,
        detector: Detector,
        vectorizador: Vectorizador,
        margen: float = 0.05,
        max_cache: int = 64,
    ):
        self.detector = detector
        self.vectorizador = vectorizador
        self.margen = margen
        self.max_cache = max_cache
        self._cache: OrderedDict[tuple[str, str], list[float] | None] = OrderedDict()

    def detectar(self, imagen: Image.Image) -> list[Deteccion]:
        return self.detector.detectar(imagen)

    def _vector_de_referencia(self, referencia: Referencia) -> list[float] | None:
        """Vector de la referencia; se calcula una sola vez por foto y tipo."""
        if referencia.huella is None:
            return self._calcular_vector_de_referencia(referencia)
        clave = (referencia.huella, referencia.tipo_vmp)
        if clave in self._cache:
            self._cache.move_to_end(clave)
            return self._cache[clave]
        vector = self._calcular_vector_de_referencia(referencia)
        self._cache[clave] = vector
        if len(self._cache) > self.max_cache:
            self._cache.popitem(last=False)
        return vector

    def _calcular_vector_de_referencia(self, referencia: Referencia) -> list[float] | None:
        """Vector del vehículo de la foto de referencia, o None si no se ve ninguno compatible."""
        compatibles = [
            d
            for d in self.detector.detectar(referencia.imagen)
            if referencia.tipo_vmp in TIPOS_POR_CLASE.get(d.clase, ())
        ]
        if not compatibles:
            return None
        mejor = max(compatibles, key=lambda d: d.confianza)
        return self.vectorizador.vector(recortar(referencia.imagen, mejor.caja, self.margen))

    def validar(
        self, imagen: Image.Image, referencias: list[Referencia]
    ) -> list[DeteccionComparada]:
        detecciones = self.detector.detectar(imagen)
        vectores = {r.id_vehiculo: self._vector_de_referencia(r) for r in referencias}

        comparadas: list[DeteccionComparada] = []
        for deteccion in detecciones:
            tipos = TIPOS_POR_CLASE.get(deteccion.clase, ())
            # Solo se compara con referencias de un tipo compatible con la clase detectada.
            candidatas = [r for r in referencias if r.tipo_vmp in tipos and vectores[r.id_vehiculo]]
            semejanzas: list[Semejanza] = []
            if candidatas:
                vector = self.vectorizador.vector(recortar(imagen, deteccion.caja, self.margen))
                semejanzas = [
                    Semejanza(r.id_vehiculo, round(coseno(vector, vectores[r.id_vehiculo]), 4))
                    for r in candidatas
                ]
            comparadas.append(
                DeteccionComparada(deteccion.clase, deteccion.confianza, deteccion.caja, semejanzas)
            )
        return comparadas
