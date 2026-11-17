/**
 * Quién usa cada interfaz en este navegador.
 *
 * Simulación (docs/13, 17-nov-2026): el Portal y la App piden solo el código UTP,
 * sin contraseña; en el sistema real la UTP autentica al usuario y nosotros nunca
 * vemos su contraseña. El Punto de acceso pide elegir al guardia.
 *
 * La identidad se recuerda en `localStorage` solo por comodidad: si el navegador
 * no lo permite, se vuelve a pedir y nada se rompe.
 */
import { olvidarSesion } from './api'

export type Interfaz = 'portal' | 'app' | 'acceso'

const CLAVE: Record<Interfaz, string> = {
  portal: 'vmp.sesion.portal',
  app: 'vmp.sesion.app',
  acceso: 'vmp.sesion.acceso',
}

/** Parámetro de la dirección que también inicia sesión (útil para enlaces y pruebas). */
const PARAMETRO: Record<Interfaz, string> = { portal: 'codigo', app: 'codigo', acceso: 'guardia' }

export const rolDe = (interfaz: Interfaz) => (interfaz === 'acceso' ? 'guardia' : 'usuario')

export function leerSesion(interfaz: Interfaz): string | null {
  const desdeDireccion = new URLSearchParams(location.search).get(PARAMETRO[interfaz])?.trim()
  if (desdeDireccion) {
    guardarSesion(interfaz, desdeDireccion)
    return desdeDireccion
  }
  try {
    return localStorage.getItem(CLAVE[interfaz])
  } catch {
    return null
  }
}

export function guardarSesion(interfaz: Interfaz, identidad: string): void {
  try {
    localStorage.setItem(CLAVE[interfaz], identidad)
  } catch {
    // Sin almacenamiento: la sesión dura lo que dure la pestaña.
  }
}

export function cerrarSesion(interfaz: Interfaz, identidad: string): void {
  try {
    localStorage.removeItem(CLAVE[interfaz])
  } catch {
    // Nada que borrar.
  }
  olvidarSesion(rolDe(interfaz), identidad)
  // Quita `?codigo=` / `?guardia=` para que recargar no vuelva a entrar.
  history.replaceState(null, '', location.pathname)
}
