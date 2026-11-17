# Frontend · Portal UTP, App UTP y Punto de acceso

Tres interfaces en un solo proyecto React + Vite + TypeScript. Todas consumen el mismo backend. Son una **simulación académica**: llevan el rótulo en pantalla y no piden contraseñas.

| Ruta | Interfaz | Tamaño de diseño | Qué hace |
|---|---|---|---|
| `/portal` | Portal UTP (web) | Escritorio, hasta 768 px | Perfil y consentimiento, mis vehículos (máx. 3), registrar o editar, foto de referencia validada por la IA |
| `/app` | App UTP (celular) | 390 × 844 | QR tipo carné con vigencia y estado, regenerar, lista de vehículos |
| `/espacios` | Monitoreo de espacios (guardia) | Laptop o tablet | Libres y ocupados por zona (5 × 8), quién ocupa cada espacio, registrar salida y liberar |
| `/acceso` | Punto de acceso (guardia) | Tablet o laptop 1024 × 768 | Leer el QR con la cámara, **IA en vivo** sobre el video (cajas con clase, confianza y semejanza), resultado y decisión manual con motivo |

## Puesta en marcha

Necesita el backend en `http://localhost:8000` con `ENTORNO=dev` (ver `backend/README.md`) y, para la IA real, `ia_service` en el puerto 8001.

```powershell
cd frontend
npm install
npm run dev        # http://localhost:5173
```

**Inicio de sesión simulado** (`docs/13`, 17-nov-2026): el Portal y la App piden solo el **código UTP**, sin contraseña (en el sistema real autentica la UTP); el Punto de acceso pide **elegir al guardia**. Las tres pantallas muestran los perfiles de ejemplo de `GET /api/v1/dev/identidades` y tienen botón para salir. La sesión se recuerda en el navegador.

Atajo para pruebas: `?codigo=U90000001` en `/portal` o `/app`, y `?guardia=guardia.tarde` en `/acceso`, entran directamente.

## Cómo está organizado

| Archivo | Para qué |
|---|---|
| `src/servicios/api.ts` | **Único archivo que llama al backend.** Tipos con los nombres de campos de la API |
| `src/servicios/mensajes.ts` | **Único mapa** de códigos de error y motivos a texto para personas |
| `src/servicios/sesion.ts` | Qué identidad usa cada interfaz en este navegador |
| `src/componentes/InicioSesion.tsx` | Pantalla de inicio de sesión de las tres interfaces |
| `src/acceso/maquina.ts` | Máquina de estados del punto de acceso (lógica pura, con pruebas) |
| `src/acceso/EnVivo.tsx` | IA en vivo: envía cuadros a `/acceso/{id}/cuadro`, dibuja las cajas y las barras de confianza y semejanza |
| `src/acceso/Monitoreo.tsx` | Monitoreo de espacios y el contador «N de 40 espacios libres» del punto de acceso |
| `src/acceso/reglaEnVivo.ts` | Cuándo decide el video en vivo (lógica pura, con pruebas) |
| `src/acceso/usoCamara.ts`, `Camara.tsx` | Cámara elegida, lector de QR (`jsQR`) y selector de cámara |
| `src/estilos.css` | Colores, tipografía y piezas comunes |

## Comprobaciones

```powershell
npm test           # pruebas de la lógica (vitest)
npm run lint
npm run build      # incluye la comprobación de tipos
```

## Cosas que conviene saber

- **La cámara solo funciona en `https://` o en `localhost`.** Por eso siempre hay respaldo: escribir el código del QR y «¿Sin cámara? Subir una foto».
- **IA en vivo:** se analiza un cuadro a la vez (unos 3 por segundo en la laptop de desarrollo). Con **3 cuadros «validado» seguidos** el ingreso se valida solo; si se ve un vehículo que no llega al umbral en **8 s**, se envía el mejor cuadro y decide el guardia. Sin vehículo a la vista, espera. Los cuadros intermedios no se guardan: solo el cuadro final queda como evidencia.
- **Celular en la misma Wi-Fi:** sin `VITE_API_URL`, el backend se busca en el mismo equipo que sirve la página (puerto 8000), y en modo desarrollo el backend acepta direcciones de la red local. Ver `docs/27`.
- **Logo:** copia el logo oficial a `src/assets/logo-utp.svg` (ver `src/assets/LEEME.md`). Sin él se ve un marcador con las letras «UTP».
- **Otro backend:** copia `.env.example` a `.env` y pon `VITE_API_URL`. El backend debe aceptar el origen del frontend (`CORS_ORIGENES` o `CORS_REGEX`).
- El resultado de la IA se obtiene consultando el estado cada segundo. El backend también ofrece SSE (`/acceso/{id}/stream`), que no se usa todavía.
- Sin registro de salida en este avance, un vehículo validado queda «dentro»: su siguiente ingreso pasa a «verificar» (`VEHICULO_YA_DENTRO`). Para repetir la demo, en `/acceso` está el enlace «registrar la salida de sus vehículos», que llama a una ruta que solo existe en modo desarrollo.

## Probado el 17-nov-2026

Recorridos automáticos en Edge contra el backend y la IA reales (en Docker):

- Registro en el Portal (validaciones, foto de otra clase rechazada, foto correcta aceptada), QR en la App, rechazo manual, regreso automático y código inexistente.
- Inicio y cierre de sesión en las tres interfaces, código inexistente y sesión recordada al recargar.
- **IA en vivo con una cámara simulada** (un video con el QR y luego el vehículo): el QR se lee con la cámara en menos de 1 s; con el scooter registrado se valida solo (confianza 78 %, semejanza 91 %); con otro scooter (semejanza 69 %) se deriva al guardia a los 8 s. Entre 2 y 3,5 cuadros por segundo.

No probado: una cámara física, un celular y una tablet reales.
