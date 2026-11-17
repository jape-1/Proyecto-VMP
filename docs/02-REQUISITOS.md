# 02 · Requisitos y reglas de negocio

> Fuente: Avance 2 §2.3 (Kanban: RF01–RF22 en 6 módulos). Los RNF y reglas derivadas están marcados **[PROPUESTA]** porque el Avance no define requisitos no funcionales numerados.

## 1. Requisitos funcionales [DOC]

Los 6 módulos del tablero Kanban **no son** los 4 módulos del monolito (ver §3 para el mapeo).

### Módulo Kanban 1 · Registro y perfil de usuario

| RF | Requisito | HU | Épica |
|---|---|---|---|
| RF01 | Permitir que el usuario (estudiante, docente o personal) se registre con sus datos personales a través del Portal UTP. | HU01 | EP01 |
| RF02 | Permitir registrar hasta un **máximo de 3 vehículos (VMP)** por usuario. | HU02 | EP01 |
| RF03 | Permitir cargar una **fotografía de referencia** por cada vehículo registrado. | HU03 | EP01 |
| RF04 | Permitir **editar o eliminar** los datos de un vehículo ya registrado. | HU04 | EP01 |
| RF05 | Generar automáticamente un **código QR único** vinculado al perfil del usuario y sus vehículos. | HU05 | EP01 |
| RF06 | Mostrar el código QR generado en la **app UTP**. | HU06 | EP01 |

### Módulo Kanban 2 · Control de acceso e IA

| RF | Requisito | HU | Épica |
|---|---|---|---|
| RF07 | Permitir **escanear el QR** en el punto de ingreso del estacionamiento. | HU07, HU08 | EP02 |
| RF08 | **Capturar una fotografía** del vehículo en el momento del ingreso. | HU09 | EP02 |
| RF09 | **Comparar automáticamente (IA)** la foto capturada contra las fotos registradas del usuario. | HU10 | EP02 |
| RF10 | **Validar y confirmar** si el vehículo corresponde a uno de los registrados por el usuario. | HU11 | EP02 |
| RF11 | **Rechazar o marcar como incidencia** un ingreso cuando el vehículo no coincide con los registrados. | HU12 | EP02 |

### Módulo Kanban 3 · Gestión de espacios

| RF | Requisito | HU | Épica |
|---|---|---|---|
| RF12 | **Monitorear de forma continua** cada espacio mediante cámaras. | HU13 | EP03 |
| RF13 | Detectar automáticamente cuándo un vehículo **ocupa** un espacio y marcarlo «ocupado». | HU14 | EP03 |
| RF14 | Detectar automáticamente cuándo un vehículo **abandona** un espacio y marcarlo «disponible». | HU15 | EP03 |
| RF15 | Actualizar **en tiempo real** el estado (ocupado/disponible) de cada espacio en la BD. | HU16 | EP03 |

### Módulo Kanban 4 · Panel administrativo / seguridad

| RF | Requisito | HU | Épica |
|---|---|---|---|
| RF16 | Mostrar a seguridad y administrativos un **panel con la ubicación exacta** de espacios disponibles y ocupados. | HU17 | EP04 |
| RF17 | Registrar un **historial (log)** de ingresos, salidas e incidencias para auditoría. | HU18, HU19, HU20 | EP04 |
| RF18 | Permitir al personal administrativo **consultar y filtrar** el historial (por usuario, fecha o vehículo). | HU21 | EP04 |

### Módulo Kanban 5 · Notificaciones al usuario

| RF | Requisito | HU | Épica |
|---|---|---|---|
| RF19 | Enviar notificación al usuario **confirmando el registro de su ingreso**. | HU22 | EP05 |
| RF20 | Enviar notificación/aviso al usuario cuando el **estacionamiento esté lleno**. | HU23 | EP05 |
| RF21 | **No** mostrar al usuario la vista detallada de espacios (exclusiva de seguridad/administrativos). | HU17, HU23 | EP04/EP05 |

### Módulo Kanban 6 · Piloto y reportes

| RF | Requisito | HU | Épica |
|---|---|---|---|
| RF22 | Generar **reportes con indicadores del piloto** (tiempo promedio de ingreso, número de incidencias, satisfacción). | HU24 | EP06 |

> El mapeo RF→HU de esta tabla es **inferido** a partir de las dependencias y las anotaciones de prototipo (el Avance no incluye una matriz de trazabilidad). RF17 se reparte entre tres HU; RF21 es una restricción transversal.

## 2. Reglas de negocio consolidadas

Cada regla indica su origen. **[DOC]** viene del Avance 2; **[DERIVADA]** se deduce de forma directa de un prototipo o del ER.

| ID | Regla | Origen | Dónde aplicarla |
|---|---|---|---|
| BR-01 | Máximo **3 VMP activos** por usuario; un cuarto se rechaza. | [DOC] RF02, HU02 (3), ER nota | `identidad.service.registrar_vehiculo` (capa de aplicación, no constraint) |
| BR-02 | Cada VMP debe tener foto de referencia y la imagen debe contener un vehículo. | [DOC] RF03, HU03 (4) | Carga de foto → validación con el detector |
| BR-03 | No se elimina un vehículo con sesión «en curso» (está «dentro»). | [DOC] HU04 (4) | `identidad.service.eliminar_vehiculo` consulta a estacionamiento |
| BR-04 | Editar un vehículo regenera/actualiza el QR. | [DOC] HU04 (2) | `identidad.service.editar_vehiculo` |
| BR-05 | Un QR por usuario agrupa al usuario y todos sus vehículos. El QR guarda solo un token. | [DOC] RF05, HU05 (3)(4) | `CODIGO_QR.token_hash` |
| BR-06 | El QR tiene vigencia (ciclo académico) y estados activo/revocado/expirado. | [DOC] HU05 (2), ER | `fecha_expiracion`, `estado` |
| BR-07 | QR vencido, alterado o inexistente → lectura rechazada con mensaje. | [DOC] HU07 (4) | `POST /acceso/qr` |
| BR-08 | Con el QR se verifica que **matrícula y servicio estén vigentes** antes de seguir. | [DOC] HU08 (2) | `usuario_utp.estado_matricula = activo` |
| BR-09 | La cámara de ingreso se activa **solo después** de leer el QR. | [DOC] HU09 (1) | Orquestación del ingreso |
| BR-10 | La foto capturada se guarda con el ID del QR y la hora. | [DOC] HU09 (3) | `EVENTO_DETECCION_IA.imagen_capturada_url` |
| BR-11 | La IA calcula similitud con **cada** vehículo registrado y solo valida si **alguno** supera el umbral. | [DOC] HU10 (3)(4) | Servicio de IA |
| BR-12 | La comparación debe resolverse **en segundos**. | [DOC] HU10 (5), 1.5 | RNF-01 |
| BR-13 | Validado → mensaje «puede ingresar», muestra qué vehículo fue reconocido, guarda el ingreso y dispara la notificación. | [DOC] HU11 | `estacionamiento.service.registrar_ingreso` |
| BR-14 | No coincide → bloquear ingreso, mostrar motivo, **alerta en tiempo real con evidencia**; el personal decide rechazar o verificación manual; se clasifica el motivo. | [DOC] RF11, HU12 | Incidencia `VEHICULO_NO_COINCIDE` |
| BR-15 | Los **intentos fallidos** también se guardan. | [DOC] HU18 (4) | `SESION_ESTACIONAMIENTO.resultado_validacion = rechazado` |
| BR-16 | Cada detección de ocupación/liberación es un evento con hora y confianza. | [DOC] HU14 (2), HU15 (2) | `EVENTO_DETECCION_IA` |
| BR-17 | Ocupación: regla anti falsos positivos (quien solo pasa no ocupa la casilla). | [DOC] HU14 (3) | Servicio de IA: N cuadros consecutivos (valor a calibrar) |
| BR-18 | Liberación: **tiempo de confirmación** para evitar errores por personas que tapan la cámara. | [DOC] HU15 (3) | Servicio de IA: T segundos (valor a calibrar) |
| BR-19 | La liberación se asocia a la **salida** del usuario (cierra la sesión). | [DOC] HU15 (4), HU19 (2) | `estacionamiento.service.registrar_salida` |
| BR-20 | El contador de la zona y los totales se recalculan con cada cambio de estado. | [DOC] HU14 (4), HU16 (3) | Consulta/agregado en tiempo real |
| BR-21 | La vista detallada de espacios es **solo** de seguridad y administración. Los usuarios reciben avisos generales. | [DOC] RF21, HU17 (5), HU23 (4) | Autorización por rol en `GET /espacios`; payload de notificaciones sin ubicación |
| BR-22 | La notificación de ingreso es inmediata; también se avisa si el ingreso es **rechazado**. | [DOC] HU22 (1)(3) | `notificaciones.service` |
| BR-23 | El usuario puede reportar un ingreso que no reconoce (seguridad). | [DOC] HU22 (4) | Crea incidencia tipo «otro» **[PENDIENTE]** |
| BR-24 | Aviso push cuando la ocupación llega a 100 %. | [DOC] HU23 (1) | Evento `espacios.zona_llena` |
| BR-25 | El usuario puede suscribirse al aviso de «espacio libre». | [DOC] HU23 (3) | Requiere tabla de suscripciones **[PENDIENTE]** |
| BR-26 | La salida de vehículos que no salieron al cierre se controla. | [DOC] HU19 (4) | Job de cierre del día |
| BR-27 | La incidencia pasa por estados abierta → en revisión → cerrada, con evidencia, responsable, línea de tiempo y comentario final de cierre. | [DOC] HU20 | Requiere ampliar `INCIDENCIA` **[PENDIENTE]** |
| BR-28 | El historial se filtra por usuario, rango de fechas, vehículo y tipo de movimiento (combinables) y se exporta. | [DOC] HU21 | `GET /movimientos` + export CSV |
| BR-29 | La consulta sobre el Portal/App UTP se registra en `SINCRONIZACION_UTP` (exitoso/fallido). | [DOC] ER | Conector UTP |
| BR-30 | El consentimiento para el uso de datos e imágenes es **obligatorio** en el registro. | [DOC] HU01 (4) | Requiere dónde guardarlo **[PENDIENTE]** |

## 3. Mapeo: módulos Kanban → módulos del monolito → épicas

| Módulo Kanban | Módulo del monolito (dueño) | Épica |
|---|---|---|
| 1 Registro y perfil | Identidad y Accesos | EP01 |
| 2 Control de acceso e IA | Identidad y Accesos (QR/usuario) + Estacionamiento e IA (sesión, eventos) + Servicio de IA | EP02 |
| 3 Gestión de espacios | Estacionamiento e IA + Servicio de IA | EP03 |
| 4 Panel admin/seguridad | Administración e Incidencias + Estacionamiento e IA (lectura) | EP04 |
| 5 Notificaciones | Notificaciones y Reportes | EP05 |
| 6 Piloto y reportes | Notificaciones y Reportes | EP06 |

## 4. Requisitos no funcionales **[PROPUESTA]**

El Avance 2 no los enumera. Los de abajo se deducen del texto («en segundos», «tiempo real», «auditoría», «datos personales») y de buenas prácticas. Los valores numéricos son **objetivos de diseño provisionales**, no compromisos: se fijan con la línea base del piloto.

| ID | Categoría | Requisito | Valor |
|---|---|---|---|
| RNF-01 | Desempeño | Validación de ingreso (QR leído → resultado en pantalla) en pocos segundos | Objetivo a fijar tras medir; el Avance dice «en segundos» |
| RNF-02 | Desempeño | Cambio de casilla visible en el panel casi al instante («tiempo real») | Objetivo a fijar tras medir |
| RNF-03 | Disponibilidad | Falla del servicio de IA no tumba el monolito; contingencia manual desde el panel | Cualitativo |
| RNF-04 | Seguridad | Tokens QR y contraseñas solo como hash; HTTPS; secretos fuera del repo; acceso por rol | Obligatorio |
| RNF-05 | Privacidad | Fotos con acceso restringido, retención limitada y consentimiento; cumplir normativa peruana de datos personales (Ley 29733, **citada de memoria, verificar**) | Obligatorio |
| RNF-06 | Auditabilidad | Toda decisión automática guarda evidencia (imagen, cámara, confianza, hora) | Obligatorio |
| RNF-07 | Mantenibilidad | Módulos con límites claros; el conector UTP es el único punto de contacto con sistemas UTP | Obligatorio |
| RNF-08 | Escalabilidad | Campo `sede` en usuario y zona; despliegue repetible por sede (IaC) | Preparado, no usado en piloto |
| RNF-09 | Usabilidad | Mensajes claros en el punto de acceso («puede ingresar», motivo del bloqueo) | Cualitativo |
| RNF-10 | Observabilidad | Logs estructurados por sesión y evento; métricas de confianza por cámara | Ver docs/09 |
| RNF-11 | Portabilidad | Todo corre con `docker compose up` en una laptop | Obligatorio |
| RNF-12 | Exactitud del modelo | Precisión/recall por clase medidos sobre conjunto de prueba; sin cifras prometidas de antemano | Medir (docs/06) |

## 5. Restricciones y supuestos

- **No hay acceso real** al Portal UTP ni a la App UTP → conector simulado (RNF-07).
- Una sola sede en el piloto, 40 espacios.
- Equipo de 4 personas, 10 semanas de planificación para 24 HU (103 puntos).
- Las cámaras del piloto pueden simularse con **video grabado o webcam** hasta tener cámaras IP reales **[PROPUESTA]**.
- Fuera de alcance del piloto: mapa de espacios para usuarios, pagos, reservas de casilla, integración real con sistemas UTP, otras sedes.
