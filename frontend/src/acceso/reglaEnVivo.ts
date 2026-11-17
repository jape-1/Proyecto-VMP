/**
 * Cuándo el video en vivo deja de mirar y pide la decisión oficial (17-nov-2026).
 * Lógica pura, sin pantalla ni red, para poder probarla sola.
 *
 * - Si varios cuadros seguidos salen «validado», se decide con el último.
 * - Si se ve un vehículo pero no llega a validarse en un tiempo, se decide con el
 *   mejor cuadro visto (y el guardia resuelve lo que la IA no pudo).
 * - Si no se ve ningún vehículo, se sigue esperando: el guardia puede cancelar.
 */
import type { CuadroEnVivo } from '../servicios/api'

export const CUADROS_ESTABLES = 3
export const ESPERA_MAXIMA_MS = 8000

export interface Seguimiento {
  /** Cuadros «validado» seguidos. */
  racha: number
  /** Momento en que se vio el primer vehículo confiable. */
  desde: number | null
  /** Puntaje del mejor cuadro visto hasta ahora. */
  mejorPuntaje: number
}

export const SEGUIMIENTO_INICIAL: Seguimiento = {
  racha: 0,
  desde: null,
  mejorPuntaje: -1,
}

export type Accion = 'seguir' | 'decidir_con_este' | 'decidir_con_mejor'

/** Hay al menos una detección que supera el umbral de confianza del detector. */
export function vioVehiculo(cuadro: CuadroEnVivo): boolean {
  return cuadro.detecciones.some((d) => d.confianza >= cuadro.umbral_confianza)
}

/**
 * Qué cuadro conviene usar como evidencia: validado antes que dudoso, y dentro de
 * cada grupo el que más se parece (o, sin semejanza, el más confiable).
 */
export function puntaje(cuadro: CuadroEnVivo): number {
  const fino = cuadro.semejanza ?? cuadro.confianza ?? 0
  if (cuadro.estado === 'validado') return 3 + fino
  if (cuadro.estado === 'verificar' && vioVehiculo(cuadro)) return 2 + fino
  if (cuadro.estado === 'rechazado') return 1 + fino
  return fino
}

export function seguir(
  seguimiento: Seguimiento,
  cuadro: CuadroEnVivo,
  ahora: number,
  opciones = { estables: CUADROS_ESTABLES, esperaMs: ESPERA_MAXIMA_MS },
): { seguimiento: Seguimiento; accion: Accion; esMejor: boolean } {
  const racha = cuadro.estado === 'validado' ? seguimiento.racha + 1 : 0
  const desde = seguimiento.desde ?? (vioVehiculo(cuadro) ? ahora : null)
  const valor = puntaje(cuadro)
  const esMejor = valor > seguimiento.mejorPuntaje
  const nuevo: Seguimiento = {
    racha,
    desde,
    mejorPuntaje: Math.max(valor, seguimiento.mejorPuntaje),
  }

  let accion: Accion = 'seguir'
  if (racha >= opciones.estables) accion = 'decidir_con_este'
  else if (desde !== null && ahora - desde >= opciones.esperaMs) accion = 'decidir_con_mejor'
  return { seguimiento: nuevo, accion, esMejor }
}

/** Segundos que faltan para decidir con el mejor cuadro, o null si aún no corre. */
export function segundosRestantes(
  seguimiento: Seguimiento,
  ahora: number,
  esperaMs = ESPERA_MAXIMA_MS,
) {
  if (seguimiento.desde === null) return null
  const transcurrido = Math.max(0, ahora - seguimiento.desde) // el reloj de pantalla puede ir atrasado
  return Math.max(0, Math.ceil((esperaMs - transcurrido) / 1000))
}
