# 06 · Servicio de IA y Machine Learning

> **[DOC]** del Avance 2: Python + YOLOv8 (Ultralytics) + OpenCV; dos tipos de cámara (ingreso y zona); comparación contra los vehículos registrados; detección de ocupación y liberación; evidencia con `score_confianza`.
> **[PROPUESTA]** todo lo demás (clases, datasets, experimentos, parámetros iniciales, modos del piloto). **Regla de oro:** ninguna métrica se afirma sin haberse medido sobre un conjunto de prueba. Los valores numéricos de este archivo son **puntos de partida a calibrar**, no resultados.

## 1. Qué hace la IA en este proyecto

| # | Tarea | Disparador | Entrada | Salida | HU |
|---|---|---|---|---|---|
| T1 | **Validar ingreso** (identidad del VMP) | Evento `ia.validacion.solicitada` (foto subida tras leer el QR) | Foto del VMP en el acceso + fotos de referencia de los ≤3 VMP del usuario | Puntaje de similitud por vehículo, mejor candidato, `score_confianza` | HU09, HU10, HU11 |
| T2 | **Detectar ocupación** de casilla | Flujo continuo de la cámara de zona | Cuadros de video + ROI de cada casilla | Evento `ocupado` por casilla (tras estabilidad) | HU13, HU14 |
| T3 | **Detectar liberación** de casilla | Flujo continuo | Ídem | Evento `liberado` por casilla (tras tiempo de confirmación) | HU13, HU15 |

T1 se descompone a su vez en: (a) **detección** (¿hay un VMP en la foto y de qué clase?) y (b) **comparación** (¿es *el* VMP registrado?). Son dos modelos/etapas distintas: YOLO responde (a), la similitud responde (b).

## 2. Tipos de aprendizaje y por qué

- Detección: **aprendizaje supervisado** (cada imagen con cajas + clase), con **transfer learning/fine-tuning** desde YOLOv8 preentrenado en COCO.
- Por qué no basta un modelo preentrenado: COCO tiene `bicycle` y `motorcycle` pero **no scooter eléctrico** (ni distingue bicicleta eléctrica de una común).
- Comparación (T1b): primera versión con **visión clásica de OpenCV** (histograma de color, ORB); después evaluar **embeddings** (experimento E4). No requiere entrenamiento supervisado de identidad en la v1.
- Fuera de alcance del piloto (solo ideas): predicción de ocupación por horas, detección de ingresos atípicos (necesitan semanas de datos), aprendizaje por refuerzo (no aplica).

## 3. Clases del detector **[PROPUESTA]**

| id | Clase | Notas |
|---|---|---|
| 0 | `scooter` | scooter eléctrico |
| 1 | `bicicleta_electrica` | difícil de distinguir de bicicleta común; ver riesgos |
| 2 | `moto` | moto (eléctrica o no: visualmente indistinguible) |
| 3 | `bicicleta` | **clase de contraste** (no es VMP del servicio): enseña al modelo la diferencia con la eléctrica. Recomendada para la Fase 1; ver `docs/13` #22/#26 |

`tipo_vmp = 'bicicleta'` del ER (no eléctrica) no es VMP de interés en el Avance 2; se decide en docs/13 #1 si entra como cuarta clase.

> **Fase 1 (decisión 14-nov-2026):** el detector se entrena **solo con 2 clases**: `scooter` (id 0) y `bicicleta` (id 1, cualquier bicicleta, eléctrica o común). `moto` y la distinción de `bicicleta_electrica` quedan para fases posteriores (`docs/13` #22 y #28; `docs/14` §0.1). La tabla de arriba es el objetivo del producto completo.

Además se recomienda una clase auxiliar `persona` (reutilizando COCO) **solo** para descartar casillas “tapadas” por personas (HU15 punto 3). **[PROPUESTA]**

## 4. Datos

> La guía operativa para armar el dataset **entre los cuatro** (workspace de Roboflow, protocolo de captura, nombres de archivo, reparto, calidad) está en **`docs/14-DATASET-ROBOFLOW.md`**; el demo del primer avance, en **`docs/15-DEMO-RECONOCIMIENTO-AVANCE1.md`**. Lo de abajo es el resumen técnico.

### 4.1 Recolección
- Fuentes: fotos propias en la entrada de la Torre Arequipa (con el celular o la cámara real), con **permiso/consentimiento** (docs/10); vehículos de los propios integrantes y voluntarios.
- Variabilidad mínima a cubrir: distintas **horas** (mañana, mediodía, tarde, noche), **luz** (sol directo, sombra, artificial), **ángulos** (frontal, lateral, ¾), **distancias**, **oclusión parcial** (personas, otros vehículos), fondo del estacionamiento real.
- Para **T2/T3**: video de las casillas con y sin vehículo, con personas pasando, sombras, lluvia/garúa, cámara ligeramente movida.
- Para **T1b**: por cada usuario/vehículo, **1 foto de referencia (registro)** + **varias fotos de ingreso** en condiciones distintas (positivos) y pares con vehículos de **otros** dueños (negativos).

### 4.2 Etiquetado
- Herramienta: **Roboflow** (o CVAT / LabelImg). Formato de exportación: **YOLO**.
- Cada imagen `x.jpg` tiene `x.txt` con una línea por objeto: `clase x_centro y_centro ancho alto`, todo **normalizado 0–1**. Ejemplo: `0 0.58 0.62 0.31 0.44` = scooter centrado un poco a la derecha y abajo.
- Revisión cruzada: toda imagen etiquetada por una persona la revisa otra (calidad > cantidad).

### 4.3 Estructura de carpetas del dataset

```
ia_service/dataset/
├── data.yaml
├── images/{train,val,test}/*.jpg
└── labels/{train,val,test}/*.txt
```

```yaml
# data.yaml
path: ./dataset
train: images/train
val: images/val
test: images/test
names:
  0: scooter
  1: bicicleta_electrica
  2: moto
  3: bicicleta
```

> En la Fase 1 el `data.yaml` solo tiene `0: scooter` y `1: bicicleta` (`docs/14` §0.1).

### 4.4 Particiones
- Proporción de partida **[PROPUESTA]**: 70 / 20 / 10 (train / val / test).
- **Sin fuga de datos:** fotos casi idénticas del mismo vehículo/escena (ráfagas, cuadros consecutivos de un video) deben ir **todas al mismo grupo**. Partir por **vehículo y sesión de captura**, no por imagen suelta.
- El conjunto `test` no se toca hasta la evaluación final de cada experimento.

### 4.5 Tamaño del dataset
No se fija una cifra mágica. Procedimiento: empezar con un lote pequeño, entrenar, mirar la curva y los errores, y decidir cuánto más etiquetar. Las clases con pocas imágenes (p. ej. `moto`) se reportan por separado.

## 5. Entrenamiento (T1a y T2/T3) **[PROPUESTA]**

En la Fase 1 el entrenamiento y la evaluación se ejecutan en **Google Colab** (`docs/17`), con el cuaderno de `ia_service/training/` (no se entrena en las laptops). Parámetros de partida **[PROPUESTA]**: `yolo26n.pt`, 100 épocas, `imgsz` 640, parada temprana con paciencia 20, semilla 42. La evaluación sobre `test` se hace **una sola vez por experimento**.

- Punto de partida: modelo **nano** (rápido). **[DOC]** el Avance dice YOLOv8; la API de Ultralytics es la misma para YOLOv8, YOLO11 y YOLO26, así que cambiar de familia es cambiar el nombre del archivo de pesos (`yolov8n.pt`, `yolo11n.pt`, `yolo26n.pt`). Ver §16 y `docs/13` #20.
- `seed` fija para reproducibilidad; `patience` para parar cuando deja de mejorar la validación.
- El set `test` solo lo toca la evaluación final de cada experimento (`docs/16` §6.2).

- Salida: `runs/<nombre>/weights/best.pt` → se sube a S3 con versión (`models/vmp/v1/best.pt`) y se referencia desde `MODEL_VERSION` del servicio.
- Registrar en cada entrenamiento: commit, fecha, versión del dataset, hiperparámetros, métricas por clase, tiempo de inferencia por imagen (CPU/GPU).
- Aumentos de datos (brillo, contraste, volteo horizontal, escala, blur leve): usar los de Ultralytics por defecto; probar mosaicos de iluminación nocturna si hace falta.

## 6. Métricas **[DOC conceptual / PROPUESTA de uso]**

| Métrica | Qué mide | Dónde se usa |
|---|---|---|
| Precisión (P) | De lo que el modelo marcó, cuánto era cierto | Detección y validación |
| Recall (R) | De lo que era cierto, cuánto encontró | Detección y validación |
| F1 | Equilibrio P–R | Selección de umbral de confianza |
| IoU | Solapamiento caja predicha vs. real | Criterio de acierto en detección |
| mAP50 | Calidad media con IoU ≥ 0,50 | Reporte principal por clase |
| mAP50-95 | Promedio entre IoU 0,50–0,95 (más exigente) | Reporte complementario |
| Falso rechazo (FN de validación) | Usuario autorizado rechazado | **Experiencia**: colas |
| Falsa aceptación (FP de validación) | Ajeno aceptado | **Seguridad**: riesgo crítico |
| Latencia de inferencia | ms por imagen | Cumplir “en segundos” (RNF-01) |

Reportar **siempre por clase** y con **matriz de confusión**; no solo el promedio.

## 7. T1b: comparación con el vehículo registrado **[PROPUESTA]**

### 7.1 Algoritmo v1 (OpenCV)
1. Recortar la caja del VMP detectado (bbox YOLO) en la foto del acceso y en cada foto de referencia del usuario (precomputar y **cachear** las características de las referencias al registrar el vehículo).
2. Normalizar tamaño y luz (resize fijo, CLAHE opcional).
3. Calcular un **puntaje compuesto** (pesos a calibrar en E4):
   - similitud de **histograma de color** HSV (`cv2.compareHist`, Bhattacharyya/correlación),
   - coincidencias **ORB** + *ratio test* + RANSAC (proporción de buenos *matches*),
   - **coincidencia de clase** (el `tipo_vmp` registrado debe coincidir con la clase detectada; si no, el puntaje se penaliza o descarta).
4. Para cada uno de los ≤3 VMP del usuario se obtiene un puntaje; se toma el **máximo**.
5. Decisión: `puntaje_max ≥ UMBRAL_VALIDACION` → **validado** (devuelve qué VMP coincidió); si no → **rechazado** (incidencia `vehiculo_no_coincide`).
6. Además: si el **segundo mejor** puntaje está demasiado cerca del primero con puntajes bajos → marcar *zona gris* para verificación humana (ver 7.3).

### 7.2 Algoritmo v2 (si E4 lo justifica): embeddings
Un modelo de *re-identification* / embeddings genéricos (p. ej. features de una CNN preentrenada) → similitud coseno entre embeddings del recorte y de la referencia. Se evalúa contra v1 en E4 con pares reales.

### 7.3 Tres zonas de decisión **[PROPUESTA]**

| Zona | Condición | Acción |
|---|---|---|
| Verde | puntaje ≥ `U_ALTO` | validado automáticamente |
| Gris | `U_BAJO` ≤ puntaje < `U_ALTO` | “verificar” en la pantalla del guardia (confirma/rechaza) |
| Roja | puntaje < `U_BAJO` | rechazado + incidencia |

`U_ALTO` y `U_BAJO` se **calibran** (E5). Empezar **estricto** (más casos grises) y relajar solo cuando el piloto muestre error bajo.

### 7.4 Matriz de errores del proyecto

| | Realidad: autorizado | Realidad: ajeno |
|---|---|---|
| Se acepta | VP: entra sin demora | **FP: falsa aceptación** — entra un ajeno (riesgo de seguridad) |
| Se rechaza | **FN: falso rechazo** — cola y molestia | VN: ajeno rechazado |

Subir el umbral reduce FP y aumenta FN. Por eso hay zona gris y un humano decide los casos dudosos (RF11).

## 8. T2/T3: ocupación y liberación de casillas **[PROPUESTA]**

### 8.1 ROIs por casilla
Cada cámara de zona vigila varias casillas. Para cada casilla se guarda un **polígono ROI** en coordenadas de la imagen (`espacio_estacionamiento.roi_json`, brecha 8). Una casilla se considera ocupada si hay un detección de `scooter|bicicleta_electrica|moto` cuya caja tenga **IoU/solapamiento con el ROI ≥ `OVERLAP_MIN`** (p. ej. 0.5, calibrar).

### 8.2 Estabilidad (anti falsos positivos/negativos)

```
estado_actual[casilla] ∈ {libre, ocupada}
candidato[casilla], contador[casilla]

por cada cuadro procesado:
    obs = ocupada si hay detección solapada con el ROI, si no libre
    si obs == estado_actual: contador = 0; continuar
    si obs != candidato: candidato = obs; contador = 1
    si no: contador += 1
    si candidato == ocupada y contador >= N_OCUPAR:   # HU14 (3): quien solo pasa no ocupa
        cambiar a ocupada; publicar ia.espacio.ocupado
    si candidato == libre   y tiempo_en_candidato >= T_LIBERAR:   # HU15 (3): tiempo de confirmación
        cambiar a libre;    publicar ia.espacio.liberado
```

Valores de partida **[PROPUESTA]**: `N_OCUPAR` ≈ el equivalente a unos pocos segundos de video; `T_LIBERAR` > `N_OCUPAR` (liberar es más delicado: una persona frente al vehículo no debe liberar la casilla). **Se calibran con video real de la cámara del piloto.**

### 8.3 Casos que hay que probar
Persona que pasa; persona que se detiene frente a la casilla; vehículo mal estacionado ocupando dos casillas; sombra/luz de faros; lluvia; obstrucción de cámara; vehículo desplazado levemente dentro de su casilla; dos vehículos a la vez.

### 8.4 Eficiencia
Procesar 1 de cada K cuadros; inferencia a `imgsz` menor en zona; una sola inferencia por cuadro y reparto de detecciones a las casillas por solapamiento (no una inferencia por casilla); publicar **solo cambios** de estado (más un *heartbeat* cada X segundos para saber que la cámara está viva).

## 9. Contratos del servicio de IA

Detalle de eventos en `docs/07-API-EVENTOS.md`. Interfaz interna del servicio:

```python
# ia_service/detector/detector.py
class Detector:
    def detectar(self, imagen_bgr) -> list[Deteccion]: ...   # Deteccion(clase, score, bbox)

# ia_service/matcher/matcher.py
class Comparador:
    def comparar(self, recorte_ingreso, referencias: list[Referencia]) -> ResultadoComparacion:
        """Devuelve puntaje por referencia, mejor id_vehiculo y zona (verde/gris/roja)."""

# ia_service/zonas/estabilidad.py
class EstadoCasillas:
    def procesar_cuadro(self, camara: str, detecciones: list[Deteccion], ts: float) -> list[CambioCasilla]: ...
```

Configuración por variables de entorno: `MODEL_PATH`, `MODEL_VERSION`, `CONF_MIN` (confianza mínima YOLO), `UMBRAL_ALTO`, `UMBRAL_BAJO`, `N_OCUPAR`, `T_LIBERAR`, `OVERLAP_MIN`, `FRAME_STRIDE`.

## 10. Experimentos planificados **[PROPUESTA]** (ninguno ejecutado aún)

| ID | Pregunta | Métrica | Decide |
|---|---|---|---|
| **E1** | ¿Qué tan bien detecta YOLOv8 preentrenado (COCO), sin ajuste, `bicycle` y `motorcycle` en fotos de la entrada? | Precisión, recall en `test` | Línea base: cuánto hay que mejorar. **Ojo:** el modelo COCO usa otros ids de clase; en la Fase 1 se hace cualitativo + tabla de coincidencias, no mAP directo (`docs/16` §6.3) |
| **E2** | ¿Cuánto mejora el ajuste fino con fotos propias, incluyendo `scooter`? | mAP50 y mAP50-95 en `test` | Si el etiquetado vale el costo |
| **E3** | ¿Compensa un modelo mayor (`s`) frente al `n`? ¿Y otra familia (YOLO11/YOLO26, o RF-DETR Nano, §16)? | mAP vs. tiempo de inferencia en la máquina objetivo | Tamaño y familia del modelo según equipo |
| **E4** | ¿Qué método compara mejor con el registrado: histograma, ORB, compuesto o embeddings (p. ej. DINOv2, §16)? | FN y FP sobre pares reales | Método de coincidencia de la v1 |
| **E5** | ¿Qué umbral equilibra seguridad y fluidez? | Curva P–R con datos del piloto | `U_ALTO`/`U_BAJO` iniciales y cuándo relajarlos |
| **E6** (nuevo) | ¿Qué `N_OCUPAR`/`T_LIBERAR`/`OVERLAP_MIN` minimizan errores de casilla? | Errores por hora de video etiquetado | Parámetros de estabilidad |

Orden: E1 → E2 → E3; E4 y E5 necesitan pares de fotos reales (piloto); E6 con video de las cámaras de zona.

## 11. Despliegue del modelo **[PROPUESTA]**

1. `best.pt` versionado en S3 (`models/vmp/<version>/best.pt`) + `metrics.json` + `dataset_version.txt`.
2. Imagen Docker de `ia_service` que descarga el modelo al arrancar según `MODEL_VERSION` (o lo trae montado).
3. Prueba de humo al arrancar (inferencia sobre una imagen de ejemplo) antes de marcar el servicio *healthy*.
4. Rollback = cambiar `MODEL_VERSION` a la anterior.
5. CPU suficiente para el piloto con modelo `n`; GPU opcional si E3 elige un modelo mayor o si se suman cámaras.

## 12. Monitoreo y reentrenamiento **[PROPUESTA]**

Señales a vigilar: distribución de `score_confianza` por cámara y hora; tasa de `vehiculo_no_coincide` por tipo de VMP; tasa de overrides del guardia (la IA dijo X, el humano dijo Y); latencia p95; casillas “pegadas” (sin cambio durante horas).

**Disparadores de reentrenamiento:** caída sostenida de confianza media; aumento de falsos rechazos reportados por guardias; nuevos tipos de VMP/colores/accesorios frecuentes; cambio físico (cámara movida, nueva iluminación, nueva zona). Los casos corregidos por humanos se guardan como **datos nuevos etiquetados** para el siguiente entrenamiento (con consentimiento).

## 13. Modos de operación del piloto **[PROPUESTA]**

| Modo | La IA… | El humano… | Cuándo pasar al siguiente |
|---|---|---|---|
| **Sombra** | Decide en silencio y registra; no bloquea ni habilita nada | Sigue con el proceso manual | Cuando las decisiones de la IA coincidan con las humanas en un periodo suficiente (criterio definido tras medir) |
| **Asistido** | Propone “validado/rechazado/verificar”; la decisión sigue siendo del guardia | Confirma o corrige con un toque | Cuando los overrides sean raros |
| **Automático** | Valida verdes; rechaza rojas con incidencia | Revisa grises e incidencias | — (siempre con salida manual de emergencia) |

## 14. Escalera de prototipos **[PROPUESTA]**

| Nivel | Qué es | Sirve para |
|---|---|---|
| 0 | Mockups (los 24 prototipos del Avance 2) | Validar flujos |
| 1 | Notebook: YOLOv8 preentrenado sobre fotos propias (E1) | Línea base |
| 2 | Script CLI: foto → detección + comparación contra carpeta de referencias | Probar T1 sin sistema |
| 3 | `ia_service` con eventos + simulador de cámaras (video/webcam) | Integración |
| 4 | Piloto con cámaras reales en modo sombra → asistido → automático | Medir indicadores |

## 15. Riesgos específicos de IA

| Riesgo | Efecto | Mitigación |
|---|---|---|
| Bicicleta eléctrica ≈ bicicleta común | Clase confusa | Etiquetado cuidadoso; quizá fusionar a nivel detector y distinguir por `tipo_vmp` registrado |
| Pocos datos de `moto`/`scooter` | Baja recall en esa clase | Muestreo dirigido; reportar por clase |
| Foto de referencia mala (borrosa, parcial) | Falsos rechazos | HU03: validar que contiene un vehículo, tamaño mínimo y nitidez (`variance of Laplacian`) |
| Dos vehículos casi idénticos (mismo modelo/color) | Falsa aceptación | `caracteristica_distintiva`; zona gris; humano |
| Foto de pantalla / QR reutilizado | Suplantación | Ver docs/10 (QR + validación de vehículo juntos; QR rotatorio opcional) |
| Cambio de luz / noche | Caída de recall | Datos nocturnos; iluminación en el acceso |
| Latencia en CPU | Cola en el acceso | `yolov8n`, `imgsz` menor, caché de referencias, medir en E3 |
| Privacidad de fotos | Riesgo legal/ético | docs/10: consentimiento, retención, acceso restringido, evitar rostros |

## 16. Tecnologías de GitHub que pueden mejorar el reconocimiento **[PROPUESTA]**

Qué se verificó en esta guía: los datos de YOLO26 y RF-DETR salen de la documentación de Ultralytics y de Roboflow (consultada al redactar); `yolo26n.pt` y `yolov8n.pt` se descargan y corren con `ultralytics` 8.4. El resto viene de conocimiento general y debe revisarse en su repositorio antes de adoptarlo (⚠).

**Decisión del equipo (9-nov-2026): se usa YOLO26** (`yolo26n.pt` de partida). Lo demás de esta tabla son candidatos para más adelante.

**Principio:** la calidad del reconocimiento depende **primero de los datos** (variedad, etiquetas correctas, test limpio), **segundo del modelo**, **tercero de trucos de inferencia**. Cambiar de modelo sin arreglar el dataset rara vez resuelve el problema.

| Tecnología | Para qué en este proyecto | Qué sabemos | Etapa |
|---|---|---|---|
| **Ultralytics YOLO26** (también YOLO11, YOLOv8) | Detector de VMP y de casillas (T1a, T2/T3) | YOLO26 se presentó en enero 2026; tamaños n/s/m/l/x; opción de inferencia sin NMS; mejoras orientadas a objetos pequeños y a CPU/dispositivos de borde (según Ultralytics, la versión `n` es más rápida en CPU que YOLO11n). Misma API que YOLOv8 → migración trivial. ⚠ Código bajo AGPL-3.0 con licencia empresarial alternativa (verificar si algún día se comercializa) | E1–E3 |
| **RF-DETR** (Roboflow) | Detector alternativo basado en transformers con *backbone* DINOv2; detección y segmentación | `pip install rfdetr`; modelos Nano–Large bajo Apache 2.0; los tamaños mayores/menores bajo licencia de plataforma de Roboflow. En los benchmarks de Roboflow (propios, T4/TensorRT) logra más AP50 que YOLO26 a latencia similar o algo mayor; **no** asumirlo para nuestros datos: medirlo en E3 | E3 (opcional) |
| **DINOv2** (Meta) | **Embeddings** para decidir «¿es *este* vehículo?» (T1b): similitud coseno entre el recorte capturado y la referencia; candidato a superar histograma+ORB | Características visuales autosupervisadas, usadas en recuperación/similitud de imágenes. ⚠ Verificar licencia de los pesos y tamaño del modelo (hay variantes pequeñas) | E4 |
| **`supervision`** (Roboflow, código abierto) | Utilidades de visión: **zonas poligonales** (nuestras casillas/ROI), seguimiento entre cuadros, anotación | ⚠ No verificado aquí; revisar su documentación. Encaja con `ia_service/zonas/` | E6, HU13–HU15 |
| **Grounding DINO / YOLO-World / SAM 2** | **Pre-etiquetado** acelerado (cajas o máscaras a partir de texto o clics) | ⚠ Conocimiento general; todo pre-etiquetado se revisa a ojo | Dataset |
| **Roboflow Universe** | Datasets públicos para complementar entrenamiento | ⚠ Revisar licencia y calidad; **no** mezclar con el test | Dataset |
| **Exportación ONNX / OpenVINO / TensorRT** (`model.export(...)` en Ultralytics) | Más velocidad en CPU del servidor del piloto | Mejora latencia; medir antes y después | Despliegue |
| Re-ID de vehículos (**torchreid**, **FastReID**) | Identificación individual de vehículos entrenada a propósito | ⚠ Más pesado y orientado a coches/personas; solo si E4 muestra que embeddings genéricos no bastan | Futuro |

### Trucos de inferencia baratos (mejoran sin reentrenar)
1. **Votación multicuadro** en el acceso: tomar 3–5 fotos en ráfaga, comparar cada una con las referencias y **promediar o tomar la mediana** de los puntajes. Reduce el efecto de un cuadro borroso o mal encuadrado.
2. **Resolución de entrada** mayor (`imgsz`) para vehículos pequeños o lejanos, midiendo el costo en ms.
3. **Umbral de confianza por clase** (en vez de uno global) si una clase es más difícil.
4. **Recorte primero:** detectar → recortar el vehículo → comparar solo el recorte (ya previsto en §7.1).
5. **Aumento en test (TTA)**: solo si sobra tiempo de latencia; no es prioritario.

### Recomendación de orden
`yolo26n` (o `yolo11n`/`yolov8n` como control) en E1–E2 → cambiar de tamaño/familia en E3 **solo si** hay margen en el dataset → DINOv2 vs. histograma+ORB en E4 → `supervision` para ROIs en E6. RF-DETR queda como candidato opcional de E3 si el equipo quiere comparar arquitecturas.
