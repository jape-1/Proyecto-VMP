# 01 · Contexto del proyecto

> Fuentes: Avance 1, Avance 2 (93 págs.), material de clase S04 sesión 7 (Henríquez Taboada), y entregables propios posteriores (arquitectura/ER, DevOps, IA, ML). Etiquetas: **[DOC]** viene de los avances; **[PROPUESTA]** lo propusimos nosotros; **[PENDIENTE]** está abierto.

## 1. Identificación

| Campo | Valor |
|---|---|
| Universidad | Universidad Tecnológica del Perú (UTP), Sede Centro, **Torre Arequipa** |
| Curso | Innovación y Transformación Digital · ciclo **2026-II** |
| Docente | Henríquez Taboada, Héctor Hernán (MSc.) |
| Entregable | Proyecto final: Avance 1 y Avance 2 («Avance Proyecto Final 2», 93 páginas) |

### Equipo

| Integrante | Rol Scrum |
|---|---|
| Caballero Castillo, Raphael Saimon | Scrum Master |
| Condori Yucra, Giancarlo Jesus | Scrum Team |
| Huaraca Escobar, José Alberto | Product Owner |
| Villavicencio Huaman, Miladia Paloma | Scrum Team |

Responsabilidad de los roles **[DOC]**: el PO representa las necesidades de los usuarios y define prioridades; el SM facilita Scrum y coordina; el Scrum Team analiza requerimientos y desarrolla las actividades.

## 2. Idea innovadora [DOC]

Mejorar el actual método de registro de estacionamiento para VMP de la UTP Sede Centro Torre Arequipa mediante un servicio de estacionamiento implementado con IA: **ingreso con QR** que contiene los datos del vehículo y del estudiante/docente/personal, mientras que **la IA monitorea la entrada y la salida** de los vehículos.

> Nota de evolución: el Avance 1 decía que la IA solo monitoreaba la **salida**. El Avance 2 corrigió: la IA también valida el **ingreso** (compara foto capturada con foto registrada). Prevalece el Avance 2.

## 3. Problema [DOC]

El registro de ingreso/salida de VMP es **manual**. Deficiencias identificadas:

1. **Colas y demoras:** cada ingreso toma tiempo; hay aglomeraciones al inicio y fin de clases.
2. **Ambigüedad en el control:** no hay método preciso ni automatizado para verificar qué vehículo pertenece a qué usuario, ni control confiable de espacios ocupados/disponibles.
3. **Falta de trazabilidad:** sin registro digital estructurado es difícil auditar quién ingresó, cuándo y con qué vehículo; se complica gestionar pérdidas, confusiones o uso indebido del espacio.
4. **Experiencia negativa del usuario:** tiempo perdido y desorganización generan insatisfacción en estudiantes, docentes y administrativos que usan VMP a diario.

**Point of View (Design Thinking):** «Los usuarios de VMP en la Torre Arequipa necesitan una forma rápida y confiable de registrar el ingreso y salida de su vehículo, porque el sistema manual actual genera colas, ambigüedad sobre la propiedad del vehículo y falta de trazabilidad ante incidencias».

**How Might We:** ¿Cómo podríamos automatizar el registro y control de VMP para reducir los tiempos de espera y garantizar que cada vehículo esté validado con su propietario?

## 4. Delimitación de VMP [DOC]

Se consideran VMP **principalmente los vehículos eléctricos de uso personal y dimensiones reducidas**: **motos, scooters y bicicletas eléctricas**, para desplazamiento individual de la comunidad universitaria.

> Ojo para el código **[PENDIENTE]**: el texto del Avance usa distintas listas según la sección (motos+scooters+bicicletas eléctricas en la delimitación; solo scooters y bicicletas eléctricas en HU02/HU08/HU14; bicicleta, bicicleta eléctrica, scooter eléctrico y moto eléctrica en el ER). Ver `docs/13` #1.

## 5. Producto [DOC]

Sistema inteligente de estacionamiento para VMP que automatiza el registro de ingreso y salida con QR e IA.

- Cada usuario tiene un **QR vinculado a sus datos y a los de su(s) vehículo(s)**.
- Al ingresar, el sistema **captura una foto del vehículo** y la IA la **compara con la imagen registrada** previamente en el formulario del usuario.
- Un sistema de IA **monitorea** también el estado de cada casilla (ocupada/libre) y actualiza la disponibilidad automáticamente.
- Objetivos: reducir tiempos de espera, minimizar errores humanos, validar la identidad del vehículo, mejorar la gestión del estacionamiento.

### Objetivo del proyecto y visión (Scrum, fase Inicio) [DOC]

- **Visión:** proporcionar a la comunidad UTP Torre Arequipa un servicio inteligente de estacionamiento para motos, scooters y bicicletas eléctricas que agilice el registro de ingreso, mejore el control de vehículos y optimice la gestión de espacios, integrando QR, reconocimiento de imágenes con IA y monitoreo por cámaras; reduciendo demoras, fortaleciendo la trazabilidad y facilitando la supervisión de seguridad y administración.
- **Objetivo:** desarrollar una propuesta de servicio inteligente de estacionamiento (QR + IA + cámaras) para agilizar ingreso y salida, mejorar el control de acceso, optimizar la gestión de espacios y fortalecer la trazabilidad.

## 6. Mercado y usuarios [DOC]

Miembros de la comunidad UTP de la Torre Arequipa que usan VMP: **estudiantes de pregrado y posgrado, docentes, personal administrativo y trabajadores**. El segmento más beneficiado: quienes hoy pasan por un registro manual y lento.

Modelo de negocio (conclusiones del Avance 2): **la UTP es el cliente que financia el servicio**; la **comunidad universitaria es usuaria sin costo**. Propuesta de valor: ingreso rápido, verificación del vehículo con IA y trazabilidad de movimientos. (La sección Lean Startup del Avance 2 está en imágenes; no se pudo extraer su texto.)

### Actores del sistema

| Actor | Qué hace | Por dónde interactúa |
|---|---|---|
| Usuario UTP (estudiante / docente / administrativo) | Se registra, registra hasta 3 VMP con foto, muestra su QR, recibe notificaciones | Portal UTP (web, simulado), App UTP (móvil, simulada) |
| Personal de seguridad | Opera el punto de acceso, ve el panel de espacios, resuelve incidencias | Tablet + lector en el acceso; panel web |
| Personal administrativo | Consulta historial, filtra movimientos, genera reportes del piloto | Panel web |
| Sistema (IA) | Detecta vehículos, compara, detecta ocupación/liberación | Servicio de IA + cámaras |

## 7. Cómo se implementaría (Transformación Digital) [DOC]

Fases del Avance 2 §1.5:

1. **Digitalización del registro:** reemplazar el formato en papel por un formulario digital en el **Portal UTP**; máximo 3 VMP por usuario, cada uno con foto de referencia; el sistema genera un **QR único y personal** disponible en la **app UTP** (sin imprimir).
2. **Automatización con IA y cámaras:** Python + **YOLOv8 (Ultralytics)** para detección en tiempo real + **OpenCV** para procesar y comparar imágenes. Dos tipos de cámara:
   - **Cámara de ingreso:** al escanear el QR captura foto del vehículo y la compara contra los vehículos registrados del perfil; valida en segundos que corresponde a uno de los tres autorizados.
   - **Cámaras de zona/espacio:** monitorean continuamente cada casilla; ocupada al detectar vehículo estacionado, liberada al retirarse.
3. **Centralización en la nube:** usuarios, vehículos, estado de espacios, horarios y incidencias en una BD en la nube conectada al Portal y la App UTP. **Solo seguridad y administrativos** ven el panel con la ubicación exacta de cada espacio; los usuarios reciben notificaciones (confirmación de ingreso, alerta de estacionamiento lleno).
4. **Capacitación y adopción:** breve capacitación al personal de seguridad (panel) y difusión a la comunidad sobre cómo registrar VMP y ubicar su QR.
5. **Piloto y escalamiento:** primero en la Torre Arequipa midiendo **tiempo promedio de ingreso, número de incidencias y satisfacción**; luego evaluar otras torres/sedes.

Marco conceptual: IBM (2024) define la transformación digital como iniciativa que incorpora tecnología digital en todas las áreas de una organización para permitir innovación continua y orientada al usuario; el proyecto se ubica sobre todo en los dominios de **procesos** y **experiencia del cliente**, con un componente de **producto**. Tecnologías: digitalización + QR, app móvil/web, IoT (cámaras IP), IA/visión por computadora, nube, automatización.

## 8. Design Thinking aplicado [DOC]

| Etapa | Resultado |
|---|---|
| Empatizar | Encuestas breves y entrevistas en horas pico (inicio/fin de clases) + observación directa del registro manual. Problemas a validar: demoras, dificultad para verificar propiedad, preocupación por seguridad. |
| Definir | POV y HMW (arriba). |
| Idear | 4 alternativas: (a) checklist digital para seguridad, (b) tarjetas RFID, (c) reconocimiento biométrico, (d) **QR personal + IA de reconocimiento vehicular** ← elegida. Razón: integra identificación digital del usuario con validación visual del vehículo y aprovecha la infraestructura digital existente de la UTP. RFID no verifica el vehículo físico; biometría exige equipamiento, costo y protección de datos. |
| Prototipar | Prototipo de baja fidelidad: mockup del formulario de registro (hasta 3 VMP con foto) y simulación del QR en la app UTP; luego 24 prototipos (uno por HU). |
| Testear | Piloto con un grupo reducido; indicadores abajo. Los resultados ajustan formulario, flujo de validación y parámetros del modelo. |

La elección QR+IA es **una propuesta de diseño que debe evaluarse con pruebas técnicas y de usuario** (viabilidad, precisión y desempeño en condiciones reales).

## 9. Indicadores del piloto [DOC]

| Indicador | Qué mide | Dónde se materializa |
|---|---|---|
| Tiempo promedio de ingreso | Duración del ingreso nuevo frente al manual (cuando existan mediciones de ambos) | `REPORTE_PILOTO.tiempo_promedio_ingreso_seg`, HU24 |
| Tasa de error en la validación | Frecuencia con que el sistema identifica mal un vehículo o no reconoce uno autorizado | Falsos rechazos y falsas aceptaciones (docs/06, docs/11) |
| Número de incidencias | Problemas de ingreso, identificación y control | `REPORTE_PILOTO.total_incidencias` |
| Nivel de satisfacción | Encuesta breve: facilidad de uso, espera percibida, experiencia general | `REPORTE_PILOTO.nivel_satisfaccion_promedio` |

## 10. Kanban (estado reportado) [DOC]

El tablero (Trello) organiza los **22 requerimientos** (RF01–RF22). Estado reportado en las conclusiones del Avance 2: **4 completados, 5 en revisión, 3 en progreso, 1 bloqueado, 9 planificados**. El bloqueado es la **detección con IA**, «el componente más complejo del proyecto».

## 11. Estado actual (a la fecha de redacción)

- Entregado: Avance 1, Avance 2 (arquitectura, ER de 12 entidades, 24 prototipos de baja fidelidad, backlog, estimaciones), documento de arquitectura/ER, ciclo DevOps, documentos y presentaciones de IA y de ML.
- Al escribir este documento no existía código implementado. **[PENDIENTE]** confirmar con el equipo si el código será un prototipo funcional de clase o un sistema real; el roadmap (`docs/12`) asume prototipo funcional con UTP simulada.

## 12. Glosario

| Término | Definición en este proyecto |
|---|---|
| VMP | Vehículo de movilidad personal eléctrico: moto, scooter o bicicleta eléctrica |
| Portal UTP / App UTP | Sistemas existentes de la UTP (externos; en el proyecto están **simulados**). La HU06 los llama también «aplicación UTP+» |
| Conector / Adaptador UTP | Único componente que «sabe» de la UTP; si hay acceso real solo cambia él |
| Punto de acceso | Tablet + lector de QR + cámara de ingreso en la entrada del estacionamiento de VMP |
| Cámara de ingreso | Toma la foto del VMP al escanear el QR |
| Cámara de zona | Vigila varias casillas; alimenta ocupación/liberación |
| Casilla / espacio | Plaza individual (`A-01`, `A-05`…) dentro de una zona |
| Sesión de estacionamiento | Una visita completa: del intento de ingreso hasta la salida. Tabla central del modelo |
| Evento de detección | Cada cosa que la IA «ve» (validación de ingreso, ocupación, liberación) con imagen y confianza |
| Score de confianza | Qué tan seguro está el modelo (0–1), p. ej. 0.91 |
| Similitud | Porcentaje de parecido entre la foto capturada y cada foto de referencia |
| Umbral | Puntaje mínimo de similitud para validar. Es el «dial» entre falso rechazo y falsa aceptación |
| Falso rechazo (FN) | Se rechaza a un usuario autorizado: cola y molestia |
| Falsa aceptación (FP) | Entra un vehículo ajeno: riesgo de seguridad |
| Incidencia | Excepción que requiere intervención humana (vehículo no coincide, sin espacio, error de lectura de QR, otro) |
| Piloto | Despliegue inicial en la Torre Arequipa para medir indicadores |
| Modo sombra / asistido / automático | Etapas **[PROPUESTA]** del piloto: la IA decide en silencio → propone y el guardia confirma → actúa sola con revisión humana de incidencias |
| mAP, IoU, precisión, recall | Métricas de detección de objetos (ver docs/06) |
| Monolito modular | Una sola aplicación y una BD, organizada por dominios de negocio |

## 13. Fuentes de verdad y su prioridad

1. **Avance 2** (mas reciente) > **Avance 1** donde se contradicen.
2. Diagramas en Lucidchart (ER y arquitectura) = esquema de datos vigente. Si el código necesita algo distinto, se propone el cambio (docs/13).
3. Estos `.md` son una **derivación** de lo anterior; si hay conflicto, gana el Avance 2 y se corrige el `.md`.
