"""Comparador de semejanza: vector de imagen + coseno (docs/26 §2).

Responde la comprobación 3: ¿el vehículo de la cámara se parece al registrado?
No se entrena nada: una red preentrenada en ImageNet convierte cada recorte en un
vector, y la semejanza es el coseno entre vectores.

Limitación (docs/26 §6): dos vehículos del mismo modelo y color dan semejanza alta.
"""

from __future__ import annotations

from typing import Protocol

from PIL import Image


class Vectorizador(Protocol):
    version: str

    def vector(self, imagen: Image.Image) -> list[float]:
        """Vector de norma 1 que describe la imagen."""
        ...


def recortar(imagen: Image.Image, caja: list[float], margen: float = 0.05) -> Image.Image:
    """Recorta la caja normalizada [x1, y1, x2, y2], con un margen alrededor."""
    ancho, alto = imagen.size
    x1, y1, x2, y2 = caja
    dx, dy = (x2 - x1) * margen, (y2 - y1) * margen
    izquierda = max(0, round((x1 - dx) * ancho))
    arriba = max(0, round((y1 - dy) * alto))
    derecha = min(ancho, round((x2 + dx) * ancho))
    abajo = min(alto, round((y2 + dy) * alto))
    if derecha - izquierda < 2 or abajo - arriba < 2:
        return imagen
    return imagen.crop((izquierda, arriba, derecha, abajo))


def coseno(a: list[float], b: list[float]) -> float:
    """Semejanza coseno de dos vectores de norma 1, acotada a [0, 1]."""
    producto = sum(x * y for x, y in zip(a, b, strict=True))
    return min(max(producto, 0.0), 1.0)


class VectorizadorTorchvision:
    """Red de clasificación de torchvision sin su última capa."""

    MODELOS = ("resnet18", "resnet50")

    def __init__(self, nombre: str = "resnet18", device: str = "cpu") -> None:
        if nombre not in self.MODELOS:
            raise ValueError(f"Modelo de comparador no soportado: {nombre}. Usa {self.MODELOS}.")
        import torch  # imports diferidos: las pruebas rápidas no los necesitan
        from torchvision import models

        self._torch = torch
        if nombre == "resnet18":
            pesos = models.ResNet18_Weights.DEFAULT
            red = models.resnet18(weights=pesos)
        else:
            pesos = models.ResNet50_Weights.DEFAULT
            red = models.resnet50(weights=pesos)
        # Sin la capa que clasifica en 1000 categorías queda el vector descriptivo.
        red.fc = torch.nn.Identity()
        self._red = red.eval().to(device)
        self._preparar = pesos.transforms()
        self._device = device
        self.version = f"torchvision-{nombre}-{pesos.name.lower()}"

    def vector(self, imagen: Image.Image) -> list[float]:
        torch = self._torch
        entrada = self._preparar(imagen.convert("RGB")).unsqueeze(0).to(self._device)
        with torch.inference_mode():
            salida = self._red(entrada)
        salida = torch.nn.functional.normalize(salida, dim=1)
        return salida[0].cpu().tolist()
