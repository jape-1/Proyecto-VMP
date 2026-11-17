# 14 · Dataset de VMP en Roboflow (trabajo en equipo)

> Todo este archivo es **[PROPUESTA]** salvo lo que se indique. Decisiones del equipo: *«como es grupal, armar el dataset en Roboflow empezando desde un dataset ya existente»* (9-nov-2026), modelo **YOLO26**, y **para el primer avance reconocer solo bicicleta y scooter** (14-nov-2026). Esto es la **Fase 1** (demo de reconocimiento, `docs/15`). **El dataset es el cuello de botella real del proyecto**: las fotos tardan días en reunirse aunque el código tarde horas. Empieza ya.
> Los detalles de la interfaz de Roboflow (planes, límites, nombres de menús) cambian con frecuencia: **verifícalos en su documentación**. Lo marcado ⚠ es especialmente propenso a cambiar o no pudo comprobarse sin entrar a una cuenta.

## 0. Estrategia en dos pasos (Fase 1)

**Paso A · Dataset base a partir de un dataset existente (Roboflow Universe).** Se *bifurca* (fork) un dataset público a nuestro workspace y se renombran sus clases a **nuestras dos etiquetas**. Da un punto de partida inmediato (miles de imágenes ya anotadas) para entrenar el primer modelo **sin esperar** a reunir fotos propias.

**Paso B · Fotos propias del entorno real, en grupo.** Los cuatro agregan fotos de la Torre Arequipa y de vehículos reales, las anotan y las suman al proyecto propio. **Estas fotos propias son las únicas que forman `val` y `test`**: miden el desempeño en el entorno donde se usará el sistema. Los datos externos solo sirven para entrenar.

> Por qué no basta el Paso A: los datasets públicos vienen de otras ciudades, cámaras y criterios de etiquetado; un modelo entrenado solo con ellos suele rendir peor en tu entorno real. Y por qué no esperar al Paso B: sin una base, el primer entrenamiento se retrasa días.

### 0.1 Etiquetas finales de la Fase 1 (decisión del equipo, 14-nov-2026)

| id | Etiqueta | Qué incluye |
|---|---|---|
| 0 | `scooter` | Scooter eléctrico de pie (plataforma, manubrio vertical, ruedas pequeñas) |
| 1 | `bicicleta` | **Cualquier bicicleta**, eléctrica o común |

- Nombres **exactos**, minúsculas, sin tildes, sin guion bajo (coinciden con `data.yaml` y el código). Al ser palabras simples no chocan con la restricción de caracteres de Roboflow.
- **Por qué una sola clase `bicicleta`:** visualmente casi no se distingue una bicicleta eléctrica de una común (la batería o el motor muchas veces no se ven). Con pocas fotos, forzar esa distinción solo confunde al modelo. **La diferencia eléctrica/no eléctrica se deja para una fase posterior** y se apoyará en los datos del registro del vehículo (`tipo_vmp` del ER), no solo en la imagen. Para no perder esa información, **sí se anota en `registro_capturas.csv`** si cada bicicleta fotografiada es eléctrica (§3.4).
- **Fuera de la Fase 1 (para fases posteriores):** `moto`, distinguir `bicicleta_electrica`, y las demás clases del producto completo (`docs/06` §3). Si en una foto aparece una moto u otro vehículo de fondo, **no se etiqueta** (queda como fondo): es una limitación conocida del demo y se dice en la exposición.
- Lo que **no** se etiqueta nunca: patinetas/skateboards, hoverboards, sillas de ruedas motorizadas (*mobility scooter*), personas, autos. Se descartan.

### 0.2 Datasets de Universe (consultados el 9-nov-2026)

Verificado en las páginas de cada dataset: nombre, clases y licencia. **No verificado** (hay que abrir las imágenes): cómo están dibujadas las cajas, la calidad de las etiquetas y el número de imágenes cuando la página no lo muestra.

| Dataset (Universe) | Clases según la página | Imágenes | Licencia | Uso |
|---|---|---|---|---|
| **E-Bikes Detection** — `computer-vision-j1upd/e-bikes-detection` | `bicycle`, `e-bike`, `e-hoverboard`, `e-scooter`, `mobility-scooter`, `skateboard` | no indicado | CC BY 4.0 | **Base recomendada**: trae las dos clases de la Fase 1 en un solo dataset |
| **electric scooter** — `kdigital/electric-scooter-cd7hw` | `electric scooter` | 2,524 | CC BY 4.0 | Refuerzo opcional de `scooter`; ⚠ última actualización de hace ~3 años |
| **electric scooters images** — `yolov7-ow4kh/electric-scooters-images` | `e-scooters rider` | 3,600 | CC BY 4.0 | ⚠ La clase incluye al *rider*; si la caja abarca a la persona **no cumple la regla de oro** (caja del vehículo). Solo si al revisar las cajas son del vehículo |
| **scooter_bicycle** — `vfdata/scooter_bicycle` | 4 clases (la página no las nombra) | no indicado | CC BY 4.0 | Posible complemento; ⚠ revisar clases antes |

Otros resultados de la búsqueda sin revisar a fondo: `e-scooter` (capstonedesignproject-hcpo2/e-scooter-ccjvp), `Scooter` (computer-vision-dibh7/scooter-31wb6), `scooter_detection_Final` (school-mdkgi), `E-Scooter` (e-scooter/e-scooter-h83gg). **Antes de elegir, abrir cada uno y mirar 30–50 imágenes anotadas.**

### 0.3 Mapeo de etiquetas (origen → nuestras clases)

| Dataset | Clase de origen | → Nuestra etiqueta |
|---|---|---|
| E-Bikes Detection | `e-scooter` | `scooter` |
| E-Bikes Detection | `e-bike` | `bicicleta` |
| E-Bikes Detection | `bicycle` | `bicicleta` (mismo nombre que la anterior: **se fusionan**) |
| E-Bikes Detection | `e-hoverboard`, `mobility-scooter`, `skateboard` | **borrar** |
| electric scooter (kdigital) | `electric scooter` | `scooter` |
| electric scooters images | `e-scooters rider` | `scooter` **solo si** la caja es del vehículo; si no, no usar |

### 0.4 Procedimiento resumido

1. Montar el workspace y los proyectos, invitar al equipo (§2, §2.2).
2. Revisar el dataset base (30–50 imágenes) y hacer el *fork* a `base-externa` (§2.2).
3. **Renombrar las clases en Roboflow** (*Settings → Classes*) según §0.3 y limpiar imágenes vacías.
4. En paralelo, **los cuatro capturan, suben y anotan** fotos propias en `vmp-propias` (§3, §5).
5. Generar versiones **sin aumentos** de ambos proyectos y **exportarlas en formato YOLO** a Drive (§6; `docs/17` §2).
6. En Colab: partición (externo → solo train; propias por vehículo → train/val/test), E1, entrenar, evaluar (`docs/16`, `docs/17`).

### 0.5 Si el *fork* falla

Si Roboflow no deja hacer el *fork* (cuota o créditos), usar *Download Dataset* → formato YOLO del dataset base y remapear las clases con un script. Con *fork* correcto, ese script no hace falta.

### 0.6 Licencias y atribución (obligatorio)

Los datasets candidatos están bajo **CC BY 4.0**, que exige **dar crédito** (autor/fuente, enlace, licencia) e indicar si se modificó. Mantener `ia_service/ATRIBUCIONES.md` (plantilla en `docs/16` §9) con una fila por dataset externo y citarlo en la presentación y el informe. Si un dataset no indica licencia o es de uso no comercial, **no lo uses** sin consultar. (Comprobar el texto de la licencia en la página de cada dataset; esto no es asesoría legal.)

### 0.7 Qué pasa con el dominio (aviso honesto)

Un modelo entrenado con imágenes de otros países y cámaras puede fallar con tus fotos. Por eso: (1) `val`/`test` solo con fotos propias; (2) en `docs/15` se muestra el modelo **antes y después**; (3) cualquier cifra se reporta indicando qué proporción del entrenamiento es externa.

## 1. Qué construimos

Un dataset de **detección de objetos** con las **2 etiquetas de §0.1**. Definiciones operativas para anotar (confirmar en equipo):

| Etiqueta | Se anota cuando… | No confundir con… |
|---|---|---|
| `scooter` | Se ve plataforma + manubrio vertical + ruedas pequeñas | patineta (skateboard), hoverboard, silla de ruedas motorizada → no se anotan |
| `bicicleta` | Cuadro de bicicleta con dos ruedas grandes, manubrio y pedales, con o sin motor | moto, scooter → otra clase o no se anotan |

Casos grises que el equipo debe **resolver por escrito** (anótalos en `docs/13` si afectan al producto): scooter plegado o cargado en la mano, bicicleta plegable, vehículo con rider encima, bicicleta parcialmente tapada, moto pequeña o scooter «tipo moto».

> **Regla de oro de etiquetado: la caja es del vehículo, no de la persona.** Si hay rider, la caja cubre el vehículo (ruedas, manubrio, plataforma); la persona queda fuera salvo lo que se superponga inevitablemente.

## 2. Montaje en Roboflow (una sola vez)

1. **Un integrante** crea el *workspace* y los *proyectos* (tipo «Object Detection»; ver §2.2: el workspace solo no basta) e **invita a los otros tres** (por correo o enlace; en gratuito todos entran como administradores). El dueño del workspace custodia la cuenta.
2. Las 2 clases de §0.1 deben llamarse **exactamente** `scooter` y `bicicleta` (minúsculas, sin tildes). En el proyecto con *fork*, las clases vienen del origen: renombrarlas según §0.3 y §2.2.
3. La **API key** del workspace (Settings → API) solo se necesita si se descarga el dataset por código. Si se usa, va en un gestor de contraseñas o en los *Secrets* de Colab; **nunca** en Git ni en el cuaderno.
4. **Privacidad (plan gratuito):** según la página de precios y la documentación de Roboflow (consultadas el 9-nov-2026), en el plan gratuito (*Core*) los proyectos son **privados** salvo que los publiques en Universe, así que **no pulses «publicar en Universe»**. ⚠ Aun así, confirma en tu cuenta que el proyecto aparece como privado antes de subir fotos. La documentación indica además que el **licenciamiento de datos viene activado por defecto** en workspaces nuevos (aplica también a proyectos privados) y se puede desactivar en *Project Settings*: **desactívalo**, porque subirán fotos de vehículos y personas reales (`docs/10` §4–5). Sin rostros ni placas legibles.
5. **Límites del plan gratuito** (según Roboflow, 9-nov-2026; verifica en tu cuenta): **10 créditos al mes** (los no usados no se acumulan); administradores ilimitados; hasta 20 proyectos; un *fork* grande puede fallar por cuota. Las herramientas de **IA de etiquetado** (*Label Assist*, *Auto Label*, *Smart Polygon*) y el **entrenamiento alojado** **consumen créditos**: **no los usamos**; anotamos a mano y entrenamos **en Colab con Ultralytics** (`docs/17`). Los roles *Labeler/Reviewer* y *Review Mode* requieren un add-on de pago (*Teams*): en el plan gratuito **todos los invitados son administradores** → acuerdo de equipo: **solo una persona** (Giancarlo) borra proyectos, versiones o clases; los demás suben y anotan.

### 2.1 Proyectos en el mismo workspace

Se separa **lo externo** de **lo propio** para que nunca se mezclen:

| Proyecto | Para qué | Quién lo toca |
|---|---|---|
| **Externos** (uno o varios): `base-externa` (fork de *E-Bikes Detection*) o, p. ej., un proyecto `bicycle` y otro `scooter`, cada uno fork de un dataset de Universe | Material de **entrenamiento** externo. Solo se renombran sus clases y se limpia; no se les suben fotos propias | Giancarlo |
| `vmp-propias` (proyecto nuevo, *Object Detection*) | **Nuestras fotos**, con **las 2 clases juntas**; aquí se anotan en grupo; de aquí salen `val` y `test` | Los 4 |

Reglas para los externos:
1. En cada proyecto externo las clases se llaman **exactamente** `scooter` o `bicicleta` (aunque el proyecto tenga una sola clase).
2. Todo lo externo va **solo a train**, y cada dataset se cita en `ATRIBUCIONES.md`.
3. ⚠ **Riesgo de un proyecto por clase:** una foto del proyecto de bicicletas que también tenga un scooter **sin etiquetar** le enseña al modelo «ahí no hay scooter» (y al revés). Al revisar las 30–50 imágenes, busca específicamente esto. Un dataset que ya trae ambas clases etiquetadas juntas (como *E-Bikes Detection*) evita el problema.
4. `vmp-propias` **no** se divide por clase: es un solo proyecto con `scooter` y `bicicleta`.

### 2.2 Paso a paso para principiantes (plan gratuito) — de invitar al equipo a tener el dataset base

> Verificado en la documentación y la página de precios de Roboflow el 9-nov-2026 (fuentes al final). Lo marcado ⚠ no pudo comprobarse sin entrar a una cuenta: confírmalo en pantalla.

**¿Basta con el workspace? No.** El *workspace* es solo el «cuarto» del equipo (miembros, facturación, API key). Las imágenes y etiquetas viven dentro de **proyectos**. Hacen falta como mínimo `vmp-propias` (lo creas tú) y `base-externa` (lo crea solo el *fork*). El plan gratuito permite hasta 20 proyectos.

**Fase A — Giancarlo (dueño del workspace)**

1. **Invitar a los 3:** abrir *Workspace Settings → Team Members* (dirección directa: `app.roboflow.com/settings/members`). Escribir los correos separados por comas, elegir rol, *Send Invites*. Alternativa: copiar el **enlace de invitación** y pasarlo por WhatsApp. ⚠ Las invitaciones por correo **caducan a los 3 días**; si caducan, reenviarlas. En el plan gratuito todos entran como administradores (regla de equipo: solo Giancarlo borra proyectos, versiones o clases).
2. **Comprobar privacidad:** en gratuito los proyectos son **privados salvo que los publiques en Universe**. No pulsar nada que diga *publish*. ⚠ Verificar en *Project Settings* que el proyecto figura como privado y **desactivar el licenciamiento de datos** si aparece (§2 punto 4).
3. **Crear el proyecto propio:** en el panel, *Create New Project* → tipo **Object Detection** → nombre `vmp-propias` → *annotation group* `vmp-propias`. ⚠ **Trampa:** los proyectos que comparten *annotation group* **comparten lista de clases y anotaciones**; usa un grupo distinto para cada proyecto (el *fork* traerá el suyo).
4. **Buscar el dataset base:** iniciar sesión, abrir `https://universe.roboflow.com/computer-vision-j1upd/e-bikes-detection` (o buscar «e-bikes detection» en Universe). Mirar **30–50 imágenes anotadas**: ¿la caja es del vehículo? ¿las clases son correctas? Anotar la fuente en `ATRIBUCIONES.md` (CC BY 4.0).
5. **Hacer el fork:** *Use this Dataset → Fork Project*. Se copia **todo** el dataset (no se elige un subconjunto) a tu workspace como proyecto nuevo, con versiones y exportaciones en blanco. Renómbralo a `base-externa`. ⚠ Si no alcanzan los créditos o la cuota de imágenes, el fork puede fallar: ver §0.5.

**Fase B — Giancarlo, sobre `base-externa`: dejar las clases como las nuestras**

6. Ir a *Settings → Classes* del proyecto. Marcar las clases y usar **Rename**; para **fusionar**, darles el mismo nombre; luego *Review Changes → Confirm Changes*. Aplica a **todas** las imágenes del proyecto. Cambios:
   - `e-scooter` → `scooter`
   - `e-bike` → `bicicleta`
   - `bicycle` → `bicicleta` (al llevar el mismo nombre que `e-bike`, **se fusionan**)
   - `e-hoverboard`, `mobility-scooter`, `skateboard` → **Delete** (borra esas anotaciones en todas las imágenes y **no se puede deshacer**; es solo tu copia, el original de Universe no cambia).
7. **Limpiar:** las imágenes que solo tenían hoverboards, skateboards o sillas motorizadas quedan sin objetos útiles. Filtrarlas y borrarlas (o dejarlas como fondo, que ayuda un poco a reducir falsos positivos, pero no en exceso: revisar la proporción).
8. **Generar una versión sin aumentos ni preprocesos** y exportarla en formato YOLO (*Export Dataset*) → subir el `.zip` a Drive como `externo-1.zip` (`docs/17` §2).
9. *(Opcional, solo para experimentar)* Para probar un cambio de clases **sin destruir** las etiquetas existe el paso de preprocesamiento de **remapeo de clases** a nivel de versión, que es reversible. Renombrar, fusionar y borrar en *Settings → Classes* son **irreversibles**.

**Si quieren sumar un segundo dataset (p. ej. *electric scooter*):** primero hacer su *fork* y renombrar sus clases a los mismos nombres; luego se pueden fusionar proyectos con *Merge Datasets* (menú de tres puntos del proyecto): crea un proyecto nuevo con copias de las imágenes y anotaciones. ⚠ La documentación no explica qué pasa con clases de nombres distintos, así que **renombrar antes de fusionar** y probar primero con datasets pequeños. Para exportarlos a Drive basta una exportación por proyecto: no hace falta fusionarlos si el cuaderno acepta varios `.zip` externos.

**Fase C — los 4, en paralelo desde hoy (no esperan a la Fase B)**

10. Cada uno acepta la invitación, entra a `vmp-propias` y trabaja **su propio lote**: fotografiar (§3), nombrar los archivos con la convención (§3.3), subirlos como lote con su nombre (`lote-raphael-01`) y **anotarlos** dibujando la caja y escribiendo la clase.
11. Giancarlo anota primero **una imagen de cada clase** (`scooter`, `bicicleta`) y activa **Lock Classes** (*Settings → Classes*), para que nadie invente variantes (`Scooter`, `scooter `, `e-scooter`…).
12. Lo externo (`base-externa`) **solo va a `train`**. Las fotos propias forman `val` y `test` (§6).

**No usar en el plan gratuito:** *Label Assist*, *Auto Label*, *Smart Polygon* y el entrenamiento alojado **consumen créditos** (hay 10 al mes y no se acumulan). Se anota a mano y se entrena en Colab.

*Fuentes (consultadas 9-nov-2026):* docs.roboflow.com — «Add Team Members» (`/workspaces/adding-team-members-to-a-workspace`), «Fork a Universe Dataset» (`/datasets/universe/universe/fork-a-universe-dataset`), «Create a Project» (`/datasets/create-a-project`), «Set Dataset Classes» (`/datasets/manage-classes`), «Merge Projects» (`/datasets/merge-datasets`), «Plans» (`/billing/plans`) y roboflow.com/pricing; blog «Advanced class management».

## 3. Protocolo de captura (cada integrante)

### 3.1 Qué fotografiar

Solo **scooters y bicicletas** (las dos clases de la Fase 1).

| Objetivo | Cómo |
|---|---|
| **Variedad de vehículos** | Muchos vehículos *distintos* (amigos, compañeros, estacionamiento de la sede) importan más que muchas fotos del mismo. Busca scooters **y** bicicletas de colores, tamaños y modelos distintos |
| **Variedad de condiciones** | Mañana, mediodía, tarde, noche; sol directo, sombra, luz artificial; seco y garúa si se puede |
| **Variedad de ángulos** | Frontal, lateral izquierdo/derecho, ¾ delantero/trasero; alturas distintas (a la altura de una cámara de acceso y de una cámara elevada) |
| **Distancias** | Cerca (el vehículo llena el cuadro) y lejos (como lo vería una cámara de zona) |
| **Entorno real** | La entrada y el estacionamiento reales de la Torre Arequipa, tal como los verá el sistema |
| **Oclusión y desorden** | Con personas pasando, otros vehículos al lado, vehículo parcialmente tapado |
| **Negativos** | Algunas fotos del estacionamiento **sin** scooters ni bicicletas (sin etiquetas), para reducir falsos positivos |

Para fases posteriores (no ahora): video de casillas libres y ocupadas, y pares «foto de registro / foto de ingreso» por vehículo.

### 3.2 Reglas técnicas
- Foto horizontal o vertical, **sin filtros** ni recorte previo, resolución normal del celular (se reduce al entrenar).
- Evitar ráfagas casi idénticas: una toma cada vez que cambie ángulo, luz o posición.
- **Sin personas identificables** como sujeto; si salen, fondo desenfocado o fuera de plano. **No** captar placas legibles de terceros.
- Pedir **permiso** al dueño del vehículo (frase corta registrada en `registro_capturas.csv`).
- Quitar la ubicación GPS de las fotos (EXIF) antes de subirlas.

### 3.3 Convención de nombres (obligatoria: la usa el script de partición, `docs/16` §3)

```
<tipo>-v<ID>-<nnn>.jpg
   tipo : scooter | bici          (bici = cualquier bicicleta, eléctrica o común)
   ID   : número del vehículo físico, único en todo el equipo (v01, v02, …)
   nnn  : correlativo de la foto de ese vehículo (001, 002, …)

ejemplos:  scooter-v03-017.jpg   bici-v21-004.jpg
```

Los tipos `ebike`, `moto` y `zona` quedan **reservados** para fases posteriores; por ahora una bicicleta eléctrica se nombra `bici-…` y se marca como eléctrica en el registro.

**Todas las fotos del mismo vehículo comparten el mismo `v<ID>`.** Esto permite repartirlas en train/val/test **por vehículo** y que el test mida vehículos nunca vistos (lo que pasa en producción). Los IDs se reservan en `registro_capturas.csv` para que dos personas no usen el mismo.

### 3.4 `registro_capturas.csv` (una fila por vehículo, en una hoja compartida)

| id_vehiculo | tipo | electrica (sí/no/no sé) | marca_modelo | color | fotografo | fecha | lugar | consentimiento (sí/no) | observaciones |
|---|---|---|---|---|---|---|---|---|---|
| v03 | scooter | sí | Xiaomi Mi 3 | negro | Giancarlo | … | entrada Torre Arequipa | sí | … |
| v21 | bici | no | — | azul | Miladia | … | … | sí | … |

## 4. Reparto del trabajo **[PROPUESTA]**

| Tarea | Responsable sugerido | Apoyo |
|---|---|---|
| Dueño del workspace, invitaciones, versiones del dataset, carpeta de Drive y ejecución en Colab | **Giancarlo** (líder de IA en las fichas) | — |
| Captura: reunir vehículos distintos | **Los 4** (cada uno con su «cupo»: ver §4.1) | — |
| Etiquetado | **Los 4**, repartido por lotes | Revisión cruzada (§7) |
| Guía de etiquetado y casos grises | **Raphael** (SM) lleva el acta de decisiones | Todos |
| Hoja `registro_capturas.csv` y control de IDs | **José** (PO) | — |
| Revisión de calidad y *health check* del dataset | **Miladia** | Giancarlo |

### 4.1 Cupos de partida (heurística, a ajustar tras E1/E2)
Para el **primer entrenamiento** basta con un lote pequeño pero **variado**: por ejemplo, cada integrante reúne **3 scooters y 3 bicicletas distintos** (6 vehículos) y toma **10–20 fotos por vehículo** en condiciones variadas. Con 4 integrantes son unos **24 vehículos y 240–480 fotos**. No es una cifra «suficiente para producción»: es lo mínimo para ver al modelo reconocer algo y medir una línea base; la curva de aprendizaje y los errores dicen cuánto más hace falta. Meta real acordada: `____`.

## 5. Anotación en Roboflow

1. Subir las fotos por **lotes** (un lote = un integrante/fecha) conservando los nombres del §3.3.
2. Anotar con **cajas ajustadas** (herramienta *bounding box*). Cuidar:
   - La caja toca los bordes del vehículo; incluir ruedas, manubrio, plataforma/asiento.
   - Un objeto = una caja. Vehículos parcialmente cortados por el borde de la foto: etiquetar lo visible si se reconoce.
   - Si hay duda de clase, **no adivinar**: marcar con la etiqueta (*tag*) `dudoso` y resolver en pareja.
   - Vehículos de fondo muy pequeños o ilegibles: criterio común (p. ej., etiquetar solo si se distingue el tipo). Documentar el criterio.
3. ⚠ **Asistencia de etiquetado** (*Label Assist* / *Auto Label*): consume créditos y, aunque acelera, **todo se revisa a ojo**. En el plan gratuito, no usarla.
4. **Imágenes de fondo / negativos:** incluir algunas fotos de estacionamiento **sin** scooters ni bicicletas (sin etiquetas) para reducir falsos positivos.

## 6. Versiones, aumentos y particiones (decisión importante)

**Riesgo:** si Roboflow reparte las fotos *al azar* y varias son del mismo vehículo, el test queda «contaminado» y las métricas salen infladas.

**Camino recomendado** (lo **externo** va solo a train; ver §0):
1. En Roboflow se **anota y se genera una versión SIN aumentos** (augmentation vacío) y con preprocesamiento mínimo, en **cada** proyecto (`base-externa` y `vmp-propias`).
2. Se **exporta en formato YOLO** (en Roboflow suele llamarse *YOLOv8*: es el YOLO genérico que usan YOLOv8/YOLO11/YOLO26) y se sube a Drive (`docs/17`).
3. En Colab, el script de partición (`docs/16` §3) **re-reparte por vehículo** (70/20/10 por defecto sobre **nuestras** fotos; semilla fija) y manda **todo lo externo a train**.
4. Los **aumentos los aplica Ultralytics durante el entrenamiento** (solo sobre train, sin duplicar archivos). Así no hay copias aumentadas de una foto repartidas entre train y test.

**Versionado:** cada vez que cambie el contenido (más fotos, correcciones), crear una **versión nueva** y anotar con qué versión se entrenó cada modelo (`dataset_version` en el reporte). Nunca sobrescribir.

## 7. Calidad y control

| Control | Cómo | Cuándo |
|---|---|---|
| **Revisión cruzada** | Otra persona revisa ≥ 20 % de cada lote (o todo el lote al inicio) | Antes de generar la versión |
| **Consistencia** | Misma regla de caja y de casos grises en todos | Acta de decisiones |
| **Salud del dataset** | Conteo de imágenes y de objetos **por clase**, por condición (hora/luz) y por fotógrafo; detectar clases con muy pocos ejemplos | Cada versión |
| **Duplicados** | Detectar fotos casi idénticas (misma ráfaga) y quitar sobrantes | Antes de dividir |
| **Test blindado** | El test **no** se usa para decidir nada; solo para el reporte final de cada experimento | Siempre |
| **Errores del modelo → datos** | Revisar los fallos de E2 y capturar más fotos de esos casos | Tras cada entrenamiento |

## 8. Fuentes adicionales (complemento, nunca sustituto)

- **Roboflow Universe** (datasets públicos; candidatos y mapeo en §0.2–0.3): útil para *arrancar* o enriquecer el set de entrenamiento. ⚠ Revisar **licencia** de cada dataset y su calidad; **no mezclarlos en el test** (el test debe ser solo fotos nuestras, del entorno real), y reportar siempre qué proporción del entrenamiento es externa.
- COCO ya cubre `bicycle` por el preentrenamiento, pero no `scooter`; no sustituye fotos del entorno real de la Torre Arequipa.
- Imágenes de internet: solo con licencia compatible; preferir fotos propias.

## 9. Checklist «listo para entrenar»

- [ ] Workspace con los 4 integrantes; visibilidad del proyecto verificada (privado).
- [ ] Dataset base **revisado a ojo** (30–50 imágenes), *fork* hecho, `ATRIBUCIONES.md` completo.
- [ ] Clases de `base-externa` renombradas a `scooter` y `bicicleta` (y las demás borradas); conteos por clase revisados.
- [ ] Clases y casos grises acordados por escrito.
- [ ] `registro_capturas.csv` completo, con consentimientos y columna «eléctrica».
- [ ] Nombres de archivo con la convención `<tipo>-v<ID>-<nnn>`.
- [ ] Todas las imágenes de los lotes anotadas y revisadas por otra persona.
- [ ] Conteos por clase impresos y revisados (¿alguna clase casi vacía en las fotos propias?).
- [ ] Versiones de Roboflow **sin aumentos** exportadas en formato YOLO y subidas a Drive (`externo-*.zip`, `propias.zip`).
- [ ] Cuaderno de Colab probado hasta la partición, sin subconjuntos vacíos (`docs/17` §6).

## 10. Errores comunes

| Error | Consecuencia | Evitarlo |
|---|---|---|
| Cajas sueltas o que incluyen a la persona | Modelo confunde persona con vehículo | Regla de oro del §1 |
| Mismo vehículo en train y test | Métricas infladas | Partición por `v<ID>` (§6) |
| Clase con 3 fotos | Modelo ciego para esa clase | Health check; capturar más |
| Solo fotos de día | Falla al anochecer | Cubrir franjas horarias |
| Solo fotos de cerca | Falla con cámara de zona lejana | Incluir distancias |
| API key en el repositorio o en el cuaderno | Fuga de acceso | Variable de entorno / *Secrets* de Colab |
| Subir fotos con rostros a un proyecto público | Problema de privacidad | §2 punto 4 |
| Auto-etiquetas sin revisar | Dataset ruidoso | Revisión humana siempre |
| Borrar clases en el proyecto equivocado | Pérdida irreversible de anotaciones | Solo Giancarlo, y solo en `base-externa` |
