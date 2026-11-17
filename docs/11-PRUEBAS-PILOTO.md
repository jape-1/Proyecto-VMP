# 11 · Pruebas y piloto

> **[DOC]**: el piloto en la Torre Arequipa mide **tiempo promedio de ingreso**, **tasa de error en la validación**, **número de incidencias** y **nivel de satisfacción**; el resultado ajusta formulario, flujo de validación y parámetros del modelo; la IA «debe evaluarse con pruebas técnicas y de usuario (viabilidad, precisión y desempeño en condiciones reales)».
> **[PROPUESTA]**: estrategia de pruebas, casos, datos de prueba, criterios de salida y plan de piloto. Los **umbrales de aceptación numéricos no existen en el Avance**: se fijan con el equipo tras medir una línea base; aquí aparecen como `<X>` a completar.

## 1. Pirámide de pruebas

| Nivel | Qué prueba | Herramienta | Dónde corre |
|---|---|---|---|
| Unitarias | Reglas puras: límite de 3 VMP, vigencia de QR, estados de sesión, zonas de decisión, estabilidad de casillas | `pytest` | CI (cada PR) |
| Integración | Módulo + BD real (Postgres de CI) + Redis: servicios y repositorios, eventos | `pytest` + `httpx` + testcontainers/servicios de Actions | CI |
| Contrato | Esquemas de eventos y de API estables (JSON Schema / OpenAPI) | `schemathesis` o tests de esquema | CI |
| Autorización | Cada endpoint × cada rol (matriz) | `pytest` parametrizado | CI |
| E2E panel | Flujos del guardia/administrador | `Playwright` | CI nocturno / pre-release |
| IA offline | Precisión/recall por clase; falsos rechazos/aceptaciones sobre pares; casillas sobre clips | `ultralytics val`, scripts propios, `scikit-learn` | Manual/pipeline de entrenamiento |
| Rendimiento | Latencia de validación y carga del panel | `locust`/`k6` + cronómetro en punto de acceso | Pre-piloto |
| Seguridad | Bandit, pip-audit, ZAP básico, revisión de roles | CI + manual | CI / pre-release |
| UAT | Usuarios reales y guardias | Guion + encuesta | Piloto |

## 2. Pruebas de reglas de negocio (obligatorias)

Cada fila es al menos un test automatizado con nombre `test_<regla>`.

| ID | Regla | Caso | Esperado |
|---|---|---|---|
| T-01 | BR-01 / RF02 | Usuario con 3 VMP activos agrega un cuarto | `409 LIMITE_VMP_ALCANZADO`; nada guardado |
| T-02 | BR-01 | Usuario con 3 VMP da de baja uno y agrega otro | Permitido |
| T-03 | BR-01 (concurrencia) | Dos solicitudes simultáneas crean el 3.º y 4.º | Solo una prospera |
| T-04 | BR-02 | Foto sin vehículo | `FOTO_SIN_VEHICULO`; no se guarda |
| T-05 | BR-03 | Eliminar vehículo con sesión `en_curso` | `409 VEHICULO_DENTRO_NO_ELIMINABLE` |
| T-06 | BR-04 | Editar vehículo | QR/lista asociada actualizada |
| T-07 | BR-05/06 | Generar QR dos veces | Solo uno `activo`; el anterior `revocado` |
| T-08 | BR-07 | QR expirado / revocado / alterado / inexistente | Códigos `QR_EXPIRADO`, `QR_REVOCADO`, `QR_ALTERADO`, `QR_INEXISTENTE`; **ninguna sesión creada** (o creada como intento fallido según decisión #5) |
| T-09 | BR-08 | Usuario con matrícula `inactivo` | `USUARIO_INACTIVO` |
| T-10 | BR-09 | Capturar foto sin leer QR | Rechazado (`SESION_NO_ENCONTRADA`) |
| T-11 | BR-11 | 3 vehículos, el 2.º supera umbral | Validado con `id_vehiculo` = 2.º |
| T-12 | BR-14 | Ninguno supera `U_BAJO` | Rechazado + incidencia `vehiculo_no_coincide` con evidencia |
| T-13 | zona gris | Puntaje entre `U_BAJO` y `U_ALTO` | Estado `verificar`; no aprueba solo |
| T-14 | BR-15 | Intento rechazado | Queda `sesion` con `resultado_validacion=rechazado` y aparece en historial |
| T-15 | BR-17 | Persona pasa frente a casilla < N cuadros | Casilla sigue libre |
| T-16 | BR-18 | Vehículo sale y persona tapa la cámara < T | Casilla sigue ocupada |
| T-17 | BR-19 | Evento de liberación | Sesión `finalizada`, `fecha_hora_salida` set, espacio `disponible` |
| T-18 | BR-20 | Cambio de casilla | Totales de zona recalculados |
| T-19 | BR-21 | Rol `usuario` llama `GET /espacios` | `403` |
| T-20 | BR-21 | Payload de notificaciones | No contiene `codigo_espacio` ni zona |
| T-21 | BR-22 | Ingreso validado | Notificación `confirmacion_ingreso` creada; rechazado → `ingreso_rechazado` |
| T-22 | BR-24 | Ocupación llega a 100 % | Un solo evento `parking.zona.llena` (no repite mientras siga lleno) |
| T-23 | idempotencia | Mismo `event_id` dos veces | Procesado una vez |
| T-24 | unicidad | Dos sesiones vigentes en el mismo espacio | La BD lo impide |
| T-25 | BR-26 | Cierre del día con sesiones abiertas | Aparecen en `pendientes-cierre` |
| T-26 | BR-28 | Filtros combinados | Resultado = intersección; exporta el mismo conjunto |
| T-27 | contingencia | `ia_service` caído | `IA_NO_DISPONIBLE`, flujo manual funciona, queda incidencia/auditoría |
| T-28 | token | Token nunca en claro | Búsqueda en BD y logs del test: sin coincidencias |

### Matriz de autorización (extracto)
| Endpoint | usuario | seguridad | administrador | sin token |
|---|---|---|---|---|
| `GET /espacios` | 403 | 200 | 200 | 401 |
| `POST /acceso/qr` | 403 | 200 | 403 | 401 |
| `GET /reportes/piloto` | 403 | 403 | 200 | 401 |
| `GET /usuarios/me/vehiculos` | 200 | 403 | 403 | 401 |
| `PUT /usuarios/me/vehiculos/{id}` ajeno | 404/403 | — | — | 401 |

## 3. Datos de prueba

- **Seeds** de docs/05 §6 (usuarios, vehículos, zonas, espacios, personal).
- **Imágenes sintéticas/neutrales** para tests automáticos (no personas). Un conjunto pequeño versionado en `backend/tests/data/` (< 5 MB).
- **Clips de video** de casillas (en `ia_service/tests/data/`, o descarga en CI desde S3 por tamaño): libre→ocupada, ocupada→libre, persona que pasa, persona tapando, noche, lluvia.
- **Pares de comparación**: por vehículo, referencia + ingresos “mismo vehículo” (positivos) y “otro vehículo” (negativos, incluidos casi idénticos).
- **Simulador de cámaras** (`simulador_camaras`): reproduce un video o carpeta de imágenes como si fuera RTSP/HTTP, con *seed* y velocidad configurable para pruebas deterministas.

## 4. Pruebas de IA (offline)

| Prueba | Método | Reporte |
|---|---|---|
| Detección por clase | `model.val(split="test")` | P, R, mAP50, mAP50-95 **por clase** + matriz de confusión |
| Línea base (E1) | YOLO preentrenado en COCO (`bicycle`/`motorcycle`) | Cualitativa + tabla de coincidencias en la Fase 1 (`docs/16` §6.3); mAP solo con correspondencia de clases explícita |
| Comparación (E4/E5) | Pares positivos/negativos → curva P–R y ROC; FN y FP a umbrales candidatos | Tabla de umbrales con FN/FP |
| Robustez | Mismo conjunto con brillo/contraste/blur/rotación leve | Caída de métricas |
| Latencia | 100 inferencias, medir p50/p95 en la CPU/GPU objetivo | Tabla ms |
| Casillas (E6) | Clips etiquetados cuadro a cuadro | Errores por hora de video; retraso medio de detección de cambio |

Reglas: el set `test` se usa **una vez por experimento**; los resultados se guardan en `ia_service/resultados/E*.md` con fecha, commit, dataset y parámetros. **Ninguna cifra se cita en documentos del proyecto hasta que exista ese archivo.**

## 5. Rendimiento

| Medida | Cómo | Criterio |
|---|---|---|
| Tiempo QR→resultado (extremo a extremo) | Cronometrar en el punto de acceso con 30–50 ingresos reales/simulados | Objetivo `<X>` s, definido con la UTP tras la línea base |
| Carga del panel con 40 espacios + 5 cámaras | k6 con 10 usuarios simultáneos | Sin errores; refresco < `<X>` s |
| Eventos por segundo (5 cámaras) | Simulador | Sin retraso acumulado en Redis |

## 6. Plan del piloto **[PROPUESTA]**

### 6.1 Fases
| Fase | Duración (a definir) | Qué pasa | Salida |
|---|---|---|---|
| 0 · Preparación | — | Instalar punto de acceso y cámaras; consentimientos; capacitación a seguridad (panel) y difusión (cómo registrar VMP y ubicar el QR) | Checklist de instalación |
| 1 · Línea base | 1–2 semanas | Medir **tiempo de ingreso manual actual** y errores; encuesta inicial | Línea base de indicadores |
| 2 · Modo sombra | — | Sistema decide en silencio; el proceso manual sigue | Concordancia IA vs. humano |
| 3 · Modo asistido | — | IA propone, guardia confirma | Tasa de override, tiempos |
| 4 · Modo automático supervisado | — | IA valida verdes; guardia atiende grises/rojos | Indicadores finales |
| 5 · Cierre | 1 semana | Reporte (HU24), lecciones, decisión de escalar | Informe del piloto |

### 6.2 Muestra y participantes
Grupo reducido de usuarios con VMP (estudiantes, docentes, administrativos) y todo el personal de seguridad de los turnos involucrados. Tamaño de muestra **[PENDIENTE]**; registrar la composición por tipo de usuario y de VMP.

### 6.3 Indicadores y fórmulas

| Indicador | Definición operativa **[PROPUESTA]** | Fuente | Comparación |
|---|---|---|---|
| Tiempo promedio de ingreso | Media de (resultado de validación − lectura del QR) en segundos; en línea base: (registro manual completado − llegada) | `sesion` + `evento_deteccion_ia`; cronómetro manual en línea base | Antes vs. después |
| Tasa de error en validación | (Falsos rechazos + falsas aceptaciones) / total de validaciones con verdad conocida | Decisión de IA vs. decisión final del guardia + auditoría de muestra | Por modo y por tipo de VMP |
| — Falso rechazo | Autorizado rechazado por la IA (el guardia lo aprueba manualmente) | `incidencia` + `override` | |
| — Falsa aceptación | Ajeno aceptado (detectado por auditoría de muestra o reclamo) | Auditoría manual de N casos/semana | Prioridad de seguridad |
| Número de incidencias | Total y por tipo (`vehiculo_no_coincide`, `sin_espacio_disponible`, `error_lectura_qr`, `otro`) | `incidencia` | Por semana |
| Nivel de satisfacción | Promedio de encuesta breve (facilidad, espera percibida, experiencia general; escala 1–5) | `encuesta_satisfaccion` | Antes vs. después |
| Exactitud de casillas | Coincidencia entre estado del sistema y conteo manual en muestras horarias | Conteo manual vs. `espacio.estado` | |
| Disponibilidad | % de tiempo con IA y cámaras operativas | Logs/CloudWatch | |

### 6.4 Criterios de avance entre modos **[PENDIENTE: definir con el PO]**
Ejemplo de forma (no de valores): «pasar de sombra a asistido cuando la concordancia IA–humano sea ≥ `<X>` % en `<N>` validaciones y la falsa aceptación observada sea ≤ `<Y>`». Los valores los decide el equipo con datos.

### 6.5 Encuesta de satisfacción (borrador)
1. ¿Qué tan fácil fue registrar tu vehículo? (1–5)
2. ¿Cómo percibiste el tiempo de espera al ingresar? (1–5)
3. ¿Cómo calificas tu experiencia general? (1–5)
4. ¿Qué mejorarías? (texto breve, opcional)

### 6.6 Riesgos del piloto
| Riesgo | Mitigación |
|---|---|
| Cámaras con mala luz/ángulo | Prueba de sitio previa; ajustar posición; datos nocturnos |
| Baja adopción (usuarios no registran) | Capacitación + difusión; registro asistido el primer día |
| IA con errores en horas pico | Modo asistido primero; guardia siempre con salida manual |
| Reclamos por privacidad | Consentimiento claro; retención corta; contacto responsable |
| Sin línea base | Medirla en la fase 1 sin falta; sin ella no hay comparación |
| Cambio de personal de seguridad | Capacitación por turno; guía rápida impresa |

## 7. Definición de «hecho» (DoD) por HU **[PROPUESTA]**

- [ ] Cumple **todos** los comportamientos numerados del prototipo de la HU (docs/03).
- [ ] Reglas de negocio asociadas con prueba automática (sección 2).
- [ ] Migración Alembic revisada (y reversible o documentada).
- [ ] Endpoints documentados en OpenAPI y reflejados en docs/07 si cambian.
- [ ] Autorización por rol probada.
- [ ] Sin secretos ni datos personales en logs/tests.
- [ ] Lint (`ruff`), seguridad (`bandit`) y pruebas en verde en CI.
- [ ] Revisión de otro integrante.
- [ ] Demo corta contra el prototipo del Avance.
- [ ] Tarjeta de Trello movida a «completado».
