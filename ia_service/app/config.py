"""Configuración del servicio de IA, por variables de entorno."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

IA_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Pesos del detector (fuera de Git, ver pesos/LEEME.md).
    modelo_path: Path = IA_DIR / "pesos" / "E2-3clases-best.pt"
    modelo_version: str = "E2-3clases"
    imgsz: int = 640
    device: str = "cpu"
    # Confianza mínima para que el detector devuelva una caja. Es baja a propósito:
    # el umbral que decide (IA_UMBRAL_VALIDADO) lo aplica el backend, no este servicio.
    confianza_minima: float = 0.25
    max_detecciones: int = 10

    # Red preentrenada que convierte un recorte en vector (docs/26 §2).
    comparador_modelo: str = "resnet18"
    # Margen alrededor de la caja al recortar, como fracción del lado de la caja.
    margen_recorte: float = 0.05


settings = Settings()
