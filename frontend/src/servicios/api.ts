/**
 * ÚNICO archivo que habla con el backend (docs/24 §4).
 * Los nombres de campos son los de la API real (backend/app/modules/*\/schemas.py).
 *
 * Inicio de sesión simulado: el token se pide a `/dev/sesion/*`
 * (solo existe con ENTORNO=dev, docs/18 §4).
 */

/**
 * Sin `VITE_API_URL`, el backend está en el mismo equipo que sirve el frontend,
 * puerto 8000. Así un celular que abre http://192.168.x.x:5173 llega al backend
 * de la laptop y no a su propio `localhost`.
 */
export const URL_BACKEND: string = (
  import.meta.env.VITE_API_URL ||
  (typeof location === 'undefined'
    ? 'http://localhost:8000' // pruebas sin navegador
    : `${location.protocol}//${location.hostname}:8000`)
).replace(/\/$/, '')
const API = `${URL_BACKEND}/api/v1`

// ---------------------------------------------------------------- tipos
export type TipoVMP = 'bicicleta' | 'bicicleta_electrica' | 'scooter_electrico' | 'moto_electrica'
export type TipoUsuario = 'estudiante' | 'docente' | 'administrativo'
export type EstadoValidacion =
  | 'pendiente'
  | 'validado'
  | 'verificar'
  | 'rechazado'
  | 'ia_no_disponible'

export interface Perfil {
  id_usuario_utp: number
  codigo_utp: string
  tipo_usuario: TipoUsuario
  nombres: string
  apellidos: string
  correo_institucional: string
  sede: string
  estado_matricula: 'activo' | 'inactivo'
  acepta_tratamiento_datos: boolean
}

export interface DatosVehiculo {
  tipo_vmp: TipoVMP
  marca: string
  modelo: string | null
  color: string
  caracteristica_distintiva: string | null
}

export interface Vehiculo extends DatosVehiculo {
  id_vehiculo: number
  foto_referencia_url: string | null
  tiene_foto: boolean
}

export interface ListaVehiculos {
  items: Vehiculo[]
  max: number
  usados: number
}

export interface QR {
  id_qr: number
  estado: 'activo' | 'revocado' | 'expirado'
  vigente: boolean
  fecha_expiracion: string | null
  imagen_qr_png_base64: string
  vehiculos: Pick<Vehiculo, 'id_vehiculo' | 'tipo_vmp' | 'marca' | 'modelo' | 'color'>[]
}

export interface UsuarioAcceso {
  codigo_utp: string
  nombres: string
  apellidos: string
  tipo_usuario: TipoUsuario
  sede: string
}

export interface LecturaQR {
  id_sesion: number
  usuario: UsuarioAcceso
  vehiculos: Vehiculo[]
}

export interface Deteccion {
  clase: string
  confianza: number
  /** Caja normalizada [x1, y1, x2, y2] respecto a la imagen. */
  caja?: number[] | null
  semejanzas: { id_vehiculo: number; semejanza: number }[]
}

/** Monitoreo de espacios: solo seguridad y administración (RF21). */
export type EstadoEspacio = 'disponible' | 'ocupado' | 'mantenimiento'

export interface Espacio {
  id_espacio: number
  codigo: string
  estado: EstadoEspacio
  ocupante: {
    id_sesion: number
    nombre: string
    codigo_utp: string
    vehiculo: { tipo_vmp: TipoVMP; marca: string; color: string | null } | null
    desde: string | null
  } | null
}

export interface Espacios {
  sede: string
  total: number
  libres: number
  ocupados: number
  mantenimiento: number
  lleno: boolean
  zonas: { nombre: string; total: number; libres: number; espacios: Espacio[] }[]
}

/** Lo que la IA ve en un cuadro del video en vivo. No se guarda. */
export interface CuadroEnVivo {
  estado: EstadoValidacion
  motivo: string | null
  confianza: number | null
  semejanza: number | null
  id_vehiculo_mas_parecido: number | null
  detecciones: Deteccion[]
  umbral_confianza: number
  umbral_semejanza: number
  ms: number | null
}

export interface EstadoSesion {
  id_sesion: number
  estado: EstadoValidacion
  motivo: string | null
  mensaje: string
  id_vehiculo_reconocido: number | null
  confianza: number | null
  semejanza: number | null
  id_vehiculo_mas_parecido: number | null
  detecciones: Deteccion[]
  modelo_version: string | null
  evidencia_url: string | null
  puede_decidir: boolean
  /** Espacio asignado al validar, p. ej. «A-03». Solo lo ve el guardia (RF21). */
  espacio: string | null
  usuario: UsuarioAcceso | null
  vehiculos: Vehiculo[]
}

export interface Salud {
  backend: boolean
  ia: boolean
}

/** Error uniforme del backend: `{codigo, mensaje, detalle, request_id}`. */
export class ErrorApi extends Error {
  codigo: string
  detalle: unknown
  requestId: string
  status: number

  constructor(codigo: string, mensaje: string, status = 0, detalle: unknown = {}, requestId = '') {
    super(mensaje)
    this.codigo = codigo
    this.status = status
    this.detalle = detalle
    this.requestId = requestId
  }
}

// ---------------------------------------------------------------- base
type Rol = 'usuario' | 'guardia'

/** Lo que devuelve `/dev/sesion/*`. */
export interface SesionDemo {
  access_token: string
  rol: string
  id: number
  nombre: string
}

const sesiones = new Map<string, Promise<SesionDemo>>()

async function leerError(respuesta: Response): Promise<ErrorApi> {
  try {
    const cuerpo = await respuesta.json()
    return new ErrorApi(
      cuerpo.codigo ?? `HTTP_${respuesta.status}`,
      cuerpo.mensaje ?? 'Error del servidor',
      respuesta.status,
      cuerpo.detalle,
      cuerpo.request_id ?? '',
    )
  } catch {
    return new ErrorApi(`HTTP_${respuesta.status}`, 'Error del servidor', respuesta.status)
  }
}

async function pedir(ruta: string, opciones: RequestInit = {}): Promise<Response> {
  let respuesta: Response
  try {
    respuesta = await fetch(ruta, opciones)
  } catch {
    throw new ErrorApi('SIN_CONEXION', 'No se pudo conectar con el servidor.')
  }
  if (!respuesta.ok) throw await leerError(respuesta)
  return respuesta
}

/**
 * Inicia sesión con una identidad de ejemplo. Se pide una sola vez por identidad;
 * si falla (código inexistente, sin conexión) se olvida para poder reintentar.
 */
export function iniciarSesion(rol: Rol, identidad: string): Promise<SesionDemo> {
  const clave = `${rol}:${identidad}`
  let promesa = sesiones.get(clave)
  if (!promesa) {
    promesa = pedir(`${API}/dev/sesion/${rol}/${encodeURIComponent(identidad)}`, {
      method: 'POST',
    }).then((r) => r.json() as Promise<SesionDemo>)
    promesa.catch(() => sesiones.delete(clave))
    sesiones.set(clave, promesa)
  }
  return promesa
}

export function olvidarSesion(rol: Rol, identidad: string): void {
  sesiones.delete(`${rol}:${identidad}`)
}

const token = (rol: Rol, identidad: string) =>
  iniciarSesion(rol, identidad).then((sesion) => sesion.access_token)

async function conToken<T>(
  rol: Rol,
  identidad: string,
  ruta: string,
  opciones: RequestInit = {},
): Promise<T> {
  const cabeceras = new Headers(opciones.headers)
  cabeceras.set('Authorization', `Bearer ${await token(rol, identidad)}`)
  if (typeof opciones.body === 'string') cabeceras.set('Content-Type', 'application/json')
  const respuesta = await pedir(`${API}${ruta}`, { ...opciones, headers: cabeceras })
  return respuesta.json() as Promise<T>
}

/** Las imágenes llegan como rutas firmadas relativas: hay que anteponer el backend. */
export function urlImagen(ruta: string | null): string | null {
  return ruta ? `${URL_BACKEND}${ruta}` : null
}

function conFoto(archivo: Blob, nombre: string): FormData {
  const datos = new FormData()
  datos.append('archivo', archivo, nombre)
  return datos
}

// ---------------------------------------------------------------- usuario (Portal y App)
export function apiUsuario(codigoUtp: string) {
  const pedirJson = <T>(ruta: string, opciones?: RequestInit) =>
    conToken<T>('usuario', codigoUtp, `/usuarios/me${ruta}`, opciones)

  return {
    perfil: () => pedirJson<Perfil>(''),
    aceptarConsentimiento: () =>
      pedirJson<Perfil>('/perfil', {
        method: 'PUT',
        body: JSON.stringify({ acepta_tratamiento_datos: true }),
      }),
    vehiculos: () => pedirJson<ListaVehiculos>('/vehiculos'),
    crearVehiculo: (datos: DatosVehiculo) =>
      pedirJson<{ id_vehiculo: number }>('/vehiculos', {
        method: 'POST',
        body: JSON.stringify(datos),
      }),
    editarVehiculo: (id: number, datos: DatosVehiculo) =>
      pedirJson<Vehiculo>(`/vehiculos/${id}`, { method: 'PUT', body: JSON.stringify(datos) }),
    eliminarVehiculo: (id: number) => pedirJson<Vehiculo>(`/vehiculos/${id}`, { method: 'DELETE' }),
    subirFoto: (id: number, archivo: Blob, nombre: string) =>
      pedirJson<Vehiculo>(`/vehiculos/${id}/foto`, {
        method: 'POST',
        body: conFoto(archivo, nombre),
      }),
    qr: () => pedirJson<QR>('/qr'),
    regenerarQr: () => pedirJson<QR>('/qr/regenerar', { method: 'POST' }),
  }
}

// ---------------------------------------------------------------- guardia (Punto de acceso)
export function apiGuardia(usuarioAcceso: string) {
  const pedirJson = <T>(ruta: string, opciones?: RequestInit) =>
    conToken<T>('guardia', usuarioAcceso, `/acceso${ruta}`, opciones)

  return {
    leerQr: (tokenQr: string) =>
      pedirJson<LecturaQR>('/qr', { method: 'POST', body: JSON.stringify({ token: tokenQr }) }),
    subirCaptura: (idSesion: number, archivo: Blob, nombre: string) =>
      pedirJson<{ estado: EstadoValidacion }>(`/${idSesion}/captura`, {
        method: 'POST',
        body: conFoto(archivo, nombre),
      }),
    analizarCuadro: (idSesion: number, cuadro: Blob) =>
      pedirJson<CuadroEnVivo>(`/${idSesion}/cuadro`, {
        method: 'POST',
        body: conFoto(cuadro, 'cuadro.jpg'),
      }),
    estado: (idSesion: number) => pedirJson<EstadoSesion>(`/${idSesion}`),
    espacios: () => conToken<Espacios>('guardia', usuarioAcceso, '/espacios'),
    liberarEspacio: (idEspacio: number) =>
      conToken<Espacios>('guardia', usuarioAcceso, `/espacios/${idEspacio}/liberar`, {
        method: 'POST',
      }),
    decidir: (
      idSesion: number,
      decision: 'aprobar_manual' | 'rechazar',
      motivo: string,
      idVehiculo?: number,
    ) =>
      pedirJson<EstadoSesion>(`/${idSesion}/decision`, {
        method: 'POST',
        body: JSON.stringify({ decision, motivo, id_vehiculo: idVehiculo ?? null }),
      }),
    cancelar: (idSesion: number) =>
      pedirJson<EstadoSesion>(`/${idSesion}/cancelar`, { method: 'POST' }),

    /**
     * Espera el resultado de la IA consultando el estado cada segundo.
     * (El backend también ofrece SSE en `/stream`; el sondeo es más simple y es el
     * respaldo que pide docs/20.) Devuelve el primer estado que ya no es «pendiente».
     */
    async esperarResultado(
      idSesion: number,
      senal: AbortSignal,
      maxSegundos = 30,
    ): Promise<EstadoSesion> {
      const limite = Date.now() + maxSegundos * 1000
      for (;;) {
        const estado = await pedirJson<EstadoSesion>(`/${idSesion}`, { signal: senal })
        if (estado.estado !== 'pendiente') return estado
        if (Date.now() > limite) {
          throw new ErrorApi('IA_NO_DISPONIBLE', 'La IA no respondió a tiempo.')
        }
        await new Promise((resolver) => setTimeout(resolver, 1000))
        if (senal.aborted) throw new ErrorApi('CANCELADO', 'Operación cancelada.')
      }
    },
  }
}

// ---------------------------------------------------------------- comunes
export async function salud(): Promise<Salud> {
  try {
    const cuerpo = await (await pedir(`${URL_BACKEND}/salud`)).json()
    return { backend: cuerpo.base_datos === 'ok', ia: Boolean(cuerpo.ia?.disponible) }
  } catch {
    return { backend: false, ia: false }
  }
}

/** Solo para la demo: texto del QR de un usuario, para simular la lectura sin cámara. */
export async function tokenQrDeDemo(codigoUtp: string): Promise<string> {
  const cuerpo = await (await pedir(`${API}/dev/qr/${encodeURIComponent(codigoUtp)}`)).json()
  return cuerpo.token as string
}

/**
 * Solo para la demo: registra la salida de los vehículos de un usuario. Este avance
 * no tiene salida real, y sin esto un vehículo validado quedaría «dentro» para siempre.
 */
export async function salidaDeDemo(codigoUtp: string): Promise<number> {
  const respuesta = await pedir(`${API}/dev/salida/${encodeURIComponent(codigoUtp)}`, {
    method: 'POST',
  })
  return (await respuesta.json()).salidas_registradas as number
}

/** Perfiles de ejemplo para la pantalla de inicio de sesión (solo modo desarrollo). */
export interface Identidades {
  usuarios: {
    codigo_utp: string
    nombres: string
    apellidos: string
    tipo_usuario: string
    estado_matricula: string
  }[]
  guardia: { usuario_acceso: string; nombres: string; apellidos: string; turno: string }[]
}

export async function identidadesDeDemo(): Promise<Identidades> {
  return (await pedir(`${API}/dev/identidades`)).json() as Promise<Identidades>
}
