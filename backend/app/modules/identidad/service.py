"""Reglas de negocio del módulo Identidad y Accesos.

Puntos públicos (los demás módulos solo pueden usar esto, nunca el repositorio).
"""

from __future__ import annotations

import base64
import io
import logging
from datetime import timedelta

import qrcode
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import MAPA_CLASE_A_TIPOS, EstadoActivo, EstadoQR, OrigenSync
from app.core.errors import ErrorNegocio
from app.core.security import (
    es_token_qr,
    generar_token_qr,
    hash_token,
    nuevo_secreto,
)
from app.core.storage import guardar_imagen, normalizar_imagen, ruta_de, url_de
from app.core.time import ahora
from app.ia.cliente import ErrorIA, Referencia, obtener_cliente_ia
from app.modules.identidad import repository
from app.modules.identidad.conector_utp.base import obtener_conector
from app.modules.identidad.models import CodigoQR, UsuarioUTP, VehiculoVMP
from app.modules.identidad.schemas import (
    MAX_VMP,
    ListaVehiculosOut,
    PerfilOut,
    PerfilUpdate,
    QROut,
    QRVehiculoOut,
    VehiculoIn,
    VehiculoOut,
    VehiculoUpdate,
)

logger = logging.getLogger(__name__)

VERSION_CONSENTIMIENTO_ACTUAL = "2026-11"


# ---------------------------------------------------------------------
# Usuario y perfil (HU01)
# ---------------------------------------------------------------------
def sincronizar_usuario(
    db: Session, codigo_utp: str, origen: OrigenSync = OrigenSync.login_portal
) -> UsuarioUTP:
    """Trae el usuario del Conector UTP y deja rastro en `sincronizacion_utp`."""
    datos = obtener_conector().obtener_usuario(codigo_utp)
    usuario = repository.usuario_por_codigo(db, datos.codigo_utp)
    if usuario is None:
        usuario = UsuarioUTP(codigo_utp=datos.codigo_utp)
        db.add(usuario)
    usuario.tipo_usuario = datos.tipo_usuario
    usuario.nombres = datos.nombres
    usuario.apellidos = datos.apellidos
    usuario.correo_institucional = datos.correo_institucional
    usuario.sede = datos.sede
    usuario.estado_matricula = datos.estado_matricula
    usuario.fecha_ultima_sincronizacion = ahora()
    db.flush()
    repository.registrar_sincronizacion(db, usuario.id_usuario_utp, origen)
    db.commit()
    db.refresh(usuario)
    return usuario


def obtener_perfil(db: Session, id_usuario_utp: int) -> PerfilOut | None:
    """Lectura pública del perfil, sin volver a llamar al Conector."""
    usuario = repository.usuario_por_id(db, id_usuario_utp)
    return perfil_out(usuario) if usuario is not None else None


def perfil_out(usuario: UsuarioUTP) -> PerfilOut:
    return PerfilOut(
        id_usuario_utp=usuario.id_usuario_utp,
        codigo_utp=usuario.codigo_utp,
        tipo_usuario=usuario.tipo_usuario,
        nombres=usuario.nombres,
        apellidos=usuario.apellidos,
        correo_institucional=usuario.correo_institucional,
        sede=usuario.sede,
        estado_matricula=usuario.estado_matricula,
        acepta_tratamiento_datos=usuario.acepta_tratamiento_datos,
        fecha_consentimiento=usuario.fecha_consentimiento,
        fecha_ultima_sincronizacion=usuario.fecha_ultima_sincronizacion,
    )


def actualizar_perfil(db: Session, usuario: UsuarioUTP, datos: PerfilUpdate) -> UsuarioUTP:
    if not datos.acepta_tratamiento_datos:
        raise ErrorNegocio(
            "CONSENTIMIENTO_REQUERIDO",
            "Debes aceptar el tratamiento de datos para usar el servicio.",
            409,
            {"version": VERSION_CONSENTIMIENTO_ACTUAL},
        )
    if datos.tipo_usuario is not None:
        usuario.tipo_usuario = datos.tipo_usuario
    if datos.correo_institucional:
        usuario.correo_institucional = datos.correo_institucional
    usuario.acepta_tratamiento_datos = True
    usuario.fecha_consentimiento = ahora()
    usuario.version_consentimiento = datos.version_consentimiento or VERSION_CONSENTIMIENTO_ACTUAL
    db.commit()
    db.refresh(usuario)
    return usuario


def _exigir_consentimiento(usuario: UsuarioUTP) -> None:
    if not usuario.acepta_tratamiento_datos:
        raise ErrorNegocio(
            "CONSENTIMIENTO_REQUERIDO",
            "Debes aceptar el tratamiento de datos antes de registrar vehículos.",
            409,
            {"version": VERSION_CONSENTIMIENTO_ACTUAL},
        )


# ---------------------------------------------------------------------
# Vehículos (HU02, HU03, HU04)
# ---------------------------------------------------------------------
def vehiculo_out(vehiculo: VehiculoVMP) -> VehiculoOut:
    return VehiculoOut(
        id_vehiculo=vehiculo.id_vehiculo,
        tipo_vmp=vehiculo.tipo_vmp,
        marca=vehiculo.marca,
        modelo=vehiculo.modelo,
        color=vehiculo.color,
        caracteristica_distintiva=vehiculo.caracteristica_distintiva,
        foto_referencia_url=url_de(vehiculo.foto_referencia_url),
        tiene_foto=bool(vehiculo.foto_referencia_url),
        estado=vehiculo.estado,
        fecha_registro=vehiculo.fecha_registro,
    )


def listar_vehiculos(db: Session, usuario: UsuarioUTP) -> ListaVehiculosOut:
    vehiculos = repository.listar_vehiculos(db, usuario.id_usuario_utp)
    return ListaVehiculosOut(
        items=[vehiculo_out(v) for v in vehiculos],
        max=MAX_VMP,
        usados=len(vehiculos),
    )


def crear_vehiculo(db: Session, usuario: UsuarioUTP, datos: VehiculoIn) -> VehiculoVMP:
    # Bloquea al usuario: dos peticiones simultáneas no pueden pasar de 3.
    repository.bloquear_usuario(db, usuario.id_usuario_utp)
    actualizado = repository.usuario_por_id(db, usuario.id_usuario_utp)
    if actualizado is None:
        raise ErrorNegocio("USUARIO_INEXISTENTE", "El usuario no existe.", 404)
    _exigir_consentimiento(actualizado)

    usados = repository.contar_vehiculos_activos(db, usuario.id_usuario_utp)
    if usados >= MAX_VMP:
        raise ErrorNegocio(
            "LIMITE_VMP_ALCANZADO",
            f"Ya tienes {MAX_VMP} vehículos registrados.",
            409,
            {"max": MAX_VMP, "actuales": usados},
        )

    vehiculo = VehiculoVMP(
        id_usuario_utp=usuario.id_usuario_utp,
        tipo_vmp=datos.tipo_vmp,
        marca=datos.marca,
        modelo=datos.modelo,
        color=datos.color,
        caracteristica_distintiva=datos.caracteristica_distintiva,
    )
    db.add(vehiculo)
    db.commit()
    db.refresh(vehiculo)
    return vehiculo


def _vehiculo_propio(db: Session, usuario: UsuarioUTP, id_vehiculo: int) -> VehiculoVMP:
    vehiculo = repository.vehiculo_por_id(db, id_vehiculo)
    if vehiculo is None or vehiculo.id_usuario_utp != usuario.id_usuario_utp:
        raise ErrorNegocio("VEHICULO_NO_ENCONTRADO", "El vehículo no existe.", 404)
    return vehiculo


def editar_vehiculo(
    db: Session, usuario: UsuarioUTP, id_vehiculo: int, datos: VehiculoUpdate
) -> VehiculoVMP:
    vehiculo = _vehiculo_propio(db, usuario, id_vehiculo)
    if vehiculo.estado != EstadoActivo.activo:
        raise ErrorNegocio("VEHICULO_NO_ENCONTRADO", "El vehículo no existe.", 404)
    cambios = datos.model_dump(exclude_unset=True)
    cambia_tipo = "tipo_vmp" in cambios and cambios["tipo_vmp"] != vehiculo.tipo_vmp
    for campo, valor in cambios.items():
        setattr(vehiculo, campo, valor)
    if cambia_tipo:
        # La foto se validó para el tipo anterior (HU03): hay que subir otra.
        vehiculo.foto_referencia_url = None
    # BR-04 / docs/13 #4: el QR solo identifica al usuario, así que la lista de
    # vehículos se actualiza sola; no se rota el token al editar.
    db.commit()
    db.refresh(vehiculo)
    return vehiculo


def dar_baja_vehiculo(db: Session, usuario: UsuarioUTP, id_vehiculo: int) -> VehiculoVMP:
    from app.modules.estacionamiento import service as estacionamiento  # import diferido

    vehiculo = _vehiculo_propio(db, usuario, id_vehiculo)
    if vehiculo.estado != EstadoActivo.activo:
        raise ErrorNegocio("VEHICULO_NO_ENCONTRADO", "El vehículo no existe.", 404)
    if estacionamiento.vehiculo_esta_dentro(db, id_vehiculo):
        raise ErrorNegocio(
            "VEHICULO_DENTRO_NO_ELIMINABLE",
            "No puedes dar de baja un vehículo que está dentro del estacionamiento.",
            409,
        )
    vehiculo.estado = EstadoActivo.inactivo
    db.commit()
    db.refresh(vehiculo)
    return vehiculo


def guardar_foto_referencia(
    db: Session,
    usuario: UsuarioUTP,
    id_vehiculo: int,
    contenido: bytes,
    content_type: str | None,
    nombre_archivo: str,
) -> VehiculoVMP:
    vehiculo = _vehiculo_propio(db, usuario, id_vehiculo)
    if vehiculo.estado != EstadoActivo.activo:
        raise ErrorNegocio("VEHICULO_NO_ENCONTRADO", "El vehículo no existe.", 404)
    _exigir_consentimiento(usuario)

    imagen = normalizar_imagen(contenido, content_type)

    try:
        resultado = obtener_cliente_ia().validar_foto_referencia(
            imagen, "image/jpeg", nombre_archivo
        )
    except ErrorIA as exc:
        raise ErrorNegocio(
            "IA_NO_DISPONIBLE",
            "No se pudo validar la foto: el servicio de IA no responde. Intenta de nuevo.",
            503,
        ) from exc

    # HU03: la foto debe mostrar, con confianza suficiente, un vehículo del tipo declarado.
    confiables = [d for d in resultado.detecciones if d.confianza >= settings.ia_umbral_validado]
    if not confiables:
        raise ErrorNegocio(
            "FOTO_SIN_VEHICULO",
            "No se reconoce ningún scooter, bicicleta ni moto en la foto.",
            422,
        )
    if not any(vehiculo.tipo_vmp in MAPA_CLASE_A_TIPOS.get(d.clase, ()) for d in confiables):
        raise ErrorNegocio(
            "FOTO_TIPO_NO_COINCIDE",
            "La foto no corresponde al tipo de vehículo que registraste.",
            422,
            {
                "detectado": sorted({d.clase for d in confiables}),
                "tipo_vmp": vehiculo.tipo_vmp.value,
            },
        )

    key = guardar_imagen(imagen, f"referencias/{usuario.id_usuario_utp}")
    vehiculo.foto_referencia_url = key
    db.commit()
    db.refresh(vehiculo)
    return vehiculo


# ---------------------------------------------------------------------
# Código QR (HU05, HU06)
# ---------------------------------------------------------------------
def _crear_qr(db: Session, usuario: UsuarioUTP) -> CodigoQR:
    # Se inserta con un hash provisional para obtener el id, del que se deriva
    # el token definitivo; el token en claro nunca se guarda.
    qr = CodigoQR(
        id_usuario_utp=usuario.id_usuario_utp,
        token_hash=hash_token(nuevo_secreto()),
        fecha_generacion=ahora(),
        fecha_expiracion=ahora() + timedelta(days=settings.qr_vigencia_dias),
        estado=EstadoQR.activo,
    )
    db.add(qr)
    db.flush()
    qr.token_hash = hash_token(generar_token_qr(qr.id_qr, qr.id_usuario_utp))
    db.commit()
    db.refresh(qr)
    return qr


def obtener_qr(db: Session, usuario: UsuarioUTP) -> CodigoQR:
    """Devuelve el QR vigente; si no existe (o venció), lo genera."""
    qr = repository.qr_activo(db, usuario.id_usuario_utp)
    if qr is not None and qr.fecha_expiracion <= ahora():
        qr.estado = EstadoQR.expirado
        db.commit()
        qr = None
    if qr is not None:
        return qr
    try:
        return _crear_qr(db, usuario)
    except IntegrityError:
        # Otra petición creó el QR activo al mismo tiempo.
        db.rollback()
        existente = repository.qr_activo(db, usuario.id_usuario_utp)
        if existente is None:
            raise
        return existente


def regenerar_qr(db: Session, usuario: UsuarioUTP) -> CodigoQR:
    actual = repository.qr_activo(db, usuario.id_usuario_utp)
    if actual is not None:
        actual.estado = EstadoQR.revocado
        db.flush()
    return _crear_qr(db, usuario)


def token_de_qr(qr: CodigoQR) -> str:
    return generar_token_qr(qr.id_qr, qr.id_usuario_utp)


def _png_base64(token: str) -> str:
    imagen = qrcode.make(token)
    buffer = io.BytesIO()
    imagen.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def qr_out(db: Session, usuario: UsuarioUTP, qr: CodigoQR) -> QROut:
    vehiculos = repository.listar_vehiculos(db, usuario.id_usuario_utp)
    return QROut(
        id_qr=qr.id_qr,
        estado=qr.estado,
        fecha_generacion=qr.fecha_generacion,
        fecha_expiracion=qr.fecha_expiracion,
        vigente=qr.estado == EstadoQR.activo and qr.fecha_expiracion > ahora(),
        imagen_qr_png_base64=_png_base64(token_de_qr(qr)),
        vehiculos=[
            QRVehiculoOut(
                id_vehiculo=v.id_vehiculo,
                tipo_vmp=v.tipo_vmp,
                marca=v.marca,
                modelo=v.modelo,
                color=v.color,
            )
            for v in vehiculos
        ],
    )


def validar_token_qr(db: Session, token: str) -> CodigoQR:
    """Valida formato, hash, estado y vigencia. Lanza el código de error estable."""
    if not token or not es_token_qr(token):
        raise ErrorNegocio(
            "QR_ALTERADO",
            "El código QR no es válido. Preséntalo de nuevo desde la App UTP.",
            400,
        )

    qr = repository.qr_por_hash(db, hash_token(token))
    if qr is None:
        raise ErrorNegocio("QR_INEXISTENTE", "El código QR no está registrado.", 404)

    if qr.estado == EstadoQR.revocado:
        raise ErrorNegocio("QR_REVOCADO", "El código QR fue revocado.", 409)

    if qr.estado == EstadoQR.expirado or qr.fecha_expiracion <= ahora():
        if qr.estado == EstadoQR.activo:
            qr.estado = EstadoQR.expirado
            db.commit()
        raise ErrorNegocio(
            "QR_EXPIRADO",
            "El código QR venció. Debe renovarlo desde la App UTP.",
            409,
        )
    return qr


def vehiculos_activos(db: Session, usuario: UsuarioUTP) -> list[VehiculoVMP]:
    return repository.listar_vehiculos(db, usuario.id_usuario_utp)


def vehiculos_out(db: Session, id_usuario_utp: int) -> list[VehiculoOut]:
    """Vehículos activos ya serializados (con URL firmada de la foto)."""
    return [vehiculo_out(v) for v in repository.listar_vehiculos(db, id_usuario_utp)]


def referencias_para_comparar(db: Session, id_usuario_utp: int) -> list[Referencia]:
    """Fotos de referencia de los vehículos activos del usuario (docs/26 §4).

    Un vehículo sin foto, o cuya foto ya no está en disco, simplemente no se incluye.
    """
    referencias: list[Referencia] = []
    for vehiculo in repository.listar_vehiculos(db, id_usuario_utp):
        if not vehiculo.foto_referencia_url:
            continue
        try:
            imagen = ruta_de(vehiculo.foto_referencia_url).read_bytes()
        except (ErrorNegocio, OSError):
            logger.warning("Falta la foto de referencia del vehículo %s", vehiculo.id_vehiculo)
            continue
        referencias.append(Referencia(vehiculo.id_vehiculo, vehiculo.tipo_vmp.value, imagen))
    return referencias


def validar_token_qr_para_acceso(db: Session, token: str) -> tuple[int, int, str]:
    """Devuelve (id_qr, id_usuario_utp, codigo_utp) sin exponer el modelo al otro módulo."""
    qr = validar_token_qr(db, token)
    return qr.id_qr, qr.id_usuario_utp, qr.usuario.codigo_utp
