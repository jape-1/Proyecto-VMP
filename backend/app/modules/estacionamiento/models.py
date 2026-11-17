"""Módulo Estacionamiento e IA: sesiones de ingreso, eventos de IA e intentos de QR."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.db_types import enum_col
from app.core.enums import (
    EstadoEspacio,
    EstadoSesion,
    EstadoValidacion,
    ResultadoValidacion,
    TipoEventoIA,
)
from app.core.time import ahora


class ZonaEstacionamiento(Base):
    """Se crea vacía en este avance (docs/18 §8)."""

    __tablename__ = "zona_estacionamiento"
    __table_args__ = (UniqueConstraint("sede", "nombre_zona"),)

    id_zona: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre_zona: Mapped[str] = mapped_column(String(50), nullable=False)
    sede: Mapped[str] = mapped_column(String(50), nullable=False)
    capacidad_total: Mapped[int] = mapped_column(Integer, nullable=False)


class EspacioEstacionamiento(Base):
    __tablename__ = "espacio_estacionamiento"
    __table_args__ = (UniqueConstraint("id_zona", "codigo_espacio"),)

    id_espacio: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_zona: Mapped[int] = mapped_column(ForeignKey("zona_estacionamiento.id_zona"), nullable=False)
    codigo_espacio: Mapped[str] = mapped_column(String(10), nullable=False)
    estado: Mapped[EstadoEspacio] = mapped_column(
        enum_col(EstadoEspacio, "estado_espacio"),
        nullable=False,
        default=EstadoEspacio.disponible,
    )
    ultima_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=ahora
    )
    pos_x: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    pos_y: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    roi_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class SesionEstacionamiento(Base):
    __tablename__ = "sesion_estacionamiento"
    __table_args__ = (
        Index("ix_sesion_usuario_fecha", "id_usuario_utp", text("fecha_hora_ingreso DESC")),
        Index("ix_sesion_vehiculo", "id_vehiculo"),
        Index(
            "ux_sesion_vehiculo_dentro",
            "id_vehiculo",
            unique=True,
            postgresql_where=text(
                "estado_sesion = 'en_curso' AND resultado_validacion = 'validado' "
                "AND fecha_hora_salida IS NULL"
            ),
        ),
        Index(
            "ux_sesion_espacio_vigente",
            "id_espacio",
            unique=True,
            postgresql_where=text("id_espacio IS NOT NULL AND fecha_hora_salida IS NULL"),
        ),
    )

    id_sesion: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_vehiculo: Mapped[int | None] = mapped_column(
        ForeignKey("vehiculo_vmp.id_vehiculo"), nullable=True
    )
    id_usuario_utp: Mapped[int] = mapped_column(
        ForeignKey("usuario_utp.id_usuario_utp"), nullable=False
    )
    id_qr: Mapped[int] = mapped_column(ForeignKey("codigo_qr.id_qr"), nullable=False)
    id_espacio: Mapped[int | None] = mapped_column(
        ForeignKey("espacio_estacionamiento.id_espacio"), nullable=True
    )
    fecha_hora_ingreso: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=ahora
    )
    fecha_hora_salida: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resultado_validacion: Mapped[ResultadoValidacion | None] = mapped_column(
        enum_col(ResultadoValidacion, "resultado_valid"), nullable=True
    )
    estado_sesion: Mapped[EstadoSesion] = mapped_column(
        enum_col(EstadoSesion, "estado_sesion"),
        nullable=False,
        default=EstadoSesion.en_curso,
        server_default=EstadoSesion.en_curso.value,
    )

    # --- Brechas aprobadas 2026-11-15 ---------------------------------
    estado_validacion: Mapped[EstadoValidacion] = mapped_column(
        enum_col(EstadoValidacion, "estado_validacion"),
        nullable=False,
        default=EstadoValidacion.pendiente,
        server_default=EstadoValidacion.pendiente.value,
    )
    motivo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mejor_confianza: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    id_personal_decision: Mapped[int | None] = mapped_column(
        ForeignKey("personal_seguridad.id_personal"), nullable=True
    )
    fecha_decision: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_decision: Mapped[str | None] = mapped_column(String(255), nullable=True)


class EventoDeteccionIA(Base):
    __tablename__ = "evento_deteccion_ia"
    __table_args__ = (
        Index("ix_evento_espacio_fecha", "id_espacio", text("fecha_hora DESC")),
        Index("ix_evento_sesion", "id_sesion"),
    )

    id_evento: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_sesion: Mapped[int | None] = mapped_column(
        ForeignKey("sesion_estacionamiento.id_sesion"), nullable=True
    )
    id_espacio: Mapped[int | None] = mapped_column(
        ForeignKey("espacio_estacionamiento.id_espacio"), nullable=True
    )
    tipo_evento: Mapped[TipoEventoIA] = mapped_column(
        enum_col(TipoEventoIA, "tipo_evento_ia"), nullable=False
    )
    codigo_camara: Mapped[str] = mapped_column(String(20), nullable=False)
    imagen_capturada_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    score_confianza: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=ahora
    )
    event_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, unique=True, default=uuid4)

    # --- Brechas aprobadas 2026-11-15 (evidencia de docs/18 §5) -------
    modelo_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    detecciones: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    motivo: Mapped[str | None] = mapped_column(String(50), nullable=True)


class IntentoLecturaQR(Base):
    """Registro de intentos con QR inválido (docs/13 #5, opción A)."""

    __tablename__ = "intento_lectura_qr"
    __table_args__ = (Index("ix_intento_fecha", text("fecha_hora DESC")),)

    id_intento: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_hash_parcial: Mapped[str] = mapped_column(String(16), nullable=False)
    motivo: Mapped[str] = mapped_column(String(50), nullable=False)
    codigo_camara: Mapped[str | None] = mapped_column(String(20), nullable=True)
    id_personal: Mapped[int | None] = mapped_column(
        ForeignKey("personal_seguridad.id_personal"), nullable=True
    )
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=ahora
    )
