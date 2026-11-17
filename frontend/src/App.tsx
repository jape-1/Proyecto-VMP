import { useState } from 'react'
import type { ReactNode } from 'react'
import { PuntoAcceso } from './acceso/PuntoAcceso'
import { InicioSesion } from './componentes/InicioSesion'
import { LogoUTP, RotuloSimulacion } from './componentes/comunes'
import { Monitoreo } from './acceso/Monitoreo'
import { AppMovil } from './movil/AppMovil'
import { Portal } from './portal/Portal'
import type { Interfaz } from './servicios/sesion'
import { cerrarSesion, guardarSesion, leerSesion } from './servicios/sesion'

/** Tres interfaces en un solo proyecto, una por ruta (docs/25 §2). */
const VISTAS = [
  { ruta: '/portal', titulo: 'Portal UTP (web)', texto: 'Registra tus vehículos y su foto.' },
  { ruta: '/app', titulo: 'App UTP (celular)', texto: 'Muestra tu QR de estacionamiento.' },
  { ruta: '/acceso', titulo: 'Punto de acceso (guardia)', texto: 'Lee el QR y verifica el vehículo.' },
  { ruta: '/espacios', titulo: 'Monitoreo de espacios (guardia)', texto: 'Espacios libres y ocupados por zona.' },
]

/** Pide la identidad antes de mostrar la interfaz y permite cerrar sesión. */
function ConSesion({
  interfaz,
  children,
}: {
  interfaz: Interfaz
  children: (identidad: string, alSalir: () => void) => ReactNode
}) {
  const [identidad, setIdentidad] = useState(() => leerSesion(interfaz))

  if (!identidad) {
    return (
      <InicioSesion
        interfaz={interfaz}
        alEntrar={(nueva) => {
          guardarSesion(interfaz, nueva)
          setIdentidad(nueva)
        }}
      />
    )
  }
  return children(identidad, () => {
    cerrarSesion(interfaz, identidad)
    setIdentidad(null)
  })
}

export default function App() {
  const ruta = location.pathname.replace(/\/$/, '')
  if (ruta === '/acceso') {
    return (
      <ConSesion interfaz="acceso">
        {(guardia, alSalir) => <PuntoAcceso key={guardia} guardia={guardia} alSalir={alSalir} />}
      </ConSesion>
    )
  }
  if (ruta === '/espacios') {
    return (
      <ConSesion interfaz="acceso">
        {(guardia, alSalir) => <Monitoreo key={guardia} guardia={guardia} alSalir={alSalir} />}
      </ConSesion>
    )
  }
  if (ruta === '/portal') {
    return (
      <ConSesion interfaz="portal">
        {(codigo, alSalir) => <Portal key={codigo} codigo={codigo} alSalir={alSalir} />}
      </ConSesion>
    )
  }
  if (ruta === '/app') {
    return (
      <ConSesion interfaz="app">
        {(codigo, alSalir) => <AppMovil key={codigo} codigo={codigo} alSalir={alSalir} />}
      </ConSesion>
    )
  }

  return (
    <main className="inicio columna">
      <div className="fila">
        <LogoUTP />
        <h1>Estacionamiento VMP</h1>
      </div>
      <RotuloSimulacion />
      {VISTAS.map((vista) => (
        <a key={vista.ruta} className="tarjeta" href={vista.ruta}>
          <h2>{vista.titulo}</h2>
          <p className="suave">{vista.texto}</p>
        </a>
      ))}
    </main>
  )
}
