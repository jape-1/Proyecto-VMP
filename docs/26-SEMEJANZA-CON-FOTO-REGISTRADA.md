# 26 · Semejanza entre la foto de la cámara y la foto registrada

> **Decisión del 17-nov-2026 (Giancarlo):** en el ingreso la cámara hace **tres** comprobaciones, no una.
> Adelanta al avance la comparación T1b de `docs/06` §7, que `docs/18` §5 había dejado fuera.
> Cumple la regla de negocio 5 (`docs/02`) **[DOC]**: «si el puntaje de similitud supera el umbral → validado».

## 1. Las tres comprobaciones

| # | Pregunta | Quién responde | Estado |
|---|---|---|---|
| 1 | ¿Hay un VMP en la foto? | Detector YOLO26 (`E2-3clases`) | Modelo entrenado (`docs/25`) |
| 2 | ¿De qué clase es? (`scooter`, `bicicleta`, `moto_electrica`) | El mismo detector | Modelo entrenado |
| 3 | ¿Se parece a **alguno de los vehículos que ese usuario registró** en el Portal? | Comparador por vector de imagen | **Por construir** |

**La IA mide; el backend decide** (principio de `docs/IA-CONTRATO.md` §1, sin cambios).

## 2. Método [PROPUESTA]

Decidido por el equipo: **vector de imagen + semejanza coseno**.

1. Se detecta el vehículo en la foto de la cámara y se **recorta** su caja.
2. Se hace lo mismo con cada foto de referencia del usuario (máximo 3) cuya clase sea compatible.
3. Un modelo preentrenado convierte cada recorte en un vector. No se entrena nada nuevo.
4. La semejanza es el coseno entre el vector de la cámara y el de cada referencia, entre 0 y 1.

**Modelo del vector: se empieza con `resnet18` de `torchvision` (decisión del 17-nov); el definitivo se elige midiendo.** Candidatos (`docs/06` §7 y §16): DINOv2 pequeño; una red de clasificación preentrenada de `torchvision`; `model.embed()` de Ultralytics. Se elige el que mejor separe «mismo vehículo» de «vehículo distinto» en el experimento E4 (§5), siempre que corra en CPU dentro del tiempo límite del backend (`IA_TIMEOUT_SEG`, 8 s).

## 3. Regla de decisión (reemplaza la tabla de `docs/IA-CONTRATO.md` §5)

Se evalúan **todas** las detecciones con confianza ≥ `IA_UMBRAL_VALIDADO` (corrige también el hallazgo 4 de `docs/23`).

| Situación | `estado_validacion` | Motivo |
|---|---|---|
| Alguna detección es de una clase que corresponde a un vehículo del usuario **y** su semejanza con ese vehículo ≥ `IA_UMBRAL_SEMEJANZA` | `validado` (se guarda el `id_vehiculo` más parecido) | — |
| La clase corresponde, pero la semejanza queda por debajo del umbral | `verificar` | `SEMEJANZA_BAJA` (nuevo) |
| La clase corresponde, pero no se pudo comparar (el vehículo no tiene foto, o no se detectó vehículo en la referencia) | `verificar` | `SIN_REFERENCIA_COMPARABLE` (nuevo) |
| Ninguna detección corresponde a un tipo del usuario | `rechazado` | `VEHICULO_NO_COINCIDE` |
| Confianza del detector < umbral | `verificar` | `CONFIANZA_DUDOSA` |
| Sin detecciones | `verificar` | `SIN_DETECCION` |
| Falla o tiempo agotado | `ia_no_disponible` | `IA_NO_DISPONIBLE` |

**Decidido por el equipo:** una semejanza baja **nunca rechaza sola**. Pasa a `verificar` y el guardia decide viendo ambas fotos.

## 4. Cambios de contrato

> **Backend: implementado el 17-nov-2026** (probado con el doble de la IA, `backend/tests/test_semejanza.py`). **Servicio de IA: implementado el 17-nov-2026** con `resnet18` de `torchvision` (`ia_service/`), probado contra el backend por HTTP.

**Servicio de IA.** `POST /v1/validar` recibe además las fotos de referencia y devuelve la semejanza por detección:

- Petición: se añaden las partes `referencias` (archivos, máx. 3) y `referencias_meta` (JSON: `[{id_vehiculo, tipo_vmp}]`, en el mismo orden). El servicio sigue sin guardar nada ni conocer usuarios.
- Respuesta:

```json
{
  "detecciones": [
    { "clase": "scooter", "confianza": 0.91, "caja": [0.31, 0.22, 0.62, 0.78],
      "semejanzas": [ { "id_vehiculo": "…", "semejanza": 0.83 } ] }
  ],
  "modelo_version": "E2-3clases",
  "comparador_version": "<modelo del vector>",
  "ms": 310
}
```

- `GET /v1/salud` informa `clases` (las 3) y `comparador_version`.
- `semejanzas: []` es válido (no hubo referencia comparable).

**Backend.**
- Nueva variable `IA_UMBRAL_SEMEJANZA`.
- Motivos nuevos en `core/enums.Motivo`.
- `SesionEstadoOut` añade `semejanza` (la mejor) e `id_vehiculo_mas_parecido`, junto a `confianza`.
- La semejanza se guarda dentro del JSON `detecciones` de `evento_deteccion_ia`, que ya existe, así que **no hace falta una columna nueva**. Si se quisiera una columna `mejor_semejanza`, es cambio de ER: proponerlo en `docs/13` y esperar aprobación.
- El doble de pruebas (`IA_MODO=stub`) debe poder simular semejanza alta y baja.

**Frontend del guardia.** Muestra «Semejanza: 83 %» junto a la foto de referencia más parecida, además de la confianza del detector.

## 5. Umbral: se mide, no se inventa

- **Experimento E4:** pares de fotos «mismo vehículo» (referencia + foto en el punto de acceso) y «vehículo distinto de la misma clase». Se reporta la distribución de semejanza de cada grupo y la tasa de falsos aceptados y falsos rechazados por umbral.
- **Hacen falta fotos propias.** Los datasets externos no traen el mismo vehículo fotografiado dos veces. Mínimo para una primera medida: cada vehículo del equipo fotografiado como referencia y, aparte, en el punto de acceso.
- Hasta tener esa medida, `IA_UMBRAL_SEMEJANZA` lleva un valor **provisional: 0,70** (decisión de Giancarlo del 17-nov, tras la primera observación de abajo; antes 0,60), declarado como tal en el README y en la exposición, igual que `IA_UMBRAL_VALIDADO`.

### Primera observación (17-nov-2026): no es una medición

Con 6 fotos de los datasets externos (2 por clase, vehículos distintos) y `resnet18`, en la laptop de desarrollo:

| Par | Semejanza |
|---|---|
| La misma foto contra sí misma | 1.00 |
| Dos bicicletas distintas | 0.46–0.47 |
| Dos scooters distintos (fotos distintas) | 0.57–0.59 |
| Dos motos distintas | 0.69 |
| Scooters del mismo modelo en una misma foto | 0.85–0.86 |

Son 3 pares: **no sirven para fijar el umbral**, pero avisan de dos cosas. Con 0,60 una moto distinta habría pasado como «parecida», así que el valor provisional es probablemente bajo. Y los scooters del mismo modelo se confunden, como anticipa la limitación de abajo. Falta lo esencial: pares del **mismo** vehículo en fotos distintas, que solo se consiguen con fotos propias. Tiempo de `POST /v1/validar` con 2 referencias en CPU: 0,4–0,7 s.

## 6. Limitaciones a declarar

- Dos vehículos del **mismo modelo y color** (dos scooters grises iguales) darán semejanza alta: la semejanza es un segundo factor que se suma al QR, no una identificación única.
- La luz, el ángulo y los objetos colgados (mochila, casco) bajan la semejanza. Por eso la foto de referencia tiene pautas y un valor bajo va a `verificar`, no a rechazo.
- La comparación suma tiempo por ingreso (hasta 4 vectores en CPU). Medirlo en la laptop del demo.

## 7. Pruebas mínimas (primero la prueba, luego el código)

1. Clase correcta y semejanza alta → `validado` con el `id_vehiculo` correcto.
2. Clase correcta y semejanza baja → `verificar` con `SEMEJANZA_BAJA`.
3. El usuario tiene dos vehículos de la misma clase → se elige el más parecido.
4. Vehículo sin foto de referencia → `verificar` con `SIN_REFERENCIA_COMPARABLE`.
5. Clase que no corresponde → `rechazado`, sin importar la semejanza.
6. En `ia_service`: la misma imagen contra sí misma da semejanza ≈ 1; el vector tiene norma 1.
