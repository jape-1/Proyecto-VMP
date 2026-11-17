"""Módulo Identidad y Accesos: usuarios UTP, sincronización, vehículos y QR (docs/04 §2)."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.db_types import enum_col
from app.core.enums import (
    EstadoActivo,
    EstadoMatricula,
    EstadoQR,
    OrigenSync,
    ResultadoSync,
    TipoUsuario,
    TipoVMP,
)
from app.core.time import ahora


class UsuarioUTP(Base):
    __tablename__ = "usuario_utp"

    id_usuario_utp: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo_utp: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    tipo_usuario: Mapped[TipoUsuario] = mapped_column(
        enum_col(TipoUsuario, "tipo_usuario"), nullable=False
    )
    nombres: Mapped[str] = mapped_column(String(100), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(100), nullable=False)
    correo_institucional: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    sede: Mapped[str] = mapped_column(String(50), nullable=False)
    estado_matricula: Mapped[EstadoMatricula] = mapped_column(
        enum_col(EstadoMatricula, "estado_matricula"),
        nullable=False,
        default=EstadoMatricula.activo,
        server_default=EstadoMatricula.activo.value,
    )
    fecha_ultima_sincronizacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # BRECHA 4 (aprobada 2026-11-15)
    acepta_tratamiento_datos: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    fecha_consentimiento: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    version_consentimiento: Mapped[str | None] = mapped_column(String(20), nullable=True)

    vehiculos: Mapped[list["VehiculoVMP"]] = relationship(back_populates="usuario", lazy="selectin")
    codigos_qr: Mapped[list["CodigoQR"]] = relationship(back_populates="usuario", lazy="selectin")


class SincronizacionUTP(Base):
    __tablename__ = "sincronizacion_utp"
    __table_args__ = (Index("ix_sync_usuario_fecha", "id_usuario_utp", text("fecha_hora DESC")),)

    id_sincronizacion: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_usuario_utp: Mapped[int] = mapped_column(
        ForeignKey("usuario_utp.id_usuario_utp"), nullable=False
    )
    origen: Mapped[OrigenSync] = mapped_column(enum_col(OrigenSync, "origen_sync"), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=ahora
    )
    resultado: Mapped[ResultadoSync] = mapped_column(
        enum_col(ResultadoSync, "resultado_sync"), nullable=False
    )


class VehiculoVMP(Base):
    __tablename__ = "vehiculo_vmp"
    __table_args__ = (
        Index("ix_vehiculo_usuario", "id_usuario_utp", postgresql_where=text("estado = 'activo'")),
    )

    id_vehiculo: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_usuario_utp: Mapped[int] = mapped_column(
        ForeignKey("usuario_utp.id_usuario_utp"), nullable=False
    )
    tipo_vmp: Mapped[TipoVMP] = mapped_column(enum_col(TipoVMP, "tipo_vmp"), nullable=False)
    marca: Mapped[str] = mapped_column(String(50), nullable=False)
    modelo: Mapped[str | None] = mapped_column(String(50), nullable=True)  # BRECHA 2
    color: Mapped[str] = mapped_column(String(50), nullable=False)
    caracteristica_distintiva: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Nullable hasta que se sube la foto (HU03): el vehículo se crea antes.
    foto_referencia_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=ahora
    )
    estado: Mapped[EstadoActivo] = mapped_column(
        enum_col(EstadoActivo, "estado_activo"),
        nullable=False,
        default=EstadoActivo.activo,
        server_default=EstadoActivo.activo.value,
    )

    usuario: Mapped[UsuarioUTP] = relationship(back_populates="vehiculos")


class CodigoQR(Base):
    __tablename__ = "codigo_qr"
    __table_args__ = (
        Index(
            "ux_qr_activo_por_usuario",
            "id_usuario_utp",
            unique=True,
            postgresql_where=text("estado = 'activo'"),
        ),
    )

    id_qr: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_usuario_utp: Mapped[int] = mapped_column(
        ForeignKey("usuario_utp.id_usuario_utp"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    fecha_generacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=ahora
    )
    fecha_expiracion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estado: Mapped[EstadoQR] = mapped_column(
        enum_col(EstadoQR, "estado_qr"),
        nullable=False,
        default=EstadoQR.activo,
        server_default=EstadoQR.activo.value,
    )

    usuario: Mapped[UsuarioUTP] = relationship(back_populates="codigos_qr")
