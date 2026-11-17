"""Tablas de Notificaciones y Reportes.

El módulo **no se implementa** en este avance (docs/18 §2): solo se crean las
tablas para que el esquema sea el del ER (docs/18 §8).
"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.db_types import enum_col
from app.core.enums import CanalNotif, TipoNotificacion
from app.core.time import ahora


class Notificacion(Base):
    __tablename__ = "notificacion"

    id_notificacion: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_usuario_utp: Mapped[int] = mapped_column(
        ForeignKey("usuario_utp.id_usuario_utp"), nullable=False
    )
    id_sesion: Mapped[int | None] = mapped_column(
        ForeignKey("sesion_estacionamiento.id_sesion"), nullable=True
    )
    tipo_notificacion: Mapped[TipoNotificacion] = mapped_column(
        enum_col(TipoNotificacion, "tipo_notificacion"), nullable=False
    )
    mensaje: Mapped[str] = mapped_column(String(255), nullable=False)
    fecha_envio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=ahora
    )
    canal: Mapped[CanalNotif] = mapped_column(
        enum_col(CanalNotif, "canal_notif"),
        nullable=False,
        default=CanalNotif.app_utp,
        server_default=CanalNotif.app_utp.value,
    )


class ReportePiloto(Base):
    __tablename__ = "reporte_piloto"

    id_reporte: Mapped[int] = mapped_column(Integer, primary_key=True)
    periodo_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    periodo_fin: Mapped[date] = mapped_column(Date, nullable=False)
    tiempo_promedio_ingreso_seg: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_incidencias: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    nivel_satisfaccion_promedio: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    generado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=ahora
    )
