"""Cliente del servicio de IA (docs/18 §5, docs/26). El backend decide; la IA solo mide.

Es síncrono a propósito: las rutas se declaran `def` y FastAPI las ejecuta en su
pool de hilos, igual que las consultas a PostgreSQL. Una sola forma de bloquear.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Protocol

import httpx

from app.core.config import settings


class ErrorIA(Exception):
    """El servicio de IA no respondió o respondió algo inutilizable."""


@dataclass
class Referencia:
    """Foto de referencia de un vehículo registrado, para comparar (docs/26 §4)."""

    id_vehiculo: int
    tipo_vmp: str
    imagen: bytes


@dataclass
class Semejanza:
    id_vehiculo: int
    semejanza: float


@dataclass
class Deteccion:
    clase: str
    confianza: float
    caja: list[float] | None = None
    semejanzas: list[Semejanza] = field(default_factory=list)

    def a_dict(self) -> dict[str, Any]:
        return {
            "clase": self.clase,
            "confianza": round(self.confianza, 4),
            "caja": self.caja,
            "semejanzas": [
                {"id_vehiculo": s.id_vehiculo, "semejanza": round(s.semejanza, 4)}
                for s in self.semejanzas
            ],
        }


@dataclass
class ResultadoIA:
    detecciones: list[Deteccion]
    modelo_version: str | None = None
    ms: int | None = None
    error: str | None = None
    comparador_version: str | None = None

    @property
    def mejor(self) -> Deteccion | None:
        return max(self.detecciones, key=lambda d: d.confianza) if self.detecciones else None


class ClienteIA(Protocol):
    def validar_ingreso(
        self,
        imagen: bytes,
        content_type: str,
        tipos_esperados: list[str],
        nombre_archivo: str = "captura.jpg",
        referencias: list[Referencia] | None = None,
    ) -> ResultadoIA: ...

    def validar_foto_referencia(
        self,
        imagen: bytes,
        content_type: str,
        nombre_archivo: str = "referencia.jpg",
    ) -> ResultadoIA: ...

    def salud(self) -> dict[str, Any]: ...


# ---------------------------------------------------------------------
# Implementación HTTP: el contrato que implementa el servicio de IA real
# ---------------------------------------------------------------------
class ClienteIAHTTP:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.ia_url).rstrip("/")

    def _post(self, ruta: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{self.base_url}{ruta}"
        try:
            with httpx.Client(timeout=settings.ia_timeout_seg) as cliente:
                respuesta = cliente.post(url, **kwargs)
            respuesta.raise_for_status()
            return respuesta.json()
        except httpx.TimeoutException as exc:
            raise ErrorIA("Tiempo de espera agotado") from exc
        except httpx.HTTPError as exc:
            raise ErrorIA(f"El servicio de IA falló: {type(exc).__name__}") from exc
        except ValueError as exc:
            raise ErrorIA("El servicio de IA devolvió una respuesta ilegible") from exc

    def validar_ingreso(
        self,
        imagen: bytes,
        content_type: str,
        tipos_esperados: list[str],
        nombre_archivo: str = "captura.jpg",
        referencias: list[Referencia] | None = None,
    ) -> ResultadoIA:
        referencias = referencias or []
        archivos = [("imagen", (nombre_archivo, imagen, content_type))]
        archivos += [
            ("referencias", (f"referencia-{r.id_vehiculo}.jpg", r.imagen, "image/jpeg"))
            for r in referencias
        ]
        meta = [{"id_vehiculo": r.id_vehiculo, "tipo_vmp": r.tipo_vmp} for r in referencias]
        datos = self._post(
            "/v1/validar",
            files=archivos,
            data={
                "tipos_esperados": json.dumps(tipos_esperados),
                "referencias_meta": json.dumps(meta),
            },
        )
        return _parsear(datos)

    def validar_foto_referencia(
        self,
        imagen: bytes,
        content_type: str,
        nombre_archivo: str = "referencia.jpg",
    ) -> ResultadoIA:
        datos = self._post(
            "/v1/validar-foto-referencia",
            files={"imagen": (nombre_archivo, imagen, content_type)},
        )
        return _parsear(datos, campos_referencia=True)

    def salud(self) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=min(settings.ia_timeout_seg, 3)) as cliente:
                respuesta = cliente.get(f"{self.base_url}/v1/salud")
            respuesta.raise_for_status()
            return {"disponible": True, **respuesta.json()}
        except Exception as exc:  # el estado de salud nunca debe tumbar /salud
            return {"disponible": False, "error": type(exc).__name__}


def _parsear(datos: dict[str, Any], campos_referencia: bool = False) -> ResultadoIA:
    try:
        crudas = datos.get("detecciones") or []
        detecciones = [
            Deteccion(
                clase=str(d["clase"]),
                confianza=float(d.get("confianza", 0.0)),
                caja=d.get("caja"),
                semejanzas=[
                    Semejanza(int(s["id_vehiculo"]), float(s["semejanza"]))
                    for s in (d.get("semejanzas") or [])
                ],
            )
            for d in crudas
        ]
        if campos_referencia and not detecciones and datos.get("clase"):
            detecciones = [
                Deteccion(
                    clase=str(datos["clase"]),
                    confianza=float(datos.get("confianza", 0.0)),
                    caja=None,
                )
            ]
        return ResultadoIA(
            detecciones=detecciones,
            modelo_version=datos.get("modelo_version"),
            ms=int(datos["ms"]) if datos.get("ms") is not None else None,
            error=datos.get("error"),
            comparador_version=datos.get("comparador_version"),
        )
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise ErrorIA("El servicio de IA devolvió un formato no esperado") from exc


# ---------------------------------------------------------------------
# Stub: permite que todo funcione sin el detector (pruebas y demo)
# ---------------------------------------------------------------------
class ClienteIAStub:
    """Doble de prueba/demo. La clase se deduce del nombre del archivo.

    Semejanza (solo en el ingreso): 0.85 con cada referencia de un tipo compatible;
    "distinto" -> 0.20; "ultimo" -> 0.90 con la última referencia y 0.40 con las demás.
    "ajeno" -> un scooter ajeno (0.95) y una bicicleta (0.80) en la misma foto.

    Nombres reconocidos: contiene "vacio"/"nada" -> sin detecciones;
    "bicicleta" -> bicicleta; "moto" -> moto_electrica; "dudosa" -> confianza en zona
    gris; resto -> scooter.
    """

    version = "stub-v1"
    version_comparador = "stub-comparador-v1"

    def _detectar(self, nombre_archivo: str) -> list[Deteccion]:
        nombre = (nombre_archivo or "").lower()
        if any(p in nombre for p in ("vacio", "nada", "sin_vehiculo")):
            return []
        if "ajeno" in nombre:
            return [
                Deteccion("scooter", 0.95, [0.05, 0.30, 0.35, 0.85]),
                Deteccion("bicicleta", 0.80, [0.45, 0.25, 0.90, 0.85]),
            ]
        if "bicicleta" in nombre or "bike" in nombre:
            return [Deteccion("bicicleta", 0.92, [0.30, 0.25, 0.62, 0.79])]
        if "moto" in nombre:
            return [Deteccion("moto_electrica", 0.91, [0.28, 0.24, 0.66, 0.80])]
        if "dudosa" in nombre:
            return [Deteccion("scooter", 0.45, [0.31, 0.24, 0.60, 0.78])]
        return [Deteccion("scooter", 0.90, [0.31, 0.22, 0.62, 0.78])]

    def validar_ingreso(
        self,
        imagen: bytes,
        content_type: str,
        tipos_esperados: list[str],
        nombre_archivo: str = "captura.jpg",
        referencias: list[Referencia] | None = None,
    ) -> ResultadoIA:
        detecciones = self._detectar(nombre_archivo)
        for deteccion in detecciones:
            deteccion.semejanzas = self._comparar(deteccion, referencias or [], nombre_archivo)
        return ResultadoIA(
            detecciones=detecciones,
            modelo_version=self.version,
            ms=12,
            comparador_version=self.version_comparador,
        )

    def _comparar(
        self, deteccion: Deteccion, referencias: list[Referencia], nombre_archivo: str
    ) -> list[Semejanza]:
        from app.core.enums import MAPA_CLASE_A_TIPOS

        tipos = {t.value for t in MAPA_CLASE_A_TIPOS.get(deteccion.clase, ())}
        compatibles = [r for r in referencias if r.tipo_vmp in tipos]
        nombre = (nombre_archivo or "").lower()
        semejanzas = []
        for posicion, referencia in enumerate(compatibles):
            if "distinto" in nombre:
                valor = 0.20
            elif "ultimo" in nombre:
                valor = 0.90 if posicion == len(compatibles) - 1 else 0.40
            else:
                valor = 0.85
            semejanzas.append(Semejanza(referencia.id_vehiculo, valor))
        return semejanzas

    def validar_foto_referencia(
        self,
        imagen: bytes,
        content_type: str,
        nombre_archivo: str = "referencia.jpg",
    ) -> ResultadoIA:
        return ResultadoIA(
            detecciones=self._detectar(nombre_archivo),
            modelo_version=self.version,
            ms=10,
        )

    def salud(self) -> dict[str, Any]:
        return {
            "disponible": True,
            "estado": "ok",
            "modo": "stub",
            "modelo_version": self.version,
        }


@lru_cache
def obtener_cliente_ia() -> ClienteIA:
    if settings.ia_modo.lower() == "http":
        return ClienteIAHTTP()
    return ClienteIAStub()
