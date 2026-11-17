"""Reglas de negocio del ingreso: QR -> captura -> IA -> decisión humana (HU07–HU12).

La IA mide tres cosas (docs/26): si hay un VMP, de qué clase es y cuánto se parece
a las fotos registradas por el usuario. La regla de decisión está en `_evaluar`.

La IA **nunca** decide un rechazo definitivo: solo propone un estado. Si dice
«no coincide» o no está disponible, un guardia decide a mano (docs/18 §7.4).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.enums import (
    MAPA_CLASE_A_TIPOS,
    EstadoEspacio,
    EstadoMatricula,
    EstadoSesion,
    EstadoValidacion,
    Motivo,
    OrigenSync,
    ResultadoValidacion,
    TipoVMP,
)
from app.core.errors import ErrorNegocio
from app.core.security import token_para_log
from app.core.storage import guardar_imagen, normalizar_imagen, url_de
from app.core.time import ahora
from app.ia.cliente import ErrorIA, ResultadoIA, obtener_cliente_ia
from app.modules.estacionamiento import repository
from app.modules.estacionamiento.models import (
    EspacioEstacionamiento,
    EventoDeteccionIA,
    SesionEstacionamiento,
    ZonaEstacionamiento,
)
from app.modules.estacionamiento.schemas import (
    AccesoQROut,
    CuadroOut,
    DecisionIn,
    DecisionOut,
    DeteccionOut,
    EspacioOut,
    EspaciosOut,
    OcupanteOut,
    SesionEstadoOut,
    UsuarioAccesoOut,
    VehiculoAccesoOut,
    VehiculoOcupanteOut,
    ZonaOut,
)
from app.modules.identidad import service as identidad
from app.modules.identidad.service import PerfilOut, VehiculoOut

logger = logging.getLogger(__name__)

CAMARA_INGRESO = "CAM-ING-01"
# Piloto: 5 zonas × 8 espacios en la Torre Arequipa (docs/05, docs/13 #8).
SEDE = "Torre Arequipa"
ZONAS = "ABCDE"
ESPACIOS_POR_ZONA = 8

MENSAJES = {
    EstadoValidacion.pendiente: "Esperando el resultado de la IA.",
    EstadoValidacion.validado: "Puede ingresar.",
    EstadoValidacion.verificar: "Verificación manual requerida.",
    EstadoValidacion.rechazado: "El vehículo no coincide con los registrados.",
    EstadoValidacion.ia_no_disponible: "La IA no responde: decide manualmente.",
}

ESTADOS_DECIDIBLES = {
    EstadoValidacion.verificar,
    EstadoValidacion.rechazado,
    EstadoValidacion.ia_no_disponible,
}


def _cerrada(sesion: SesionEstacionamiento) -> bool:
    """Una sesión cancelada o ya decidida por un guardia no cambia más (HU12)."""
    return (
        sesion.estado_sesion == EstadoSesion.finalizada or sesion.id_personal_decision is not None
    )


def _puede_decidir(sesion: SesionEstacionamiento) -> bool:
    return sesion.estado_validacion in ESTADOS_DECIDIBLES and not _cerrada(sesion)


# ---------------------------------------------------------------------
# Lectura del QR (HU07/HU08)
# ---------------------------------------------------------------------
def crear_sesion(db: Session, token: str, id_personal: int) -> AccesoQROut:
    try:
        id_qr, id_usuario_utp, codigo_utp = identidad.validar_token_qr_para_acceso(db, token)
    except ErrorNegocio as exc:
        repository.registrar_intento(
            db, token_para_log(token), exc.codigo, id_personal, CAMARA_INGRESO
        )
        raise

    # Consulta al Conector: estado de matrícula fresco + bitácora.
    identidad.sincronizar_usuario(db, codigo_utp, OrigenSync.consulta_qr_app)
    perfil = identidad.obtener_perfil(db, id_usuario_utp)
    if perfil is None:
        raise ErrorNegocio("USUARIO_INEXISTENTE", "El usuario no existe.", 404)

    if perfil.estado_matricula != EstadoMatricula.activo:
        repository.registrar_intento(
            db, token_para_log(token), "USUARIO_INACTIVO", id_personal, CAMARA_INGRESO
        )
        raise ErrorNegocio(
            "USUARIO_INACTIVO",
            "La matrícula del usuario no está activa.",
            403,
        )

    vehiculos = identidad.vehiculos_out(db, id_usuario_utp)
    if not vehiculos:
        repository.registrar_intento(
            db, token_para_log(token), "SIN_VEHICULOS_REGISTRADOS", id_personal, CAMARA_INGRESO
        )
        raise ErrorNegocio(
            "SIN_VEHICULOS_REGISTRADOS",
            "El usuario no tiene vehículos activos registrados.",
            409,
        )

    if estacionamiento_lleno(db):
        repository.registrar_intento(
            db, token_para_log(token), "ESTACIONAMIENTO_LLENO", id_personal, CAMARA_INGRESO
        )
        raise ErrorNegocio(
            "ESTACIONAMIENTO_LLENO",
            "No hay espacios libres en el estacionamiento.",
            409,
        )

    sesion = SesionEstacionamiento(
        id_usuario_utp=id_usuario_utp,
        id_qr=id_qr,
        estado_validacion=EstadoValidacion.pendiente,
        estado_sesion=EstadoSesion.en_curso,
    )
    db.add(sesion)
    db.commit()
    db.refresh(sesion)

    return AccesoQROut(
        id_sesion=sesion.id_sesion,
        usuario=_usuario_out(perfil),
        vehiculos=[_vehiculo_out(v) for v in vehiculos],
    )


def _usuario_out(perfil: PerfilOut) -> UsuarioAccesoOut:
    return UsuarioAccesoOut(
        id_usuario_utp=perfil.id_usuario_utp,
        codigo_utp=perfil.codigo_utp,
        nombres=perfil.nombres,
        apellidos=perfil.apellidos,
        tipo_usuario=perfil.tipo_usuario,
        sede=perfil.sede,
    )


def _vehiculo_out(vehiculo: VehiculoOut) -> VehiculoAccesoOut:
    return VehiculoAccesoOut(
        id_vehiculo=vehiculo.id_vehiculo,
        tipo_vmp=vehiculo.tipo_vmp,
        marca=vehiculo.marca,
        modelo=vehiculo.modelo,
        color=vehiculo.color,
        caracteristica_distintiva=vehiculo.caracteristica_distintiva,
        foto_referencia_url=vehiculo.foto_referencia_url,
        tiene_foto=vehiculo.tiene_foto,
    )


# ---------------------------------------------------------------------
# Captura de la foto (HU09) y llamada a la IA
# ---------------------------------------------------------------------
def registrar_captura(
    db: Session,
    id_sesion: int,
    contenido: bytes,
    content_type: str | None,
    nombre_archivo: str,
) -> str:
    sesion = _sesion(db, id_sesion)
    _exigir_sesion_abierta(sesion)

    imagen = normalizar_imagen(contenido, content_type)
    carpeta = f"capturas/{ahora():%Y/%m/%d}"
    key = guardar_imagen(imagen, carpeta)

    sesion.estado_validacion = EstadoValidacion.pendiente
    sesion.motivo = None
    db.commit()
    return key


def _exigir_sesion_abierta(sesion: SesionEstacionamiento) -> None:
    if sesion.estado_validacion == EstadoValidacion.validado:
        raise ErrorNegocio(
            "SESION_ESTADO_INVALIDO",
            "La sesión ya fue validada.",
            409,
            {"estado": sesion.estado_validacion.value},
        )
    if _cerrada(sesion):
        raise ErrorNegocio(
            "SESION_ESTADO_INVALIDO",
            "La sesión está cerrada: vuelve a leer el QR.",
            409,
        )


def analizar_cuadro(
    db: Session,
    id_sesion: int,
    contenido: bytes,
    content_type: str | None,
    nombre_archivo: str = "cuadro.jpg",
) -> CuadroOut:
    """Análisis de un cuadro del video en vivo (17-nov-2026, docs/13).

    Misma IA y misma regla que la captura, pero **no guarda nada**: ni imagen ni
    evento. Cuando el video muestra un resultado estable, el frontend envía ese
    cuadro a `/captura`, que es lo que decide y queda como evidencia (RF17).
    """
    sesion = _sesion(db, id_sesion)
    _exigir_sesion_abierta(sesion)
    imagen = normalizar_imagen(contenido, content_type)
    vehiculos = identidad.vehiculos_out(db, sesion.id_usuario_utp)
    try:
        resultado = obtener_cliente_ia().validar_ingreso(
            imagen,
            "image/jpeg",
            [v.tipo_vmp.value for v in vehiculos],
            nombre_archivo,
            identidad.referencias_para_comparar(db, sesion.id_usuario_utp),
        )
    except ErrorIA as exc:
        raise ErrorNegocio("IA_NO_DISPONIBLE", "La IA no respondió.", 503) from exc
    evaluacion = _marcar_si_ya_dentro(db, _evaluar(resultado, vehiculos))
    return CuadroOut(
        estado=evaluacion.estado,
        motivo=evaluacion.motivo,
        confianza=evaluacion.confianza,
        semejanza=evaluacion.semejanza,
        id_vehiculo_mas_parecido=evaluacion.id_vehiculo_mas_parecido,
        detecciones=[DeteccionOut(**d.a_dict()) for d in resultado.detecciones],
        umbral_confianza=settings.ia_umbral_validado,
        umbral_semejanza=settings.ia_umbral_semejanza,
        ms=resultado.ms,
    )


def procesar_captura_ia(id_sesion: int, key: str, nombre_archivo: str) -> None:
    """Se ejecuta en segundo plano (la respuesta al guardia ya salió con 202)."""
    db = SessionLocal()
    try:
        sesion = repository.sesion_por_id(db, id_sesion)
        if sesion is None:
            return
        try:
            with open(settings.media_root / key, "rb") as archivo:
                imagen = archivo.read()
            vehiculos = identidad.vehiculos_out(db, sesion.id_usuario_utp)
            tipos = [v.tipo_vmp.value for v in vehiculos]
            referencias = identidad.referencias_para_comparar(db, sesion.id_usuario_utp)
            resultado = obtener_cliente_ia().validar_ingreso(
                imagen, "image/jpeg", tipos, nombre_archivo, referencias
            )
        except (ErrorIA, OSError) as exc:
            logger.warning("IA no disponible en la sesión %s: %s", id_sesion, type(exc).__name__)
            _aplicar(db, sesion, None, key)
            return
        _aplicar(db, sesion, resultado, key)
    finally:
        db.close()


@dataclass
class Evaluacion:
    estado: EstadoValidacion
    motivo: str | None = None
    id_vehiculo: int | None = None  # solo si quedó validado
    confianza: float | None = None  # del detector
    semejanza: float | None = None  # mejor semejanza con una foto registrada
    id_vehiculo_mas_parecido: int | None = None


def _evaluar(resultado: ResultadoIA, vehiculos: list[VehiculoOut]) -> Evaluacion:
    """Aplica la regla de docs/26 §3 sobre todas las detecciones confiables."""
    tipos_por_vehiculo: dict[int, TipoVMP] = {v.id_vehiculo: v.tipo_vmp for v in vehiculos}
    tipos_cubiertos = {t for tipos in MAPA_CLASE_A_TIPOS.values() for t in tipos}

    # Ningún vehículo del usuario es de un tipo que el detector reconozca: siempre a mano.
    if tipos_por_vehiculo and not (set(tipos_por_vehiculo.values()) & tipos_cubiertos):
        return Evaluacion(EstadoValidacion.verificar, Motivo.TIPO_NO_RECONOCIDO)

    mejor = resultado.mejor
    if mejor is None:
        return Evaluacion(EstadoValidacion.verificar, Motivo.SIN_DETECCION)

    confiables = [d for d in resultado.detecciones if d.confianza >= settings.ia_umbral_validado]
    if not confiables:
        return Evaluacion(
            EstadoValidacion.verificar, Motivo.CONFIANZA_DUDOSA, confianza=mejor.confianza
        )

    # Comprobación 2: ¿alguna detección es de una clase que el usuario registró?
    del_usuario = [
        d
        for d in confiables
        if set(MAPA_CLASE_A_TIPOS.get(d.clase, ())) & set(tipos_por_vehiculo.values())
    ]
    if not del_usuario:
        mas_confiable = max(confiables, key=lambda d: d.confianza)
        if not any(d.clase in MAPA_CLASE_A_TIPOS for d in confiables):
            return Evaluacion(
                EstadoValidacion.verificar,
                Motivo.TIPO_NO_RECONOCIDO,
                confianza=mas_confiable.confianza,
            )
        return Evaluacion(
            EstadoValidacion.rechazado,
            Motivo.VEHICULO_NO_COINCIDE,
            confianza=mas_confiable.confianza,
        )

    # Comprobación 3: semejanza con la foto registrada de un vehículo de esa clase.
    candidatos = [
        (s.semejanza, d.confianza, s.id_vehiculo)
        for d in del_usuario
        for s in d.semejanzas
        if tipos_por_vehiculo.get(s.id_vehiculo) in MAPA_CLASE_A_TIPOS[d.clase]
    ]
    if not candidatos:
        return Evaluacion(
            EstadoValidacion.verificar,
            Motivo.SIN_REFERENCIA_COMPARABLE,
            confianza=max(d.confianza for d in del_usuario),
        )

    semejanza, confianza, id_vehiculo = max(candidatos)
    if semejanza >= settings.ia_umbral_semejanza:
        return Evaluacion(
            EstadoValidacion.validado, None, id_vehiculo, confianza, semejanza, id_vehiculo
        )
    # Una semejanza baja nunca rechaza sola: decide el guardia (docs/26 §3).
    return Evaluacion(
        EstadoValidacion.verificar, Motivo.SEMEJANZA_BAJA, None, confianza, semejanza, id_vehiculo
    )


def _marcar_si_ya_dentro(db: Session, evaluacion: Evaluacion) -> Evaluacion:
    """Sin registro de salida en este avance, el vehículo reconocido puede figurar ya
    «dentro»: no se valida dos veces, decide el guardia."""
    if evaluacion.id_vehiculo is not None and repository.vehiculo_tiene_sesion_vigente(
        db, evaluacion.id_vehiculo
    ):
        evaluacion.estado = EstadoValidacion.verificar
        evaluacion.motivo = Motivo.VEHICULO_YA_DENTRO
        evaluacion.id_vehiculo = None
    return evaluacion


def _aplicar(
    db: Session, sesion: SesionEstacionamiento, resultado: ResultadoIA | None, key: str
) -> None:
    if resultado is None:
        evaluacion = Evaluacion(EstadoValidacion.ia_no_disponible, Motivo.IA_NO_DISPONIBLE)
        detecciones: dict | None = None
        modelo_version = None
    else:
        vehiculos = identidad.vehiculos_out(db, sesion.id_usuario_utp)
        evaluacion = _evaluar(resultado, vehiculos)
        # La semejanza va dentro del JSON de evidencia: no requiere columna nueva (docs/26 §4).
        detecciones = {
            "items": [d.a_dict() for d in resultado.detecciones],
            "semejanza": evaluacion.semejanza,
            "id_vehiculo_mas_parecido": evaluacion.id_vehiculo_mas_parecido,
            "comparador_version": resultado.comparador_version,
        }
        modelo_version = resultado.modelo_version
    evaluacion = _marcar_si_ya_dentro(db, evaluacion)
    estado, motivo = evaluacion.estado, evaluacion.motivo
    id_vehiculo, confianza = evaluacion.id_vehiculo, evaluacion.confianza

    # El guardia pudo cancelar o decidir mientras la IA analizaba: en ese caso el
    # resultado se guarda como evidencia, pero ya no cambia la sesión.
    db.refresh(sesion)
    if not _cerrada(sesion):
        sesion.estado_validacion = estado
        sesion.motivo = motivo
        sesion.id_vehiculo = id_vehiculo
        sesion.mejor_confianza = confianza
        sesion.resultado_validacion = {
            EstadoValidacion.validado: ResultadoValidacion.validado,
            EstadoValidacion.rechazado: ResultadoValidacion.rechazado,
        }.get(estado)
        if estado == EstadoValidacion.rechazado:
            sesion.estado_sesion = EstadoSesion.con_incidencia
        if estado == EstadoValidacion.validado:
            _asignar_espacio(db, sesion)

    db.add(
        EventoDeteccionIA(
            id_sesion=sesion.id_sesion,
            tipo_evento="validacion_ingreso",
            codigo_camara=CAMARA_INGRESO,
            imagen_capturada_url=key,
            score_confianza=confianza,
            modelo_version=modelo_version,
            detecciones=detecciones,
            motivo=motivo,
        )
    )
    db.commit()


# ---------------------------------------------------------------------
# Consulta del estado (HU10/HU11) y decisión del guardia (HU12)
# ---------------------------------------------------------------------
def _sesion(db: Session, id_sesion: int) -> SesionEstacionamiento:
    sesion = repository.sesion_por_id(db, id_sesion)
    if sesion is None:
        raise ErrorNegocio("SESION_NO_ENCONTRADA", "La sesión no existe.", 404)
    return sesion


def obtener_estado(db: Session, id_sesion: int) -> SesionEstadoOut:
    sesion = _sesion(db, id_sesion)
    evento = repository.ultimo_evento_validacion(db, id_sesion)
    perfil = identidad.obtener_perfil(db, sesion.id_usuario_utp)
    vehiculos = identidad.vehiculos_out(db, sesion.id_usuario_utp)

    detecciones: list[DeteccionOut] = []
    modelo_version = None
    evidencia = None
    semejanza = None
    id_vehiculo_mas_parecido = None
    if evento is not None:
        modelo_version = evento.modelo_version
        evidencia = url_de(evento.imagen_capturada_url)
        if evento.detecciones and isinstance(evento.detecciones.get("items"), list):
            detecciones = [DeteccionOut(**d) for d in evento.detecciones["items"]]
            semejanza = evento.detecciones.get("semejanza")
            id_vehiculo_mas_parecido = evento.detecciones.get("id_vehiculo_mas_parecido")

    decision = None
    if sesion.id_personal_decision is not None:
        decision = DecisionOut(
            decision=(
                "aprobar_manual"
                if sesion.resultado_validacion == ResultadoValidacion.validado
                else "rechazar"
            ),
            id_personal=sesion.id_personal_decision,
            fecha_decision=sesion.fecha_decision,
            motivo=sesion.motivo_decision,
        )

    return SesionEstadoOut(
        id_sesion=sesion.id_sesion,
        estado=sesion.estado_validacion,
        motivo=sesion.motivo,
        mensaje=MENSAJES[sesion.estado_validacion],
        id_vehiculo_reconocido=sesion.id_vehiculo,
        confianza=float(sesion.mejor_confianza) if sesion.mejor_confianza is not None else None,
        semejanza=semejanza,
        id_vehiculo_mas_parecido=id_vehiculo_mas_parecido,
        detecciones=detecciones,
        modelo_version=modelo_version,
        evidencia_url=evidencia,
        fecha_hora_ingreso=sesion.fecha_hora_ingreso,
        fecha_hora_decision=sesion.fecha_decision,
        decision=decision,
        puede_decidir=_puede_decidir(sesion),
        espacio=_codigo_espacio(db, sesion.id_espacio),
        usuario=_usuario_out(perfil) if perfil is not None else None,
        vehiculos=[_vehiculo_out(v) for v in vehiculos],
    )


def decidir(db: Session, id_sesion: int, id_personal: int, datos: DecisionIn) -> SesionEstadoOut:
    sesion = _sesion(db, id_sesion)
    if not _puede_decidir(sesion):
        raise ErrorNegocio(
            "SESION_ESTADO_INVALIDO",
            "Esta sesión no admite una decisión manual.",
            409,
            {"estado": sesion.estado_validacion.value},
        )

    vehiculos = identidad.vehiculos_out(db, sesion.id_usuario_utp)

    if datos.decision == "aprobar_manual":
        id_vehiculo = datos.id_vehiculo
        if id_vehiculo is None and len(vehiculos) == 1:
            id_vehiculo = vehiculos[0].id_vehiculo
        if id_vehiculo is not None and id_vehiculo not in {v.id_vehiculo for v in vehiculos}:
            raise ErrorNegocio(
                "VEHICULO_NO_ENCONTRADO",
                "El vehículo indicado no pertenece al usuario.",
                400,
            )
        sesion.id_vehiculo = id_vehiculo
        sesion.resultado_validacion = ResultadoValidacion.validado
        sesion.estado_validacion = EstadoValidacion.validado
        sesion.estado_sesion = EstadoSesion.en_curso
        sesion.motivo = Motivo.APROBADO_MANUAL
        _asignar_espacio(db, sesion)
    else:
        sesion.resultado_validacion = ResultadoValidacion.rechazado
        sesion.estado_validacion = EstadoValidacion.rechazado
        sesion.estado_sesion = EstadoSesion.con_incidencia
        sesion.motivo = Motivo.RECHAZADO_MANUAL

    sesion.id_personal_decision = id_personal
    sesion.fecha_decision = ahora()
    sesion.motivo_decision = datos.motivo

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ErrorNegocio(
            "VEHICULO_YA_DENTRO",
            "Ese vehículo ya tiene un ingreso vigente.",
            409,
        ) from exc
    db.refresh(sesion)
    return obtener_estado(db, id_sesion)


def cancelar(db: Session, id_sesion: int) -> SesionEstadoOut:
    sesion = _sesion(db, id_sesion)
    if sesion.estado_validacion == EstadoValidacion.validado:
        raise ErrorNegocio(
            "SESION_ESTADO_INVALIDO",
            "La sesión ya fue validada; no se puede cancelar.",
            409,
        )
    if _cerrada(sesion):
        raise ErrorNegocio("SESION_ESTADO_INVALIDO", "La sesión ya está cerrada.", 409)
    sesion.estado_sesion = EstadoSesion.finalizada
    sesion.motivo = Motivo.CANCELADO
    db.commit()
    db.refresh(sesion)
    return obtener_estado(db, id_sesion)


def vehiculo_esta_dentro(db: Session, id_vehiculo: int) -> bool:
    """Regla de este avance (HU04, docs/18 §7.9): hay un ingreso validado vigente."""
    return repository.vehiculo_tiene_sesion_vigente(db, id_vehiculo)


def registrar_salida_de_demo(db: Session, id_usuario_utp: int) -> int:
    """Cierra los ingresos vigentes de un usuario. Devuelve cuántos cerró.

    La salida real (HU16) queda fuera de este avance (docs/18 §2). Esto existe solo
    para repetir el ingreso en una demostración y se expone únicamente en `/dev/*`.
    """
    sesiones = repository.sesiones_vigentes_de_usuario(db, id_usuario_utp)
    for sesion in sesiones:
        _registrar_salida(db, sesion)
    db.commit()
    return len(sesiones)


def fecha_utc() -> datetime:
    return ahora()


# ---------------------------------------------------------------------
# Espacios: asignación al validar y monitoreo básico (17-nov-2026, docs/13)
#
# Todavía no hay cámaras de casillas (HU13–HU15): el sistema asigna el primer
# espacio libre al validar el ingreso y el guardia lo libera a mano. Cuando lleguen
# las cámaras, confirmarán la ocupación del espacio asignado y lo liberarán solas.
# ---------------------------------------------------------------------
def asegurar_espacios(
    db: Session,
    zonas: str = ZONAS,
    por_zona: int = ESPACIOS_POR_ZONA,
    sede: str = SEDE,
) -> None:
    """Crea las zonas y espacios que falten (`A-01` … `E-08`). No duplica."""
    for nombre in zonas:
        zona = db.scalar(
            select(ZonaEstacionamiento).where(
                ZonaEstacionamiento.sede == sede, ZonaEstacionamiento.nombre_zona == nombre
            )
        )
        if zona is None:
            zona = ZonaEstacionamiento(nombre_zona=nombre, sede=sede, capacidad_total=por_zona)
            db.add(zona)
            db.flush()
        existentes = set(
            db.scalars(
                select(EspacioEstacionamiento.codigo_espacio).where(
                    EspacioEstacionamiento.id_zona == zona.id_zona
                )
            )
        )
        for numero in range(1, por_zona + 1):
            codigo = f"{nombre}-{numero:02d}"
            if codigo not in existentes:
                db.add(EspacioEstacionamiento(id_zona=zona.id_zona, codigo_espacio=codigo))
    db.commit()


def estacionamiento_lleno(db: Session) -> bool:
    """Lleno = hay espacios configurados y ninguno disponible. Sin espacios, no se bloquea."""
    total, libres = repository.contar_espacios(db)
    return total > 0 and libres == 0


def _asignar_espacio(db: Session, sesion: SesionEstacionamiento) -> None:
    """Primer espacio libre. Si no queda ninguno, el ingreso sigue validado sin espacio."""
    if sesion.id_espacio is not None:
        return
    espacio = repository.espacio_libre_para_asignar(db)
    if espacio is None:
        logger.warning("Sesión %s validada sin espacio libre", sesion.id_sesion)
        return
    sesion.id_espacio = espacio.id_espacio
    espacio.estado = EstadoEspacio.ocupado
    espacio.ultima_actualizacion = ahora()


def _registrar_salida(db: Session, sesion: SesionEstacionamiento) -> None:
    sesion.fecha_hora_salida = ahora()
    sesion.estado_sesion = EstadoSesion.finalizada
    if sesion.id_espacio is not None:
        espacio = db.get(EspacioEstacionamiento, sesion.id_espacio)
        if espacio is not None and espacio.estado == EstadoEspacio.ocupado:
            espacio.estado = EstadoEspacio.disponible
            espacio.ultima_actualizacion = ahora()


def _codigo_espacio(db: Session, id_espacio: int | None) -> str | None:
    if id_espacio is None:
        return None
    espacio = db.get(EspacioEstacionamiento, id_espacio)
    return espacio.codigo_espacio if espacio is not None else None


def _ocupante(db: Session, sesion: SesionEstacionamiento) -> OcupanteOut:
    perfil = identidad.obtener_perfil(db, sesion.id_usuario_utp)
    vehiculo = next(
        (
            v
            for v in identidad.vehiculos_out(db, sesion.id_usuario_utp)
            if v.id_vehiculo == sesion.id_vehiculo
        ),
        None,
    )
    return OcupanteOut(
        id_sesion=sesion.id_sesion,
        nombre=f"{perfil.nombres} {perfil.apellidos}" if perfil else "—",
        codigo_utp=perfil.codigo_utp if perfil else "—",
        vehiculo=(
            VehiculoOcupanteOut(
                tipo_vmp=vehiculo.tipo_vmp.value, marca=vehiculo.marca, color=vehiculo.color
            )
            if vehiculo
            else None
        ),
        desde=sesion.fecha_decision or sesion.fecha_hora_ingreso,
    )


def resumen_espacios(db: Session) -> EspaciosOut:
    """Vista detallada de espacios para seguridad y administración (HU17, RF16, RF21)."""
    dentro = repository.sesiones_dentro_por_espacio(db)
    zonas: dict[str, list[EspacioOut]] = {}
    sede = SEDE
    for espacio, zona in repository.espacios_con_zona(db):
        sede = zona.sede
        sesion = dentro.get(espacio.id_espacio)
        zonas.setdefault(zona.nombre_zona, []).append(
            EspacioOut(
                id_espacio=espacio.id_espacio,
                codigo=espacio.codigo_espacio,
                estado=espacio.estado,
                ocupante=_ocupante(db, sesion) if sesion is not None else None,
            )
        )
    todos = [e for lista in zonas.values() for e in lista]
    libres = sum(e.estado == EstadoEspacio.disponible for e in todos)
    return EspaciosOut(
        sede=sede,
        total=len(todos),
        libres=libres,
        ocupados=sum(e.estado == EstadoEspacio.ocupado for e in todos),
        mantenimiento=sum(e.estado == EstadoEspacio.mantenimiento for e in todos),
        lleno=bool(todos) and libres == 0,
        zonas=[
            ZonaOut(
                nombre=nombre,
                total=len(lista),
                libres=sum(e.estado == EstadoEspacio.disponible for e in lista),
                espacios=lista,
            )
            for nombre, lista in zonas.items()
        ],
    )


def liberar_espacio(db: Session, id_espacio: int) -> EspaciosOut:
    """El guardia marca la salida del vehículo de ese espacio (sustituye a la cámara)."""
    espacio = db.get(EspacioEstacionamiento, id_espacio)
    if espacio is None:
        raise ErrorNegocio("ESPACIO_NO_ENCONTRADO", "El espacio no existe.", 404)
    sesion = repository.sesiones_dentro_por_espacio(db).get(id_espacio)
    if sesion is not None:
        _registrar_salida(db, sesion)
    elif espacio.estado == EstadoEspacio.ocupado:
        espacio.estado = EstadoEspacio.disponible
        espacio.ultima_actualizacion = ahora()
    db.commit()
    return resumen_espacios(db)
