import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react'
import {
  AlertaError,
  Girando,
  IconoVMP,
  LogoUTP,
  RotuloSimulacion,
} from '../componentes/comunes'
import type { EstadoSesion, Identidades, LecturaQR, Salud, Vehiculo } from '../servicios/api'
import {
  apiGuardia,
  identidadesDeDemo,
  salud as consultarSalud,
  salidaDeDemo,
  tokenQrDeDemo,
  urlImagen,
} from '../servicios/api'
import {
  nombreDeClase,
  porcentaje,
  textoDeError,
  textoDeMotivo,
  TIPO_USUARIO,
  TIPO_VMP,
} from '../servicios/mensajes'
import { LectorQR, SelectorCamara } from './Camara'
import { AnalisisEnVivo } from './EnVivo'
import { ResumenEspacios } from './Monitoreo'
import { ESTADO_INICIAL, etapa, reducir, requiereDecision } from './maquina'

const PASOS = ['Leer QR', 'IA en vivo', 'Resultado']

/** Sonido distinto para aprobado, error y aviso (docs/24 §3). */
function sonar(tipo: 'ok' | 'error' | 'aviso') {
  try {
    const audio = new AudioContext()
    const notas = { ok: [660, 880], error: [220, 180], aviso: [440, 440] }[tipo]
    notas.forEach((frecuencia, i) => {
      const oscilador = audio.createOscillator()
      const volumen = audio.createGain()
      oscilador.frequency.value = frecuencia
      oscilador.type = tipo === 'error' ? 'square' : 'sine'
      const inicio = audio.currentTime + i * 0.18
      volumen.gain.setValueAtTime(0.0001, inicio)
      volumen.gain.exponentialRampToValueAtTime(0.18, inicio + 0.02)
      volumen.gain.exponentialRampToValueAtTime(0.0001, inicio + 0.16)
      oscilador.connect(volumen).connect(audio.destination)
      oscilador.start(inicio)
      oscilador.stop(inicio + 0.2)
    })
  } catch {
    // Sin audio: la pantalla ya lo dice con color, ícono y texto.
  }
}

export function PuntoAcceso({ guardia, alSalir }: { guardia: string; alSalir: () => void }) {
  const api = useMemo(() => apiGuardia(guardia), [guardia])
  const [estado, despachar] = useReducer(reducir, ESTADO_INICIAL)
  const [estadoSalud, setEstadoSalud] = useState<Salud | null>(null)
  const espera = useRef<AbortController | null>(null)
  const [avisoDemo, setAvisoDemo] = useState('')
  // Atajos solo para la demo: de quién simular el QR sin cámara.
  const [usuariosDemo, setUsuariosDemo] = useState<Identidades['usuarios']>([])
  const [usuarioDemo, setUsuarioDemo] = useState(
    () => new URLSearchParams(location.search).get('codigo') ?? '',
  )
  useEffect(() => {
    identidadesDeDemo()
      .then((identidades) => {
        setUsuariosDemo(identidades.usuarios)
        setUsuarioDemo((actual) => actual || identidades.usuarios[0]?.codigo_utp || '')
      })
      .catch(() => undefined)
  }, [])
  const { paso, lectura, resultado, error, capturaLocal } = estado

  // Indicadores Backend / IA.
  useEffect(() => {
    const consultar = () => void consultarSalud().then(setEstadoSalud)
    consultar()
    const reloj = window.setInterval(consultar, 15000)
    return () => window.clearInterval(reloj)
  }, [])

  const reiniciar = useCallback(() => {
    espera.current?.abort()
    if (capturaLocal) URL.revokeObjectURL(capturaLocal)
    despachar({ tipo: 'REINICIAR' })
  }, [capturaLocal])

  // Un sonido distinto según el resultado.
  useEffect(() => {
    if (paso === 'ingreso_ok') sonar('ok')
    if (paso === 'qr_error' || paso === 'rechazado' || paso === 'denegado') sonar('error')
    if (paso === 'verificar' || paso === 'ia_no_disponible') sonar('aviso')
  }, [paso])

  async function validarQr(texto: string) {
    const token = texto.trim()
    if (!token || (paso !== 'esperando_qr' && paso !== 'qr_error')) return
    despachar({ tipo: 'QR_LEIDO' })
    try {
      despachar({ tipo: 'QR_OK', lectura: await api.leerQr(token) })
    } catch (e) {
      despachar({ tipo: 'QR_ERROR', error: textoDeError(e) })
    }
  }

  async function enviarFoto(foto: Blob, nombre: string) {
    if (!lectura) return
    despachar({ tipo: 'FOTO_ENVIADA', capturaLocal: URL.createObjectURL(foto) })
    espera.current = new AbortController()
    try {
      await api.subirCaptura(lectura.id_sesion, foto, nombre)
      const final = await api.esperarResultado(lectura.id_sesion, espera.current.signal)
      despachar({ tipo: 'RESULTADO', resultado: final })
    } catch (e) {
      if (espera.current.signal.aborted) return
      const texto = textoDeError(e)
      if (texto.codigo === 'IA_NO_DISPONIBLE' || texto.codigo === 'SIN_CONEXION') {
        despachar({ tipo: 'IA_SIN_RESPUESTA' })
      } else {
        // P. ej. el archivo no es una imagen: se vuelve a pedir la foto.
        despachar({ tipo: 'QR_OK', lectura })
        despachar({ tipo: 'ERROR', error: texto })
      }
    }
  }

  async function decidir(decision: 'aprobar_manual' | 'rechazar', motivo: string, id?: number) {
    if (!lectura) return
    try {
      const final = await api.decidir(lectura.id_sesion, decision, motivo, id)
      despachar({ tipo: 'RESULTADO', resultado: final })
    } catch (e) {
      despachar({ tipo: 'ERROR', error: textoDeError(e) })
    }
  }

  async function cancelar() {
    const idSesion = lectura?.id_sesion
    reiniciar()
    // Avisar al backend es un intento: si la sesión ya cerró, no hay nada que hacer.
    if (idSesion) await api.cancelar(idSesion).catch(() => undefined)
  }

  const vehiculos = resultado?.vehiculos.length ? resultado.vehiculos : (lectura?.vehiculos ?? [])

  return (
    <div className="acceso">
      <header className="acceso-cabecera">
        <LogoUTP />
        <div>
          <strong>Punto de acceso VMP</strong>
          <div className="suave pequeno">Sede Torre Arequipa · Puerta 1</div>
        </div>
        <RotuloSimulacion />
        <span className="crecer" />
        <span className={`indicador ${estadoSalud?.backend ? '' : 'mal'}`} role="status">
          Backend{estadoSalud?.backend ? '' : ' sin conexión'}
        </span>
        <span className={`indicador ${estadoSalud?.ia ? '' : 'mal'}`} role="status">
          IA{estadoSalud?.ia ? '' : ' no disponible'}
        </span>
        <span className="pequeno">
          <strong>Guardia:</strong> {guardia}
        </span>
        <SelectorCamara />
        <button type="button" className="boton compacto" onClick={alSalir}>
          Terminar turno
        </button>
      </header>

      <div className="acceso-pasos">
        <ol aria-label="Pasos">
          {PASOS.map((nombre, i) => {
            const actual = etapa(paso)
            return (
              <li
                key={nombre}
                className={i < actual ? 'hecho' : i === actual ? 'actual' : ''}
                aria-current={i === actual ? 'step' : undefined}
              >
                <span>{i < actual ? '✓' : i + 1}</span>
                {nombre}
              </li>
            )
          })}
        </ol>
        <ResumenEspacios api={api} refrescar={`${paso}:${resultado?.id_sesion ?? ''}`} />
        <button type="button" className="boton" onClick={() => void cancelar()}>
          ✕ Cancelar
        </button>
      </div>

      <main className="acceso-cuerpo" aria-live="polite">
        {error && paso !== 'qr_error' && <AlertaError error={error} />}

        {(paso === 'esperando_qr' || paso === 'qr_error') && (
          <div className="acceso-dos">
            <LectorQR alLeer={(texto) => void validarQr(texto)} />
            <div className="columna">
              {paso === 'qr_error' && error ? (
                <div className="resultado error" role="alert">
                  <h2>{error.mensaje}</h2>
                  <span>Código: {error.codigo}</span>
                </div>
              ) : (
                <div className="tarjeta">
                  <h2>Acerca el QR a la cámara</h2>
                  <p className="suave">El usuario lo muestra desde la App UTP.</p>
                </div>
              )}
              <CodigoManual alEnviar={(texto) => void validarQr(texto)} />
            </div>
          </div>
        )}

        {paso === 'validando_qr' && (
          <div className="tarjeta fila">
            <Girando lado={48} />
            <h2>Validando QR…</h2>
          </div>
        )}

        {paso === 'capturando_foto' && lectura && (
          <div className="acceso-dos">
            <AnalisisEnVivo
              idSesion={lectura.id_sesion}
              vehiculos={lectura.vehiculos}
              analizar={api.analizarCuadro}
              alDecidir={(foto, nombre) => void enviarFoto(foto, nombre)}
              alFallar={(texto) =>
                texto.codigo === 'IA_NO_DISPONIBLE' || texto.codigo === 'SIN_CONEXION'
                  ? despachar({ tipo: 'IA_SIN_RESPUESTA' })
                  : despachar({ tipo: 'QR_ERROR', error: texto })
              }
            >
              <DatosUsuario lectura={lectura} />
            </AnalisisEnVivo>
          </div>
        )}

        {paso === 'analizando' && (
          <div className="acceso-dos">
            <div className="visor">{capturaLocal && <img src={capturaLocal} alt="Foto capturada" />}</div>
            <div className="tarjeta columna">
              <div className="fila">
                <Girando lado={48} />
                <h2>Verificando el vehículo…</h2>
              </div>
              <Cronometro />
            </div>
          </div>
        )}

        {paso === 'ingreso_ok' && resultado && (
          <>
            <div className="resultado ok" role="status">
              <h2>✓ Puede ingresar</h2>
              {resultado.espacio && (
                <p className="espacio-asignado">
                  Espacio asignado <strong>{resultado.espacio}</strong>
                </p>
              )}
              <span>
                {resultado.motivo === 'APROBADO_MANUAL'
                  ? 'Aprobado por el guardia.'
                  : `Confianza ${porcentaje(resultado.confianza)} · Semejanza ${porcentaje(resultado.semejanza)}`}
              </span>
              <CuentaRegresiva alTerminar={reiniciar} />
            </div>
            <Comparacion
              resultado={resultado}
              vehiculos={vehiculos}
              capturaLocal={capturaLocal}
              destacado={resultado.id_vehiculo_reconocido}
            />
          </>
        )}

        {paso === 'denegado' && (
          <div className="resultado error" role="alert">
            <h2>✕ Ingreso rechazado</h2>
            <span>Quedó registrado con evidencia.</span>
            <CuentaRegresiva alTerminar={reiniciar} />
          </div>
        )}

        {requiereDecision(paso) && (
          <>
            <div
              className={`resultado ${paso === 'rechazado' ? 'error' : 'aviso'}`}
              role="alert"
            >
              <h2>
                {paso === 'rechazado' && 'El vehículo no coincide'}
                {paso === 'verificar' && 'Revisa el vehículo y decide'}
                {paso === 'ia_no_disponible' && 'La IA no responde: decide tú'}
              </h2>
              <span>{textoDeMotivo(resultado?.motivo ?? 'IA_NO_DISPONIBLE')}</span>
              {resultado && resultado.detecciones.length > 0 && (
                <span>
                  La IA ve:{' '}
                  {resultado.detecciones
                    .map((d) => `${nombreDeClase(d.clase)} (${porcentaje(d.confianza)})`)
                    .join(', ')}
                  {resultado.semejanza !== null &&
                    ` · Semejanza con la foto registrada: ${porcentaje(resultado.semejanza)}`}
                </span>
              )}
            </div>
            <Comparacion
              resultado={resultado}
              vehiculos={vehiculos}
              capturaLocal={capturaLocal}
              destacado={resultado?.id_vehiculo_mas_parecido ?? null}
            />
            <Decision vehiculos={vehiculos} alDecidir={decidir} />
          </>
        )}

        {paso === 'esperando_qr' && usuarioDemo && (
          <p className="suave pequeno demo-atajos">
            <label htmlFor="usuario-demo">Solo para la demo, QR de</label>
            <select
              id="usuario-demo"
              value={usuarioDemo}
              onChange={(e) => {
                setUsuarioDemo(e.target.value)
                setAvisoDemo('')
              }}
            >
              {usuariosDemo.length === 0 && <option value={usuarioDemo}>{usuarioDemo}</option>}
              {usuariosDemo.map((u) => (
                <option key={u.codigo_utp} value={u.codigo_utp}>
                  {u.nombres.split(' ')[0]} {u.apellidos.split(' ')[0]} · {u.codigo_utp}
                </option>
              ))}
            </select>
            :
            <button
              type="button"
              className="boton enlace"
              onClick={() =>
                void tokenQrDeDemo(usuarioDemo)
                  .then(validarQr)
                  .catch((e) => despachar({ tipo: 'QR_ERROR', error: textoDeError(e) }))
              }
            >
              simular la lectura del QR
            </button>
            ·
            <button
              type="button"
              className="boton enlace"
              onClick={() =>
                void salidaDeDemo(usuarioDemo)
                  .then((n) =>
                    setAvisoDemo(
                      n > 0 ? `Salida registrada (${n}).` : 'No tenía vehículos dentro.',
                    ),
                  )
                  .catch((e) => setAvisoDemo(textoDeError(e).mensaje))
              }
            >
              registrar la salida de sus vehículos
            </button>
            {avisoDemo && <span role="status"> {avisoDemo}</span>}
          </p>
        )}
      </main>
    </div>
  )
}

/** Segundos que lleva la IA analizando. Empieza en 0 cada vez que se monta. */
function Cronometro() {
  const [segundos, setSegundos] = useState(0)
  useEffect(() => {
    const reloj = window.setInterval(() => setSegundos((s) => s + 1), 1000)
    return () => window.clearInterval(reloj)
  }, [])
  return <p className="suave">{segundos} s transcurridos</p>
}

/** Vuelve sola a «Leer QR» a los 5 s (docs/24 §3). */
function CuentaRegresiva({ alTerminar }: { alTerminar: () => void }) {
  const [quedan, setQuedan] = useState(5)
  useEffect(() => {
    if (quedan <= 0) {
      alTerminar()
      return
    }
    const espera = window.setTimeout(() => setQuedan((q) => q - 1), 1000)
    return () => window.clearTimeout(espera)
  }, [quedan, alTerminar])
  return <span>Vuelve a leer QR en {quedan} s</span>
}

function CodigoManual({ alEnviar }: { alEnviar: (texto: string) => void }) {
  const [codigo, setCodigo] = useState('')
  return (
    <form
      className="tarjeta columna"
      onSubmit={(evento) => {
        evento.preventDefault()
        alEnviar(codigo)
        setCodigo('')
      }}
    >
      <label className="campo">
        Ingresar código manualmente
        <input
          value={codigo}
          onChange={(evento) => setCodigo(evento.target.value)}
          placeholder="vmp1_…"
          autoComplete="off"
        />
      </label>
      <button type="submit" className="boton primario" disabled={codigo.trim().length < 8}>
        Validar código
      </button>
    </form>
  )
}

function DatosUsuario({ lectura }: { lectura: LecturaQR }) {
  const { usuario, vehiculos } = lectura
  return (
    <div className="tarjeta columna">
      <div>
        <h2>
          {usuario.nombres} {usuario.apellidos}
        </h2>
        <p className="suave">
          {usuario.codigo_utp} · {TIPO_USUARIO[usuario.tipo_usuario]}
        </p>
      </div>
      <strong>Vehículos registrados</strong>
      {vehiculos.map((v) => (
        <div className="vehiculo" key={v.id_vehiculo}>
          <FotoReferencia vehiculo={v} />
          <div>
            <strong>{TIPO_VMP[v.tipo_vmp]}</strong>
            <div className="suave pequeno">
              {v.marca} {v.modelo ?? ''} · {v.color}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

function FotoReferencia({ vehiculo }: { vehiculo: Vehiculo }) {
  const url = urlImagen(vehiculo.foto_referencia_url)
  return url ? (
    <img className="miniatura" src={url} alt={`Referencia: ${vehiculo.marca}`} />
  ) : (
    <span className="miniatura">
      <IconoVMP tipo={vehiculo.tipo_vmp} />
    </span>
  )
}

/** Captura y fotos de referencia lado a lado. */
function Comparacion({
  resultado,
  vehiculos,
  capturaLocal,
  destacado,
}: {
  resultado: EstadoSesion | null
  vehiculos: Vehiculo[]
  capturaLocal: string | null
  destacado: number | null
}) {
  const captura = urlImagen(resultado?.evidencia_url ?? null) ?? capturaLocal
  const semejanzaDe = (id: number) => {
    const valores = (resultado?.detecciones ?? []).flatMap((d) =>
      d.semejanzas.filter((s) => s.id_vehiculo === id).map((s) => s.semejanza),
    )
    return valores.length ? Math.max(...valores) : null
  }
  return (
    <div className="comparacion">
      <figure>
        {captura ? <img src={captura} alt="Foto capturada" /> : <div className="sin-foto">Sin foto</div>}
        <figcaption>
          <strong>Captura de la cámara</strong>
        </figcaption>
      </figure>
      {vehiculos.map((v) => {
        const url = urlImagen(v.foto_referencia_url)
        const semejanza = semejanzaDe(v.id_vehiculo)
        return (
          <figure key={v.id_vehiculo} className={v.id_vehiculo === destacado ? 'destacada' : ''}>
            {url ? (
              <img src={url} alt={`Referencia: ${v.marca}`} />
            ) : (
              <div className="sin-foto">Sin foto registrada</div>
            )}
            <figcaption>
              <strong>
                Registrado: {TIPO_VMP[v.tipo_vmp]} {v.marca}
              </strong>
              <div className="suave">
                {v.color}
                {semejanza !== null && ` · Semejanza ${porcentaje(semejanza)}`}
              </div>
            </figcaption>
          </figure>
        )
      })}
    </div>
  )
}

function Decision({
  vehiculos,
  alDecidir,
}: {
  vehiculos: Vehiculo[]
  alDecidir: (decision: 'aprobar_manual' | 'rechazar', motivo: string, id?: number) => Promise<void>
}) {
  const [motivo, setMotivo] = useState('')
  const [idVehiculo, setIdVehiculo] = useState<number | undefined>(vehiculos[0]?.id_vehiculo)
  const [enviando, setEnviando] = useState(false)
  const falta = motivo.trim().length < 3

  async function enviar(decision: 'aprobar_manual' | 'rechazar') {
    setEnviando(true)
    await alDecidir(decision, motivo.trim(), decision === 'aprobar_manual' ? idVehiculo : undefined)
    setEnviando(false)
  }

  return (
    <div className="tarjeta columna">
      <div className="fila">
        <label className="campo crecer">
          Motivo de la decisión (obligatorio)
          <input
            value={motivo}
            onChange={(evento) => setMotivo(evento.target.value)}
            maxLength={255}
            placeholder="Ej.: es su scooter, lo verifiqué a la vista"
          />
        </label>
        {vehiculos.length > 1 && (
          <label className="campo">
            Vehículo que ingresa
            <select
              value={idVehiculo}
              onChange={(evento) => setIdVehiculo(Number(evento.target.value))}
            >
              {vehiculos.map((v) => (
                <option key={v.id_vehiculo} value={v.id_vehiculo}>
                  {TIPO_VMP[v.tipo_vmp]} {v.marca}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>
      <div className="fila">
        <button
          type="button"
          className="boton ok grande crecer"
          disabled={falta || enviando}
          onClick={() => void enviar('aprobar_manual')}
        >
          ✓ Aprobar
        </button>
        <button
          type="button"
          className="boton peligro grande crecer"
          disabled={falta || enviando}
          onClick={() => void enviar('rechazar')}
        >
          ✕ Rechazar
        </button>
      </div>
    </div>
  )
}
