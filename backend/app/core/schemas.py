"""Tipos y serializadores compartidos por los esquemas de la API."""

from datetime import datetime
from typing import Annotated

from pydantic import PlainSerializer

from app.core.time import iso_local

# Toda fecha sale en ISO-8601 con la zona de Lima (docs/18 §6).
FechaLima = Annotated[
    datetime,
    PlainSerializer(iso_local, return_type=str | None, when_used="json"),
]
FechaLimaOpcional = Annotated[
    datetime | None,
    PlainSerializer(iso_local, return_type=str | None, when_used="json"),
]
