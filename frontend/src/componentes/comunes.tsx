import type { ReactNode } from 'react'
import type { TipoVMP } from '../servicios/api'
import type { TextoError } from '../servicios/mensajes'

/**
 * Logo de la UTP en un solo lugar (docs/25 §2, hallazgo 4).
 * Si existe `src/assets/logo-utp.svg` (o .png) se usa ese archivo oficial; si no,
 * el marcador de letras del diseño. El archivo oficial no está en el repositorio.
 */
const ARCHIVOS_LOGO = import.meta.glob<string>('../assets/logo-utp.{svg,png}', {
  eager: true,
  query: '?url',
  import: 'default',
})
const URL_LOGO: string | undefined = Object.values(ARCHIVOS_LOGO)[0]

export function LogoUTP() {
  return (
    <span className="logo-utp" role="img" aria-label="UTP">
      {URL_LOGO ? (
        <img src={URL_LOGO} alt="" />
      ) : (
        ['U', 'T', 'P'].map((letra) => <span key={letra}>{letra}</span>)
      )}
    </span>
  )
}

/** Rótulo obligatorio en todas las pantallas (docs/24 §1.4). */
export function RotuloSimulacion() {
  return (
    <span className="rotulo-simulacion">
      ⓘ Simulación académica – no es el sistema oficial de la UTP
    </span>
  )
}

const TRAZOS: Record<TipoVMP, string> = {
  bicicleta:
    'M2 17.5a3.5 3.5 0 1 0 7 0a3.5 3.5 0 1 0-7 0M15 17.5a3.5 3.5 0 1 0 7 0a3.5 3.5 0 1 0-7 0M5.5 17.5 9 10h7l2.5 7.5M9 10 7.5 6H5M12 17.5 16 10M14 6h3',
  bicicleta_electrica:
    'M2 17.5a3.5 3.5 0 1 0 7 0a3.5 3.5 0 1 0-7 0M15 17.5a3.5 3.5 0 1 0 7 0a3.5 3.5 0 1 0-7 0M5.5 17.5 9 10h7l2.5 7.5M9 10 7.5 6H5M12 17.5 16 10M14 6h3M11 2.5 9.5 5h2.5L10.5 7.5',
  scooter_electrico:
    'M3 18a2 2 0 1 0 4 0a2 2 0 1 0-4 0M17 18a2 2 0 1 0 4 0a2 2 0 1 0-4 0M7 18h10M19 18 15.5 5H12',
  moto_electrica:
    'M2 17a3 3 0 1 0 6 0a3 3 0 1 0-6 0M16 17a3 3 0 1 0 6 0a3 3 0 1 0-6 0M5 17l3-6h6l3 6M14 11l-2-4H9M17 11h3',
}

export function IconoVMP({ tipo, lado = 40 }: { tipo: TipoVMP; lado?: number }) {
  return (
    <svg
      width={lado}
      height={lado}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={TRAZOS[tipo]} />
    </svg>
  )
}

export function Miniatura({ url, tipo }: { url: string | null; tipo: TipoVMP }) {
  return url ? (
    <img className="miniatura" src={url} alt="Foto de referencia" />
  ) : (
    <span className="miniatura" title="Sin foto">
      <IconoVMP tipo={tipo} />
    </span>
  )
}

export function Girando({ lado = 28 }: { lado?: number }) {
  return (
    <svg
      className="girando"
      width={lado}
      height={lado}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.4"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <path d="M12 3a9 9 0 1 0 9 9" />
    </svg>
  )
}

/** Error con botón Reintentar y el código pequeño para soporte (docs/24 §2). */
export function AlertaError({
  error,
  alReintentar,
  children,
}: {
  error: TextoError
  alReintentar?: () => void
  children?: ReactNode
}) {
  return (
    <div className="alerta" role="alert">
      <span aria-hidden="true">⚠</span>
      <div className="crecer">
        {error.mensaje}
        <small>
          Código: {error.codigo}
          {error.requestId ? ` · ${error.requestId.slice(0, 8)}` : ''}
        </small>
        {children}
      </div>
      {alReintentar && (
        <button type="button" className="boton" onClick={alReintentar}>
          Reintentar
        </button>
      )}
    </div>
  )
}
