# 07 · API REST y eventos

> **Todo este archivo es [PROPUESTA]**: el Avance 2 define componentes y flujos, pero no endpoints ni formatos de eventos. Se diseñaron para cubrir las 24 HU y respetar las reglas de `docs/02`. Si el equipo cambia algo, se actualiza aquí **antes** de codificar.

## 1. Convenciones

- Base: `/api/v1`. JSON UTF-8. Fechas ISO-8601 con zona (`2026-11-09T16:38:00-05:00`). Zona horaria de negocio: **America/Lima** (UTC-5, sin horario de verano). Guardar en BD en UTC o en hora local de forma consistente **[PENDIENTE]** (recomendado: `timestamptz` en UTC).
- Identificadores en rutas: enteros del ER (`id_vehiculo`, `id_sesion`, …).
- Autenticación (detalle en `docs/10`):
  - **Usuarios UTP**: a través del Conector UTP simulado → JWT corto con `sub=id_usuario_utp`, `rol=usuario`.
  - **Personal**: login `usuario_acceso` + contraseña → JWT con `rol=seguridad|administrador`.
  - **Punto de acceso (tablet)**: autenticado como personal de seguridad + `X-Device-Id` registrado **[PROPUESTA]**.
  - **Servicio de IA**: token de servicio (`rol=servicio_ia`).
- Errores uniformes (RFC 7807 simplificado):

```json
{ "codigo": "LIMITE_VMP_ALCANZADO", "mensaje": "Ya tienes 3 vehículos registrados.", "detalle": {"max": 3, "actuales": 3}, "request_id": "9f1c…" }
```

| Código HTTP | Uso |
|---|---|
| 400 | Datos inválidos |
| 401 | Sin token / token inválido |
| 403 | Rol sin permiso (p. ej. usuario pidiendo el mapa de espacios) |
| 404 | No existe |
| 409 | Conflicto de regla (límite de 3 VMP, vehículo dentro, espacio ya ocupado) |
| 422 | Validación de esquema (Pydantic) |
| 202 | Aceptado para proceso asíncrono (captura enviada a la IA) |

### Catálogo de códigos de error de negocio

`LIMITE_VMP_ALCANZADO`, `VEHICULO_DENTRO_NO_ELIMINABLE`, `FOTO_SIN_VEHICULO`, `FOTO_INVALIDA`, `QR_INEXISTENTE`, `QR_ALTERADO`, `QR_EXPIRADO`, `QR_REVOCADO`, `USUARIO_INACTIVO`, `UTP_NO_DISPONIBLE`, `SESION_NO_ENCONTRADA`, `SESION_ESTADO_INVALIDO`, `CAPTURA_FUERA_DE_CUADRO`, `IA_NO_DISPONIBLE`, `ESPACIO_OCUPADO`, `SIN_PERMISO_VISTA_ESPACIOS`, `CONSENTIMIENTO_REQUERIDO`.

**Añadidos al implementar el avance (2026-11-15)** — `docs/18` §9 pide la tabla completa para el frontend:

| Código | HTTP | Cuándo |
|---|---|---|
| `SIN_TOKEN` | 401 | Falta `Authorization: Bearer` (o `?token=` en el SSE) |
| `TOKEN_INVALIDO` | 401 | JWT mal formado o de una sesión que ya no existe |
| `TOKEN_EXPIRADO` | 401 | JWT vencido |
| `SIN_PERMISO` | 403 | El rol no corresponde a la ruta (usuario→guardia y guardia→usuario) |
| `USUARIO_INEXISTENTE` | 404 | El código UTP no está en el Conector |
| `PERSONAL_INEXISTENTE` | 404 | `usuario_acceso` sin fila activa (solo `/dev/sesion/guardia/*`) |
| `SIN_VEHICULOS_REGISTRADOS` | 409 | El QR es válido pero el usuario no tiene VMP activos |
| `VEHICULO_NO_ENCONTRADO` | 404/400 | No existe, es de otro usuario o no pertenece a la sesión |
| `VEHICULO_YA_DENTRO` | 409 | Ese vehículo ya tiene un ingreso validado vigente |
| `ARCHIVO_NO_ENCONTRADO` | 404 | URL de imagen sin firma válida o vencida |
| `DATOS_INVALIDOS` | 422 | Validación de Pydantic (con `detalle` por campo) |
| `ERROR_INTERNO` | 500 | Fallo no controlado (sin datos personales en la respuesta) |

Convención de las URLs de imágenes: el backend devuelve rutas **relativas**
(`/api/v1/archivos/<clave>?e=…&s=…`); el frontend antepone la URL base del backend.


## 2. Endpoints por módulo

### 2.1 Identidad y Accesos

| Método y ruta | Rol | HU | Descripción |
|---|---|---|---|
| `POST /auth/usuario/login` | — | HU01 | Simula el login del Portal UTP: recibe `codigo_utp` (+ clave simulada), consulta el Conector, registra `sincronizacion_utp(origen=login_portal)`, devuelve JWT |
| `GET /usuarios/me` | usuario | HU01 | Perfil (datos que trae el Conector) |
| `PUT /usuarios/me/perfil` | usuario | HU01 | Completa lo que el Portal no tiene (tipo de usuario, contacto) + `acepta_tratamiento_datos=true` (obligatorio, `CONSENTIMIENTO_REQUERIDO`) |
| `GET /usuarios/me/vehiculos` | usuario | HU02/HU04 | Lista activos + contador `{items, max:3, usados:n}` |
| `POST /usuarios/me/vehiculos` | usuario | HU02 | Crea vehículo. `409 LIMITE_VMP_ALCANZADO` si ya hay 3 activos |
| `PUT /usuarios/me/vehiculos/{id_vehiculo}` | usuario | HU04 | Edita; regenera/actualiza el QR (BR-04) |
| `DELETE /usuarios/me/vehiculos/{id_vehiculo}` | usuario | HU04 | Baja lógica; `409 VEHICULO_DENTRO_NO_ELIMINABLE` |
| `POST /usuarios/me/vehiculos/{id_vehiculo}/foto` | usuario | HU03 | `multipart/form-data`. Valida tipo/tamaño y que contenga un vehículo (llama a IA/detector); sube a almacenamiento; guarda `foto_referencia_url` |
| `GET /usuarios/me/qr` | usuario | HU05/HU06 | QR vigente: `{id_qr, vigencia, estado, imagen_qr_png_base64, vehiculos:[{id, tipo, marca, color}]}`. Genera uno si no existe |
| `POST /usuarios/me/qr/regenerar` | usuario | HU05 | Revoca el actual y emite otro |
| `GET /usuarios/{id}` | seguridad | HU08 | Datos del usuario para el acceso (nunca expone hash ni datos extra) |

Contrato de creación de vehículo:

```json
// POST /usuarios/me/vehiculos
{ "tipo_vmp": "scooter_electrico", "marca": "Xiaomi", "modelo": "Mi 3", "color": "negro",
  "caracteristica_distintiva": "calcomanía azul en el manubrio" }
// 201
{ "id_vehiculo": 17, "estado": "activo", "foto_requerida": true }
```

### 2.2 Punto de acceso e ingreso (orquesta Identidad + Estacionamiento)

| Método y ruta | Rol | HU | Descripción |
|---|---|---|---|
| `POST /acceso/qr` | seguridad (tablet) | HU07/HU08 | Body `{token}`. Valida token (hash), vigencia, estado; consulta Conector (`consulta_qr_app`); verifica `estado_matricula=activo`; crea **sesión preliminar**; devuelve usuario + vehículos con foto de referencia |
| `POST /acceso/{id_sesion}/captura` | seguridad | HU09 | `multipart` con la foto (o la cámara de ingreso publica directamente). Valida encuadre/calidad; guarda imagen; publica `ia.validacion.solicitada`; `202` |
| `GET /acceso/{id_sesion}` | seguridad | HU10-12 | Estado actual: `pendiente_ia` / `validado` / `verificar` / `rechazado`, vehículo reconocido, puntajes, motivo |
| `GET /acceso/{id_sesion}/stream` | seguridad | HU11/12 | SSE con el resultado (alternativa al polling) |
| `POST /acceso/{id_sesion}/decision` | seguridad | HU12 | `{decision: "aprobar_manual" \| "rechazar", motivo, id_vehiculo?}` — resuelve zona gris o rechazo; deja incidencia/evento de auditoría |
| `POST /acceso/{id_sesion}/cancelar` | seguridad | HU07 | Aborta un ingreso a medias (usuario se fue) |

Respuestas relevantes:

```json
// POST /acceso/qr → 200
{ "id_sesion": 4521,
  "usuario": {"id_usuario_utp": 8, "codigo_utp": "U90000002", "nombres": "…", "tipo_usuario": "estudiante"},
  "vehiculos": [{"id_vehiculo": 17, "tipo_vmp": "scooter_electrico", "marca": "Xiaomi", "color": "negro", "foto_referencia_url": "https://…/firmada"}],
  "siguiente_paso": "capturar_foto" }

// POST /acceso/qr → 409 / 400
{ "codigo": "QR_EXPIRADO", "mensaje": "El código QR venció. Debe renovarlo desde la App UTP." }

// GET /acceso/4521 → 200 (validado)
{ "estado": "validado", "id_vehiculo_reconocido": 17, "similitud": 0.91,
  "mensaje": "Puede ingresar", "ts": "…" }

// GET /acceso/4521 → 200 (rechazado)
{ "estado": "rechazado", "motivo": "VEHICULO_NO_COINCIDE", "mejor_similitud": 0.31,
  "evidencia_url": "https://…", "id_incidencia": 903 }
```

### 2.3 Estacionamiento e IA

| Método y ruta | Rol | HU | Descripción |
|---|---|---|---|
| `GET /zonas` | seguridad, administrador | HU17 | Zonas con totales (ocupados/disponibles/mantenimiento) |
| `GET /espacios?zona=A` | seguridad, administrador | HU17/HU16 | Detalle por espacio (estado, última actualización, vehículo/usuario si aplica). **403 para rol `usuario`** (BR-21) |
| `GET /espacios/{id_espacio}` | seguridad, administrador | HU17 | Detalle al pasar el cursor: último evento, sesión activa |
| `PATCH /espacios/{id_espacio}` | administrador | HU13 | Poner/quitar `mantenimiento` |
| `GET /espacios/stream` | seguridad, administrador | HU16 | SSE de cambios `{id_espacio, estado, ts}` + totales |
| `GET /estacionamiento/estado` | **usuario** | HU23 | **Solo** agregado general: `{lleno: bool, ocupacion_pct}` (sin zonas ni casillas) |
| `GET /camaras` | seguridad | HU13 | Lista de cámaras con estado de conexión |
| `GET /camaras/{codigo}/snapshot` | seguridad | HU13 | Último cuadro (JPEG) |
| `POST /sesiones/{id_sesion}/salida-manual` | seguridad | HU19 | Cierra la sesión sin esperar la liberación por IA (contingencia) |
| `GET /sesiones?…` | seguridad, administrador | HU18/19/21 | Historial. Filtros: `codigo_utp`, `id_vehiculo`, `desde`, `hasta`, `tipo` (`ingreso`, `salida` o `rechazado`), paginado |
| `GET /sesiones/resumen-dia` | seguridad, administrador | HU18/19 | `{total, autorizados, rechazados, salidas, siguen_dentro}` |
| `GET /sesiones/pendientes-cierre` | administrador | HU19 | Vehículos que no salieron al cierre |
| `GET /sesiones/{id}/eventos` | seguridad, administrador | HU18 | Eventos de IA y evidencia de la sesión |
| `GET /sesiones/export.csv` | administrador | HU21 | Exportación del filtro actual |

Contrato de `GET /espacios`:

```json
{ "zona": "A", "totales": {"ocupados": 3, "disponibles": 5, "mantenimiento": 0},
  "items": [ {"id_espacio": 5, "codigo": "A-05", "estado": "ocupado", "ultima_actualizacion": "…",
              "pos": {"x": 0.62, "y": 0.18}, "sesion": {"id_sesion": 4521, "codigo_utp": "U90000002", "tipo_vmp": "scooter_electrico"}} ] }
```

### 2.4 Administración e Incidencias

| Método y ruta | Rol | HU | Descripción |
|---|---|---|---|
| `POST /auth/personal/login` | — | — | `usuario_acceso` + contraseña → JWT (bcrypt) |
| `GET /incidencias?estado=abierta` | seguridad, administrador | HU20 | Lista por estado |
| `GET /incidencias/{id}` | idem | HU20 | Detalle: evidencia, responsable, línea de tiempo |
| `POST /incidencias` | seguridad | HU20/HU22 | Crea manual (p. ej. «otro»: usuario no reconoce un ingreso) |
| `PATCH /incidencias/{id}` | seguridad, administrador | HU20 | Asignar `id_personal`, cambiar estado, agregar comentario |
| `POST /incidencias/{id}/cerrar` | seguridad, administrador | HU20 | `{comentario_cierre}` → `estado=cerrada`, `resuelta=true`, `fecha_cierre` |
| `GET /personal` / `POST /personal` | administrador | — | Gestión del personal (no hay HU explícita; mínimo para operar) |

### 2.5 Notificaciones y Reportes

| Método y ruta | Rol | HU | Descripción |
|---|---|---|---|
| `GET /notificaciones` | usuario | HU22 | Historial de avisos del usuario |
| `POST /notificaciones/{id}/reportar` | usuario | HU22 | «No reconozco este ingreso» → crea incidencia `otro` |
| `PUT /usuarios/me/suscripcion-aviso` | usuario | HU23 | Activa/desactiva el aviso de espacio libre **[PENDIENTE brecha 7]** |
| `POST /dispositivos/push` | usuario | HU22 | Registra token FCM del dispositivo (para push real; en simulación puede omitirse) |
| `POST /encuestas` | usuario | HU24 | Respuesta de satisfacción (1–5 + comentario) **[PENDIENTE brecha 3]** |
| `GET /reportes/piloto?desde=&hasta=` | administrador | HU24 | Calcula/recupera indicadores; incluye evolución diaria del tiempo de ingreso |
| `POST /reportes/piloto` | administrador | HU24 | Genera y guarda un `reporte_piloto` |
| `GET /reportes/piloto/{id}/export` | administrador | HU24 | CSV/PDF |

### 2.6 Integración con IA (internos)

| Método y ruta | Quién llama | Descripción |
|---|---|---|
| `POST /ia/validar-foto-referencia` (en `ia_service`) | monolito (HU03) | Síncrono: `{imagen}` → `{contiene_vehiculo: bool, clase, score, nitidez}` |
| `GET /ia/salud` | monolito/monitor | Modelo cargado, versión, latencia reciente |
| `GET /ia/camaras` | monolito | Estado por cámara (último cuadro, fps) |

### 2.7 Simulador del Portal/App UTP (solo entorno de desarrollo)

| Método y ruta | Descripción |
|---|---|
| `GET /simulador-utp/usuarios/{codigo}` | Datos del usuario como los entregaría la UTP (nombres, correo, sede, matrícula) |
| `POST /simulador-utp/push` | Recibe la notificación del monolito y la muestra en la «App UTP» simulada |

La interfaz `ConectorUTP` (en `identidad/conector_utp/`) define `obtener_usuario(codigo)`, `esta_matriculado(codigo)`, `enviar_push(id_usuario, titulo, cuerpo)`. Dos implementaciones: `ConectorSimulado` (apunta al simulador) y, si algún día hay API real, `ConectorUTPReal`. Cada llamada escribe `sincronizacion_utp`.

## 3. Eventos (Redis Streams) **[PROPUESTA]**

### 3.1 Sobre común

```json
{ "event_id": "b4b1e0f4-…-uuid", "tipo": "ia.validacion.completada", "version": 1,
  "ocurrido_en": "2026-11-09T16:38:02.113-05:00", "origen": "ia_service", "payload": { … } }
```

- `event_id` UUID: el consumidor guarda los ya procesados (tabla/clave Redis) → **idempotencia**.
- Versionado: `version` en el sobre; cambios compatibles solo agregan campos opcionales.
- Reintentos: 3 intentos con espera creciente; luego `*.dlq` + alerta.

### 3.2 Catálogo

**`ia.validacion.solicitada`** (monolito → IA)
```json
{ "id_sesion": 4521, "imagen_url": "s3://vmp/ingresos/2026/11/09/4521.jpg", "camara": "CAM-ING-01",
  "referencias": [ {"id_vehiculo": 17, "tipo_vmp": "scooter_electrico", "foto_url": "s3://vmp/refs/17.jpg"} ] }
```

**`ia.validacion.completada`** (IA → monolito)
```json
{ "id_sesion": 4521, "modelo_version": "vmp-v1", "latencia_ms": 640,
  "deteccion": {"clase": "scooter", "score": 0.93, "bbox": [0.31,0.22,0.62,0.78]},
  "puntajes": [ {"id_vehiculo": 17, "similitud": 0.91}, {"id_vehiculo": 21, "similitud": 0.12} ],
  "mejor": {"id_vehiculo": 17, "similitud": 0.91}, "zona": "verde",
  "imagen_evidencia_url": "s3://vmp/evidencias/4521.jpg", "codigo_camara": "CAM-ING-01",
  "error": null }
```
`zona` ∈ `verde|gris|roja|sin_vehiculo|error`. El monolito escribe `evento_deteccion_ia(tipo=validacion_ingreso, score_confianza=mejor.similitud o score)`, decide y actualiza la sesión.

**`ia.espacio.ocupado` / `ia.espacio.liberado`** (IA → monolito)
```json
{ "codigo_camara": "CAM-ZA-01", "codigo_espacio": "A-05", "confianza": 0.88,
  "cuadros_confirmados": 12, "imagen_url": "s3://vmp/eventos/….jpg", "ocurrido_en": "…" }
```

**`parking.ingreso.validado`** (monolito → notificaciones, panel): `{id_sesion, id_usuario_utp, id_vehiculo, hora}`
**`parking.ingreso.rechazado`** (monolito → administración, notificaciones): `{id_sesion, id_usuario_utp, motivo, id_incidencia}`
**`parking.espacio.cambio`** (monolito → panel/SSE): `{id_espacio, codigo, estado, zona, totales_zona}`
**`parking.zona.llena`** / **`parking.zona.libre`** (monolito → notificaciones): `{ocupacion_pct}` / `{id_zona}` (suscriptores)
**`parking.sesion.finalizada`**: `{id_sesion, permanencia_seg}`

### 3.3 Reglas de consumo

| Consumidor | Evento | Efecto |
|---|---|---|
| `estacionamiento` | `ia.validacion.completada` | `zona=verde` → sesión `validado`; `roja` → `rechazado` + incidencia; `gris` → queda `pendiente de verificación`; `sin_vehiculo`/`error` → reintento de captura o contingencia manual |
| `estacionamiento` | `ia.espacio.ocupado` | Busca la sesión `validado` sin espacio más reciente de la zona/cámara → asigna `id_espacio`, `espacio.estado=ocupado`. Si no hay sesión: evento sin sesión + alerta (**anomalía: ocupación sin ingreso registrado**) |
| `estacionamiento` | `ia.espacio.liberado` | Cierra la sesión que ocupaba ese espacio (`fecha_hora_salida`, `finalizada`), `espacio.estado=disponible` |
| `notificaciones` | `parking.ingreso.validado` | Crea `notificacion(confirmacion_ingreso)` y envía push (HU22) |
| `notificaciones` | `parking.ingreso.rechazado` | Aviso de rechazo (HU22 p.3) |
| `notificaciones` | `parking.zona.llena` | Aviso general **sin ubicación** a usuarios activos del día (HU23) |
| `administracion` | `parking.ingreso.rechazado` | Asegura incidencia abierta con evidencia |

**Correlación de ocupación con sesión [PENDIENTE #9]:** el documento no define cómo se relaciona el vehículo que la cámara de zona ve en `A-05` con la sesión de ingreso. Opciones: (a) la sesión validada queda “esperando espacio” y la primera ocupación nueva en la zona la toma (simple, ambiguo si entran dos seguidos); (b) reconocer el vehículo por la IA en la casilla (comparando con las referencias de las sesiones esperando); (c) el guardia asigna manualmente. Propuesta inicial: (a) con ventana de tiempo máxima y resolución por (b) si hay más de una sesión esperando.

## 4. Secuencias

### 4.1 Ingreso feliz
```
Tablet ─POST /acceso/qr──────────────▶ Gateway ▶ identidad.valida_qr ▶ Conector.UTP ▶ crea sesión preliminar
Tablet ◀─ usuario + vehículos + id_sesion
Tablet ─POST /acceso/{id}/captura────▶ estacionamiento ▶ guarda imagen ▶ XADD ia.validacion.solicitada ─▶ 202
ia_service ◀─ evento ▶ detecta + compara ▶ XADD ia.validacion.completada
estacionamiento ◀─ evento ▶ verde ▶ sesión validado ▶ evento_deteccion_ia ▶ XADD parking.ingreso.validado
Tablet ◀─ SSE/polling "Puede ingresar, Xiaomi Mi 3"        notificaciones ▶ push "Ingreso registrado"
(más tarde) cámara de zona ▶ ia.espacio.ocupado ▶ asigna A-05 ▶ parking.espacio.cambio ▶ panel
```

### 4.2 Rechazo
```
… ia.validacion.completada(zona=roja) ▶ sesión rechazado/con_incidencia ▶ incidencia VEHICULO_NO_COINCIDE (evidencia)
▶ alerta en panel (SSE) ▶ guardia: POST /acceso/{id}/decision {rechazar | aprobar_manual}
```

### 4.3 Salida
```
cámara de zona ▶ ia.espacio.liberado (tras T_LIBERAR) ▶ cierra sesión ▶ espacio disponible ▶ parking.espacio.cambio ▶ panel
(si el estacionamiento estaba lleno) ▶ parking.zona.libre ▶ push a suscriptores
```

## 5. Seguridad de la API (resumen; ver `docs/10`)

- Todo bajo HTTPS; CORS restringido al panel y simuladores.
- Rate limiting en `/auth/*` y `/acceso/qr` (anti fuerza bruta y anti copia masiva de QR).
- El rol `usuario` jamás puede llamar a `/espacios*` (BR-21); tests obligatorios de autorización por rol.
- URLs de imágenes **firmadas y con expiración corta**; nunca públicas.
- Sin datos personales en el contenido del QR; el `token` es aleatorio de ≥ 128 bits.
