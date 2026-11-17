"""Esquemas del punto de acceso (HU07–HU12)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.core.enums import EstadoEspacio, EstadoValidacion, TipoUsuario, TipoVMP
from app.core.schemas import FechaLimaOpcional


class AccesoQRIn(BaseModel):
    token: str = Field(min_length=8, max_length=200, description="Contenido del QR leído")


class UsuarioAccesoOut(BaseModel):
    id_usuario_utp: int
    codigo_utp: str
    nombres: str
    apellidos: str
    tipo_usuario: TipoUsuario
    sede: str


class VehiculoAccesoOut(BaseModel):
    id_vehiculo: int
    tipo_vmp: TipoVMP
    marca: str
    modelo: str | None
    color: str
    caracteristica_distintiva: str | None
    foto_referencia_url: str | None
    tiene_foto: bool


class AccesoQROut(BaseModel):
    id_sesion: int
    usuario: UsuarioAccesoOut
    vehiculos: list[VehiculoAccesoOut]
    siguiente_paso: Literal["capturar_foto"] = "capturar_foto"


class CapturaOut(BaseModel):
    id_sesion: int
    estado: EstadoValidacion
    mensaje: str


class SemejanzaOut(BaseModel):
    id_vehiculo: int
    semejanza: float


class DeteccionOut(BaseModel):
    clase: str
    confianza: float
    caja: list[float] | None = None
    semejanzas: list[SemejanzaOut] = []


class CuadroOut(BaseModel):
    """Análisis de un cuadro del video en vivo. No se guarda: solo orienta al guardia."""

    estado: EstadoValidacion
    motivo: str | None = None
    confianza: float | None = None
    semejanza: float | None = None
    id_vehiculo_mas_parecido: int | None = None
    detecciones: list[DeteccionOut] = []
    umbral_confianza: float
    umbral_semejanza: float
    ms: int | None = None


class DecisionOut(BaseModel):
    decision: str
    id_personal: int
    fecha_decision: FechaLimaOpcional = None
    motivo: str | None = None


class SesionEstadoOut(BaseModel):
    id_sesion: int
    estado: EstadoValidacion
    motivo: str | None
    mensaje: str
    id_vehiculo_reconocido: int | None
    confianza: float | None
    semejanza: float | None = Field(
        default=None, description="Mejor semejanza con una foto registrada (0 a 1)"
    )
    id_vehiculo_mas_parecido: int | None = None
    detecciones: list[DeteccionOut]
    modelo_version: str | None
    evidencia_url: str | None
    fecha_hora_ingreso: FechaLimaOpcional = None
    fecha_hora_decision: FechaLimaOpcional = None
    decision: DecisionOut | None = None
    puede_decidir: bool
    espacio: str | None = Field(
        default=None, description="Espacio asignado al validar, p. ej. «A-03» (solo guardia)"
    )
    usuario: UsuarioAccesoOut | None = None
    vehiculos: list[VehiculoAccesoOut] = []


class DecisionIn(BaseModel):
    decision: Literal["aprobar_manual", "rechazar"]
    motivo: str | None = Field(default=None, max_length=255)
    id_vehiculo: int | None = Field(default=None, description="Vehículo reconocido por el guardia")


# ---------------------------------------------------------------- espacios (monitoreo)
class VehiculoOcupanteOut(BaseModel):
    tipo_vmp: str
    marca: str
    color: str | None = None


class OcupanteOut(BaseModel):
    id_sesion: int
    nombre: str
    codigo_utp: str
    vehiculo: VehiculoOcupanteOut | None = None
    desde: FechaLimaOpcional = None


class EspacioOut(BaseModel):
    id_espacio: int
    codigo: str
    estado: EstadoEspacio
    ocupante: OcupanteOut | None = None


class ZonaOut(BaseModel):
    nombre: str
    total: int
    libres: int
    espacios: list[EspacioOut]


class EspaciosOut(BaseModel):
    """Vista detallada de espacios: solo seguridad y administración (RF21)."""

    sede: str
    total: int
    libres: int
    ocupados: int
    mantenimiento: int
    lleno: bool
    zonas: list[ZonaOut]
