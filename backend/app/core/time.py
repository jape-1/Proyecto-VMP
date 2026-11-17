"""Fechas del negocio: se guardan en UTC y se muestran en America/Lima."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.core.config import settings

TZ_NEGOCIO = ZoneInfo(settings.tz_negocio)


def ahora() -> datetime:
    """Instante actual en UTC (con zona, para columnas `timestamptz`)."""
    return datetime.now(UTC)


def a_local(valor: datetime) -> datetime:
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=UTC)
    return valor.astimezone(TZ_NEGOCIO)


def iso_local(valor: datetime | None) -> str | None:
    """ISO-8601 con zona de Lima, p. ej. 2026-11-15T16:38:00-05:00."""
    if valor is None:
        return None
    return a_local(valor).isoformat(timespec="seconds")
