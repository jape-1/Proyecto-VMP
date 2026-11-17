# 03 · Backlog y historias de usuario (HU01–HU24)

> Fuente: Avance 2, secciones 2.4.1.1.5 (backlog), 2.4.1.2.1 (fichas), 2.4.1.2.2 (puntos), 2.4.1.2.3 (plazos), 2.4.1.2.4 (sprint backlog) y 2.5.3 (prototipos). Todo este archivo es **[DOC]** salvo donde se indique **[PROPUESTA]**. Las columnas «Comportamiento del prototipo» reproducen las anotaciones numeradas de cada figura del Avance 2: son la especificación funcional de facto.

## 1. Épicas

| Épica | Nombre | Alcance | HU |
|---|---|---|---|
| EP01 | Gestión de usuarios y registro de vehículos | Registro de datos personales, alta/edición/baja de vehículos con foto de referencia y QR único por usuario. | HU01–HU06 |
| EP02 | Control de acceso y reconocimiento mediante IA | Lectura del QR, captura de imagen, comparación automática con fotos registradas, validación o alerta. | HU07–HU12 |
| EP03 | Gestión y monitoreo de espacios | Supervisión por cámaras, detección de ocupación/liberación, actualización de disponibilidad en BD. | HU13–HU16 |
| EP04 | Panel administrativo y trazabilidad | Panel de espacios, registro de movimientos e incidencias, historial con filtros. | HU17–HU21 |
| EP05 | Notificaciones y comunicación con el usuario | Confirmación de ingreso y aviso de estacionamiento lleno; detalle de espacios restringido al personal. | HU22–HU23 |
| EP06 | Reportes e indicadores del piloto | Tiempo promedio de ingreso, cantidad de incidencias, satisfacción. | HU24 |

## 2. Sprints (release plan)

| Sprint | Contenido | Duración | HU | Días de trabajo (suma de plazos) | Puntos |
|---|---|---|---|---|---|
| SPT01 | SPT01 · Gestión de usuarios y registro de vehículos | 2 semanas | HU01–HU06 | 10 | 19 |
| SPT02 | SPT02 · Control de acceso y reconocimiento mediante IA | 3 semanas | HU07–HU12 | 15 | 30 |
| SPT03 | SPT03 · Gestión de espacios de estacionamiento y administración | 3 semanas | HU13–HU21 | 15 | 42 |
| SPT04 | SPT04 · Gestión de notificaciones y reportes | 2 semanas | HU22–HU24 | 10 | 12 |
| **Total** | | **10 semanas** | 24 HU | **50** | **103** |

Escala de puntos: 1–3 dificultad baja · 4–6 media · 7–9 alta. Las HU de mayor esfuerzo son HU10 (8), HU14 (7) y HU15 (7); las tres dependen del componente de IA.

## 3. Tabla maestra

| HU | Nombre | Actor | Depende de | Sprint | Pts | Días | Prioridad (backlog) | Prioridad (ficha) | RF | Épica |
|---|---|---|---|---|---|---|---|---|---|---|
| HU01 | Registro de datos personales del usuario mediante el Portal UTP existente | Estudiante, docente o personal administrativo | — | SPT01 | 3 | 2 | Alta | Alta | RF01 | EP01 |
| HU02 | Registro y vinculación de vehículos al usuario, con un máximo de tres VMP | Estudiante, docente o personal administrativo | HU01 | SPT01 | 4 | 2 | Muy alta | Alta | RF02 | EP01 |
| HU03 | Carga y almacenamiento de fotografías de referencia de cada vehículo | Estudiante, docente o personal administrativo | HU02 | SPT01 | 4 | 2 | Alta | Alta | RF03 | EP01 |
| HU04 | Modificación y eliminación de los datos de los vehículos registrados | Estudiante, docente o personal administrativo | HU02 | SPT01 | 3 | 1 | Alta | Alta | RF04 | EP01 |
| HU05 | Generación de un código QR único asociado al estudiante y sus vehículos registrados | Estudiante, docente o personal administrativo | HU02 | SPT01 | 3 | 1 | Muy alta | Alta | RF05 | EP01 |
| HU06 | Visualización del código QR generado para el ingreso con VMP | Estudiante, docente o personal administrativo | HU05 | SPT01 | 2 | 2 | Alta | Alta | RF06 | EP01 |
| HU07 | Lectura del código QR en el punto de acceso destinado a VMP | Personal de seguridad | HU06 | SPT02 | 3 | 2 | Muy alta | Alta | RF07 | EP02 |
| HU08 | Identificación del estudiante y consulta de sus vehículos registrados a partir del QR | Personal de seguridad | HU07 | SPT02 | 4 | 2 | Muy alta | Alta | RF07 | EP02 |
| HU09 | Captura de una imagen del VMP mediante la cámara de ingreso | Personal de seguridad | HU07 | SPT02 | 4 | 2 | Muy alta | Alta | RF08 | EP02 |
| HU10 | Comparación mediante inteligencia artificial de la imagen capturada con las fotografías registradas | Sistema | HU03, HU09 | SPT02 | 8 | 3 | Muy alta | Muy alta | RF09 | EP02 |
| HU11 | Validación de correspondencia entre el VMP ingresante y los vehículos asociados al estudiante | Sistema | HU08, HU10 | SPT02 | 6 | 3 | Muy alta | Muy alta | RF10 | EP02 |
| HU12 | Rechazo o generación de una alerta ante un vehículo que no coincide con los registros | Personal de seguridad | HU11 | SPT02 | 5 | 3 | Alta | Muy alta | RF11 | EP02 |
| HU13 | Monitoreo del estado de los espacios de estacionamiento mediante cámaras | Personal de seguridad y administración | — | SPT03 | 6 | 2 | Muy alta | Alta | RF12 | EP03 |
| HU14 | Detección automática de espacios ocupados | Sistema | HU13 | SPT03 | 7 | 2 | Muy alta | Alta | RF13 | EP03 |
| HU15 | Detección automática de espacios liberados | Sistema | HU13 | SPT03 | 7 | 2 | Muy alta | Alta | RF14 | EP03 |
| HU16 | Actualización del estado de los espacios en la base de datos en tiempo real | Sistema | HU14, HU15 | SPT03 | 4 | 2 | Muy alta | Alta | RF15 | EP03 |
| HU17 | Visualización de espacios ocupados y disponibles en el panel administrativo | Personal de seguridad y administración | HU16 | SPT03 | 4 | 2 | Alta | Alta | RF16 | EP04 |
| HU18 | Registro de los movimientos de ingreso de estudiantes y sus VMP | Personal de seguridad y administración | HU07, HU11 | SPT03 | 3 | 1 | Muy alta | Alta | RF17 | EP04 |
| HU19 | Registro de los movimientos de salida de estudiantes y sus VMP | Personal de seguridad y administración | HU18 | SPT03 | 3 | 1 | Alta | Alta | RF17 | EP04 |
| HU20 | Registro y seguimiento de incidencias relacionadas con el acceso de VMP | Personal de seguridad y administración | HU12, HU18 | SPT03 | 4 | 2 | Alta | Alta | RF17 | EP04 |
| HU21 | Consulta y filtrado del historial de movimientos por usuario, fecha y vehículo | Personal de seguridad y administración | HU18, HU19, HU20 | SPT03 | 4 | 1 | Alta | Alta | RF18 | EP04 |
| HU22 | Notificación de confirmación del ingreso del VMP | Estudiante, docente o personal administrativo | HU11, HU18 | SPT04 | 3 | 2 | Alta | Media | RF19 | EP05 |
| HU23 | Aviso cuando el estacionamiento se encuentre lleno | Estudiante, docente o personal administrativo | HU16 | SPT04 | 3 | 3 | Alta | Media | RF20, RF21 | EP05 |
| HU24 | Generación de reportes con indicadores del piloto: tiempo promedio de ingreso, cantidad de incidencias y satisfacción del usuario | Personal de seguridad y administración | HU18, HU20 | SPT04 | 6 | 5 | Alta | Media | RF22 | EP06 |

> **Discrepancia a resolver (ver docs/13):** la prioridad del backlog (2.4.1.1.5) y la de las fichas (2.4.1.2.1) no coinciden en varias HU (HU02, HU05, HU12–HU16, HU18, HU22–HU24, entre otras). Para ordenar el trabajo se usan **Sprint + dependencias**, no la prioridad.

## 4. Orden de implementación por dependencias

```
SPT01: HU01 → HU02 → { HU03, HU04, HU05 } ; HU05 → HU06
SPT02: HU06 → HU07 → { HU08, HU09 } ; { HU03, HU09 } → HU10 ; { HU08, HU10 } → HU11 → HU12
SPT03: HU13 → { HU14, HU15 } → HU16 → HU17
       { HU07, HU11 } → HU18 → HU19 ; { HU12, HU18 } → HU20 ; { HU18, HU19, HU20 } → HU21
SPT04: { HU11, HU18 } → HU22 ; HU16 → HU23 ; { HU18, HU20 } → HU24
```
HU13 no tiene dependencia: puede iniciarse en paralelo con SPT02 si el equipo de IA tiene capacidad (ver docs/12, «vertical slice»).

## 5. Matriz de responsables (según fichas)

| HU | Raphael | José | Miladia | Giancarlo |
|---|---|---|---|---|
| HU01 | ● | ● |  |  |
| HU02 | ● |  | ● |  |
| HU03 |  |  | ● | ● |
| HU04 |  | ● |  | ● |
| HU05 | ● |  |  | ● |
| HU06 | ● |  | ● |  |
| HU07 | ● |  |  | ● |
| HU08 |  | ● |  | ● |
| HU09 |  |  | ● | ● |
| HU10 | ● |  |  | ● |
| HU11 | ● | ● |  |  |
| HU12 |  | ● | ● |  |
| HU13 | ● |  |  | ● |
| HU14 |  |  | ● | ● |
| HU15 | ● |  |  | ● |
| HU16 |  | ● |  | ● |
| HU17 | ● |  | ● |  |
| HU18 |  | ● | ● |  |
| HU19 |  | ● |  | ● |
| HU20 | ● | ● |  |  |
| HU21 |  | ● | ● |  |
| HU22 | ● |  | ● |  |
| HU23 |  | ● |  | ● |
| HU24 | ● | ● | ● | ● |

- **Raphael**: 13 HU, 59 puntos: HU01, HU02, HU05, HU06, HU07, HU10, HU11, HU13, HU15, HU17, HU20, HU22, HU24.

- **José**: 12 HU, 48 puntos: HU01, HU04, HU08, HU11, HU12, HU16, HU18, HU19, HU20, HU21, HU23, HU24.

- **Miladia**: 11 HU, 46 puntos: HU02, HU03, HU06, HU09, HU12, HU14, HU17, HU18, HU21, HU22, HU24.

- **Giancarlo**: 14 HU, 65 puntos: HU03, HU04, HU05, HU07, HU08, HU09, HU10, HU13, HU14, HU15, HU16, HU19, HU23, HU24.

Roles Scrum: Product Owner = José Alberto Huaraca Escobar · Scrum Master = Raphael Saimon Caballero Castillo · Scrum Team = Miladia Paloma Villavicencio Huaman y Giancarlo Jesus Condori Yucra.

## 6. Fichas detalladas

### HU01 · Registro de datos personales del usuario mediante el Portal UTP existente

- **Actor (ficha):** Estudiante, docente o personal administrativo
- **Épica / RF:** EP01 / RF01
- **Sprint / iteración:** SPT01 / 1
- **Depende de:** —
- **Estimación:** 3 puntos · 2 día(s)
- **Prioridad:** Alta (backlog) / Alta (ficha)
- **Responsables:** Raphael y José

**Descripción [DOC].** Registrar los datos personales del usuario mediante el Portal UTP existente para asociar su información institucional con el servicio de estacionamiento para VMP.

**Comportamiento del prototipo [DOC]** · Portal UTP · web · actor: estudiante, docente o administrativo

1. El registro se completa en 4 etapas (indicador de pasos visible).
2. Los datos se traen del Portal UTP existente; el usuario NO los reescribe (evita errores).
3. El usuario solo completa lo que el Portal no tiene: tipo de usuario y contacto.
4. Consentimiento obligatorio para el uso de datos e imágenes.
5. Al guardar se crea el perfil del usuario y se pasa al registro de vehículos (HU02).

### HU02 · Registro y vinculación de vehículos al usuario, con un máximo de tres VMP

- **Actor (ficha):** Estudiante, docente o personal administrativo
- **Épica / RF:** EP01 / RF02
- **Sprint / iteración:** SPT01 / 1
- **Depende de:** HU01
- **Estimación:** 4 puntos · 2 día(s)
- **Prioridad:** Muy alta (backlog) / Alta (ficha)
- **Responsables:** Raphael y Miladia

**Descripción [DOC].** Registrar y vincular scooters eléctricos y bicicletas eléctricas al perfil del usuario, con un máximo de tres vehículos por persona.

**Comportamiento del prototipo [DOC]** · Portal UTP · web · actor: usuario registrado

1. Contador visible del límite: máximo 3 VMP por usuario.
2. Formulario con los datos que identifican al vehículo: tipo, marca, modelo, color.
3. Regla de negocio: no se permite un cuarto vehículo.
4. Cada vehículo queda vinculado al perfil y pasa a la etapa de fotografías (HU03).

### HU03 · Carga y almacenamiento de fotografías de referencia de cada vehículo

- **Actor (ficha):** Estudiante, docente o personal administrativo
- **Épica / RF:** EP01 / RF03
- **Sprint / iteración:** SPT01 / 1
- **Depende de:** HU02
- **Estimación:** 4 puntos · 2 día(s)
- **Prioridad:** Alta (backlog) / Alta (ficha)
- **Responsables:** Miladia y Giancarlo

**Descripción [DOC].** Cargar y almacenar fotografías de referencia de cada VMP registrado para usarlas luego en el reconocimiento y validación con IA.

**Comportamiento del prototipo [DOC]** · Portal UTP · web · actor: usuario registrado

1. Una pestaña por vehículo; un check indica que ya tiene foto.
2. Zona de carga: subir archivo o tomar la foto desde el celular.
3. Pautas para que la foto sirva a la IA en la comparación (HU10).
4. Validación previa: el sistema confirma que en la imagen hay un vehículo.
5. La foto se almacena en la nube como referencia del vehículo.

### HU04 · Modificación y eliminación de los datos de los vehículos registrados

- **Actor (ficha):** Estudiante, docente o personal administrativo
- **Épica / RF:** EP01 / RF04
- **Sprint / iteración:** SPT01 / 1
- **Depende de:** HU02
- **Estimación:** 3 puntos · 1 día(s)
- **Prioridad:** Alta (backlog) / Alta (ficha)
- **Responsables:** José y Giancarlo

**Descripción [DOC].** Permitir al usuario modificar los datos de sus vehículos registrados o eliminarlos cuando ya no los use en el servicio.

**Comportamiento del prototipo [DOC]** · Portal UTP · web · actor: usuario registrado

1. Cada vehículo tiene las acciones Editar y Eliminar.
2. Al editar, el cambio se guarda y el QR se actualiza automáticamente.
3. Antes de eliminar se pide confirmación para evitar errores.
4. Regla: no se elimina un vehículo que figura como «dentro» del estacionamiento.

### HU05 · Generación de un código QR único asociado al estudiante y sus vehículos registrados

- **Actor (ficha):** Estudiante, docente o personal administrativo
- **Épica / RF:** EP01 / RF05
- **Sprint / iteración:** SPT01 / 1
- **Depende de:** HU02
- **Estimación:** 3 puntos · 1 día(s)
- **Prioridad:** Muy alta (backlog) / Alta (ficha)
- **Responsables:** Raphael y Giancarlo

**Descripción [DOC].** Generar un código QR único vinculado a la identidad institucional del usuario, que permita identificarlo y consultar los vehículos asociados a su perfil durante el ingreso.

**Comportamiento del prototipo [DOC]** · Portal UTP · web · actor: sistema / usuario registrado

1. El sistema genera automáticamente un QR único por usuario.
2. Se muestra identificador y vigencia del código (ciclo académico).
3. Un solo QR agrupa al usuario y a todos sus vehículos (hasta 3).
4. Seguridad: el QR guarda un token, NO datos personales visibles.
5. El QR queda disponible en la app UTP (HU06).

### HU06 · Visualización del código QR generado para el ingreso con VMP

- **Actor (ficha):** Estudiante, docente o personal administrativo
- **Épica / RF:** EP01 / RF06
- **Sprint / iteración:** SPT01 / 1
- **Depende de:** HU05
- **Estimación:** 2 puntos · 2 día(s)
- **Prioridad:** Alta (backlog) / Alta (ficha)
- **Responsables:** Miladia y Raphael

**Descripción [DOC].** Visualizar el código QR desde la aplicación UTP+ para presentarlo en el lector del punto de acceso destinado a scooters y bicicletas eléctricas.

**Comportamiento del prototipo [DOC]** · App UTP · móvil · actor: usuario registrado

1. Nuevo ícono QR en la barra superior de la app UTP (junto al carné y el correo).
2. QR listo para mostrar en el punto de acceso, sin imprimirlo.
3. Lista de vehículos autorizados vinculados al QR.
4. Aviso de uso personal e intransferible del código.

### HU07 · Lectura del código QR en el punto de acceso destinado a VMP

- **Actor (ficha):** Personal de seguridad
- **Épica / RF:** EP02 / RF07
- **Sprint / iteración:** SPT02 / 2
- **Depende de:** HU06
- **Estimación:** 3 puntos · 2 día(s)
- **Prioridad:** Muy alta (backlog) / Alta (ficha)
- **Responsables:** Raphael y Giancarlo

**Descripción [DOC].** Leer el código QR presentado por el usuario en el acceso para VMP e iniciar la identificación y validación.

**Comportamiento del prototipo [DOC]** · Punto de acceso · tablet + lector · actor: usuario en el ingreso

1. El usuario muestra su QR desde la app UTP frente al lector.
2. Se muestra el estado de los dispositivos del punto de acceso.
3. Lectura exitosa: se obtiene el identificador del QR y la hora.
4. Caso alterno: QR vencido, alterado o inexistente.

### HU08 · Identificación del estudiante y consulta de sus vehículos registrados a partir del QR

- **Actor (ficha):** Personal de seguridad
- **Épica / RF:** EP02 / RF07
- **Sprint / iteración:** SPT02 / 2
- **Depende de:** HU07
- **Estimación:** 4 puntos · 2 día(s)
- **Prioridad:** Muy alta (backlog) / Alta (ficha)
- **Responsables:** José y Giancarlo

**Descripción [DOC].** Identificar al usuario a partir de la información asociada al QR y consultar los scooters y bicicletas eléctricas de su perfil para compararlos con el vehículo que ingresa.

**Comportamiento del prototipo [DOC]** · Punto de acceso · tablet · actor: sistema / personal de seguridad

1. Con el QR se identifica al usuario en la base de datos.
2. Se verifica que la matrícula y el servicio estén vigentes.
3. Se consultan los vehículos vinculados al usuario.
4. Las fotos de referencia quedan listas para la validación.

### HU09 · Captura de una imagen del VMP mediante la cámara de ingreso

- **Actor (ficha):** Personal de seguridad
- **Épica / RF:** EP02 / RF08
- **Sprint / iteración:** SPT02 / 2
- **Depende de:** HU07
- **Estimación:** 4 puntos · 2 día(s)
- **Prioridad:** Muy alta (backlog) / Alta (ficha)
- **Responsables:** Miladia y Giancarlo

**Descripción [DOC].** Capturar una imagen del VMP presentado en el punto de ingreso para disponer de información visual en el reconocimiento automatizado.

**Comportamiento del prototipo [DOC]** · Punto de acceso · cámara de ingreso · actor: sistema

1. La cámara de ingreso se activa después de leer el QR.
2. La IA detecta el vehículo en tiempo real y verifica el encuadre.
3. Se guarda la foto con el ID del QR y la hora.
4. Caso alterno: vehículo fuera de cuadro o mala iluminación.

### HU10 · Comparación mediante inteligencia artificial de la imagen capturada con las fotografías registradas

- **Actor (ficha):** Sistema
- **Épica / RF:** EP02 / RF09
- **Sprint / iteración:** SPT02 / 2
- **Depende de:** HU03, HU09
- **Estimación:** 8 puntos · 3 día(s)
- **Prioridad:** Muy alta (backlog) / Muy alta (ficha)
- **Responsables:** Raphael y Giancarlo

**Descripción [DOC].** Comparar con técnicas de IA la imagen capturada en el ingreso con las fotografías de referencia de los vehículos del usuario identificado por el QR.

**Comportamiento del prototipo [DOC]** · Punto de acceso · módulo IA · actor: sistema (Python · YOLOv8 · OpenCV)

1. Entrada: foto de la cámara de ingreso (HU09) y fotos de referencia del usuario (HU03).
2. La IA calcula un porcentaje de similitud con cada vehículo registrado.
3. Solo se acepta si algún vehículo supera el umbral definido.
4. La comparación se resuelve en segundos para no generar colas.

### HU11 · Validación de correspondencia entre el VMP ingresante y los vehículos asociados al estudiante

- **Actor (ficha):** Sistema
- **Épica / RF:** EP02 / RF10
- **Sprint / iteración:** SPT02 / 2
- **Depende de:** HU08, HU10
- **Estimación:** 6 puntos · 3 día(s)
- **Prioridad:** Muy alta (backlog) / Muy alta (ficha)
- **Responsables:** Raphael y José

**Descripción [DOC].** Validar si el vehículo detectado en el ingreso corresponde a alguno de los VMP registrados por el usuario, usando el resultado de la comparación de imágenes.

**Comportamiento del prototipo [DOC]** · Punto de acceso · tablet · actor: sistema / usuario

1. Mensaje claro y visible para el usuario: puede ingresar.
2. Se muestra cuál de sus vehículos fue reconocido.
3. El ingreso se guarda automáticamente (alimenta HU18).
4. Se dispara la notificación al usuario (HU22).

### HU12 · Rechazo o generación de una alerta ante un vehículo que no coincide con los registros

- **Actor (ficha):** Personal de seguridad
- **Épica / RF:** EP02 / RF11
- **Sprint / iteración:** SPT02 / 2
- **Depende de:** HU11
- **Estimación:** 5 puntos · 3 día(s)
- **Prioridad:** Alta (backlog) / Muy alta (ficha)
- **Responsables:** José y Miladia

**Descripción [DOC].** Generar una alerta cuando el VMP detectado no coincide con los registrados; el personal de seguridad revisa el caso y decide si autoriza o impide el ingreso.

**Comportamiento del prototipo [DOC]** · Punto de acceso · tablet · actor: sistema / personal de seguridad

1. El sistema bloquea el ingreso y muestra el motivo.
2. El personal decide: rechazar o hacer verificación manual.
3. Se clasifica el motivo para el seguimiento (HU20).
4. Se genera una alerta en tiempo real con evidencia fotográfica.

### HU13 · Monitoreo del estado de los espacios de estacionamiento mediante cámaras

- **Actor (ficha):** Personal de seguridad y administración
- **Épica / RF:** EP03 / RF12
- **Sprint / iteración:** SPT03 / 3
- **Depende de:** —
- **Estimación:** 6 puntos · 2 día(s)
- **Prioridad:** Muy alta (backlog) / Alta (ficha)
- **Responsables:** Raphael y Giancarlo

**Descripción [DOC].** Monitorear con cámaras los espacios destinados a VMP para obtener la información visual que determine su estado de ocupación.

**Comportamiento del prototipo [DOC]** · Panel de seguridad · web · actor: personal de seguridad

1. Estado de conexión de todas las cámaras.
2. Cámara general para el pasillo de salida.
3. Cada casilla se marca como libre u ocupada.
4. Monitoreo continuo: 5 zonas × 8 espacios = 40 espacios.

### HU14 · Detección automática de espacios ocupados

- **Actor (ficha):** Sistema
- **Épica / RF:** EP03 / RF13
- **Sprint / iteración:** SPT03 / 3
- **Depende de:** HU13
- **Estimación:** 7 puntos · 2 día(s)
- **Prioridad:** Muy alta (backlog) / Alta (ficha)
- **Responsables:** Miladia y Giancarlo

**Descripción [DOC].** Detectar automáticamente cuándo un scooter eléctrico o bicicleta eléctrica ocupa un espacio y actualizar su condición a ocupado.

**Comportamiento del prototipo [DOC]** · Panel de seguridad · web · actor: sistema (detección con IA)

1. La IA detecta un vehículo dentro de la casilla (ejemplo del prototipo: A-05).
2. Cada detección queda como evento con hora y confianza.
3. Regla para evitar falsos positivos (alguien que solo pasa).
4. El contador de la zona se actualiza al instante.

### HU15 · Detección automática de espacios liberados

- **Actor (ficha):** Sistema
- **Épica / RF:** EP03 / RF14
- **Sprint / iteración:** SPT03 / 3
- **Depende de:** HU13
- **Estimación:** 7 puntos · 2 día(s)
- **Prioridad:** Muy alta (backlog) / Alta (ficha)
- **Responsables:** Raphael y Giancarlo

**Descripción [DOC].** Detectar cuándo un VMP deja de ocupar un espacio y actualizar su condición a disponible según lo captado por las cámaras.

**Comportamiento del prototipo [DOC]** · Panel de seguridad · web · actor: sistema (detección con IA)

1. La IA detecta que la casilla quedó vacía (ejemplo: A-02).
2. Se registra el evento con la hora exacta.
3. Hay un tiempo de confirmación para evitar errores por personas que tapan la cámara.
4. La liberación se asocia a la salida del usuario (HU19).

### HU16 · Actualización del estado de los espacios en la base de datos en tiempo real

- **Actor (ficha):** Sistema
- **Épica / RF:** EP03 / RF15
- **Sprint / iteración:** SPT03 / 3
- **Depende de:** HU14, HU15
- **Estimación:** 4 puntos · 2 día(s)
- **Prioridad:** Muy alta (backlog) / Alta (ficha)
- **Responsables:** José y Giancarlo

**Descripción [DOC].** Actualizar en la base de datos el estado de cada espacio (ocupado o disponible) según el monitoreo automatizado.

**Comportamiento del prototipo [DOC]** · Panel de seguridad · web · actor: sistema (base de datos en la nube)

1. Indicador de sincronización con la base de datos.
2. Se muestra el recorrido del dato desde la cámara hasta las pantallas.
3. Los totales se recalculan con cada cambio.
4. Ejemplo: fila A-02 cambió a «Libre» (viene de HU15).

### HU17 · Visualización de espacios ocupados y disponibles en el panel administrativo

- **Actor (ficha):** Personal de seguridad y administración
- **Épica / RF:** EP04 / RF16
- **Sprint / iteración:** SPT03 / 3
- **Depende de:** HU16
- **Estimación:** 4 puntos · 2 día(s)
- **Prioridad:** Alta (backlog) / Alta (ficha)
- **Responsables:** Raphael y Miladia

**Descripción [DOC].** Mostrar en un panel administrativo el estado de los espacios para que el personal autorizado identifique cuáles están ocupados y cuáles disponibles. La vista detallada es restringida.

**Comportamiento del prototipo [DOC]** · Panel de seguridad · web · actor: personal de seguridad y administrativo

1. Indicadores generales de ocupación.
2. Ubicación exacta de cada espacio, por zona.
3. Detalle de cada espacio al pasar el cursor.
4. Filtro por zona.
5. Esta vista solo la ven seguridad y administración (RF21).

### HU18 · Registro de los movimientos de ingreso de estudiantes y sus VMP

- **Actor (ficha):** Personal de seguridad y administración
- **Épica / RF:** EP04 / RF17
- **Sprint / iteración:** SPT03 / 3
- **Depende de:** HU07, HU11
- **Estimación:** 3 puntos · 1 día(s)
- **Prioridad:** Muy alta (backlog) / Alta (ficha)
- **Responsables:** José y Miladia

**Descripción [DOC].** Registrar los movimientos de ingreso con la información necesaria para identificar al usuario, el vehículo y la fecha y hora.

**Comportamiento del prototipo [DOC]** · Panel administrativo · web · actor: sistema / personal administrativo

1. Resumen del día: total, autorizados y rechazados.
2. Registro automático con fecha, hora, usuario, vehículo y resultado de la IA.
3. Evidencia fotográfica asociada a cada movimiento (trazabilidad).
4. Los intentos fallidos también se guardan para auditoría.

### HU19 · Registro de los movimientos de salida de estudiantes y sus VMP

- **Actor (ficha):** Personal de seguridad y administración
- **Épica / RF:** EP04 / RF17
- **Sprint / iteración:** SPT03 / 3
- **Depende de:** HU18
- **Estimación:** 3 puntos · 1 día(s)
- **Prioridad:** Alta (backlog) / Alta (ficha)
- **Responsables:** José y Giancarlo

**Descripción [DOC].** Registrar los movimientos de salida conservando usuario, vehículo y fecha y hora de salida para mantener la trazabilidad.

**Comportamiento del prototipo [DOC]** · Panel administrativo · web · actor: sistema / personal administrativo

1. Resumen: salidas del día y vehículos que siguen dentro.
2. Salida automática a partir de la detección del espacio liberado.
3. Permanencia calculada (dato útil para los reportes).
4. Control de vehículos que no salieron al cierre.

### HU20 · Registro y seguimiento de incidencias relacionadas con el acceso de VMP

- **Actor (ficha):** Personal de seguridad y administración
- **Épica / RF:** EP04 / RF17
- **Sprint / iteración:** SPT03 / 3
- **Depende de:** HU12, HU18
- **Estimación:** 4 puntos · 2 día(s)
- **Prioridad:** Alta (backlog) / Alta (ficha)
- **Responsables:** Raphael y José

**Descripción [DOC].** Registrar y consultar incidencias de acceso de VMP, como los casos en que el vehículo detectado no coincide con los registros del usuario.

**Comportamiento del prototipo [DOC]** · Panel de seguridad · web · actor: personal de seguridad y administrativo

1. Lista de incidencias por estado: abierta, en revisión, cerrada.
2. Detalle con evidencia fotográfica y responsable.
3. Línea de tiempo con cada acción tomada.
4. Cierre de la incidencia con comentario final.

### HU21 · Consulta y filtrado del historial de movimientos por usuario, fecha y vehículo

- **Actor (ficha):** Personal de seguridad y administración
- **Épica / RF:** EP04 / RF18
- **Sprint / iteración:** SPT03 / 3
- **Depende de:** HU18, HU19, HU20
- **Estimación:** 4 puntos · 1 día(s)
- **Prioridad:** Alta (backlog) / Alta (ficha)
- **Responsables:** Miladia y José

**Descripción [DOC].** Consultar y filtrar el historial de movimientos por usuario, fecha y vehículo para facilitar la revisión y trazabilidad de los accesos.

**Comportamiento del prototipo [DOC]** · Panel administrativo · web · actor: personal administrativo

1. Filtros por usuario, rango de fechas, vehículo y tipo de movimiento.
2. Se muestra la cantidad de resultados y el criterio aplicado.
3. Exportación para auditorías o reclamos.
4. Filtros combinables para encontrar un caso puntual.

### HU22 · Notificación de confirmación del ingreso del VMP

- **Actor (ficha):** Estudiante, docente o personal administrativo
- **Épica / RF:** EP05 / RF19
- **Sprint / iteración:** SPT04 / 4
- **Depende de:** HU11, HU18
- **Estimación:** 3 puntos · 2 día(s)
- **Prioridad:** Alta (backlog) / Media (ficha)
- **Responsables:** Raphael y Miladia

**Descripción [DOC].** Notificar al usuario la confirmación del ingreso una vez completada la validación y registrado el movimiento.

**Comportamiento del prototipo [DOC]** · App UTP · móvil · actor: usuario

1. Notificación push inmediata al validar el ingreso.
2. Historial de avisos dentro de la app UTP.
3. También se avisa si el ingreso fue rechazado.
4. Opción de reportar si el usuario no reconoce el ingreso (seguridad).

### HU23 · Aviso cuando el estacionamiento se encuentre lleno

- **Actor (ficha):** Estudiante, docente o personal administrativo
- **Épica / RF:** EP05 / RF20, RF21
- **Sprint / iteración:** SPT04 / 4
- **Depende de:** HU16
- **Estimación:** 3 puntos · 3 día(s)
- **Prioridad:** Alta (backlog) / Media (ficha)
- **Responsables:** José y Giancarlo

**Descripción [DOC].** Mostrar un aviso cuando todos los espacios destinados a VMP estén ocupados.

**Comportamiento del prototipo [DOC]** · App UTP · móvil · actor: usuario

1. Aviso push cuando la ocupación llega al 100 %.
2. Estado general del estacionamiento visible en la app.
3. El usuario puede suscribirse al aviso de espacio libre.
4. No se muestra el mapa detallado al usuario (RF21).

### HU24 · Generación de reportes con indicadores del piloto: tiempo promedio de ingreso, cantidad de incidencias y satisfacción del usuario

- **Actor (ficha):** Personal de seguridad y administración
- **Épica / RF:** EP06 / RF22
- **Sprint / iteración:** SPT04 / 4
- **Depende de:** HU18, HU20
- **Estimación:** 6 puntos · 5 día(s)
- **Prioridad:** Alta (backlog) / Media (ficha)
- **Responsables:** Raphael y José y Miladia y Giancarlo

**Descripción [DOC].** Generar reportes con los indicadores del piloto (tiempo promedio de ingreso, cantidad de incidencias y satisfacción) para evaluar el servicio.

**Comportamiento del prototipo [DOC]** · Panel administrativo · web · actor: personal administrativo

1. Muestra los indicadores del piloto definidos en la etapa Testear.
2. Evolución diaria del tiempo de ingreso.
3. Resultados de la encuesta de satisfacción.
4. Selección del periodo y exportación del reporte.
