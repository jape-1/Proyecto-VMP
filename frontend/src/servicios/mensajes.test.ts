import { describe, expect, it } from 'vitest'
import { ErrorApi } from './api'
import { fechaLima, nombreDeClase, porcentaje, textoDeError, textoDeMotivo } from './mensajes'

describe('textoDeError', () => {
  it('traduce los códigos del QR a los mensajes del guardia', () => {
    expect(textoDeError(new ErrorApi('QR_EXPIRADO', 'x')).mensaje).toBe(
      'QR vencido: el usuario debe renovarlo',
    )
    expect(textoDeError(new ErrorApi('USUARIO_INACTIVO', 'x')).mensaje).toBe('Matrícula no vigente')
  })

  it('explica qué vio la IA cuando la foto es de otra clase', () => {
    const error = new ErrorApi('FOTO_TIPO_NO_COINCIDE', 'x', 422, {
      detectado: ['scooter'],
      tipo_vmp: 'bicicleta',
    })
    expect(textoDeError(error).mensaje).toBe(
      'La foto muestra scooter, pero registraste bicicleta. Sube una foto de tu vehículo.',
    )
  })

  it('conserva el código y el request_id para soporte', () => {
    const texto = textoDeError(new ErrorApi('QR_REVOCADO', 'x', 409, {}, 'abc123'))
    expect(texto.codigo).toBe('QR_REVOCADO')
    expect(texto.requestId).toBe('abc123')
  })

  it('usa el mensaje del backend si el código es desconocido', () => {
    expect(textoDeError(new ErrorApi('CODIGO_NUEVO', 'Mensaje del backend')).mensaje).toBe(
      'Mensaje del backend',
    )
  })

  it('no falla con errores que no vienen del backend', () => {
    expect(textoDeError(new TypeError('x')).codigo).toBe('ERROR_DESCONOCIDO')
  })
})

describe('etiquetas', () => {
  it('nombra las clases del detector sin decir «eléctrica»', () => {
    // El modelo se entrenó con motos en general (docs/25 §1).
    expect(nombreDeClase('moto_electrica')).toBe('Moto')
    expect(nombreDeClase('scooter')).toBe('Scooter')
    expect(nombreDeClase('clase_rara')).toBe('clase_rara')
  })

  it('explica los motivos de la semejanza', () => {
    expect(textoDeMotivo('SEMEJANZA_BAJA')).toContain('se parece poco')
    expect(textoDeMotivo(null)).toBe('')
  })

  it('muestra porcentajes y fechas de Lima', () => {
    expect(porcentaje(0.834)).toBe('83 %')
    expect(porcentaje(null)).toBe('—')
    // 03:30 UTC del 16 es todavía el 15 en Lima (UTC-5).
    expect(fechaLima('2027-05-16T03:30:00Z')).toBe('15/05/2027')
  })
})

describe('porcentaje', () => {
  it('trunca para no aparentar que se alcanzó un umbral', () => {
    expect(porcentaje(0.6957)).toBe('69 %')
    expect(porcentaje(0.7)).toBe('70 %')
    expect(porcentaje(0.29)).toBe('29 %')
    expect(porcentaje(1)).toBe('100 %')
    expect(porcentaje(null)).toBe('—')
  })
})

