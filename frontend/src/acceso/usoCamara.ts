/**
 * Acceso a la cámara del navegador. Solo funciona en https:// o en localhost
 * (docs/20 §4): quien la use debe ofrecer siempre un respaldo.
 */
import { useEffect, useRef, useState, useSyncExternalStore } from 'react'

// ---------------------------------------------------------------- cámara elegida
// Con una cámara USB y la de la laptop, el guardia elige cuál usar. Se recuerda en
// este navegador; si falla el almacenamiento, se usa la cámara por defecto.
const CLAVE_CAMARA = 'vmp.camara'
/** Avisos cuando cambia la cámara elegida o la lista de cámaras. */
export const oyentes = new Set<() => void>()
let camaraElegida = (() => {
  try {
    return localStorage.getItem(CLAVE_CAMARA) ?? ''
  } catch {
    return ''
  }
})()

export function elegirCamara(id: string) {
  camaraElegida = id
  try {
    localStorage.setItem(CLAVE_CAMARA, id)
  } catch {
    // Solo dura esta pestaña.
  }
  oyentes.forEach((avisar) => avisar())
}

export function useCamaraElegida(): string {
  return useSyncExternalStore(
    (avisar) => {
      oyentes.add(avisar)
      return () => oyentes.delete(avisar)
    },
    () => camaraElegida,
  )
}

/** En una página sin https (que no sea localhost) el navegador no expone la cámara. */
export function hayCamara(): boolean {
  return Boolean((navigator as { mediaDevices?: MediaDevices }).mediaDevices)
}

async function abrirCamara(id: string): Promise<MediaStream> {
  if (id) {
    try {
      return await navigator.mediaDevices.getUserMedia({
        video: { deviceId: { exact: id } },
        audio: false,
      })
    } catch {
      // La cámara recordada ya no está conectada: se usa la de por defecto.
    }
  }
  return navigator.mediaDevices.getUserMedia({
    video: { facingMode: 'environment' },
    audio: false,
  })
}

export function useCamara() {
  const video = useRef<HTMLVideoElement>(null)
  const id = useCamaraElegida()
  const [error, setError] = useState<string | null>(() =>
    hayCamara() ? null : 'Este navegador no permite usar la cámara aquí.',
  )

  useEffect(() => {
    let flujo: MediaStream | null = null
    let vigente = true
    if (!hayCamara()) return
    abrirCamara(id)
      .then((nuevo) => {
        if (!vigente) {
          nuevo.getTracks().forEach((pista) => pista.stop())
          return
        }
        flujo = nuevo
        setError(null)
        if (video.current) {
          video.current.srcObject = nuevo
          void video.current.play().catch(() => undefined)
        }
        // Con el permiso concedido ya se conocen los nombres de las cámaras.
        oyentes.forEach((avisar) => avisar())
      })
      .catch(() => setError('No se pudo abrir la cámara. Revisa el permiso del navegador.'))
    return () => {
      vigente = false
      flujo?.getTracks().forEach((pista) => pista.stop())
    }
  }, [id])

  return { video, error }
}

/** Cuadro actual del video, reducido a `ladoMaximo` píxeles por lado. */
export function cuadro(video: HTMLVideoElement, ladoMaximo: number): HTMLCanvasElement | null {
  if (!video.videoWidth) return null
  const escala = Math.min(1, ladoMaximo / Math.max(video.videoWidth, video.videoHeight))
  const lienzo = document.createElement('canvas')
  lienzo.width = Math.round(video.videoWidth * escala)
  lienzo.height = Math.round(video.videoHeight * escala)
  lienzo
    .getContext('2d', { willReadFrequently: true })
    ?.drawImage(video, 0, 0, lienzo.width, lienzo.height)
  return lienzo
}
