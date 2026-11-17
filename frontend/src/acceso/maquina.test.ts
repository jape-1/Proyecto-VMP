import { describe, expect, it } from 'vitest'
import type { EstadoSesion, LecturaQR } from '../servicios/api'
import { ESTADO_INICIAL, etapa, pasoDeResultado, reducir, requiereDecision } from './maquina'

const LECTURA: LecturaQR = {
  id_sesion: 7,
  usuario: {
    codigo_utp: 'U90000001',
    nombres: 'Ana',
    apellidos: 'Pérez',
    tipo_usuario: 'estudiante',
    sede: 'Torre Arequipa',
  },
  vehiculos: [],
}

function resultado(parcial: Partial<EstadoSesion>): EstadoSesion {
  return {
    id_sesion: 7,
    estado: 'validado',
    motivo: null,
    mensaje: '',
    id_vehiculo_reconocido: null,
    confianza: null,
    semejanza: null,
    id_vehiculo_mas_parecido: null,
    detecciones: [],
    modelo_version: null,
    evidencia_url: null,
    puede_decidir: false,
    espacio: null,
    usuario: null,
    vehiculos: [],
    ...parcial,
  }
}

describe('flujo del punto de acceso', () => {
  it('recorre el camino feliz: QR, foto, análisis, ingreso', () => {
    let estado = reducir(ESTADO_INICIAL, { tipo: 'QR_LEIDO' })
    expect(estado.paso).toBe('validando_qr')

    estado = reducir(estado, { tipo: 'QR_OK', lectura: LECTURA })
    expect(estado.paso).toBe('capturando_foto')
    expect(estado.lectura?.id_sesion).toBe(7)

    estado = reducir(estado, { tipo: 'FOTO_ENVIADA', capturaLocal: 'blob:1' })
    expect(estado.paso).toBe('analizando')

    estado = reducir(estado, { tipo: 'RESULTADO', resultado: resultado({ estado: 'validado' }) })
    expect(estado.paso).toBe('ingreso_ok')
    expect(estado.lectura?.id_sesion).toBe(7)
  })

  it('un QR con error vuelve a permitir otra lectura', () => {
    const error = { mensaje: 'QR revocado', codigo: 'QR_REVOCADO', requestId: '' }
    let estado = reducir(reducir(ESTADO_INICIAL, { tipo: 'QR_LEIDO' }), { tipo: 'QR_ERROR', error })
    expect(estado.paso).toBe('qr_error')
    expect(estado.error?.codigo).toBe('QR_REVOCADO')

    estado = reducir(estado, { tipo: 'QR_LEIDO' })
    expect(estado.paso).toBe('validando_qr')
    expect(estado.error).toBeNull()
  })

  it('ignora un QR leído en mitad de otro ingreso', () => {
    const enCurso = reducir(ESTADO_INICIAL, { tipo: 'QR_OK', lectura: LECTURA })
    expect(reducir(enCurso, { tipo: 'QR_LEIDO' })).toBe(enCurso)
  })

  it('si la IA no responde, el guardia decide a mano', () => {
    const analizando = reducir(reducir(ESTADO_INICIAL, { tipo: 'QR_OK', lectura: LECTURA }), {
      tipo: 'FOTO_ENVIADA',
      capturaLocal: 'blob:1',
    })
    const estado = reducir(analizando, { tipo: 'IA_SIN_RESPUESTA' })
    expect(estado.paso).toBe('ia_no_disponible')
    expect(requiereDecision(estado.paso)).toBe(true)
    // Conserva la foto y los datos del usuario para decidir.
    expect(estado.capturaLocal).toBe('blob:1')
    expect(estado.lectura).not.toBeNull()
  })

  it('reiniciar limpia todo', () => {
    const estado = reducir(ESTADO_INICIAL, { tipo: 'QR_OK', lectura: LECTURA })
    expect(reducir(estado, { tipo: 'REINICIAR' })).toEqual(ESTADO_INICIAL)
  })
})

describe('pasoDeResultado', () => {
  it('traduce cada estado del backend a una pantalla', () => {
    expect(pasoDeResultado(resultado({ estado: 'validado' }))).toBe('ingreso_ok')
    expect(pasoDeResultado(resultado({ estado: 'verificar', puede_decidir: true }))).toBe(
      'verificar',
    )
    expect(pasoDeResultado(resultado({ estado: 'ia_no_disponible', puede_decidir: true }))).toBe(
      'ia_no_disponible',
    )
  })

  it('distingue el rechazo que propone la IA del que ya decidió el guardia', () => {
    expect(pasoDeResultado(resultado({ estado: 'rechazado', puede_decidir: true }))).toBe(
      'rechazado',
    )
    expect(pasoDeResultado(resultado({ estado: 'rechazado', puede_decidir: false }))).toBe(
      'denegado',
    )
  })
})

describe('barra de pasos', () => {
  it('agrupa las pantallas en tres etapas', () => {
    expect(etapa('qr_error')).toBe(0)
    expect(etapa('analizando')).toBe(1)
    expect(etapa('verificar')).toBe(2)
    expect(etapa('denegado')).toBe(2)
  })
})
