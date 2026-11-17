import { describe, expect, it } from 'vitest'
import type { CuadroEnVivo } from '../servicios/api'
import {
  CUADROS_ESTABLES,
  ESPERA_MAXIMA_MS,
  SEGUIMIENTO_INICIAL,
  segundosRestantes,
  seguir,
} from './reglaEnVivo'

function cuadro(cambios: Partial<CuadroEnVivo> = {}): CuadroEnVivo {
  return {
    estado: 'validado',
    motivo: null,
    confianza: 0.9,
    semejanza: 0.85,
    id_vehiculo_mas_parecido: 1,
    detecciones: [
      {
        clase: 'scooter',
        confianza: 0.9,
        caja: [0.1, 0.1, 0.5, 0.9],
        semejanzas: [],
      },
    ],
    umbral_confianza: 0.6,
    umbral_semejanza: 0.7,
    ms: 200,
    ...cambios,
  }
}
const vacio = () =>
  cuadro({
    estado: 'verificar',
    motivo: 'SIN_DETECCION',
    detecciones: [],
    confianza: null,
    semejanza: null,
  })
const dudoso = (semejanza: number) =>
  cuadro({ estado: 'verificar', motivo: 'SEMEJANZA_BAJA', semejanza })

describe('video en vivo', () => {
  it('decide solo tras varios cuadros validados seguidos', () => {
    let s = SEGUIMIENTO_INICIAL
    for (let i = 1; i < CUADROS_ESTABLES; i++) {
      const paso = seguir(s, cuadro(), i * 300)
      expect(paso.accion).toBe('seguir')
      s = paso.seguimiento
    }
    expect(seguir(s, cuadro(), 1000).accion).toBe('decidir_con_este')
  })

  it('un cuadro dudoso en medio reinicia la racha', () => {
    let s = seguir(SEGUIMIENTO_INICIAL, cuadro(), 0).seguimiento
    s = seguir(s, cuadro(), 300).seguimiento
    s = seguir(s, dudoso(0.5), 600).seguimiento
    expect(s.racha).toBe(0)
    expect(seguir(s, cuadro(), 900).accion).toBe('seguir')
  })

  it('sin vehículo a la vista espera sin límite', () => {
    let s = SEGUIMIENTO_INICIAL
    for (let t = 0; t < 60000; t += 1000) {
      const paso = seguir(s, vacio(), t)
      expect(paso.accion).toBe('seguir')
      s = paso.seguimiento
    }
    expect(segundosRestantes(s, 60000)).toBeNull()
  })

  it('con un vehículo que no llega al umbral decide con el mejor cuadro al agotarse la espera', () => {
    let s = seguir(SEGUIMIENTO_INICIAL, vacio(), 0).seguimiento
    let paso = seguir(s, dudoso(0.5), 1000)
    expect(paso.esMejor).toBe(true)
    s = paso.seguimiento
    paso = seguir(s, dudoso(0.4), 2000)
    expect(paso.esMejor).toBe(false)
    s = paso.seguimiento
    paso = seguir(s, dudoso(0.6), 3000)
    expect(paso.esMejor).toBe(true)
    s = paso.seguimiento
    expect(segundosRestantes(s, 3000)).toBe(6)
    expect(seguir(s, dudoso(0.3), 1000 + ESPERA_MAXIMA_MS).accion).toBe('decidir_con_mejor')
  })

  it('un cuadro validado vale más que uno dudoso con más semejanza', () => {
    const s = seguir(SEGUIMIENTO_INICIAL, dudoso(0.69), 0).seguimiento
    expect(seguir(s, cuadro({ semejanza: 0.7 }), 300).esMejor).toBe(true)
  })

  it('la cuenta regresiva no pasa de la espera máxima aunque el reloj vaya atrasado', () => {
    const s = seguir(SEGUIMIENTO_INICIAL, dudoso(0.5), 10_000).seguimiento
    expect(segundosRestantes(s, 9_600)).toBe(ESPERA_MAXIMA_MS / 1000)
  })
})
