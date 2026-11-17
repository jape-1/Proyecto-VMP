import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import type { Identidades } from '../servicios/api'
import { identidadesDeDemo, iniciarSesion } from '../servicios/api'
import { textoDeError, TIPO_USUARIO } from '../servicios/mensajes'
import type { TipoUsuario } from '../servicios/api'
import type { Interfaz } from '../servicios/sesion'
import { rolDe } from '../servicios/sesion'
import { Girando, LogoUTP, RotuloSimulacion } from './comunes'

const TURNO: Record<string, string> = { manana: 'mañana', tarde: 'tarde', noche: 'noche' }

const TITULO: Record<Interfaz, string> = {
  portal: 'Portal UTP',
  app: 'App UTP',
  acceso: 'Punto de acceso VMP',
}

/**
 * Inicio de sesión simulado (docs/13, 17-nov-2026).
 * Usuario: solo el código UTP, sin contraseña (la UTP real autentica; nosotros no
 * pedimos ni guardamos su contraseña). Guardia: elige su usuario de la lista.
 */
export function InicioSesion({
  interfaz,
  alEntrar,
}: {
  interfaz: Interfaz
  alEntrar: (identidad: string) => void
}) {
  const rol = rolDe(interfaz)
  const [identidades, setIdentidades] = useState<Identidades | null>(null)
  const [sinLista, setSinLista] = useState(false)
  const [codigo, setCodigo] = useState('')
  const [entrando, setEntrando] = useState<string | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    identidadesDeDemo()
      .then(setIdentidades)
      .catch(() => setSinLista(true))
  }, [])

  function entrar(identidad: string) {
    const limpia = rol === 'usuario' ? identidad.trim().toUpperCase() : identidad
    if (!limpia) return
    setError('')
    setEntrando(limpia)
    iniciarSesion(rol, limpia)
      .then(() => alEntrar(limpia))
      .catch((e) => {
        const texto = textoDeError(e)
        setError(
          texto.codigo === 'USUARIO_INEXISTENTE'
            ? 'No encontramos ese código UTP. Prueba con uno de los perfiles de ejemplo.'
            : texto.mensaje,
        )
        setEntrando(null)
      })
  }

  function enviar(evento: FormEvent) {
    evento.preventDefault()
    entrar(codigo)
  }

  return (
    <main className={`inicio-sesion ${interfaz}`}>
      <div className="tarjeta inicio-sesion-caja">
        <div className="fila">
          <LogoUTP />
          <strong>{TITULO[interfaz]}</strong>
        </div>
        <RotuloSimulacion />

        {rol === 'usuario' ? (
          <>
            <h1>Inicia sesión</h1>
            <form className="columna" onSubmit={enviar}>
              <div className="campo">
                <label htmlFor="codigo-utp">Código UTP</label>
                <input
                  id="codigo-utp"
                  value={codigo}
                  onChange={(e) => setCodigo(e.target.value)}
                  placeholder="U90000001"
                  autoComplete="off"
                  autoCapitalize="characters"
                  spellCheck={false}
                />
              </div>
              <button
                type="submit"
                className="boton primario"
                disabled={!codigo.trim() || entrando !== null}
              >
                {entrando === codigo.trim().toUpperCase() ? <Girando /> : 'Ingresar'}
              </button>
            </form>
            <p className="suave pequeno">
              Simulación: no se pide contraseña. En el sistema real, la UTP verifica tu
              identidad y este servicio nunca ve tu contraseña.
            </p>
          </>
        ) : (
          <>
            <h1>Iniciar turno</h1>
            <p className="suave">Elige tu usuario de seguridad.</p>
          </>
        )}

        {error && (
          <p className="alerta" role="alert">
            <span aria-hidden="true">⚠</span> {error}
          </p>
        )}

        {sinLista && (
          <p className="suave pequeno" role="status">
            No se pudo cargar la lista de perfiles. ¿Está encendido el backend?
          </p>
        )}

        {identidades && rol === 'usuario' && (
          <section className="columna" aria-labelledby="titulo-perfiles">
            <h2 id="titulo-perfiles" className="pequeno suave">
              Perfiles de ejemplo
            </h2>
            {identidades.usuarios.map((u) => (
              <button
                key={u.codigo_utp}
                type="button"
                className="perfil-ejemplo"
                disabled={entrando !== null}
                onClick={() => entrar(u.codigo_utp)}
              >
                <strong>
                  {u.nombres} {u.apellidos}
                </strong>
                <span className="suave pequeno">
                  {u.codigo_utp} · {TIPO_USUARIO[u.tipo_usuario as TipoUsuario] ?? u.tipo_usuario}
                  {u.estado_matricula !== 'activo' && ' · matrícula no vigente'}
                </span>
              </button>
            ))}
          </section>
        )}

        {identidades && rol === 'guardia' && (
          <section className="columna" aria-label="Personal de seguridad">
            {identidades.guardia.map((g) => (
              <button
                key={g.usuario_acceso}
                type="button"
                className="perfil-ejemplo"
                disabled={entrando !== null}
                onClick={() => entrar(g.usuario_acceso)}
              >
                <strong>
                  {g.nombres} {g.apellidos}
                </strong>
                <span className="suave pequeno">
                  {g.usuario_acceso} · turno {TURNO[g.turno] ?? g.turno}
                </span>
              </button>
            ))}
          </section>
        )}
      </div>
    </main>
  )
}
