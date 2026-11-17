import { useCallback, useEffect, useMemo, useState } from 'react'
import { AlertaError, LogoUTP, RotuloSimulacion } from '../componentes/comunes'
import type { Espacio, Espacios } from '../servicios/api'
import { apiGuardia } from '../servicios/api'
import type { TextoError } from '../servicios/mensajes'
import { fechaLima, textoDeError, TIPO_VMP } from '../servicios/mensajes'

/** Cada cuánto se refresca el monitoreo. Sin cámaras, solo cambia con ingresos y salidas. */
const REFRESCO_MS = 5000

type ApiGuardia = ReturnType<typeof apiGuardia>

const ESTADO = {
  disponible: 'Libre',
  ocupado: 'Ocupado',
  mantenimiento: 'Mantenimiento',
} as const

/** Contador compacto para la cabecera del punto de acceso. Enlaza al monitoreo. */
export function ResumenEspacios({ api, refrescar }: { api: ApiGuardia; refrescar?: string }) {
  const [espacios, setEspacios] = useState<Espacios | null>(null)
  useEffect(() => {
    const consultar = () =>
      void api
        .espacios()
        .then(setEspacios)
        .catch(() => undefined)
    consultar()
    const reloj = window.setInterval(consultar, REFRESCO_MS)
    return () => window.clearInterval(reloj)
  }, [api, refrescar])

  if (!espacios || espacios.total === 0) return null
  return (
    <a href="/espacios" className={`chip-espacios ${espacios.lleno ? 'lleno' : ''}`}>
      {espacios.lleno
        ? 'Estacionamiento lleno'
        : `${espacios.libres} de ${espacios.total} espacios libres`}
      <span aria-hidden="true">›</span>
    </a>
  )
}

/**
 * Monitoreo básico de espacios para seguridad (HU17, RF16; 17-nov-2026, docs/13).
 *
 * Todavía sin cámaras de casillas: el sistema asigna el espacio al validar el
 * ingreso y el guardia marca la salida con «Liberar». Solo seguridad y
 * administración ven esta pantalla (RF21).
 */
export function Monitoreo({ guardia, alSalir }: { guardia: string; alSalir: () => void }) {
  const api = useMemo(() => apiGuardia(guardia), [guardia])
  const [espacios, setEspacios] = useState<Espacios | null>(null)
  const [error, setError] = useState<TextoError | null>(null)
  const [elegido, setElegido] = useState<Espacio | null>(null)
  const [aviso, setAviso] = useState('')

  const cargar = useCallback(() => {
    api
      .espacios()
      .then((nuevos) => {
        setEspacios(nuevos)
        setError(null)
      })
      .catch((e) => setError(textoDeError(e)))
  }, [api])

  useEffect(() => {
    cargar()
    const reloj = window.setInterval(cargar, REFRESCO_MS)
    return () => window.clearInterval(reloj)
  }, [cargar])

  useEffect(() => {
    if (!aviso) return
    const espera = window.setTimeout(() => setAviso(''), 2500)
    return () => window.clearTimeout(espera)
  }, [aviso])

  async function liberar(espacio: Espacio) {
    try {
      setEspacios(await api.liberarEspacio(espacio.id_espacio))
      setAviso(`${espacio.codigo} quedó libre.`)
    } catch (e) {
      setError(textoDeError(e))
    } finally {
      setElegido(null)
    }
  }

  const ocupacion = espacios && espacios.total ? espacios.ocupados / espacios.total : 0

  return (
    <div className="monitoreo">
      <header className="acceso-cabecera">
        <LogoUTP />
        <div>
          <strong>Monitoreo de espacios</strong>
          <div className="suave pequeno">Sede {espacios?.sede ?? 'Torre Arequipa'}</div>
        </div>
        <RotuloSimulacion />
        <span className="crecer" />
        <a className="boton compacto" href="/acceso">
          Punto de acceso
        </a>
        <span className="pequeno">
          <strong>Guardia:</strong> {guardia}
        </span>
        <button type="button" className="boton compacto" onClick={alSalir}>
          Terminar turno
        </button>
      </header>

      <main className="monitoreo-cuerpo">
        {error && <AlertaError error={error} alReintentar={cargar} />}

        {espacios && espacios.total === 0 && (
          <div className="tarjeta">
            <h2>No hay espacios configurados</h2>
            <p className="suave">
              Corre `python -m app.seed` en el backend para crear las 5 zonas.
            </p>
          </div>
        )}

        {espacios && espacios.total > 0 && (
          <>
            {espacios.lleno && (
              <div className="resultado error" role="alert">
                <h2>Estacionamiento lleno</h2>
                <span>El punto de acceso no deja leer más QR hasta que se libere un espacio.</span>
              </div>
            )}

            <section className="cifras" aria-label="Resumen">
              <div className="cifra libre">
                <strong>{espacios.libres}</strong>
                Libres
              </div>
              <div className="cifra ocupado">
                <strong>{espacios.ocupados}</strong>
                Ocupados
              </div>
              <div className="cifra">
                <strong>{espacios.mantenimiento}</strong>
                En mantenimiento
              </div>
              <div className="cifra">
                <strong>{espacios.total}</strong>
                Total
              </div>
            </section>

            <div className="columna">
              <div className="fila">
                <strong>Ocupación</strong>
                <span className="crecer" />
                <span>{Math.floor(ocupacion * 100)} %</span>
              </div>
              <div className="barra-ocupacion" aria-hidden="true">
                <span style={{ width: `${ocupacion * 100}%` }} />
              </div>
            </div>

            <section className="tarjeta columna" aria-label="Espacios por zona">
              {espacios.zonas.map((zona) => (
                <div className="zona" key={zona.nombre}>
                  <div className="zona-nombre">
                    Zona {zona.nombre}
                    <span className="suave pequeno">
                      {zona.libres}/{zona.total} libres
                    </span>
                  </div>
                  {zona.espacios.map((espacio) => (
                    <Casilla
                      key={espacio.id_espacio}
                      espacio={espacio}
                      alElegir={() => setElegido(espacio)}
                    />
                  ))}
                </div>
              ))}
            </section>

            <p className="suave pequeno">
              Sin cámaras de casillas todavía: el espacio se asigna al validar el ingreso y se
              libera aquí cuando el vehículo sale. Se actualiza cada {REFRESCO_MS / 1000} s.
            </p>
          </>
        )}
      </main>

      {elegido?.ocupante && (
        <div
          className="dialogo-fondo"
          role="dialog"
          aria-modal="true"
          aria-label={`Espacio ${elegido.codigo}`}
        >
          <div className="tarjeta columna">
            <h3>Espacio {elegido.codigo}</h3>
            <div>
              <strong>{elegido.ocupante.nombre}</strong>
              <div className="suave">{elegido.ocupante.codigo_utp}</div>
            </div>
            {elegido.ocupante.vehiculo && (
              <div>
                {TIPO_VMP[elegido.ocupante.vehiculo.tipo_vmp]} {elegido.ocupante.vehiculo.marca}
                {elegido.ocupante.vehiculo.color && ` · ${elegido.ocupante.vehiculo.color}`}
              </div>
            )}
            <div className="suave">Desde {fechaLima(elegido.ocupante.desde, true)}</div>
            <div className="fila">
              <button
                type="button"
                className="boton primario"
                onClick={() => void liberar(elegido)}
              >
                Registrar salida y liberar
              </button>
              <button type="button" className="boton" onClick={() => setElegido(null)}>
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
      {aviso && (
        <div className="aviso-flotante" role="status">
          {aviso}
        </div>
      )}
    </div>
  )
}

function Casilla({ espacio, alElegir }: { espacio: Espacio; alElegir: () => void }) {
  const { ocupante } = espacio
  const contenido = (
    <>
      <strong>{espacio.codigo}</strong>
      <span>{ESTADO[espacio.estado]}</span>
      {ocupante && (
        <>
          <span className="nombre-corto">{ocupante.nombre.split(' ')[0]}</span>
          {ocupante.vehiculo && (
            <span className="nombre-corto suave">{TIPO_VMP[ocupante.vehiculo.tipo_vmp]}</span>
          )}
        </>
      )}
    </>
  )
  if (!ocupante) {
    return (
      <div
        className={`casilla ${espacio.estado}`}
        aria-label={`${espacio.codigo}: ${ESTADO[espacio.estado]}`}
      >
        {contenido}
      </div>
    )
  }
  return (
    <button
      type="button"
      className={`casilla ${espacio.estado}`}
      onClick={alElegir}
      aria-label={`${espacio.codigo}: ocupado por ${ocupante.nombre}. Ver detalle`}
    >
      {contenido}
    </button>
  )
}
