"""Esquemas de la API del módulo Identidad."""

from pydantic import BaseModel, Field

from app.core.enums import EstadoActivo, EstadoMatricula, EstadoQR, TipoUsuario, TipoVMP
from app.core.schemas import FechaLimaOpcional

MAX_VMP = 3


class PerfilOut(BaseModel):
    id_usuario_utp: int
    codigo_utp: str
    tipo_usuario: TipoUsuario
    nombres: str
    apellidos: str
    correo_institucional: str
    sede: str
    estado_matricula: EstadoMatricula
    acepta_tratamiento_datos: bool
    fecha_consentimiento: FechaLimaOpcional = None
    fecha_ultima_sincronizacion: FechaLimaOpcional = None


class PerfilUpdate(BaseModel):
    tipo_usuario: TipoUsuario | None = None
    correo_institucional: str | None = Field(default=None, max_length=120)
    acepta_tratamiento_datos: bool
    version_consentimiento: str | None = Field(default=None, max_length=20)


class VehiculoIn(BaseModel):
    tipo_vmp: TipoVMP
    marca: str = Field(min_length=1, max_length=50)
    modelo: str | None = Field(default=None, max_length=50)
    color: str = Field(min_length=1, max_length=50)
    caracteristica_distintiva: str | None = Field(default=None, max_length=255)


class VehiculoUpdate(BaseModel):
    tipo_vmp: TipoVMP | None = None
    marca: str | None = Field(default=None, min_length=1, max_length=50)
    modelo: str | None = Field(default=None, max_length=50)
    color: str | None = Field(default=None, min_length=1, max_length=50)
    caracteristica_distintiva: str | None = Field(default=None, max_length=255)


class VehiculoOut(BaseModel):
    id_vehiculo: int
    tipo_vmp: TipoVMP
    marca: str
    modelo: str | None
    color: str
    caracteristica_distintiva: str | None
    foto_referencia_url: str | None
    tiene_foto: bool
    estado: EstadoActivo
    fecha_registro: FechaLimaOpcional = None


class ListaVehiculosOut(BaseModel):
    items: list[VehiculoOut]
    max: int = MAX_VMP
    usados: int


class VehiculoCreadoOut(BaseModel):
    id_vehiculo: int
    estado: EstadoActivo
    foto_requerida: bool = True


class QRVehiculoOut(BaseModel):
    id_vehiculo: int
    tipo_vmp: TipoVMP
    marca: str
    modelo: str | None
    color: str


class QROut(BaseModel):
    id_qr: int
    estado: EstadoQR
    fecha_generacion: FechaLimaOpcional = None
    fecha_expiracion: FechaLimaOpcional = None
    vigente: bool
    imagen_qr_png_base64: str
    vehiculos: list[QRVehiculoOut]
