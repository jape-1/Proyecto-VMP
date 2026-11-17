import { useCallback, useEffect, useMemo, useState } from 'react'
import { AlertaError, IconoVMP, LogoUTP, RotuloSimulacion } from '../componentes/comunes'
import type { Perfil, QR } from '../servicios/api'
import { apiUsuario } from '../servicios/api'
import type { TextoError } from '../servicios/mensajes'
import { fechaLima, textoDeError, TIPO_VMP } from '../servicios/mensajes'

/** Opciones de la app real: se ven, pero no funcionan en esta simulación. */
const BARRA_DECORATIVA = ['Inicio', 'Cursos', 'Agenda']

const ESTADO_QR = {
  activo: { texto: 'Vigente', clase: 'ok' },
  expirado: { texto: 'Vencido', clase: 'aviso' },
  revocado: { texto: 'Revocado', clase: 'error' },
} as const

export function AppMovil({ codigo, alSalir }: { codigo: string; alSalir: () => void }) {
  const api = useMemo(() => apiUsuario(codigo), [codigo])
  const [perfil, setPerfil] = useState<Perfil | null>(null)
  const [qr, setQr] = useState<QR | null>(null)
  const [error, setError] = useState<TextoError | null>(null)
  const [confirmar, setConfirmar] = useState(false)
  const [aviso, setAviso] = useState('')

  const cargar = useCallback(() => {
    Promise.all([api.perfil(), api.qr()])
      .then(([nuevoPerfil, nuevoQr]) => {
        setPerfil(nuevoPerfil)
        setQr(nuevoQr)
      })
      .catch((e) => setError(textoDeError(e)))
  }, [api])
  useEffect(cargar, [cargar])

  useEffect(() => {
    if (!aviso) return
    const espera = window.setTimeout(() => setAviso(''), 2500)
    return () => window.clearTimeout(espera)
  }, [aviso])

  async function regenerar() {
    setConfirmar(false)
    try {
      setQr(await api.regenerarQr())
    } catch (e) {
      setError(textoDeError(e))
    }
  }

  const estado = qr ? (qr.vigente ? ESTADO_QR.activo : ESTADO_QR[qr.estado === 'activo' ? 'expirado' : qr.estado]) : null
  const sinVehiculos = qr !== null && qr.vehiculos.length === 0

  return (
    <div className="movil-marco">
      <div className="movil">
        <header className="movil-cabecera">
          <LogoUTP />
          <strong className="crecer">Mi QR de estacionamiento</strong>
          <button type="button" className="movil-salir" onClick={alSalir}>
            Salir
          </button>
        </header>

        <main className="movil-cuerpo">
          <RotuloSimulacion />

          {error && !qr && (
            <AlertaError
              error={{ ...error, mensaje: 'No pudimos cargar tu QR.' }}
              alReintentar={() => {
                setError(null)
                cargar()
              }}
            />
          )}
          {error && qr && <AlertaError error={error} />}
          {!qr && !error && <div className="esqueleto" style={{ height: 420 }} />}

          {sinVehiculos && (
            <div className="tarjeta columna" style={{ textAlign: 'center' }}>
              <h2>Aún no registras vehículos</h2>
              <p className="suave">Hazlo desde el Portal UTP.</p>
              <a className="boton primario" href={`/portal?codigo=${codigo}`}>
                Ir al Portal UTP (simulado)
              </a>
            </div>
          )}

          {qr && estado && !sinVehiculos && (
            <>
              <section className="carne">
                <div className="carne-franja">
                  <span>Estacionamiento VMP</span>
                  <span className={`chip ${estado.clase}`}>{estado.texto}</span>
                </div>
                <img
                  className={`carne-qr ${qr.vigente ? '' : 'atenuado'}`}
                  src={`data:image/png;base64,${qr.imagen_qr_png_base64}`}
                  alt={qr.vigente ? 'Código QR de acceso' : 'Código QR no vigente'}
                />
                <div style={{ padding: '0 16px 16px' }}>
                  <strong>{perfil ? `${perfil.nombres} ${perfil.apellidos}` : ''}</strong>
                  <div className="suave">{perfil?.codigo_utp}</div>
                  <div className="pequeno">Válido hasta: {fechaLima(qr.fecha_expiracion)}</div>
                  <div className="suave pequeno">Código personal e intransferible</div>
                </div>
              </section>

              {qr.vigente ? (
                <>
                  <p className="suave pequeno" style={{ textAlign: 'center' }}>
                    💡 Sube el brillo de tu pantalla
                  </p>
                  <button type="button" className="boton" onClick={() => setConfirmar(true)}>
                    Regenerar QR
                  </button>
                </>
              ) : (
                <button type="button" className="boton primario" onClick={() => void regenerar()}>
                  Renovar QR
                </button>
              )}

              <section className="tarjeta columna">
                <strong>Mis vehículos</strong>
                {qr.vehiculos.map((v) => (
                  <div className="fila" key={v.id_vehiculo}>
                    <IconoVMP tipo={v.tipo_vmp} lado={32} />
                    <div>
                      <strong>{TIPO_VMP[v.tipo_vmp]}</strong>
                      <div className="suave pequeno">
                        {v.marca} {v.modelo ?? ''} · {v.color}
                      </div>
                    </div>
                  </div>
                ))}
              </section>
            </>
          )}
        </main>

        <nav className="movil-barra" aria-label="Navegación de la app">
          {BARRA_DECORATIVA.map((opcion) => (
            <button
              key={opcion}
              type="button"
              onClick={() => setAviso('No disponible en esta simulación')}
            >
              {opcion}
            </button>
          ))}
          <button type="button" className="activo">
            Mi QR
          </button>
        </nav>
      </div>

      {confirmar && (
        <div className="dialogo-fondo" role="dialog" aria-modal="true" aria-label="Regenerar QR">
          <div className="tarjeta columna">
            <h3>¿Regenerar tu QR?</h3>
            <p className="suave">El QR anterior dejará de funcionar.</p>
            <div className="fila">
              <button type="button" className="boton primario" onClick={() => void regenerar()}>
                Sí, regenerar
              </button>
              <button type="button" className="boton" onClick={() => setConfirmar(false)}>
                Cancelar
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
