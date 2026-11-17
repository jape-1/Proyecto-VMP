# 20 · Frontend del avance (usuario y guardia)

> **[PROPUESTA]** salvo lo marcado **[DECIDIDO]**. Reduce `docs/08` a lo que se prueba el 17-nov-2026. Son **dos aplicaciones web** que se acoplan a la API de `docs/18` §6. La especificación es la misma para quien las construya. **El contrato es la documentación OpenAPI del backend**: si algo no coincide, manda el backend y se corrige aquí.

## 1. Las dos aplicaciones

| App | Quién | Dispositivo | Ruta/puerto sugerido | Sustituye a (docs/08) |
|---|---|---|---|---|
| **App del usuario** | Quien registra sus vehículos y muestra el QR | Celular (vista de 390 px) y laptop | `:5173` | Portal UTP + App UTP **simulados**, fusionados en una sola |
| **Punto de acceso** | Guardia de seguridad | Tablet (10") o laptop | `:5174` | `panel/` ruta `/acceso`, solo el flujo de ingreso |

> **Cambiado el 17-nov-2026 (`docs/13`):** hay inicio de sesión simulado (código UTP sin contraseña; el guardia elige su usuario) y el punto de acceso analiza el video en vivo en lugar de pedir una foto. Ver `frontend/README.md` y `docs/27`.

**Sin pantalla de inicio de sesión [DECIDIDO]:** al arrancar, cada app llama una vez al endpoint de desarrollo de `docs/18` §4 con una identidad fija (variable de entorno) y guarda el token **en memoria** (no en `localStorage`). Si el backend responde 401/403, muestra «Sesión no disponible» y un botón para reintentar.

**Stack sugerido [PROPUESTA]:** React + Vite + TypeScript; un cliente de la API generado desde el OpenAPI (o tipado a mano); un solo diseño base compartido (colores, botones, mensajes) en una carpeta común. Consultar la documentación vigente de cada librería antes de usarla (enrutamiento, formularios, lectura de QR en navegador, cámara).

## 2. App del usuario

Pantallas (una por ruta, con barra inferior en móvil):

| Ruta | Qué muestra | Endpoint | Reglas visibles |
|---|---|---|---|
| `/perfil` | Datos precargados (solo lectura) + tipo de usuario y contacto + **casilla de consentimiento** | `GET /usuarios/me`, `PUT /usuarios/me/perfil` | Sin consentimiento no se avanza a vehículos. Matrícula inactiva → «Tu matrícula no figura como vigente.» |
| `/vehiculos` | Contador «2 de 3», una **tarjeta por vehículo** con check si tiene foto, botones Agregar/Editar/Eliminar | `GET /usuarios/me/vehiculos` | Con 3, «Agregar» deshabilitado con explicación; un 409 se muestra con el mensaje de límite |
| `/vehiculos/nuevo` y `/vehiculos/:id` | Formulario: tipo (lista), marca, modelo, color, característica distintiva (opcional) | `POST`, `PUT /usuarios/me/vehiculos` | Validación en pantalla y mensajes del backend |
| `/vehiculos/:id/foto` | **Subir archivo o tomar con la cámara**, pautas visibles (vehículo completo, fondo despejado, buena luz, vista lateral, sin filtros), vista previa | `POST /usuarios/me/vehiculos/{id}/foto` | `FOTO_SIN_VEHICULO` → «No detectamos un vehículo en la foto. Toma otra con el vehículo completo.»; tamaño y formato límite |
| `/qr` | **QR grande y de alto contraste** (imagen que entrega el backend), vigencia, estado, lista de vehículos con miniatura, aviso «Código personal e intransferible», botón **Regenerar** | `GET /usuarios/me/qr`, `POST …/qr/regenerar` | QR vencido o revocado → botón «Renovar» |

Detalles: eliminar pide confirmación; editar muestra «Tu QR se actualizó automáticamente» **si** `docs/13` #4 se resuelve así; el QR en móvil sube el brillo si el navegador lo permite (no es obligatorio).

## 3. Punto de acceso (guardia)

Una sola pantalla con **máquina de estados** (reducida de `docs/08` §5):

```
ESPERANDO_QR ─lee/ingresa QR─▶ VALIDANDO_QR ─ok─▶ CAPTURANDO_FOTO ─foto─▶ ANALIZANDO ─┬─ validado ─▶ INGRESO_OK ─▶ ESPERANDO_QR
      ▲                             └─ error ─▶ QR_ERROR (mensaje + reintentar)        ├─ verificar ─▶ VERIFICAR (decide el guardia)
      └──────────────────────────── cancelar / tiempo agotado ───────────────────────  ├─ rechazado ─▶ RECHAZADO (decide el guardia)
                                                                                        └─ IA caída ─▶ IA_NO_DISPONIBLE (modo manual)
```

| Estado | Qué muestra | Endpoint |
|---|---|---|
| `ESPERANDO_QR` | Visor de cámara para leer el QR **y** un campo para pegar/escribir el token (respaldo); semáforo de estado (backend, IA) | `GET /salud` |
| `VALIDANDO_QR` | Spinner corto | `POST /acceso/qr` |
| `QR_ERROR` | Mensaje específico (vencido, alterado, revocado, inexistente, matrícula inactiva) y qué hacer | — |
| `CAPTURANDO_FOTO` | Datos del usuario y **sus vehículos con foto de referencia**; cámara/subida de archivo para la foto del vehículo con guía de encuadre | `POST /acceso/{id}/captura` |
| `ANALIZANDO` | «Verificando el vehículo…» y el **tiempo transcurrido** | `GET /acceso/{id}` o `…/stream` (SSE) |
| `INGRESO_OK` | Mensaje grande **«Puede ingresar»** + vehículo reconocido (foto de referencia junto a la captura); vuelve solo a `ESPERANDO_QR` | — |
| `VERIFICAR` | Captura vs. referencias lado a lado, detecciones y confianza, botones **Aprobar / Rechazar** (con motivo) | `POST /acceso/{id}/decision` |
| `RECHAZADO` | Motivo, evidencia, botones **Rechazar ingreso / Aprobar manualmente** (motivo obligatorio) | `POST /acceso/{id}/decision` |
| `IA_NO_DISPONIBLE` | Banner «IA no disponible: modo manual»; el guardia mira ambas fotos y decide con motivo | `POST /acceso/{id}/decision` |

Además: botón **Cancelar** en cualquier paso (`POST /acceso/{id}/cancelar`) y una **lista simple de los últimos ingresos** de la sesión actual (opcional; si no hay endpoint, no se hace). Botones grandes, contraste alto, mensajes de ≤ 8 palabras, sonido distinto para OK y error.

## 4. Cámara y QR en el navegador (riesgo real)

- Los navegadores **solo permiten abrir la cámara en contexto seguro**: `https://…` o `http://localhost`. Si la tablet o el celular abren la app por la IP de la laptop (`http://192.168.x.x`), **la cámara no funcionará**. Opciones: (a) túnel HTTPS temporal; (b) certificado local de desarrollo; (c) **respaldo siempre disponible**: subir foto con `<input type="file" accept="image/*" capture>` y ingresar el token del QR a mano. **Diseñar el flujo con el respaldo (c) desde el inicio**, aunque exista cámara en vivo. Verificar el comportamiento exacto en la documentación de la librería y del navegador.
- Para **leer el QR** con la cámara hay librerías de navegador; elegir una y consultar su documentación. Si falla, el guardia pega el token o el sistema permite probar con una imagen del QR.
- Las fotos se reducen y comprimen en el navegador antes de subirlas (límite de tamaño del backend, `docs/08` §3.2: jpg/png/webp, ≤ 5 MB como punto de partida).

## 5. Acuerdos de contrato con el backend

- Base `/api/v1`; CORS permitido a los dos orígenes; `Authorization: Bearer <token>` obtenido al arrancar.
- Errores con `codigo`, `mensaje`, `detalle`, `request_id` (`docs/07` §1). **El frontend traduce el `codigo` a un mensaje propio** (`docs/08` §7) y muestra el `request_id` en un texto pequeño para depurar.
- Fechas ISO-8601 con zona; mostrar en America/Lima, 24 h.
- Imágenes por `multipart/form-data`; las URL de imágenes que entrega el backend se usan tal cual (pueden ser firmadas y expirar: pedir de nuevo si dan 403).
- Estados de la IA: `pendiente_ia`, `validado`, `verificar`, `rechazado`. Cualquier estado desconocido se trata como «verificar» y se avisa.
- Si cambia un campo o una ruta, se avisa al backend y se actualiza `docs/18` §6 y `docs/07` **antes** de codificar.

## 6. Accesibilidad y calidad

Español (Perú); contraste mínimo AA; estados con color **y** forma; botones táctiles ≥ 44 px; la app del usuario funciona a 390 px de ancho y el punto de acceso a ~1024 px. Sin datos personales en la consola ni en el almacenamiento del navegador.

## 7. Pruebas y «hecho»

- **Pruebas mínimas:** componentes clave (contador de vehículos, máquina de estados del guardia con respuestas simuladas de la API) y **un recorrido de punta a punta** con el backend real y datos de ejemplo (puede automatizarse con Playwright si hay tiempo; si no, guion manual).
- **Hecho:** `npm run build` y `npm run lint` sin errores · ambas apps levantan con `docker compose up` · se recorren los escenarios 1–12 de `docs/19` §4 · funciona con el **respaldo sin cámara** · no hay claves ni datos reales en el repositorio.
