/**
 * ÚNICO lugar donde los códigos del backend se convierten en texto para personas.
 * Códigos: backend/app/core/errors.py y core/enums.py (Motivo).
 */
import type { TipoUsuario, TipoVMP } from './api'
import { ErrorApi } from './api'

export const TIPO_VMP: Record<TipoVMP, string> = {
  bicicleta: 'Bicicleta',
  bicicleta_electrica: 'Bicicleta eléctrica',
  scooter_electrico: 'Scooter eléctrico',
  moto_electrica: 'Moto eléctrica',
}

export const TIPO_USUARIO: Record<TipoUsuario, string> = {
  estudiante: 'Estudiante',
  docente: 'Docente',
  administrativo: 'Administrativo',
}

/** Clases del detector (no son tipos de VMP: el detector no distingue si es eléctrico). */
const CLASE_DETECTOR: Record<string, string> = {
  scooter: 'Scooter',
  bicicleta: 'Bicicleta',
  moto_electrica: 'Moto',
}

export function nombreDeClase(clase: string): string {
  return CLASE_DETECTOR[clase] ?? clase
}

const MENSAJES_ERROR: Record<string, string> = {
  SIN_CONEXION: 'No hay conexión con el servidor.',
  QR_EXPIRADO: 'QR vencido: el usuario debe renovarlo',
  QR_REVOCADO: 'QR revocado',
  QR_ALTERADO: 'QR no válido',
  QR_INEXISTENTE: 'QR no registrado',
  USUARIO_INACTIVO: 'Matrícula no vigente',
  USUARIO_INEXISTENTE: 'Usuario no encontrado',
  SIN_VEHICULOS_REGISTRADOS: 'Sin vehículos registrados',
  ESTACIONAMIENTO_LLENO: 'Estacionamiento lleno: no hay espacios libres',
  ESPACIO_NO_ENCONTRADO: 'Ese espacio ya no existe.',
  CONSENTIMIENTO_REQUERIDO: 'Primero acepta el tratamiento de tus datos personales.',
  LIMITE_VMP_ALCANZADO: 'Máximo 3 vehículos por usuario.',
  FOTO_INVALIDA: 'El archivo no es una imagen válida (JPG o PNG, máximo 5 MB).',
  FOTO_SIN_VEHICULO:
    'No detectamos un vehículo en la foto. Toma otra con el vehículo completo.',
  IA_NO_DISPONIBLE: 'No se pudo validar la foto: la IA no responde. Intenta de nuevo.',
  VEHICULO_DENTRO_NO_ELIMINABLE:
    'No puedes eliminar un vehículo que está dentro del estacionamiento.',
  VEHICULO_NO_ENCONTRADO: 'El vehículo ya no existe.',
  VEHICULO_YA_DENTRO: 'Ese vehículo ya tiene un ingreso vigente.',
  SESION_ESTADO_INVALIDO: 'Esta sesión ya está cerrada. Vuelve a leer el QR.',
  SESION_NO_ENCONTRADA: 'La sesión no existe. Vuelve a leer el QR.',
  DATOS_INVALIDOS: 'Revisa los datos ingresados.',
}

export interface TextoError {
  mensaje: string
  /** Código para soporte: se muestra en pequeño. */
  codigo: string
  requestId: string
}

export function textoDeError(error: unknown): TextoError {
  if (!(error instanceof ErrorApi)) {
    return { mensaje: 'Ocurrió un error inesperado.', codigo: 'ERROR_DESCONOCIDO', requestId: '' }
  }
  let mensaje = MENSAJES_ERROR[error.codigo] ?? error.message ?? 'Ocurrió un error.'
  if (error.codigo === 'FOTO_TIPO_NO_COINCIDE') {
    const detalle = error.detalle as { detectado?: string[]; tipo_vmp?: TipoVMP }
    const visto = (detalle.detectado ?? []).map(nombreDeClase).join(' y ').toLowerCase()
    const esperado = detalle.tipo_vmp ? TIPO_VMP[detalle.tipo_vmp].toLowerCase() : 'otro tipo'
    mensaje = `La foto muestra ${visto || 'otro vehículo'}, pero registraste ${esperado}. Sube una foto de tu vehículo.`
  }
  return { mensaje, codigo: error.codigo, requestId: error.requestId }
}

/** Explicación corta del motivo que el backend da junto al estado de la sesión. */
const MOTIVOS: Record<string, string> = {
  VEHICULO_NO_COINCIDE: 'La clase detectada no es la de ningún vehículo del usuario.',
  SIN_DETECCION: 'La IA no vio ningún vehículo en la foto.',
  CONFIANZA_DUDOSA: 'La IA no está segura de lo que ve.',
  TIPO_NO_RECONOCIDO: 'La IA no reconoce este tipo de vehículo.',
  SEMEJANZA_BAJA: 'Es la clase correcta, pero se parece poco a la foto registrada.',
  SIN_REFERENCIA_COMPARABLE: 'No hay una foto registrada con la que comparar.',
  VEHICULO_YA_DENTRO: 'Este vehículo ya figura dentro del estacionamiento.',
  IA_NO_DISPONIBLE: 'La IA no respondió.',
  APROBADO_MANUAL: 'Aprobado por el guardia.',
  RECHAZADO_MANUAL: 'Rechazado por el guardia.',
  CANCELADO: 'Ingreso cancelado.',
}

export function textoDeMotivo(motivo: string | null): string {
  return motivo ? (MOTIVOS[motivo] ?? motivo) : ''
}

/**
 * Se trunca, no se redondea: 0,696 se muestra «69 %». Redondear a «70 %» haría
 * creer que alcanzó un umbral del 70 % que en realidad no alcanzó.
 */
export function porcentaje(valor: number | null): string {
  return valor === null ? '—' : `${Math.floor(valor * 100 + 1e-9)} %`
}

/** Fecha en formato peruano de 24 h (zona America/Lima). */
export function fechaLima(iso: string | null, conHora = false): string {
  if (!iso) return '—'
  return new Intl.DateTimeFormat('es-PE', {
    timeZone: 'America/Lima',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    ...(conHora ? { hour: '2-digit', minute: '2-digit', hour12: false } : {}),
  }).format(new Date(iso))
}
