"""Configuración de logs: sin datos personales, imágenes ni tokens (docs/10 §8)."""

import logging
import sys


def configurar_logs(nivel: str = "INFO") -> None:
    logging.basicConfig(
        level=nivel.upper(),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        stream=sys.stdout,
        force=True,
    )
    # httpx registra la URL completa de cada petición; no la queremos en los logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
