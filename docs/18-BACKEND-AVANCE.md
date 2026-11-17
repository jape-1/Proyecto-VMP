# 18 · Backend del próximo avance (alcance recortado)

> **[PROPUESTA]** salvo lo marcado **[DECIDIDO]** (lo dijo el equipo el 14-nov-2026). Es un **recorte** del backend completo descrito en `docs/03`–`docs/07`: aquí se fija **solo lo que se construye para el próximo avance**. El backend **debe correr de verdad**, pero entrega una **parte de la funcionalidad**. Si este archivo contradice a `docs/03`–`docs/07`, **manda este** para el avance; el resto sigue siendo el objetivo del producto completo.

## 1. Decisiones del equipo (14-nov-2026)

| # | Decisión | Estado |
|---|---|---|
| 1 | Se construyen **dos flujos**: el del **usuario** (registra sus vehículos y obtiene su QR) y el del **guardia de seguridad** (lee el QR, captura la foto, ve si el vehículo fue identificado y deja pasar o no) | [DECIDIDO] |
| 2 | **Solo ingreso.** No hay salida del vehículo | [DECIDIDO] |
| 3 | **Fuera de alcance:** control de espacios (zonas, casillas, ocupación/liberación), gestión de incidencias, reportes, notificaciones al usuario | [DECIDIDO] |
| 4 | La IA es el **detector real** desarrollado en la Fase 1 (YOLO26), no una simulación | [DECIDIDO] |
| 5 | **Dos frontends** (usuario y guardia) hechos por una compañera; **se acoplan a la API del backend** | [DECIDIDO] |
| 6 | **Sin pantalla de inicio de sesión:** cada frontend arranca con la sesión ya iniciada | [DECIDIDO] → **cambiada el 17-nov-2026**: inicio de sesión simulado sin contraseña (`docs/13`) |

**Cómo se interpreta la decisión 6 [PENDIENTE confirmar]:** el login *como pantalla* no existe, pero el backend **sigue distinguiendo las dos identidades** (usuario y guardia) y rechaza con 403 lo que no le corresponde a cada una. La sesión «ya iniciada» se logra con un mecanismo de desarrollo (§4) que entrega la identidad al frontend al arrancar. Si lo que se quiere es que el backend **no** distinga identidades en absoluto, dilo: se simplifica, pero se pierden la regla «el usuario nunca ve lo del guardia» y la trazabilidad de quién autorizó cada ingreso.

## 2. Qué entra y qué no

| Área | Entra | Fuera de este avance |
|---|---|---|
| Usuario | Perfil con consentimiento · registrar hasta **3 VMP** · foto de referencia validada con el detector · editar/dar de baja · ver su **QR** | Notificaciones, historial de movimientos, ver espacios |
| Guardia | Leer el **QR** · ver datos del usuario y sus vehículos con foto · capturar la foto del vehículo · ver el **resultado de la IA** · **aprobar/rechazar** manualmente | Salida, ocupación de casillas, panel de espacios |
| IA | Detector real (`scooter`, `bicicleta`) con comprobación del tipo (§5) | Comparación con la foto registrada (E4/E5), casillas (E6) |
| Registro | Cada intento de ingreso queda guardado, aceptado o no, con foto y hora | Incidencias con seguimiento, reportes |
| Plataforma | Conector UTP **simulado**, datos de ejemplo, ejecución con un comando, pruebas | Push real, AWS/Terraform, observabilidad avanzada |

**Historias cubiertas** (`docs/03`): HU01 (parcial: perfil + consentimiento), HU02, HU03, HU04 (edición y baja; sin regla de «dentro» hasta que haya salida: ver §7), HU05, HU06 (el backend entrega el QR; lo dibuja el frontend), HU07, HU08, HU09, HU10, HU11, HU12 (rechazo y decisión manual, **sin** gestión de incidencias) y HU18 (solo ingresos). **No cubiertas:** HU13–HU17, HU19–HU24.

## 3. Arquitectura del avance

- **Monolito modular** (FastAPI, SQLAlchemy + Alembic, PostgreSQL) con los módulos de `docs/04`: *Identidad y Accesos* (usuarios, vehículos, QR), *Estacionamiento e IA* (punto de acceso, sesiones, eventos de IA) y la parte mínima de *Administración* (personal de seguridad). *Notificaciones y Reportes* **no se crea**.
- **Servicio de IA aparte** (`ia_service`, Python + YOLO26 + OpenCV) con el `best.pt` de la Fase 1. **[PROPUESTA]** El backend lo llama **por HTTP con tiempo límite** (la alternativa aceptada en `docs/13` #6) en lugar de Redis Streams, porque con un solo consumidor es más simple de construir y de depurar; el diseño con eventos queda para cuando haya cámaras de zona. Si el equipo prefiere Redis desde ya, solo cambia el transporte: el contrato de §5 no cambia.
- **Almacenamiento de imágenes:** disco local con volumen de Docker (las URL que ve el frontend son firmadas o de un endpoint propio). S3/MinIO queda para después.
- **Docker Compose:** `db`, `backend`, `ia_service`. Todo arranca con **un comando**.
- **Conector UTP simulado** (`docs/07` §2.7): módulo propio con usuarios de ejemplo; es el único lugar que «sabe» de la UTP.
- Estructura de carpetas por módulo de negocio, no por capa (`docs/04` §6). Dominio en español, igual que el ER.

## 4. Sesión «ya iniciada» (sin pantalla de login)

**[PROPUESTA]** Solo cuando `ENTORNO=dev` (y desactivado por defecto en cualquier otro entorno):

- `POST /dev/sesion/usuario/{codigo_utp}` → devuelve el token del usuario de ejemplo.
- `POST /dev/sesion/guardia/{usuario_acceso}` → devuelve el token del guardia de ejemplo.
- Cada frontend lo llama **una vez al arrancar** con una identidad fija (configurada por variable de entorno) y desde ahí usa el token en `Authorization: Bearer …` como en cualquier API.
- El resto de la API **siempre** exige token y rol. Estos endpoints no existen fuera de desarrollo: no es una puerta trasera de producción.

## 5. Integración con la IA (detector real)

> ⚠ **Actualizado el 17-nov-2026:** el detector tiene **3 clases** (`scooter`, `bicicleta`, `moto_electrica`) y el ingreso **sí compara con la foto registrada**. La regla de decisión vigente es la de `docs/26` §3; lo que sigue describe la regla v1 (solo por tipo), que es lo que hoy hace el código.

**Qué hace el detector hoy (Fase 1):** reconoce `scooter` y `bicicleta` en una imagen y devuelve cajas con etiqueta y confianza. **No compara** la foto contra la foto registrada. Por eso, **para este avance «vehículo identificado» significa lo siguiente, y así debe decirse en la exposición:**

| Regla de validación v1 **[PROPUESTA]** | Resultado |
|---|---|
| El detector encuentra un vehículo cuya clase **corresponde al tipo de alguno de los VMP activos del usuario**, con confianza ≥ umbral | `validado`: se muestra al guardia qué vehículo del usuario coincide por tipo |
| Encuentra un vehículo pero **de un tipo que el usuario no registró** | `rechazado` (`VEHICULO_NO_COINCIDE`) |
| No detecta ningún vehículo, o la confianza queda en zona dudosa | `verificar`: el guardia decide a mano |
| El servicio de IA no responde o excede el tiempo | `IA_NO_DISPONIBLE`: el guardia puede **aprobar o rechazar a mano** y queda registrado |

- **Correspondencia de tipos:** el detector tiene 2 clases; el ER tiene más tipos. `scooter` ↔ `scooter_electrico`; `bicicleta` ↔ `bicicleta` **y** `bicicleta_electrica`. `moto_electrica` no se reconoce todavía (`docs/13` #28): un usuario con ese tipo cae siempre en `verificar`.
- **Limitación a declarar:** esta regla confirma que **hay un vehículo del tipo registrado**, no que sea **el** vehículo de ese usuario. La identidad real (similitud con la foto de referencia) es la Fase 3 (E4/E5). El umbral de confianza es **provisional** y se calibra con datos (`docs/06` §8); no inventar valores definitivos.
- **Contrato del servicio de IA** (internos, `docs/07` §2.6): entrada = imagen + lista de tipos esperados; salida = `{detecciones:[{clase, confianza, caja}], modelo_version, ms}`. El backend arma la decisión; **la IA no decide permisos**.
- La IA también se usa al subir la **foto de referencia** (HU03): rechaza con `FOTO_SIN_VEHICULO` si el detector no ve scooter ni bicicleta.
- **Evidencia:** cada captura guarda imagen, versión del modelo, detecciones y confianza en `evento_deteccion_ia`.

## 6. Endpoints del avance (subconjunto de `docs/07`)

Base `/api/v1`, errores uniformes con `codigo`, `mensaje`, `detalle`, `request_id` (`docs/07` §1). Todos exigen token salvo `/dev/*` y `/salud`.

**Frontend del usuario**

| Método y ruta | Descripción | HU |
|---|---|---|
| `GET /usuarios/me` | Perfil traído del Conector UTP | HU01 |
| `PUT /usuarios/me/perfil` | Completa perfil y `acepta_tratamiento_datos` (obligatorio: `CONSENTIMIENTO_REQUERIDO`) | HU01 |
| `GET /usuarios/me/vehiculos` | Lista activos + `{max:3, usados:n}` | HU02/04 |
| `POST /usuarios/me/vehiculos` | Crea vehículo; `409 LIMITE_VMP_ALCANZADO` al cuarto | HU02 |
| `PUT /usuarios/me/vehiculos/{id}` | Edita | HU04 |
| `DELETE /usuarios/me/vehiculos/{id}` | Baja lógica | HU04 |
| `POST /usuarios/me/vehiculos/{id}/foto` | Sube la foto de referencia (multipart); valida tipo/tamaño y que el detector vea un vehículo | HU03 |
| `GET /usuarios/me/qr` | QR vigente (`imagen_qr_png_base64`, vigencia, estado, vehículos); lo genera si no existe | HU05/06 |
| `POST /usuarios/me/qr/regenerar` | Revoca el QR y emite otro | HU05 |

**Frontend del guardia**

| Método y ruta | Descripción | HU |
|---|---|---|
| `POST /acceso/qr` | Body `{token}`: valida hash, vigencia y estado; consulta el Conector; crea la **sesión de ingreso**; devuelve usuario y vehículos con foto | HU07/08 |
| `GET /espacios` | Monitoreo: espacios por zona con estado y ocupante; libres, ocupados, lleno. Solo guardia y administración (17-nov-2026) | HU17 |
| `POST /espacios/{id_espacio}/liberar` | Registra la salida del vehículo de ese espacio y lo deja libre (sustituye a la cámara de casillas) | HU15/HU19 |
| `POST /acceso/{id_sesion}/cuadro` | Analiza un cuadro del video en vivo (multipart); `200` con detecciones, veredicto y umbrales; **no guarda nada** (17-nov-2026) | HU09 |
| `POST /acceso/{id_sesion}/captura` | Sube la foto del vehículo (multipart); `202`; dispara la IA. El video en vivo envía aquí el cuadro final | HU09 |
| `GET /acceso/{id_sesion}` | Estado: `pendiente_ia` · `validado` · `verificar` · `rechazado`, con detecciones, confianza y motivo | HU10/11 |
| `GET /acceso/{id_sesion}/stream` | SSE con el resultado (alternativa: consultar cada pocos segundos el endpoint anterior) | HU11/12 |
| `POST /acceso/{id_sesion}/decision` | `{decision: aprobar_manual \| rechazar, motivo}` | HU12 |
| `POST /acceso/{id_sesion}/cancelar` | Cancela un ingreso a medias | HU07 |

**Comunes:** `GET /salud` (estado del backend y de la IA) · documentación **OpenAPI** publicada (es el contrato que usa la compañera del frontend) · **CORS** habilitado para los orígenes de los frontends.

**Reglas para el frontend (acuerdos de contrato):** imágenes por multipart con límite de tamaño y tipos `jpg/png`; fechas ISO-8601 con zona America/Lima; códigos de error estables (`docs/07` §1) que el frontend traduce a mensajes; **no cambiar rutas ni campos sin avisar** (se versiona en `docs/07`/este archivo).

## 7. Reglas de negocio que deben cumplirse y probarse

1. Máximo **3 VMP activos** por usuario, aplicado en la capa de aplicación.
2. Cada vehículo tiene **una foto de referencia** con un vehículo detectado.
3. **El QR guarda un token opaco**: nada de datos personales; en la base solo `token_hash` (SHA-256). Un QR vencido, alterado, revocado o inexistente se rechaza (`QR_EXPIRADO`, `QR_ALTERADO`, `QR_REVOCADO`, `QR_INEXISTENTE`). **Un solo QR activo por usuario.**
4. Si el vehículo no coincide: se **bloquea** y **un humano decide** (aprobar manual o rechazar). Nunca se rechaza ni se aprueba definitivamente solo por la IA.
5. **Los intentos fallidos también se registran** (QR inválido incluido, en un registro simple; `docs/13` #5).
6. **El usuario nunca accede a lo del guardia** (403) y el guardia no edita vehículos de nadie.
7. Si la IA falla, **el flujo no se detiene**: decisión manual con registro.
8. **Contraseñas y tokens** solo como hash; secretos por variables de entorno; nada de datos personales ni imágenes en logs.
9. **«No eliminar un vehículo que está dentro» (HU04):** al no haber salida en este avance, la regla se implementa como «no se puede dar de baja un vehículo con una sesión de ingreso validada vigente» y queda documentada como incompleta.
10. **Editar un vehículo actualiza el QR** (BR-04; `docs/13` #4 propone que basta actualizar la lista asociada porque el QR solo identifica al usuario). Seguir lo que `docs/13` #4 deje decidido.

## 8. Datos

- **Se usan:** `usuario_utp`, `sincronizacion_utp` (alimentada por el Conector simulado), `vehiculo_vmp`, `codigo_qr`, `sesion_estacionamiento`, `evento_deteccion_ia`, `personal_seguridad`.
- **Se crean vacías o no se usan:** `zona_estacionamiento`, `espacio_estacionamiento`, `incidencia`, `notificacion`, `reporte_piloto`. En `sesion_estacionamiento`, `id_espacio` es **nulo** (el ER ya lo permite), no hace falta cargar espacios.
- **Registro de rechazos sin incidencias:** quedan en `sesion_estacionamiento` (`resultado_validacion`, `estado_sesion`) y en `evento_deteccion_ia` con la evidencia. Confirmar con `docs/05` los valores exactos de los tipos enumerados; **no inventar columnas**: si falta una (`modelo` del vehículo, consentimiento, `rol` del personal), proponerla en `docs/13` (brechas B1, B3, B9) y esperar aprobación.
- **Datos de ejemplo (seeds):** 3–5 usuarios del Conector (con vehículos de ejemplo), 1–2 guardias, y fotos de ejemplo para la demo.
- Migraciones solo con **Alembic**; el esquema nace del DDL de `docs/05` (validado en PostgreSQL 16).

## 9. Entregable para la compañera del frontend

- Documentación **OpenAPI** accesible en el backend corriendo.
- Un `README` con: cómo levantar todo con un comando, URLs, identidades de ejemplo (§4), **flujos felices** de cada frontend, tabla de códigos de error y ejemplos de respuesta (`docs/07` §2.2).
- Datos de ejemplo cargados para poder probar sin preparar nada.

## 10. Pruebas y criterios de aceptación

**Pruebas automáticas** (pytest + cliente HTTP), primero las reglas de negocio de §7:
- límite de 3 VMP (el cuarto da 409) · foto sin vehículo rechazada · QR vencido/alterado/revocado · un QR activo por usuario · 403 cruzados (usuario→guardia y guardia→usuario) · decisión del guardia registrada · caída de la IA con decisión manual · consentimiento obligatorio · el backend nunca devuelve `token_hash` ni datos de otro usuario.
- Con la IA **simulada en las pruebas** (doble de prueba) para que no dependan del modelo; y **al menos una prueba de integración** con el detector real sobre una imagen de ejemplo, marcada como lenta.

**Demostración de punta a punta** (la que se muestra en el avance):
1. El usuario registra un scooter con su foto y ve su QR.
2. El guardia lee el QR, captura la foto del vehículo y ve el resultado de la IA.
3. Caso coincide → pasa. Caso no coincide (otro tipo) → bloqueo y decisión del guardia. Caso IA caída → decisión manual.
4. Se ve el registro de los tres intentos.

**Criterio de «hecho»:** `docker compose up` levanta todo · pruebas verdes con resultado real pegado · demo repetible desde cero con los datos de ejemplo · OpenAPI publicada · tabla de trazabilidad HU/RF en el README · limitaciones declaradas (§5, §7.9).

## 11. Orden de construcción (rebanadas verticales)

1. **Andamiaje:** estructura, Compose con `db` + `backend` + `ia_service`, `/salud`, Alembic con el esquema, seeds, Conector simulado, `/dev/sesion/*`.
2. **Usuario:** perfil + consentimiento → vehículos (límite de 3) → foto con el detector → QR.
3. **Guardia:** `/acceso/qr` → captura → resultado de la IA → decisión manual → registro de intentos.
4. **Pulido para el frontend:** CORS, SSE, mensajes de error, OpenAPI, README.
5. **Pruebas de aceptación** y ensayo de la demo.

Cada paso: pruebas primero de la regla de negocio, un commit por rebanada, cada PR cita la HU/RF.

## 12. Reglas de trabajo

- Consultar la documentación vigente de FastAPI, SQLAlchemy, Alembic, Pydantic, `qrcode`, Ultralytics, OpenCV y pytest antes de usarlas.
- No construyas lo que está **fuera de alcance** (§2) aunque el resto de los documentos lo describa.
- No cambies el ER sin aprobación (`docs/13` §B). Si algo no cuadra entre este archivo y `docs/03`–`docs/07`, **pregunta**.
- Ninguna métrica ni umbral definitivo sin medirlo; di qué no pudiste probar.
- No subas a Git datos, imágenes, pesos del modelo ni secretos.

## 13. Preguntas abiertas

| # | Pregunta | Propuesta |
|---|---|---|
| A | ¿El backend **distingue** las dos identidades aunque no haya pantalla de login? (§1) | Sí |
| B | ¿La IA se llama por HTTP o por Redis Streams? (§3) | HTTP con tiempo límite |
| C | ¿Imágenes en disco local o en S3/MinIO? | Disco local |
| D | ¿Dónde corre el demo (laptop de quién) y con qué cámara captura el guardia (celular/tablet)? | A definir con la compañera del frontend |
| E | ¿Umbral de confianza inicial? | Provisional; calibrar con las fotos de la Fase 1 |
| F | ¿Qué hace el guardia con `moto_electrica` (no reconocida aún)? | Siempre `verificar` |


> **16-nov-2026:** frontends en `docs/20`; requisitos y aceptación en `docs/19`; herramientas y entorno en `docs/21`.
