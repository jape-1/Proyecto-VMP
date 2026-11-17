/**
 * Máquina de estados del punto de acceso (docs/20 §3, docs/24 §3).
 * Es lógica pura: no llama al backend ni toca la pantalla, por eso se puede probar sola.
 */
import type { EstadoSesion, LecturaQR } from '../servicios/api'
import type { TextoError } from '../servicios/mensajes'

export type Paso =
  | 'esperando_qr'
  | 'validando_qr'
  | 'qr_error'
  | 'capturando_foto'
  | 'analizando'
  | 'ingreso_ok'
  | 'verificar'
  | 'rechazado'
  | 'ia_no_disponible'
  | 'denegado'

export interface Estado {
  paso: Paso
  lectura: LecturaQR | null
  resultado: EstadoSesion | null
  error: TextoError | null
  /** Foto recién tomada, para mostrarla mientras la IA analiza. */
  capturaLocal: string | null
}

export const ESTADO_INICIAL: Estado = {
  paso: 'esperando_qr',
  lectura: null,
  resultado: null,
  error: null,
  capturaLocal: null,
}

export type Accion =
  | { tipo: 'QR_LEIDO' }
  | { tipo: 'QR_OK'; lectura: LecturaQR }
  | { tipo: 'QR_ERROR'; error: TextoError }
  | { tipo: 'FOTO_ENVIADA'; capturaLocal: string }
  | { tipo: 'RESULTADO'; resultado: EstadoSesion }
  | { tipo: 'IA_SIN_RESPUESTA' }
  | { tipo: 'ERROR'; error: TextoError }
  | { tipo: 'REINICIAR' }

/** A qué pantalla lleva el estado que devuelve el backend. */
export function pasoDeResultado(resultado: EstadoSesion): Paso {
  // Rechazo que ya decidió un guardia: no hay más botones, solo el aviso.
  if (resultado.estado === 'rechazado' && !resultado.puede_decidir) return 'denegado'
  switch (resultado.estado) {
    case 'validado':
      return 'ingreso_ok'
    case 'verificar':
      return 'verificar'
    case 'rechazado':
      return 'rechazado'
    case 'ia_no_disponible':
      return 'ia_no_disponible'
    case 'pendiente':
      return 'analizando'
  }
}

export function reducir(estado: Estado, accion: Accion): Estado {
  switch (accion.tipo) {
    case 'QR_LEIDO':
      return estado.paso === 'esperando_qr' || estado.paso === 'qr_error'
        ? { ...ESTADO_INICIAL, paso: 'validando_qr' }
        : estado
    case 'QR_OK':
      return { ...ESTADO_INICIAL, paso: 'capturando_foto', lectura: accion.lectura }
    case 'QR_ERROR':
      return { ...ESTADO_INICIAL, paso: 'qr_error', error: accion.error }
    case 'FOTO_ENVIADA':
      return {
        ...estado,
        paso: 'analizando',
        resultado: null,
        error: null,
        capturaLocal: accion.capturaLocal,
      }
    case 'RESULTADO':
      return {
        ...estado,
        paso: pasoDeResultado(accion.resultado),
        resultado: accion.resultado,
        error: null,
      }
    case 'IA_SIN_RESPUESTA':
      // El sistema no se detiene si la IA falla: el guardia decide (regla de negocio de docs/02).
      return { ...estado, paso: 'ia_no_disponible', error: null }
    case 'ERROR':
      return { ...estado, error: accion.error }
    case 'REINICIAR':
      return ESTADO_INICIAL
  }
}

/** Índice del paso visible en la barra: 0 leer QR, 1 foto, 2 resultado. */
export function etapa(paso: Paso): 0 | 1 | 2 {
  if (paso === 'esperando_qr' || paso === 'validando_qr' || paso === 'qr_error') return 0
  if (paso === 'capturando_foto' || paso === 'analizando') return 1
  return 2
}

/** Pasos en los que el guardia debe decidir a mano. */
export function requiereDecision(paso: Paso): boolean {
  return paso === 'verificar' || paso === 'rechazado' || paso === 'ia_no_disponible'
}
