"""Módulo Administración: personal de seguridad e incidencias (solo lo mínimo de este avance)."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.db_types import enum_col
from app.core.enums import (
    EstadoActivo,
    EstadoIncidencia,
    RolPersonal,
    TipoIncidencia,
    TurnoPersonal,
)
from app.core.time import ahora


class PersonalSeguridad(Base):
    __tablename__ = "personal_seguridad"

    id_personal: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombres: Mapped[str] = mapped_column(String(100), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(100), nullable=False)
    usuario_acceso: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    contrasena_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    turno: Mapped[TurnoPersonal] = mapped_column(
        enum_col(TurnoPersonal, "turno_personal"), nullable=False
    )
    # BRECHA 10 (aprobada 2026-11-15)
    rol: Mapped[RolPersonal] = mapped_column(
        enum_col(RolPersonal, "rol_personal"),
        nullable=False,
        default=RolPersonal.seguridad,
        server_default=RolPersonal.seguridad.value,
    )
    estado: Mapped[EstadoActivo] = mapped_column(
        enum_col(EstadoActivo, "estado_activo"),
        nullable=False,
        default=EstadoActivo.activo,
        server_default=EstadoActivo.activo.value,
    )


class Incidencia(Base):
    """Tabla creada pero sin flujo en este avance (docs/18 §2 y §8)."""

    __tablename__ = "incidencia"

    id_incidencia: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_sesion: Mapped[int] = mapped_column(
        ForeignKey("sesion_estacionamiento.id_sesion"), nullable=False
    )
    id_personal: Mapped[int | None] = mapped_column(
        ForeignKey("personal_seguridad.id_personal"), nullable=True
    )
    tipo_incidencia: Mapped[TipoIncidencia] = mapped_column(
        enum_col(TipoIncidencia, "tipo_incidencia"), nullable=False
    )
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=ahora
    )
    resuelta: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    estado: Mapped[EstadoIncidencia] = mapped_column(
        enum_col(EstadoIncidencia, "estado_incidencia"),
        nullable=False,
        default=EstadoIncidencia.abierta,
        server_default=EstadoIncidencia.abierta.value,
    )
    evidencia_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    comentario_cierre: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_cierre: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
