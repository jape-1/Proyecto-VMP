"""Tipos de columna reutilizables."""

from enum import StrEnum

from sqlalchemy import Enum as SAEnum


def enum_col(py_enum: type[StrEnum], nombre: str) -> SAEnum:
    """ENUM nativo de PostgreSQL usando los *valores* (no los nombres) del enum."""
    return SAEnum(
        py_enum,
        name=nombre,
        native_enum=True,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )
