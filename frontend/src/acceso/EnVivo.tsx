import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import type { CuadroEnVivo, Deteccion, Vehiculo } from '../servicios/api'
import type { TextoError } from '../servicios/mensajes'
import {
  nombreDeClase,
  porcentaje,
  textoDeError,
  textoDeMotivo,
  TIPO_VMP,
} from '../servicios/mensajes'
import { cuadro, useCamara } from './usoCamara'
import {
  CUADROS_ESTABLES,
  SEGUIMIENTO_INICIAL,
  segundosRestantes,
  seguir,
  vioVehiculo,
} from './reglaEnVivo'

/** Lado del cuadro que se envía a la IA: el detector trabaja a 640 px. */
const LADO_CUADRO = 960
const COLOR = { ok: '#18a957', duda: '#f2a900', bajo: '#9aa5b1' }

const pausa = (ms: number) => new Promise((resolver) => setTimeout(resolver, ms))

function aJpeg(lienzo: HTMLCanvasElement): Promise<Blob | null> {
  return new Promise((resolver) => lienzo.toBlob(resolver, 'image/jpeg', 0.85))
}

function mejorSemejanza(d: Deteccion): number | null {
  return d.semejanzas.length ? Math.max(...d.semejanzas.map((s) => s.semejanza)) : null
}

/** Cajas con clase, confianza y semejanza sobre el video, como en la demo del modelo. */
function dibujar(lienzo: HTMLCanvasElement | null, ancho: number, alto: number, c: CuadroEnVivo) {
  if (!lienzo) return
  lienzo.width = ancho
  lienzo.height = alto
  const g = lienzo.getContext('2d')
  if (!g) return
  g.clearRect(0, 0, ancho, alto)
  const grosor = Math.max(2, Math.round(ancho / 260))
  const letra = Math.max(14, Math.round(ancho / 38))
  g.font = `700 ${letra}px Lato, system-ui, sans-serif`
  g.textBaseline = 'top'

  for (const d of c.detecciones) {
    if (!d.caja || d.caja.length !== 4) continue
    const [x1, y1, x2, y2] = d.caja
    const x = x1 * ancho
    const y = y1 * alto
    const semejanza = mejorSemejanza(d)
    const color =
      d.confianza < c.umbral_confianza
        ? COLOR.bajo
        : semejanza !== null && semejanza >= c.umbral_semejanza
          ? COLOR.ok
          : COLOR.duda
    g.strokeStyle = color
    g.lineWidth = grosor
    g.strokeRect(x, y, (x2 - x1) * ancho, (y2 - y1) * alto)

    const texto =
      `${nombreDeClase(d.clase)} ${porcentaje(d.confianza)}` +
      (semejanza !== null ? ` · semejanza ${porcentaje(semejanza)}` : '')
    const anchoTexto = g.measureText(texto).width + letra * 0.6
    const yTexto = y - letra * 1.4 >= 0 ? y - letra * 1.4 : y
    g.fillStyle = color
    g.fillRect(x, yTexto, anchoTexto, letra * 1.4)
    g.fillStyle = color === COLOR.duda ? '#1b2533' : '#ffffff'
    g.fillText(texto, x + letra * 0.3, yTexto + letra * 0.2)
  }
}

function Medidor({
  nombre,
  ayuda,
  valor,
  umbral,
}: {
  nombre: string
  ayuda: string
  valor: number | null
  umbral: number
}) {
  const pasa = valor !== null && valor >= umbral
  return (
    <div className="medidor">
      <div className="fila medidor-titulo">
        <strong>{nombre}</strong>
        <span className={pasa ? 'texto-ok' : 'suave'}>
          {porcentaje(valor)} <span className="suave pequeno">(mínimo {porcentaje(umbral)})</span>
        </span>
      </div>
      <div
        className="medidor-barra"
        role="meter"
        aria-label={nombre}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={valor === null ? undefined : Math.round(valor * 100)}
      >
        <span
          className={`medidor-relleno ${pasa ? 'ok' : ''}`}
          style={{ width: `${Math.min(100, (valor ?? 0) * 100)}%` }}
        />
        <span className="medidor-umbral" style={{ left: `${umbral * 100}%` }} />
      </div>
      <span className="suave pequeno">{ayuda}</span>
    </div>
  )
}

/**
 * Paso 2 del punto de acceso: la IA mira el video en vivo (17-nov-2026, docs/13).
 *
 * Envía cuadros a `/acceso/{id}/cuadro` uno tras otro (nunca dos a la vez) y dibuja
 * lo que ve. Con {@link CUADROS_ESTABLES} cuadros «validado» seguidos, o al agotarse
 * la espera con un vehículo a la vista, entrega ese cuadro para la decisión oficial.
 */
export function AnalisisEnVivo({
  idSesion,
  vehiculos,
  analizar,
  alDecidir,
  alFallar,
  children,
}: {
  idSesion: number
  vehiculos: Vehiculo[]
  analizar: (idSesion: number, cuadro: Blob) => Promise<CuadroEnVivo>
  alDecidir: (foto: Blob, nombre: string) => void
  alFallar: (error: TextoError) => void
  children?: ReactNode
}) {
  const { video, error } = useCamara()
  const capa = useRef<HTMLCanvasElement>(null)
  const [ultimo, setUltimo] = useState<CuadroEnVivo | null>(null)
  const [seguimiento, setSeguimiento] = useState(SEGUIMIENTO_INICIAL)
  const [ahora, setAhora] = useState(() => Date.now())
  const avisos = useRef({ alDecidir, alFallar })
  useEffect(() => {
    avisos.current = { alDecidir, alFallar }
  }, [alDecidir, alFallar])

  // Reloj para la cuenta regresiva.
  useEffect(() => {
    const reloj = window.setInterval(() => setAhora(Date.now()), 500)
    return () => window.clearInterval(reloj)
  }, [])

  useEffect(() => {
    if (error) return
    let activo = true
    let actual = SEGUIMIENTO_INICIAL
    let mejor: Blob | null = null
    let fallos = 0

    void (async () => {
      while (activo) {
        const lienzo = video.current && cuadro(video.current, LADO_CUADRO)
        const foto = lienzo && (await aJpeg(lienzo))
        if (!lienzo || !foto) {
          await pausa(200) // la cámara aún no entrega imagen
          continue
        }
        try {
          const resultado = await analizar(idSesion, foto)
          if (!activo) return
          fallos = 0
          const paso = seguir(actual, resultado, Date.now())
          actual = paso.seguimiento
          if (paso.esMejor) mejor = foto
          setUltimo(resultado)
          setSeguimiento(actual)
          dibujar(capa.current, lienzo.width, lienzo.height, resultado)
          if (paso.accion !== 'seguir') {
            activo = false
            avisos.current.alDecidir(
              paso.accion === 'decidir_con_este' ? foto : (mejor ?? foto),
              'captura-en-vivo.jpg',
            )
            return
          }
        } catch (e) {
          if (!activo) return
          const texto = textoDeError(e)
          const pasajero = texto.codigo === 'IA_NO_DISPONIBLE' || texto.codigo === 'SIN_CONEXION'
          if (pasajero && ++fallos < 3) {
            await pausa(800)
            continue
          }
          activo = false
          avisos.current.alFallar(texto)
          return
        }
      }
    })()
    return () => {
      activo = false
    }
  }, [idSesion, analizar, error, video])

  const restantes = segundosRestantes(seguimiento, ahora)
  const parecido = vehiculos.find((v) => v.id_vehiculo === ultimo?.id_vehiculo_mas_parecido)
  const hayVehiculo = ultimo !== null && vioVehiculo(ultimo)

  let titulo = 'Iniciando la IA…'
  let detalle = 'Apunta la cámara al vehículo: completo y de costado.'
  if (ultimo && !hayVehiculo) {
    titulo = 'Esperando un vehículo frente a la cámara'
  } else if (ultimo?.estado === 'validado') {
    titulo = parecido
      ? `Coincide con ${TIPO_VMP[parecido.tipo_vmp]} ${parecido.marca}`
      : 'Coincide con un vehículo registrado'
    detalle = `Confirmando: ${seguimiento.racha} de ${CUADROS_ESTABLES} cuadros seguidos.`
  } else if (ultimo) {
    titulo = textoDeMotivo(ultimo.motivo ?? 'SIN_DETECCION')
    detalle =
      restantes !== null
        ? `Si no mejora, decide el guardia en ${restantes} s.`
        : 'Acerca o gira el vehículo.'
  }

  return (
    <>
      <div className="visor" aria-label="Cámara en vivo con lo que detecta la IA">
        {error ? (
          <p style={{ padding: 20 }}>{error}</p>
        ) : (
          <div className="visor-capa">
            <video ref={video} muted playsInline />
            <canvas ref={capa} className="capa-ia" aria-hidden="true" />
          </div>
        )}
      </div>

      <div className="columna">
        <div className="tarjeta columna en-vivo" aria-live="polite">
          <div className="fila">
            <span className="punto-vivo" aria-hidden="true" />
            <strong>IA en vivo</strong>
            <span className="crecer" />
            {ultimo?.ms != null && <span className="suave pequeno">{ultimo.ms} ms por cuadro</span>}
          </div>
          <h2>{titulo}</h2>
          <p className="suave">{detalle}</p>
          {ultimo && hayVehiculo && (
            <p className="pequeno">
              La IA ve:{' '}
              {ultimo.detecciones
                .filter((d) => d.confianza >= ultimo.umbral_confianza)
                .map((d) => nombreDeClase(d.clase))
                .join(', ')}
            </p>
          )}
          <Medidor
            nombre="Confianza"
            ayuda="¿Es un VMP y de qué tipo? (detector YOLO26)"
            valor={ultimo?.confianza ?? null}
            umbral={ultimo?.umbral_confianza ?? 0.6}
          />
          <Medidor
            nombre="Semejanza"
            ayuda={
              parecido
                ? `Con la foto registrada de ${TIPO_VMP[parecido.tipo_vmp]} ${parecido.marca}`
                : 'Con la foto registrada del vehículo'
            }
            valor={ultimo?.semejanza ?? null}
            umbral={ultimo?.umbral_semejanza ?? 0.7}
          />
          <label className="boton enlace pequeno subir-respaldo">
            ¿Sin cámara? Subir una foto
            <input
              type="file"
              accept="image/jpeg,image/png"
              hidden
              onChange={(evento) => {
                const archivo = evento.target.files?.[0]
                if (archivo) alDecidir(archivo, archivo.name)
                evento.target.value = ''
              }}
            />
          </label>
        </div>
        {children}
      </div>
    </>
  )
}
