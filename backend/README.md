# Servicio de estacionamiento de VMP — backend (avance 1)

Backend del servicio de estacionamiento para vehículos de movilidad personal
(VMP) de la **UTP Torre Arequipa**. Cubre **dos flujos**:

- **Usuario** (App UTP): perfil con consentimiento, hasta **3 VMP** con foto de
  referencia validada por el detector, y su **código QR**.
- **Guardia** (tablet del punto de acceso): lee el QR, ve los datos del usuario
  y sus vehículos, captura la foto, ve el resultado de la IA y **aprueba o
  rechaza a mano**.

Alcance recortado y vinculante en [`docs/18-BACKEND-AVANCE.md`](../docs/18-BACKEND-AVANCE.md).
Es **solo ingreso**: no hay salida, espacios, incidencias, reportes ni
notificaciones (las tablas existen vacías para no romper el ER).

El detector de IA es un **servicio aparte**; aquí solo se consume por HTTP. El
contrato que debe cumplir está en [`docs/IA-CONTRATO.md`](../docs/IA-CONTRATO.md).
**La IA nunca decide permisos**: propone un estado y, si duda o falla, decide una
persona.

---

## 1. Requisitos

- **Python 3.11+** (probado con 3.14.6 en Windows).
- **PostgreSQL 14+** local (probado con 17.4). No hace falta Docker.
- Opcional: Docker, para `docker-compose.yml` (no probado aquí, ver §10).

## 2. Puesta en marcha (Windows / PowerShell)

```powershell
cd estacionamiento-vmp\backend

# 1) Dependencias
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

# 2) Configuración
Copy-Item .env.example .env
#   edita DATABASE_URL si tu PostgreSQL no es postgres:admin@localhost:5432
#   y cambia JWT_SECRETO / QR_SECRETO / MEDIA_SECRETO

# 3) Base de datos (crea `vmp` y `vmp_test`)
.\scripts\dev.ps1 db-nuevo

# 4) Esquema + datos de ejemplo
.\scripts\dev.ps1 migrar
.\scripts\dev.ps1 seed

# 5) Servidor
.\scripts\dev.ps1 correr
```

Queda en:

| Recurso | URL |
|---|---|
| Documentación OpenAPI (Swagger) | <http://127.0.0.1:8000/docs> |
| Esquema OpenAPI (JSON) | <http://127.0.0.1:8000/openapi.json> |
| Salud (backend + base + IA) | <http://127.0.0.1:8000/salud> |

`scripts\dev.ps1` acepta además `probar`, `lint` y `demo`.
`python -m app.seed --reset` borra los datos de negocio y vuelve a sembrar
(útil para repetir la demo desde cero).

## 3. Identidades de ejemplo (sin pantalla de login)

No hay login **como pantalla**, pero el backend **sí distingue roles**. En
desarrollo (`ENTORNO=dev`) dos endpoints entregan el token:

```
POST /api/v1/dev/sesion/usuario/U90000001      -> token rol=usuario
POST /api/v1/dev/sesion/guardia/guardia.tarde  -> token rol=seguridad
GET  /api/v1/dev/identidades                   -> todas las identidades de ejemplo
GET  /api/v1/dev/qr/U90000001                  -> texto del QR (para la demo)
```

Fuera de `dev` (y en `test`) **no están registrados**: no son una puerta trasera
de producción.

| Rol | Identidad | Notas |
|---|---|---|
| Usuario | `U90000001` | 1 scooter (Xiaomi Mi 3) |
| Usuario | `U90000002` | 1 bicicleta |
| Usuario | `U90000004` | scooter + moto eléctrica |
| Usuario | `U90000003` | 3 VMP (prueba del límite) |
| Usuario | `U90000006` | matrícula **inactiva** (el ingreso da 403) |
| Usuario | `U90000005` | personal administrativo |
| Guardia | `guardia.tarde` | rol `seguridad` |
| Guardia | `guardia.noche` | rol `seguridad` |
| Administrador | `admin.seguridad` | rol `administrador` |

Los perfiles son **inventados** (conector simulado). Los vehículos de la columna «Notas» solo se crean con `SEED_VEHICULOS=1`; por defecto cada perfil empieza sin vehículos.

Los guardias se siembran con contraseña (`app/seed.py`), pero en este avance no
hay endpoint de login de personal: el token llega por `/dev/sesion/guardia/*`.

## 4. Flujo del usuario, con ejemplos

Todas las rutas cuelgan de `/api/v1` y llevan `Authorization: Bearer <token>`.
Las fechas salen en ISO-8601 con zona de Lima; las imágenes, como URL relativas
firmadas (`/api/v1/archivos/...?e=...&s=...`, caducan a los 15 min).

| Método y ruta | Qué hace | HU |
|---|---|---|
| `GET /usuarios/me` | Perfil traído del Conector UTP (sincroniza y registra la consulta) | HU01 |
| `PUT /usuarios/me/perfil` | Guarda el **consentimiento** (obligatorio) | HU01 |
| `GET /usuarios/me/vehiculos` | Lista activos + `{max:3, usados:n}` | HU02/HU04 |
| `POST /usuarios/me/vehiculos` | Crea un VMP; el cuarto da `409 LIMITE_VMP_ALCANZADO` | HU02 |
| `PUT /usuarios/me/vehiculos/{id}` | Edita (no rota el QR) | HU04 |
| `DELETE /usuarios/me/vehiculos/{id}` | Baja **lógica** | HU04 |
| `POST /usuarios/me/vehiculos/{id}/foto` | Sube la foto de referencia (multipart) | HU03 |
| `GET /usuarios/me/qr` | QR vigente; lo genera si no existe | HU05/HU06 |
| `POST /usuarios/me/qr/regenerar` | Revoca el actual y emite otro | HU05 |

```powershell
$api = "http://127.0.0.1:8000/api/v1"
$t   = (Invoke-RestMethod -Method Post "$api/dev/sesion/usuario/U90000001").access_token
$h   = @{ Authorization = "Bearer $t" }

# Consentimiento (sin esto, crear vehículos da 409 CONSENTIMIENTO_REQUERIDO)
Invoke-RestMethod -Method Put "$api/usuarios/me/perfil" -Headers $h `
  -ContentType "application/json" `
  -Body '{"acepta_tratamiento_datos": true, "version_consentimiento": "2026-11"}'

# Alta de vehículo
$v = Invoke-RestMethod -Method Post "$api/usuarios/me/vehiculos" -Headers $h `
  -ContentType "application/json" `
  -Body '{"tipo_vmp":"scooter_electrico","marca":"Xiaomi","modelo":"Mi 3","color":"negro"}'

# Foto de referencia (multipart). PowerShell 5.1 no tiene -Form: usa curl
curl.exe -H "Authorization: Bearer $t" `
  -F "archivo=@C:\fotos\mi-scooter.jpg;type=image/jpeg" `
  "$api/usuarios/me/vehiculos/$($v.id_vehiculo)/foto"

# QR (la imagen viene en base64: la dibuja el frontend)
Invoke-RestMethod "$api/usuarios/me/qr" -Headers $h | Select-Object id_qr, vigente, estado
```

Respuesta de `GET /usuarios/me/qr` (recortada):

```json
{
  "id_qr": 4,
  "estado": "activo",
  "fecha_generacion": "2026-11-15T17:38:00-05:00",
  "fecha_expiracion": "2027-05-14T17:38:00-05:00",
  "vigente": true,
  "imagen_qr_png_base64": "iVBORw0KGgoAAAANSUhEUg…",
  "vehiculos": [
    {"id_vehiculo": 7, "tipo_vmp": "scooter_electrico", "marca": "Xiaomi",
     "modelo": "Mi 3", "color": "negro"}
  ]
}
```

## 5. Flujo del guardia, con ejemplos

| Método y ruta | Qué hace | HU |
|---|---|---|
| `POST /acceso/qr` | Valida el QR, consulta el Conector y **abre la sesión** | HU07/HU08 |
| `POST /acceso/{id}/captura` | Sube la foto del vehículo; `202` y dispara la IA | HU09 |
| `GET /acceso/{id}` | Estado: `pendiente` · `validado` · `verificar` · `rechazado` · `ia_no_disponible` | HU10/HU11 |
| `GET /acceso/{id}/stream` | **SSE** con el resultado (o polling del anterior) | HU11/HU12 |
| `POST /acceso/{id}/decision` | `{decision: aprobar_manual \| rechazar, motivo, id_vehiculo?}` | HU12 |
| `POST /acceso/{id}/cancelar` | Cancela un ingreso a medias | HU07 |

```powershell
$g = (Invoke-RestMethod -Method Post "$api/dev/sesion/guardia/guardia.tarde").access_token
$hg = @{ Authorization = "Bearer $g" }

# El QR real se lee con cámara; para la demo, el texto está en /dev/qr
$qr = (Invoke-RestMethod "$api/dev/qr/U90000001").token
$lectura = Invoke-RestMethod -Method Post "$api/acceso/qr" -Headers $hg `
  -ContentType "application/json" -Body "{`"token`":`"$qr`"}"
$lectura | Select-Object id_sesion, siguiente_paso

# Captura -> 202 (la IA corre en segundo plano)
curl.exe -H "Authorization: Bearer $g" -F "archivo=@C:\fotos\captura.jpg" `
  "$api/acceso/$($lectura.id_sesion)/captura"

# Resultado
Invoke-RestMethod "$api/acceso/$($lectura.id_sesion)" -Headers $hg |
  Select-Object estado, motivo, id_vehiculo_reconocido, confianza, mensaje, puede_decidir

# Si hay zona gris, rechazo o IA caída: decide el guardia
Invoke-RestMethod -Method Post "$api/acceso/$($lectura.id_sesion)/decision" -Headers $hg `
  -ContentType "application/json" `
  -Body '{"decision":"aprobar_manual","motivo":"Verificado en el punto de acceso"}'
```

Respuesta de `GET /acceso/{id}`:

```json
{
  "id_sesion": 12,
  "estado": "validado",
  "motivo": null,
  "mensaje": "Puede ingresar.",
  "id_vehiculo_reconocido": 7,
  "confianza": 0.9,
  "detecciones": [{"clase": "scooter", "confianza": 0.9, "caja": [0.31, 0.22, 0.62, 0.78]}],
  "modelo_version": "stub-v1",
  "evidencia_url": "/api/v1/archivos/capturas/2026/11/15/1a3c….jpg?e=…&s=…",
  "fecha_hora_ingreso": "2026-11-15T17:49:48-05:00",
  "fecha_hora_decision": null,
  "decision": null,
  "puede_decidir": false,
  "usuario": {"id_usuario_utp": 1, "codigo_utp": "U90000001", "nombres": "Lucía Fernanda",
              "apellidos": "Rojas Paredes", "tipo_usuario": "estudiante",
              "sede": "Torre Arequipa"},
  "vehiculos": [{"id_vehiculo": 7, "tipo_vmp": "scooter_electrico", "marca": "Xiaomi",
                 "modelo": "Mi 3", "color": "negro", "caracteristica_distintiva": null,
                 "foto_referencia_url": "/api/v1/archivos/referencias/1/….jpg?e=…&s=…",
                 "tiene_foto": true}]
}
```

### SSE

`EventSource` del navegador no puede enviar cabeceras, así que el token va en la
query:

```js
const fuente = new EventSource(
  `http://127.0.0.1:8000/api/v1/acceso/${idSesion}/stream?token=${token}`
);
fuente.addEventListener("estado", (evento) => {
  const estado = JSON.parse(evento.data);   // mismo JSON que GET /acceso/{id}
  if (estado.estado !== "pendiente") fuente.close();
});
```

Emite `event: estado`, un comentario `: latido` cada 15 s y se cierra solo al
llegar a un estado final (o a los 180 s, para que el navegador reconecte).

## 6. Códigos de error

Cuerpo uniforme: `{codigo, mensaje, detalle, request_id}`. El frontend traduce
`codigo` a un texto propio; `mensaje` ya viene en español.

| Código | HTTP | Cuándo |
|---|---|---|
| `SIN_TOKEN` / `TOKEN_INVALIDO` / `TOKEN_EXPIRADO` | 401 | Falta el JWT, es inválido o venció |
| `SIN_PERMISO` | 403 | Rol equivocado (usuario→guardia y guardia→usuario) |
| `USUARIO_INACTIVO` | 403 | Matrícula inactiva al leer el QR |
| `CONSENTIMIENTO_REQUERIDO` | 409 | No aceptó el tratamiento de datos |
| `LIMITE_VMP_ALCANZADO` | 409 | Ya tiene 3 VMP activos |
| `VEHICULO_DENTRO_NO_ELIMINABLE` | 409 | Baja de un vehículo con ingreso vigente |
| `SIN_VEHICULOS_REGISTRADOS` | 409 | QR válido, pero sin VMP activos |
| `VEHICULO_YA_DENTRO` | 409 | Ese vehículo ya tiene un ingreso vigente |
| `SESION_ESTADO_INVALIDO` | 409 | Captura/decisión/cancelación en un estado que no lo admite |
| `QR_REVOCADO` / `QR_EXPIRADO` | 409 | QR no vigente |
| `QR_ALTERADO` | 400 | El token no tiene el formato del backend |
| `QR_INEXISTENTE` | 404 | Token válido en forma, desconocido en la base |
| `VEHICULO_NO_ENCONTRADO` | 404 | No existe, es de otro usuario o no es de la sesión |
| `FOTO_INVALIDA` / `FOTO_SIN_VEHICULO` | 422 | Archivo no válido, o el detector no ve un vehículo con confianza suficiente |
| `FOTO_TIPO_NO_COINCIDE` | 422 | La foto muestra un vehículo de otra clase que el tipo registrado (`detalle`: `detectado`, `tipo_vmp`) |
| `IA_NO_DISPONIBLE` | 503 | Solo al subir la foto de referencia (en el ingreso se resuelve a mano) |
| `ARCHIVO_NO_ENCONTRADO` | 404 | URL de imagen vencida o firma inválida |
| `DATOS_INVALIDOS` | 422 | Validación de esquema (con `detalle` por campo) |
| `ERROR_INTERNO` | 500 | Fallo no controlado (sin datos personales en la respuesta) |

## 7. Pruebas

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

Resultado real en esta máquina (15-nov-2026, PostgreSQL 17.4, IA en modo stub):

```
31 passed, 2 deselected, 1 warning in 5.38s
```

Cubren las reglas de [`docs/18` §7](../docs/18-BACKEND-AVANCE.md): límite de 3 VMP,
consentimiento obligatorio, foto sin vehículo, QR alterado/vencido/revocado/
inexistente, un solo QR activo, 403 cruzados, decisión del guardia registrada,
caída de la IA con decisión manual, matrícula inactiva, vehículo «dentro» no
eliminable, intento de QR registrado, SSE y que no se filtren `token_hash` ni
datos de otro usuario.

Las 2 **deseleccionadas** son la prueba de integración con el detector real
(`tests/test_ia_real.py`, marcada `lenta`): se omiten si no hay servicio de IA en
`IA_URL` o no hay foto en `tests/fixtures/`. Ver `docs/IA-CONTRATO.md` §6.

La IA se sustituye por un **doble** (`IA_MODO=stub`), así que las pruebas no
dependen del modelo. La base de pruebas es `vmp_test`: se dropea el esquema y se
aplica `alembic upgrade head` en cada corrida.

## 8. Estructura

```
backend/
  app/
    core/            configuración, BD, seguridad, errores, storage, enums
    gateway/         auth por rol; /dev/* de desarrollo; entrega de imágenes firmadas
    ia/              cliente del detector (HTTP + stub de pruebas)
    modules/
      identidad/     usuarios, sync UTP, vehículos, QR (+ conector UTP simulado)
      estacionamiento/ ingreso: QR -> captura -> IA -> decisión
      administracion/ personal de seguridad (y tabla de incidencias sin flujo)
      notificaciones/ tablas del ER, sin flujo en este avance
    seed.py          datos de ejemplo
  alembic/versions/0001_esquema_inicial.py
  tests/
  scripts/           dev.ps1 (tareas) y demo_flujo.py (demo de punta a punta)
docs/                documentación del proyecto (18 = alcance del avance)
```

## 9. Trazabilidad HU / requisito → código

| HU | Endpoint / pieza | Dónde |
|---|---|---|
| HU01 | perfil + consentimiento | `modules/identidad/service.py`, `router.py` |
| HU02 | alta de VMP y límite de 3 | `service.crear_vehiculo` (bloqueo con `FOR UPDATE`) |
| HU03 | foto de referencia validada | `service.guardar_foto_referencia` + `ia/cliente.py` |
| HU04 | edición y baja; «dentro» | `service.editar_vehiculo`, `dar_baja_vehiculo` |
| HU05 | QR único y regeneración | `service.obtener_qr`, `regenerar_qr` |
| HU06 | QR dibujado por el frontend | `service.qr_out` (PNG base64) |
| HU07 | lectura del QR y sesión | `estacionamiento/service.crear_sesion` |
| HU08 | datos del usuario y vehículos | `AccesoQROut` |
| HU09 | captura y disparo de la IA | `router.subir_captura` + `procesar_captura_ia` |
| HU10/HU11 | resultado y espera | `obtener_estado`, `GET /stream` (SSE) |
| HU12 | decisión manual auditada | `service.decidir` |
| HU18 | registro de ingresos | `sesion_estacionamiento` + `evento_deteccion_ia` |
| RF02 (3 VMP) | `MAX_VMP=3` + bloqueo de fila | `identidad/service.py` |
| BR-04 | editar no rota el QR | `docs/13` §F (2026-11-15) |
| Privacidad | solo `token_hash`; imágenes con URL firmada; sin datos en logs | `core/security.py`, `core/storage.py`, `core/logging.py` |

## 10. Limitaciones declaradas (lo que **no** está probado o está incompleto)

1. **`docker compose up` no se ejecutó**: la máquina de desarrollo no tiene
   Docker. El `Dockerfile` y `docker-compose.yml` se entregan como punto de
   partida y **no** están verificados. El camino probado es el de §2.
2. **Detector real no integrado aquí**: todas las pruebas usan el doble. La
   prueba `lenta` está escrita pero se omite hasta que exista el servicio en
   `IA_URL` y una foto de ejemplo. El contrato está en `docs/IA-CONTRATO.md`.
3. **«Vehículo identificado» = hay un vehículo del tipo registrado**, no
   necesariamente *el* vehículo de ese usuario. La comparación con la foto de
   referencia es Fase 3 (E4/E5). Con varios VMP del mismo tipo se elige el
   primero que coincide por tipo.
4. **`moto_electrica` se entrenó con motos en general** (muchas a gasolina): el
   detector reconoce «moto», no si es eléctrica (`docs/25` §1).
5. **«No eliminar un vehículo que está dentro»** se implementó como «no dar de
   baja si tiene un ingreso validado vigente», porque en este avance no hay
   salida (docs/18 §7.9).
6. **Umbrales provisionales** (`IA_UMBRAL_VALIDADO=0.60` e `IA_UMBRAL_SEMEJANZA=0.70`, `docs/26` §5): no está
   calibrado; se ajusta con las fotos de la Fase 1.
7. **Sin autenticación real**: no hay login de personal ni de usuario. Los
   tokens los entrega `/dev/*` (solo `ENTORNO=dev`).
8. **Sin rate limiting** en `/acceso/qr` ni `/dev/*` (docs/07 §4 lo pide para
   producción).
9. Las **notificaciones, incidencias, espacios y reportes** no tienen flujo:
   solo existen las tablas del ER.
10. Las pruebas usan la base `vmp_test` y **borran su esquema público**: no
    apuntes `DATABASE_URL` de pruebas a una base con datos que quieras conservar.

## 11. Documentos

| Documento | Para qué |
|---|---|
| [`docs/18-BACKEND-AVANCE.md`](../docs/18-BACKEND-AVANCE.md) | alcance vinculante del avance |
| [`docs/IA-CONTRATO.md`](../docs/IA-CONTRATO.md) | contrato HTTP que implementa quien integre el detector |
| [`docs/PENDIENTES-INTEGRACION.md`](../docs/PENDIENTES-INTEGRACION.md) | qué queda para unir el detector real y los frontends |
| [`docs/07-API-EVENTOS.md`](../docs/07-API-EVENTOS.md) | contrato de la API completa (esto es un subconjunto) |
| [`docs/13-DECISIONES-PENDIENTES.md`](../docs/13-DECISIONES-PENDIENTES.md) | brechas aprobadas y decisiones (§F) |
| [`docs/05-MODELO-DATOS.md`](../docs/05-MODELO-DATOS.md) | modelo de datos y DDL de referencia |

## 12. Traspaso

El repositorio se sube a GitHub como **privado**. No se versionan `.env`,
imágenes capturadas, pesos del modelo ni secretos (`.gitignore`).

Para arrancar en otra máquina: §2, cambiando `DATABASE_URL` y los tres secretos.
Para conectar el detector real: `IA_MODO=http`, `IA_URL=…` y
`docs/IA-CONTRATO.md`.
