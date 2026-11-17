# Contrato del servicio de IA (detector)

> Este documento es el acuerdo entre el **backend** y el **servicio de IA**
> (`ia_service`, YOLO26 + `best.pt` de la Fase 1). Si el detector cambia, se
> cambia aquí primero. El backend ya está construido contra este contrato y se
> prueba con un doble (`IA_MODO=stub`).

## 1. Principio

**La IA mide; el backend decide.** El servicio responde qué vehículos hay en
la imagen, con qué confianza y cuánto se parece cada uno a las fotos de
referencia que el backend le envía (`docs/26`). No conoce usuarios, no consulta la base y **nunca**
dice si alguien puede pasar.

## 2. Transporte

- HTTP/1.1, JSON y `multipart/form-data`. Sin autenticación en la red local del
  avance; si se expone fuera, se añade un token de servicio (pendiente).
- El backend llama con **tiempo límite** (`IA_TIMEOUT_SEG`, por defecto 8 s).
  Si se agota o falla, el ingreso **no se cae**: queda `ia_no_disponible` y el
  guardia decide a mano.
- La llamada de salud usa como máximo 3 s.

## 3. Endpoints que debe exponer el servicio

### 3.1 `GET /v1/salud`

```json
{
  "estado": "ok",
  "modelo_version": "yolo26n-vmp-2026-11-20",
  "clases": ["scooter", "bicicleta", "moto_electrica"],
  "comparador_version": "<modelo del vector>",
  "device": "cpu"
}
```

El backend lo usa en `GET /salud` (no lo llama en cada ingreso). Si no responde,
`salud.ia.disponible = false`, pero el backend sigue funcionando.

### 3.2 `POST /v1/validar` — validar el ingreso

`multipart/form-data`:

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `imagen` | archivo | sí | JPG ya normalizado por el backend (máx. 1280 px de lado) |
| `tipos_esperados` | texto JSON | sí | p. ej. `["scooter_electrico","bicicleta"]` — los tipos de VMP activos del usuario |

| `referencias` | archivos (0 a 3) | no | Fotos de referencia de los vehículos activos del usuario, ya normalizadas |
| `referencias_meta` | texto JSON | sí si hay `referencias` | `[{"id_vehiculo": 12, "tipo_vmp": "scooter_electrico"}]`, en el **mismo orden** que los archivos |

`tipos_esperados` es **informativo**: el detector puede ignorarlo; el backend
hace la correspondencia tipo↔clase (§5).

Respuesta `200`:

```json
{
  "detecciones": [
    { "clase": "scooter", "confianza": 0.91, "caja": [0.31, 0.22, 0.62, 0.78],
      "semejanzas": [ { "id_vehiculo": 12, "semejanza": 0.83 } ] }
  ],
  "modelo_version": "E2-3clases",
  "comparador_version": "<modelo del vector>",
  "ms": 310
}
```

Reglas de la respuesta:

- `clase` ∈ `scooter` | `bicicleta` | `moto_electrica` (modelo `E2-3clases`). Cualquier otra
  clase se trata como «tipo no reconocido» y va a `verificar`.
- `confianza` es un número entre 0 y 1 (no un porcentaje).
- `caja` es opcional, normalizada `[x1, y1, x2, y2]` respecto al ancho/alto de la
  imagen. El backend la guarda como evidencia y no la interpreta.
- `detecciones: []` es válido (no se vio ningún vehículo).
- `modelo_version` es obligatorio: queda registrado en `evento_deteccion_ia`.
- `semejanzas` trae, por cada detección, la semejanza coseno (0 a 1) con cada
  referencia **cuyo tipo sea compatible con la clase detectada**. Se calcula
  entre el recorte de la detección y el recorte del vehículo en la referencia.
  `semejanzas: []` es válido (no había referencia comparable).
- El backend evalúa **todas** las detecciones con confianza ≥ umbral, no solo la mejor.

**Video en vivo (17-nov-2026):** el backend llama a este endpoint varias veces por
segundo con las mismas referencias (`POST /acceso/{id}/cuadro`). El servicio guarda el
vector de cada referencia por huella SHA-256 de la foto y tipo (máximo 64), así que
reenviarlas no repite el trabajo. Medido en la laptop de desarrollo (CPU): 80–280 ms
por cuadro.

### 3.3 `POST /v1/validar-foto-referencia` — foto que registra el usuario (HU03)

`multipart/form-data` con `imagen`. Respuesta **la misma forma** que §3.2.
El backend rechaza la foto con `FOTO_SIN_VEHICULO` si `detecciones` viene vacío.

Se permite además la forma corta, por compatibilidad:

```json
{ "clase": "scooter", "confianza": 0.88, "modelo_version": "…", "ms": 120 }
```

## 4. Errores del servicio

- Cualquier `4xx`/`5xx`, respuesta ilegible o tiempo agotado ⇒ el backend lo
  trata como **IA no disponible** (`ia_no_disponible`, motivo `IA_NO_DISPONIBLE`).
- No hace falta un cuerpo de error especial; el backend no lo muestra al guardia.
- El servicio **no debe** responder `200` con un mensaje de error en texto: si
  algo falla, usa un código HTTP de error.

## 5. Qué hace el backend con la respuesta

Tabla vigente (`docs/26` §3). Dos umbrales **provisionales**: `IA_UMBRAL_VALIDADO`
(confianza del detector, 0.60) e `IA_UMBRAL_SEMEJANZA` (0.70). Ambos se miden con
fotos propias antes de darlos por buenos.

| Situación | `estado_validacion` | Motivo |
|---|---|---|
| Alguna detección confiable es de una clase del usuario **y** su semejanza con ese vehículo ≥ umbral | `validado` | — |
| La clase corresponde, pero la semejanza queda por debajo del umbral | `verificar` | `SEMEJANZA_BAJA` |
| La clase corresponde, pero no hay referencia comparable | `verificar` | `SIN_REFERENCIA_COMPARABLE` |
| Se reconoce el vehículo, pero ya tiene un ingreso vigente (no hay registro de salida en este avance) | `verificar` | `VEHICULO_YA_DENTRO` |
| Ninguna detección confiable corresponde a un tipo del usuario | `rechazado` | `VEHICULO_NO_COINCIDE` |
| Ninguna detección alcanza el umbral de confianza | `verificar` | `CONFIANZA_DUDOSA` |
| `detecciones` vacío | `verificar` | `SIN_DETECCION` |
| Clase desconocida | `verificar` | `TIPO_NO_RECONOCIDO` |
| Falla o tiempo agotado | `ia_no_disponible` | `IA_NO_DISPONIBLE` |

Correspondencia de clases: `scooter` → `scooter_electrico`;
`bicicleta` → `bicicleta` y `bicicleta_electrica`; `moto_electrica` → `moto_electrica`.

`rechazado` **no cierra el ingreso**: el guardia debe decidir
(`aprobar_manual` / `rechazar`) y la decisión queda auditada.

## 6. Cómo se conecta

```env
IA_MODO=http
IA_URL=http://localhost:8001
IA_TIMEOUT_SEG=8
IA_UMBRAL_VALIDADO=0.60
IA_UMBRAL_SEMEJANZA=0.70
```

- `IA_MODO=stub` (por defecto): doble de prueba. Deduce la clase del **nombre del
  archivo**: contiene `vacio`/`nada` → sin detecciones; `bicicleta` → bicicleta;
  `moto` → moto_electrica; `dudosa` → confianza 0.45 (zona gris); el resto → scooter 0.90.
  Semejanza: 0.85 por defecto; `distinto` → 0.20; `ultimo` → se parece más al último
  vehículo registrado; `ajeno` → un scooter ajeno y una bicicleta en la misma foto.
- `IA_MODO=http`: usa este contrato.

Prueba de integración real (no corre por defecto):

```powershell
cd backend
$env:IA_MODO="http"; $env:IA_URL="http://localhost:8001"
.\.venv\Scripts\python.exe -m pytest -m lenta tests\test_ia_real.py
```

Requiere el servicio arriba y una foto en `backend/tests/fixtures/scooter.jpg`
(o `bicicleta.jpg`). Si falta cualquiera de los dos, la prueba **se omite**.
