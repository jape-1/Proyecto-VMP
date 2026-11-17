"""Acceso a datos del módulo Estacionamiento e IA."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import EstadoEspacio, EstadoSesion, ResultadoValidacion
from app.modules.estacionamiento.models import (
    EspacioEstacionamiento,
    EventoDeteccionIA,
    IntentoLecturaQR,
    SesionEstacionamiento,
    ZonaEstacionamiento,
)


def sesion_por_id(db: Session, id_sesion: int) -> SesionEstacionamiento | None:
    return db.get(SesionEstacionamiento, id_sesion)


def ultimo_evento_validacion(db: Session, id_sesion: int) -> EventoDeteccionIA | None:
    return db.scalar(
        select(EventoDeteccionIA)
        .where(EventoDeteccionIA.id_sesion == id_sesion)
        .order_by(EventoDeteccionIA.id_evento.desc())
        .limit(1)
    )


def vehiculo_tiene_sesion_vigente(db: Session, id_vehiculo: int) -> bool:
    return (
        db.scalar(
            select(SesionEstacionamiento.id_sesion)
            .where(
                SesionEstacionamiento.id_vehiculo == id_vehiculo,
                SesionEstacionamiento.estado_sesion == EstadoSesion.en_curso,
                SesionEstacionamiento.resultado_validacion == ResultadoValidacion.validado,
                SesionEstacionamiento.fecha_hora_salida.is_(None),
            )
            .limit(1)
        )
        is not None
    )


def espacio_libre_para_asignar(db: Session) -> EspacioEstacionamiento | None:
    """Primer espacio disponible (zona y código en orden) sin un ingreso vigente.

    Se bloquea la fila elegida (`FOR UPDATE SKIP LOCKED`) para que dos ingresos
    validados al mismo tiempo no reciban el mismo espacio.
    """
    con_ingreso = select(SesionEstacionamiento.id_espacio).where(
        SesionEstacionamiento.id_espacio.is_not(None),
        SesionEstacionamiento.fecha_hora_salida.is_(None),
    )
    return db.scalar(
        select(EspacioEstacionamiento)
        .join(ZonaEstacionamiento, ZonaEstacionamiento.id_zona == EspacioEstacionamiento.id_zona)
        .where(
            EspacioEstacionamiento.estado == EstadoEspacio.disponible,
            EspacioEstacionamiento.id_espacio.not_in(con_ingreso),
        )
        .order_by(ZonaEstacionamiento.nombre_zona, EspacioEstacionamiento.codigo_espacio)
        .limit(1)
        .with_for_update(skip_locked=True, of=EspacioEstacionamiento)
    )


def contar_espacios(db: Session) -> tuple[int, int]:
    """(total, disponibles) de todos los espacios."""
    total = db.scalar(select(func.count()).select_from(EspacioEstacionamiento)) or 0
    libres = (
        db.scalar(
            select(func.count())
            .select_from(EspacioEstacionamiento)
            .where(EspacioEstacionamiento.estado == EstadoEspacio.disponible)
        )
        or 0
    )
    return total, libres


def espacios_con_zona(db: Session) -> list[tuple[EspacioEstacionamiento, ZonaEstacionamiento]]:
    filas = db.execute(
        select(EspacioEstacionamiento, ZonaEstacionamiento)
        .join(ZonaEstacionamiento, ZonaEstacionamiento.id_zona == EspacioEstacionamiento.id_zona)
        .order_by(ZonaEstacionamiento.nombre_zona, EspacioEstacionamiento.codigo_espacio)
    ).all()
    return [(espacio, zona) for espacio, zona in filas]


def sesiones_dentro_por_espacio(db: Session) -> dict[int, SesionEstacionamiento]:
    sesiones = db.scalars(
        select(SesionEstacionamiento).where(
            SesionEstacionamiento.id_espacio.is_not(None),
            SesionEstacionamiento.fecha_hora_salida.is_(None),
        )
    )
    return {s.id_espacio: s for s in sesiones if s.id_espacio is not None}


def sesiones_vigentes_de_usuario(db: Session, id_usuario_utp: int) -> list[SesionEstacionamiento]:
    """Ingresos validados que aún no tienen salida."""
    return list(
        db.scalars(
            select(SesionEstacionamiento).where(
                SesionEstacionamiento.id_usuario_utp == id_usuario_utp,
                SesionEstacionamiento.estado_sesion == EstadoSesion.en_curso,
                SesionEstacionamiento.resultado_validacion == ResultadoValidacion.validado,
                SesionEstacionamiento.fecha_hora_salida.is_(None),
            )
        )
    )


def registrar_intento(
    db: Session,
    token_hash_parcial: str,
    motivo: str,
    id_personal: int | None = None,
    codigo_camara: str | None = None,
) -> None:
    db.add(
        IntentoLecturaQR(
            token_hash_parcial=token_hash_parcial,
            motivo=motivo,
            id_personal=id_personal,
            codigo_camara=codigo_camara,
        )
    )
    db.commit()
