# Servicio de IA · detector y comparador de semejanza

Responde las tres comprobaciones del ingreso (`docs/26`): **¿hay un VMP?**, **¿de qué clase?** y **¿cuánto se parece a las fotos registradas?** No conoce usuarios y no decide nada: mide, y el backend decide (`docs/IA-CONTRATO.md`).

| Parte | Archivo | Qué hace |
|---|---|---|
| Detector | `app/detector.py` | YOLO26 con los pesos `E2-3clases` (3 clases) |
| Comparador | `app/comparador.py` | Recorta el vehículo, saca un vector con una red preentrenada de `torchvision` (`resnet18`) y calcula el coseno |
| Unión | `app/servicio.py` | Compara cada detección con las referencias de un tipo compatible |
| API | `app/main.py` | `GET /v1/salud`, `POST /v1/validar`, `POST /v1/validar-foto-referencia` |

## Puesta en marcha (Windows, PowerShell)

```powershell
cd ia_service
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -U pip
.\.venv\Scripts\python -m pip install -e ".[dev]"
# Copia E2-3clases-best.pt a ia_service\pesos\ (ver pesos\LEEME.md)
.\.venv\Scripts\python -m uvicorn app.main:app --port 8001
```

Los modelos se cargan en la primera petición (unos segundos). La primera vez se descarga la red del comparador (unos 45 MB).

Para que el backend lo use: `IA_MODO=http` e `IA_URL=http://localhost:8001` en `backend/.env`.

## Pruebas

```powershell
.\.venv\Scripts\python -m pytest -q            # rápidas: usan dobles, no cargan modelos
.\.venv\Scripts\python -m pytest -q -m lenta   # con best.pt y fotos en tests\fixtures\
```

Las pruebas lentas necesitan los pesos y fotos de ejemplo (`scooter-1.jpg`, `bicicleta-1.jpg`, `bicicleta-2.jpg`, `moto-1.jpg`) en `tests/fixtures/`. Ninguno está en Git; si faltan, se omiten.

## Configuración (variables de entorno)

| Variable | Por defecto | Para qué |
|---|---|---|
| `MODELO_PATH` | `pesos/E2-3clases-best.pt` | Pesos del detector |
| `MODELO_VERSION` | `E2-3clases` | Queda registrada en cada evento del backend |
| `COMPARADOR_MODELO` | `resnet18` | Red del vector (`resnet18` o `resnet50`) |
| `CONFIANZA_MINIMA` | `0.25` | Mínimo para devolver una caja. El umbral que decide lo aplica el backend |
| `DEVICE` | `cpu` | |

## Lo que este servicio todavía no demuestra

- **El comparador no está medido.** Que la misma foto dé semejanza 1 solo prueba que el cálculo es correcto. Cuánto separa «mismo vehículo» de «vehículo distinto» se mide con pares de fotos propias (experimento E4, `docs/26` §5).
- **Dos vehículos del mismo modelo y color dan semejanza alta.** Es un segundo factor que se suma al QR, no una identificación única.
- Las métricas del detector son las de `resultados/E2-3clases.md`: test de datasets externos, no de la Torre Arequipa.
- La imagen de Docker pesa unos 2,7 GB (PyTorch de CPU) y usa cerca de 700 MB de memoria en marcha.
