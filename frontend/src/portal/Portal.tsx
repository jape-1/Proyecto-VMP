import { useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { AlertaError, Girando, LogoUTP, Miniatura, RotuloSimulacion } from '../componentes/comunes'
import type { DatosVehiculo, ListaVehiculos, Perfil, TipoVMP, Vehiculo } from '../servicios/api'
import { apiUsuario, urlImagen } from '../servicios/api'
import type { TextoError } from '../servicios/mensajes'
import { textoDeError, TIPO_USUARIO, TIPO_VMP } from '../servicios/mensajes'

/** Opciones del portal real: se ven, pero no funcionan en esta simulación. */
const MENU_DECORATIVO = ['Inicio', 'Cursos', 'Notas', 'Horario', 'Pagos', 'Trámites']
const MAX_FOTO_BYTES = 5 * 1024 * 1024

type Vista =
  | { nombre: 'perfil' }
  | { nombre: 'vehiculos' }
  | { nombre: 'formulario'; vehiculo: Vehiculo | null }
  | { nombre: 'foto'; idVehiculo: number }
  | { nombre: 'listo' }

export function Portal({ codigo, alSalir }: { codigo: string; alSalir: () => void }) {
  const api = useMemo(() => apiUsuario(codigo), [codigo])
  const [perfil, setPerfil] = useState<Perfil | null>(null)
  const [error, setError] = useState<TextoError | null>(null)
  const [vista, setVista] = useState<Vista>({ nombre: 'perfil' })
  const [aviso, setAviso] = useState('')

  const cargarPerfil = useCallback(() => {
    api
      .perfil()
      .then(setPerfil)
      .catch((e) => setError(textoDeError(e)))
  }, [api])
  useEffect(cargarPerfil, [cargarPerfil])

  useEffect(() => {
    if (!aviso) return
    const espera = window.setTimeout(() => setAviso(''), 2500)
    return () => window.clearTimeout(espera)
  }, [aviso])

  const bloqueado = perfil?.estado_matricula !== 'activo'
  const iniciales = perfil ? `${perfil.nombres[0]}${perfil.apellidos[0]}` : '··'

  return (
    <div className="portal">
      <header className="portal-cabecera">
        <LogoUTP />
        <strong>Portal UTP</strong>
        <RotuloSimulacion />
        <span className="crecer" />
        <span className="avatar" aria-hidden="true">
          {iniciales}
        </span>
        <div className="pequeno">
          <strong>{perfil ? `${perfil.nombres} ${perfil.apellidos}` : 'Cargando…'}</strong>
          <div className="suave">{perfil?.codigo_utp ?? codigo}</div>
        </div>
        <button type="button" className="boton" onClick={alSalir}>
          Cerrar sesión
        </button>
      </header>

      <nav className="portal-menu" aria-label="Menú del portal">
        {MENU_DECORATIVO.map((opcion) => (
          <button
            key={opcion}
            type="button"
            onClick={() => setAviso('No disponible en esta simulación')}
          >
            {opcion}
          </button>
        ))}
        <button type="button" className="activo" onClick={() => setVista({ nombre: 'perfil' })}>
          Estacionamiento VMP
        </button>
      </nav>

      <main className="portal-contenido columna">
        <h1>Estacionamiento VMP</h1>
        {error && <AlertaError error={error} alReintentar={() => {
              setError(null)
              cargarPerfil()
            }} />}
        {!perfil && !error && <div className="esqueleto" style={{ height: 220 }} />}

        {perfil && vista.nombre === 'perfil' && (
          <VistaPerfil
            perfil={perfil}
            alAceptar={() => api.aceptarConsentimiento().then(setPerfil)}
            alContinuar={() => setVista({ nombre: 'vehiculos' })}
          />
        )}
        {perfil && !bloqueado && vista.nombre === 'vehiculos' && (
          <VistaVehiculos
            api={api}
            alAgregar={() => setVista({ nombre: 'formulario', vehiculo: null })}
            alEditar={(vehiculo) => setVista({ nombre: 'formulario', vehiculo })}
            alFoto={(idVehiculo) => setVista({ nombre: 'foto', idVehiculo })}
          />
        )}
        {perfil && !bloqueado && vista.nombre === 'formulario' && (
          <VistaFormulario
            api={api}
            vehiculo={vista.vehiculo}
            alCancelar={() => setVista({ nombre: 'vehiculos' })}
            alGuardar={(idVehiculo, pideFoto) =>
              setVista(pideFoto ? { nombre: 'foto', idVehiculo } : { nombre: 'vehiculos' })
            }
          />
        )}
        {perfil && !bloqueado && vista.nombre === 'foto' && (
          <VistaFoto
            api={api}
            idVehiculo={vista.idVehiculo}
            alTerminar={() => setVista({ nombre: 'listo' })}
            alVolver={() => setVista({ nombre: 'vehiculos' })}
          />
        )}
        {vista.nombre === 'listo' && (
          <section className="tarjeta columna">
            <div className="alerta ok">✓ Foto validada. Tu vehículo quedó registrado.</div>
            <h2>Tu QR de acceso está disponible en la App UTP</h2>
            <div className="fila">
              <a className="boton primario" href={`/app?codigo=${codigo}`}>
                Abrir la App UTP (simulada)
              </a>
              <button type="button" className="boton" onClick={() => setVista({ nombre: 'vehiculos' })}>
                Volver a mis vehículos
              </button>
            </div>
          </section>
        )}
      </main>

      {aviso && (
        <div className="aviso-flotante" role="status">
          {aviso}
        </div>
      )}
    </div>
  )
}

type Api = ReturnType<typeof apiUsuario>

// ------------------------------------------------------------ 1. Perfil y consentimiento
function VistaPerfil({
  perfil,
  alAceptar,
  alContinuar,
}: {
  perfil: Perfil
  alAceptar: () => Promise<void>
  alContinuar: () => void
}) {
  const [marcado, setMarcado] = useState(perfil.acepta_tratamiento_datos)
  const [verDetalle, setVerDetalle] = useState(false)
  const [error, setError] = useState<TextoError | null>(null)
  const inactivo = perfil.estado_matricula !== 'activo'

  async function continuar() {
    try {
      if (!perfil.acepta_tratamiento_datos) await alAceptar()
      alContinuar()
    } catch (e) {
      setError(textoDeError(e))
    }
  }

  return (
    <section className="tarjeta columna">
      <h2>Perfil y consentimiento</h2>
      {inactivo && (
        <div className="alerta" role="alert">
          ⚠ Tu matrícula no figura como vigente. No puedes registrar vehículos.
        </div>
      )}
      <dl className="rejilla-datos">
        {[
          ['Nombres', perfil.nombres],
          ['Apellidos', perfil.apellidos],
          ['Código UTP', perfil.codigo_utp],
          ['Tipo de usuario', TIPO_USUARIO[perfil.tipo_usuario]],
          ['Correo institucional', perfil.correo_institucional],
          ['Sede', perfil.sede],
          ['Estado de matrícula', perfil.estado_matricula === 'activo' ? 'Vigente' : 'No vigente'],
        ].map(([etiqueta, valor]) => (
          <div key={etiqueta}>
            <dt>{etiqueta}</dt>
            <dd>{valor}</dd>
          </div>
        ))}
      </dl>
      <label className="fila">
        <input
          type="checkbox"
          checked={marcado}
          disabled={inactivo || perfil.acepta_tratamiento_datos}
          onChange={(evento) => setMarcado(evento.target.checked)}
          style={{ width: 22, height: 22 }}
        />
        <span>
          Acepto el tratamiento de mis datos personales para el servicio de estacionamiento VMP.{' '}
          <button type="button" className="boton enlace" onClick={() => setVerDetalle(!verDetalle)}>
            Ver detalle
          </button>
        </span>
      </label>
      {verDetalle && (
        <p className="suave pequeno">
          Se guardan tus datos de identificación, los datos y la foto de cada vehículo, y la foto
          que toma la cámara en cada ingreso, solo para verificar que el vehículo es tuyo. Las fotos
          no se publican y se muestran únicamente al personal de seguridad.
        </p>
      )}
      {error && <AlertaError error={error} />}
      <div>
        <button
          type="button"
          className="boton primario"
          disabled={inactivo || !marcado}
          onClick={() => void continuar()}
        >
          Continuar a mis vehículos
        </button>
      </div>
    </section>
  )
}

// ------------------------------------------------------------ 2. Mis vehículos
function VistaVehiculos({
  api,
  alAgregar,
  alEditar,
  alFoto,
}: {
  api: Api
  alAgregar: () => void
  alEditar: (vehiculo: Vehiculo) => void
  alFoto: (idVehiculo: number) => void
}) {
  const [lista, setLista] = useState<ListaVehiculos | null>(null)
  const [error, setError] = useState<TextoError | null>(null)
  const [porEliminar, setPorEliminar] = useState<Vehiculo | null>(null)

  const cargar = useCallback(() => {
    api
      .vehiculos()
      .then(setLista)
      .catch((e) => setError(textoDeError(e)))
  }, [api])
  useEffect(cargar, [cargar])

  async function eliminar(vehiculo: Vehiculo) {
    setPorEliminar(null)
    try {
      await api.eliminarVehiculo(vehiculo.id_vehiculo)
      setError(null)
      cargar()
    } catch (e) {
      setError(textoDeError(e))
    }
  }

  const lleno = lista ? lista.usados >= lista.max : false

  return (
    <section className="columna">
      <div className="fila">
        <h2 className="crecer">Mis vehículos</h2>
        {lista && (
          <span className="chip">
            {lista.usados} de {lista.max} vehículos
          </span>
        )}
        <button type="button" className="boton primario" disabled={!lista || lleno} onClick={alAgregar}>
          + Agregar
        </button>
      </div>
      {lleno && <p className="suave pequeno">Máximo 3 vehículos por usuario.</p>}
      {error && <AlertaError error={error} alReintentar={() => {
              setError(null)
              cargar()
            }} />}
      {!lista && !error && (
        <>
          <div className="esqueleto" style={{ height: 96 }} />
          <div className="esqueleto" style={{ height: 96 }} />
        </>
      )}
      {lista?.items.length === 0 && (
        <div className="tarjeta columna" style={{ textAlign: 'center' }}>
          <h3>Aún no registras vehículos</h3>
          <p className="suave">Agrega tu bicicleta, scooter o moto para obtener tu QR de acceso.</p>
        </div>
      )}
      {lista?.items.map((v) => (
        <article className="tarjeta vehiculo" key={v.id_vehiculo}>
          <Miniatura url={urlImagen(v.foto_referencia_url)} tipo={v.tipo_vmp} />
          <div className="crecer">
            <strong>
              {TIPO_VMP[v.tipo_vmp]} · {v.marca} {v.modelo ?? ''}
            </strong>
            <div className="suave">
              {v.color}
              {v.caracteristica_distintiva ? ` · ${v.caracteristica_distintiva}` : ''}
            </div>
            <span className={`chip ${v.tiene_foto ? 'ok' : 'aviso'}`}>
              {v.tiene_foto ? '✓ Foto validada' : '⚠ Falta foto'}
            </span>
          </div>
          <button type="button" className="boton" onClick={() => alFoto(v.id_vehiculo)}>
            {v.tiene_foto ? 'Cambiar foto' : 'Subir foto'}
          </button>
          <button type="button" className="boton" onClick={() => alEditar(v)}>
            Editar
          </button>
          <button type="button" className="boton" onClick={() => setPorEliminar(v)}>
            Eliminar
          </button>
        </article>
      ))}

      {porEliminar && (
        <div className="dialogo-fondo" role="dialog" aria-modal="true" aria-label="Confirmar eliminación">
          <div className="tarjeta columna">
            <h3>
              ¿Eliminar {TIPO_VMP[porEliminar.tipo_vmp].toLowerCase()} {porEliminar.marca}?
            </h3>
            <p className="suave">Ya no podrás ingresar con este vehículo.</p>
            <div className="fila">
              <button type="button" className="boton peligro" onClick={() => void eliminar(porEliminar)}>
                Sí, eliminar
              </button>
              <button type="button" className="boton" onClick={() => setPorEliminar(null)}>
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

// ------------------------------------------------------------ 3. Registrar / editar
function VistaFormulario({
  api,
  vehiculo,
  alCancelar,
  alGuardar,
}: {
  api: Api
  vehiculo: Vehiculo | null
  alCancelar: () => void
  alGuardar: (idVehiculo: number, pideFoto: boolean) => void
}) {
  const [datos, setDatos] = useState({
    tipo_vmp: vehiculo?.tipo_vmp ?? ('' as TipoVMP | ''),
    marca: vehiculo?.marca ?? '',
    modelo: vehiculo?.modelo ?? '',
    color: vehiculo?.color ?? '',
    caracteristica_distintiva: vehiculo?.caracteristica_distintiva ?? '',
  })
  const [intentado, setIntentado] = useState(false)
  const [error, setError] = useState<TextoError | null>(null)
  const [guardando, setGuardando] = useState(false)

  const faltas = {
    tipo_vmp: datos.tipo_vmp ? '' : 'Elige el tipo de vehículo.',
    marca: datos.marca.trim() ? '' : 'Escribe la marca.',
    color: datos.color.trim() ? '' : 'Escribe el color.',
  }
  const cambiaTipo = vehiculo !== null && datos.tipo_vmp !== vehiculo.tipo_vmp

  async function guardar(evento: FormEvent) {
    evento.preventDefault()
    setIntentado(true)
    if (!datos.tipo_vmp || faltas.marca || faltas.color) return
    const cuerpo: DatosVehiculo = {
      tipo_vmp: datos.tipo_vmp,
      marca: datos.marca.trim(),
      modelo: datos.modelo.trim() || null,
      color: datos.color.trim(),
      caracteristica_distintiva: datos.caracteristica_distintiva.trim() || null,
    }
    setGuardando(true)
    try {
      if (vehiculo) {
        await api.editarVehiculo(vehiculo.id_vehiculo, cuerpo)
        // Al cambiar el tipo, el backend descarta la foto anterior: hay que subir otra.
        alGuardar(vehiculo.id_vehiculo, cambiaTipo || !vehiculo.tiene_foto)
      } else {
        alGuardar((await api.crearVehiculo(cuerpo)).id_vehiculo, true)
      }
    } catch (e) {
      setError(textoDeError(e))
      setGuardando(false)
    }
  }

  const campo = (clave: 'marca' | 'modelo' | 'color', etiqueta: string, obligatorio: boolean) => (
    <label className="campo">
      {etiqueta}
      {obligatorio ? '' : ' (opcional)'}
      <input
        value={datos[clave]}
        maxLength={50}
        onChange={(evento) => setDatos({ ...datos, [clave]: evento.target.value })}
        aria-invalid={intentado && clave !== 'modelo' && !!faltas[clave]}
      />
      {intentado && clave !== 'modelo' && faltas[clave] && (
        <span className="error-campo">{faltas[clave]}</span>
      )}
    </label>
  )

  return (
    <form className="tarjeta columna" onSubmit={(evento) => void guardar(evento)} noValidate>
      <h2>{vehiculo ? 'Editar vehículo' : 'Registrar vehículo'}</h2>
      <label className="campo">
        Tipo de vehículo
        <select
          value={datos.tipo_vmp}
          onChange={(evento) => setDatos({ ...datos, tipo_vmp: evento.target.value as TipoVMP })}
          aria-invalid={intentado && !!faltas.tipo_vmp}
        >
          <option value="">Selecciona…</option>
          {(Object.keys(TIPO_VMP) as TipoVMP[]).map((tipo) => (
            <option key={tipo} value={tipo}>
              {TIPO_VMP[tipo]}
            </option>
          ))}
        </select>
        {intentado && faltas.tipo_vmp && <span className="error-campo">{faltas.tipo_vmp}</span>}
      </label>
      {cambiaTipo && vehiculo?.tiene_foto && (
        <div className="alerta aviso">
          ⚠ Al cambiar el tipo tendrás que subir una foto nueva del vehículo.
        </div>
      )}
      <div className="rejilla-datos">
        {campo('marca', 'Marca', true)}
        {campo('modelo', 'Modelo', false)}
        {campo('color', 'Color', true)}
      </div>
      <label className="campo">
        Característica distintiva (opcional)
        <textarea
          rows={2}
          maxLength={255}
          value={datos.caracteristica_distintiva}
          onChange={(evento) => setDatos({ ...datos, caracteristica_distintiva: evento.target.value })}
          placeholder="Ej.: canasta delantera, sticker azul en el manubrio"
        />
        <span className="suave pequeno">{datos.caracteristica_distintiva.length} de 255</span>
      </label>
      {error && <AlertaError error={error} />}
      <div className="fila">
        <button type="submit" className="boton primario" disabled={guardando}>
          {guardando ? 'Guardando…' : 'Guardar y continuar'}
        </button>
        <button type="button" className="boton" onClick={alCancelar}>
          Cancelar
        </button>
      </div>
    </form>
  )
}

// ------------------------------------------------------------ 4. Foto de referencia
function VistaFoto({
  api,
  idVehiculo,
  alTerminar,
  alVolver,
}: {
  api: Api
  idVehiculo: number
  alTerminar: () => void
  alVolver: () => void
}) {
  const [archivo, setArchivo] = useState<File | null>(null)
  const [validando, setValidando] = useState(false)
  const [error, setError] = useState<TextoError | null>(null)
  const vistaPrevia = useMemo(() => (archivo ? URL.createObjectURL(archivo) : null), [archivo])
  useEffect(() => () => void (vistaPrevia && URL.revokeObjectURL(vistaPrevia)), [vistaPrevia])

  function elegir(nuevo: File | undefined) {
    setError(null)
    if (!nuevo) return
    if (!['image/jpeg', 'image/png'].includes(nuevo.type) || nuevo.size > MAX_FOTO_BYTES) {
      setArchivo(null)
      setError({
        mensaje: 'La foto debe ser JPG o PNG y pesar como máximo 5 MB.',
        codigo: 'FOTO_INVALIDA',
        requestId: '',
      })
      return
    }
    setArchivo(nuevo)
  }

  async function validar() {
    if (!archivo) return
    setValidando(true)
    setError(null)
    try {
      await api.subirFoto(idVehiculo, archivo, archivo.name)
      alTerminar()
    } catch (e) {
      setError(textoDeError(e))
      setValidando(false)
    }
  }

  return (
    <section className="tarjeta columna">
      <h2>Foto de referencia</h2>
      <p className="suave">
        Con esta foto la cámara del estacionamiento comprobará que el vehículo es el tuyo.
      </p>
      <ul className="pautas">
        <li>🚲 Vehículo completo</li>
        <li>🧱 Fondo despejado</li>
        <li>☀️ Buena luz</li>
        <li>↔️ Vista lateral</li>
        <li>🚫 Sin filtros</li>
      </ul>
      {vistaPrevia && <img className="vista-previa" src={vistaPrevia} alt="Vista previa de la foto elegida" />}
      <div className="fila">
        <label className="boton">
          Elegir archivo
          <input
            type="file"
            accept="image/jpeg,image/png"
            hidden
            onChange={(evento) => elegir(evento.target.files?.[0])}
          />
        </label>
        <label className="boton">
          Tomar con la cámara
          <input
            type="file"
            accept="image/*"
            capture="environment"
            hidden
            onChange={(evento) => elegir(evento.target.files?.[0])}
          />
        </label>
        <span className="suave pequeno">JPG o PNG, máximo 5 MB.</span>
      </div>
      {validando && (
        <div className="alerta aviso" role="status">
          <Girando lado={20} /> Validando con IA…
        </div>
      )}
      {error && <AlertaError error={error} />}
      <div className="fila">
        <button
          type="button"
          className="boton primario"
          disabled={!archivo || validando}
          onClick={() => void validar()}
        >
          Validar foto
        </button>
        <button type="button" className="boton" onClick={alVolver}>
          Volver a mis vehículos
        </button>
      </div>
    </section>
  )
}
