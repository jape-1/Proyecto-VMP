"""Acceso a datos del módulo Identidad (nadie fuera del módulo usa esto)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import EstadoActivo, EstadoQR, OrigenSync, ResultadoSync
from app.core.time import ahora
from app.modules.identidad.models import (
    CodigoQR,
    SincronizacionUTP,
    UsuarioUTP,
    VehiculoVMP,
)


def usuario_por_id(db: Session, id_usuario_utp: int) -> UsuarioUTP | None:
    return db.get(UsuarioUTP, id_usuario_utp)


def usuario_por_codigo(db: Session, codigo_utp: str) -> UsuarioUTP | None:
    return db.scalar(select(UsuarioUTP).where(UsuarioUTP.codigo_utp == codigo_utp))


def bloquear_usuario(db: Session, id_usuario_utp: int) -> UsuarioUTP | None:
    """Bloquea la fila del usuario para que el conteo de 3 VMP no tenga carreras."""
    return db.scalar(
        select(UsuarioUTP).where(UsuarioUTP.id_usuario_utp == id_usuario_utp).with_for_update()
    )


def listar_vehiculos(
    db: Session, id_usuario_utp: int, solo_activos: bool = True
) -> list[VehiculoVMP]:
    consulta = select(VehiculoVMP).where(VehiculoVMP.id_usuario_utp == id_usuario_utp)
    if solo_activos:
        consulta = consulta.where(VehiculoVMP.estado == EstadoActivo.activo)
    return list(db.scalars(consulta.order_by(VehiculoVMP.id_vehiculo)))


def contar_vehiculos_activos(db: Session, id_usuario_utp: int) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(VehiculoVMP)
            .where(
                VehiculoVMP.id_usuario_utp == id_usuario_utp,
                VehiculoVMP.estado == EstadoActivo.activo,
            )
        )
        or 0
    )


def vehiculo_por_id(db: Session, id_vehiculo: int) -> VehiculoVMP | None:
    return db.get(VehiculoVMP, id_vehiculo)


def qr_activo(db: Session, id_usuario_utp: int) -> CodigoQR | None:
    return db.scalar(
        select(CodigoQR).where(
            CodigoQR.id_usuario_utp == id_usuario_utp,
            CodigoQR.estado == EstadoQR.activo,
        )
    )


def qr_por_hash(db: Session, token_hash: str) -> CodigoQR | None:
    return db.scalar(select(CodigoQR).where(CodigoQR.token_hash == token_hash))


def registrar_sincronizacion(
    db: Session,
    id_usuario_utp: int,
    origen: OrigenSync,
    resultado: ResultadoSync = ResultadoSync.exitoso,
) -> None:
    db.add(
        SincronizacionUTP(
            id_usuario_utp=id_usuario_utp,
            origen=origen,
            fecha_hora=ahora(),
            resultado=resultado,
        )
    )
