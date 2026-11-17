"""Detector de VMP: YOLO26 con los pesos E2-3clases (docs/25 §1).

Responde las comprobaciones 1 y 2 de docs/26: ¿hay un VMP? ¿de qué clase?
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from PIL import Image


@dataclass
class Deteccion:
    clase: str
    confianza: float
    caja: list[float]  # [x1, y1, x2, y2] normalizada entre 0 y 1


class Detector(Protocol):
    clases: list[str]

    def detectar(self, imagen: Image.Image) -> list[Deteccion]: ...


class DetectorYOLO:
    def __init__(
        self,
        ruta_pesos: Path,
        imgsz: int = 640,
        device: str = "cpu",
        confianza_minima: float = 0.25,
        max_detecciones: int = 10,
    ) -> None:
        if not Path(ruta_pesos).is_file():
            raise FileNotFoundError(
                f"No están los pesos del detector en {ruta_pesos}. Ver ia_service/pesos/LEEME.md."
            )
        from ultralytics import YOLO  # import diferido: tarda y las pruebas rápidas no lo usan

        self._modelo = YOLO(str(ruta_pesos))
        self._imgsz = imgsz
        self._device = device
        self._confianza_minima = confianza_minima
        self._max_detecciones = max_detecciones
        self.clases = [self._modelo.names[i] for i in sorted(self._modelo.names)]

    def detectar(self, imagen: Image.Image) -> list[Deteccion]:
        resultados = self._modelo.predict(
            source=imagen,
            imgsz=self._imgsz,
            conf=self._confianza_minima,
            max_det=self._max_detecciones,
            device=self._device,
            save=False,
            verbose=False,
        )
        resultado = resultados[0]
        if resultado.boxes is None:
            return []
        cajas = resultado.boxes.xyxyn.cpu().tolist()
        confianzas = resultado.boxes.conf.cpu().tolist()
        clases = resultado.boxes.cls.int().cpu().tolist()
        detecciones = [
            Deteccion(
                clase=resultado.names[clase],
                confianza=float(confianza),
                caja=[round(min(max(float(v), 0.0), 1.0), 4) for v in caja],
            )
            for caja, confianza, clase in zip(cajas, confianzas, clases, strict=True)
        ]
        return sorted(detecciones, key=lambda d: d.confianza, reverse=True)
