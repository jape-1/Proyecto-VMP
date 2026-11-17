"""Enumeraciones del modelo de datos (docs/05 §2), compartidas por todos los módulos."""

from enum import StrEnum


class TipoUsuario(StrEnum):
    estudiante = "estudiante"
    docente = "docente"
    administrativo = "administrativo"


class EstadoMatricula(StrEnum):
    activo = "activo"
    inactivo = "inactivo"


class OrigenSync(StrEnum):
    login_portal = "login_portal"
    consulta_qr_app = "consulta_qr_app"


class ResultadoSync(StrEnum):
    exitoso = "exitoso"
    fallido = "fallido"


class TipoVMP(StrEnum):
    bicicleta = "bicicleta"
    bicicleta_electrica = "bicicleta_electrica"
    scooter_electrico = "scooter_electrico"
    moto_electrica = "moto_electrica"


class EstadoActivo(StrEnum):
    activo = "activo"
    inactivo = "inactivo"


class EstadoQR(StrEnum):
    activo = "activo"
    revocado = "revocado"
    expirado = "expirado"


class EstadoEspacio(StrEnum):
    disponible = "disponible"
    ocupado = "ocupado"
    mantenimiento = "mantenimiento"


class ResultadoValidacion(StrEnum):
    validado = "validado"
    rechazado = "rechazado"


class EstadoSesion(StrEnum):
    en_curso = "en_curso"
    finalizada = "finalizada"
    con_incidencia = "con_incidencia"


class EstadoValidacion(StrEnum):
    """Estado de la validación de un ingreso (brecha aprobada 2026-11-15).

    El ER solo tenía `resultado_validacion` (validado|rechazado), insuficiente para
    `pendiente_ia`, `verificar` e `ia_no_disponible` que exige docs/18 §5-§6.
    """

    pendiente = "pendiente"  # esperando la captura / la IA (pendiente_ia)
    validado = "validado"
    verificar = "verificar"  # zona gris: decide el guardia
    rechazado = "rechazado"  # la IA no coincide: decide el guardia
    ia_no_disponible = "ia_no_disponible"  # fallo o timeout del servicio de IA


class TipoEventoIA(StrEnum):
    validacion_ingreso = "validacion_ingreso"
    ocupacion_espacio = "ocupacion_espacio"
    liberacion_espacio = "liberacion_espacio"


class TurnoPersonal(StrEnum):
    manana = "manana"
    tarde = "tarde"
    noche = "noche"


class RolPersonal(StrEnum):
    seguridad = "seguridad"
    administrador = "administrador"


class TipoIncidencia(StrEnum):
    vehiculo_no_coincide = "vehiculo_no_coincide"
    sin_espacio_disponible = "sin_espacio_disponible"
    error_lectura_qr = "error_lectura_qr"
    otro = "otro"


class EstadoIncidencia(StrEnum):
    abierta = "abierta"
    en_revision = "en_revision"
    cerrada = "cerrada"


class TipoNotificacion(StrEnum):
    confirmacion_ingreso = "confirmacion_ingreso"
    estacionamiento_lleno = "estacionamiento_lleno"
    ingreso_rechazado = "ingreso_rechazado"


class CanalNotif(StrEnum):
    app_utp = "app_utp"


# --- Motivos (VARCHAR, no son tipos del ER) ---------------------------
class Motivo:
    VEHICULO_NO_COINCIDE = "VEHICULO_NO_COINCIDE"
    SIN_DETECCION = "SIN_DETECCION"
    CONFIANZA_DUDOSA = "CONFIANZA_DUDOSA"
    IA_NO_DISPONIBLE = "IA_NO_DISPONIBLE"
    TIPO_NO_RECONOCIDO = "TIPO_NO_RECONOCIDO"
    SEMEJANZA_BAJA = "SEMEJANZA_BAJA"
    SIN_REFERENCIA_COMPARABLE = "SIN_REFERENCIA_COMPARABLE"
    VEHICULO_YA_DENTRO = "VEHICULO_YA_DENTRO"
    APROBADO_MANUAL = "APROBADO_MANUAL"
    RECHAZADO_MANUAL = "RECHAZADO_MANUAL"
    CANCELADO = "CANCELADO"


# Correspondencia clase detectada -> tipos de VMP del ER (docs/18 §5)
CLASES_DETECTOR = ("scooter", "bicicleta", "moto_electrica")
MAPA_CLASE_A_TIPOS: dict[str, tuple[TipoVMP, ...]] = {
    "scooter": (TipoVMP.scooter_electrico,),
    "bicicleta": (TipoVMP.bicicleta, TipoVMP.bicicleta_electrica),
    # El modelo E2-3clases se entrenó con motos en general: reconoce «moto», no si es eléctrica.
    "moto_electrica": (TipoVMP.moto_electrica,),
}
