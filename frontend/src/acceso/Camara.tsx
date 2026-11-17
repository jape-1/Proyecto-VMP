import jsQR from 'jsqr'
import { useEffect, useRef, useState } from 'react'
import { cuadro, elegirCamara, hayCamara, oyentes, useCamara, useCamaraElegida } from './usoCamara'

/** Componentes de cámara del punto de acceso. La lógica está en `usoCamara.ts`. */

/** Lista para elegir cámara. No se muestra si hay una sola. */
export function SelectorCamara() {
  const id = useCamaraElegida()
  const [camaras, setCamaras] = useState<MediaDeviceInfo[]>([])

  useEffect(() => {
    if (!hayCamara()) return
    const listar = () =>
      void navigator.mediaDevices
        .enumerateDevices()
        .then((todos) => setCamaras(todos.filter((d) => d.kind === 'videoinput')))
        .catch(() => undefined)
    listar()
    oyentes.add(listar)
    navigator.mediaDevices.addEventListener('devicechange', listar)
    return () => {
      oyentes.delete(listar)
      navigator.mediaDevices.removeEventListener('devicechange', listar)
    }
  }, [])

  if (camaras.length < 2) return null
  return (
    <label className="selector-camara pequeno">
      Cámara
      <select value={id} onChange={(e) => elegirCamara(e.target.value)}>
        <option value="">Por defecto</option>
        {camaras.map((c, i) => (
          <option key={c.deviceId} value={c.deviceId}>
            {c.label || `Cámara ${i + 1}`}
          </option>
        ))}
      </select>
    </label>
  )
}

/** Lee un QR con la cámara y avisa una sola vez por código. */
export function LectorQR({ alLeer }: { alLeer: (texto: string) => void }) {
  const { video, error } = useCamara()
  const avisar = useRef(alLeer)
  useEffect(() => {
    avisar.current = alLeer
  }, [alLeer])

  useEffect(() => {
    let ultimo = ''
    const reloj = window.setInterval(() => {
      const lienzo = video.current && cuadro(video.current, 640)
      const contexto = lienzo?.getContext('2d')
      if (!lienzo || !contexto) return
      const imagen = contexto.getImageData(0, 0, lienzo.width, lienzo.height)
      const codigo = jsQR(imagen.data, imagen.width, imagen.height, {
        inversionAttempts: 'dontInvert',
      })
      if (codigo?.data && codigo.data !== ultimo) {
        ultimo = codigo.data
        avisar.current(codigo.data)
      }
    }, 250)
    return () => window.clearInterval(reloj)
  }, [video])

  return (
    <div className="visor" aria-label="Visor de la cámara para leer el QR">
      {error ? <p style={{ padding: 20 }}>{error}</p> : <video ref={video} muted playsInline />}
      {!error && <span className="guia" />}
    </div>
  )
}
