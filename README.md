# Estacionamiento inteligente para VMP · UTP Torre Arequipa

Sistema de ingreso al estacionamiento de **vehículos de movilidad personal** (scooters, bicicletas y motos eléctricas) que valida cada ingreso con un **código QR** y con **visión por computadora**.

Proyecto del curso *Innovación y Transformación Digital* (Universidad Tecnológica del Perú, ciclo 2026-II). Es un **prototipo académico: no es un sistema oficial de la UTP** y no se conecta con sus sistemas reales.

## El problema

En la Torre Arequipa (Sede Centro) el ingreso y la salida de VMP son manuales: hay colas en horas punta, no se puede verificar a quién pertenece cada vehículo y no queda registro digital de quién entró.

## Cómo funciona

1. **Registro (Portal UTP).** El estudiante, docente o administrativo acepta el tratamiento de sus datos y registra hasta **3 vehículos** con una foto. La IA comprueba que la foto muestre un vehículo del tipo declarado.
2. **QR personal (App UTP).** Cada usuario tiene un QR con vigencia por ciclo académico. El QR guarda un token opaco, no datos personales.
3. **Ingreso (punto de acceso).** El guardia acerca el QR a la cámara y la IA analiza el **video en vivo**:
   - un detector **YOLO26** reconoce si hay un VMP y de qué tipo (`scooter`, `bicicleta`, `moto_electrica`);
   - un comparador de imágenes mide cuánto se parece a la foto que el usuario registró.
4. **Decisión.** Si ambos superan su umbral en varios cuadros seguidos, el ingreso se valida y se **asigna un espacio** (por ejemplo `A-01`). Si hay dudas, **decide el guardia** con un motivo. La IA nunca rechaza sola.
5. **Monitoreo.** Seguridad ve los espacios libres y ocupados de las 5 zonas (40 espacios) y quién ocupa cada uno. El usuario no ve el mapa de espacios.

Cada decisión guarda evidencia: la imagen, la clase detectada, la confianza y la semejanza. Los intentos fallidos también quedan registrados.

## Arquitectura

```
 Navegador (React)                      Backend (FastAPI)                     Servicio de IA (FastAPI)
 ┌──────────────────────┐   HTTP    ┌──────────────────────────────┐  HTTP   ┌──────────────────────────┐
 │ /portal   Portal UTP │ ────────► │ Monolito modular             │ ──────► │ Detector YOLO26          │
 │ /app      App UTP    │           │  · Identidad y accesos       │         │ Comparador de semejanza  │
 │ /acceso   Guardia    │           │  · Estacionamiento e IA      │         │ (ResNet-18, torchvision) │
 │ /espacios Monitoreo  │           │  · Conector UTP (simulado)   │         └──────────────────────────┘
 └──────────────────────┘           └──────────────┬───────────────┘
                                                   │
                                          PostgreSQL + fotos en disco
```

| Parte | Tecnología |
|---|---|
| Frontend | React, Vite, TypeScript, jsQR |
| Backend | Python 3.11, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL |
| IA | Ultralytics YOLO26 (modelo `E2-3clases`), PyTorch y torchvision (CPU), Pillow |
| Entrenamiento | Google Colab (GPU), datasets de Roboflow Universe |
| Infraestructura | Docker y Docker Compose |
| Pruebas | pytest, vitest, Ruff |

## Cómo correrlo

**Requisitos:** Docker Desktop. Para usar el detector real, los pesos `ia_service/pesos/E2-3clases-best.pt`: **no se incluyen en el repositorio** (ver `ia_service/pesos/LEEME.md`). Sin ellos, el sistema funciona con un doble de la IA que responde según el nombre del archivo.

```powershell
# Todo, con el detector real
$env:IA_MODO="http"; docker compose --profile ia up -d --build

# Sin los pesos (doble de la IA)
docker compose up -d --build
```

Si el puerto 5432 ya está ocupado en tu equipo, antepón `$env:DB_PUERTO="55433";`. La primera construcción descarga unos 3 GB.

En Windows, `.\scripts\reiniciar-demo.ps1` deja la demo en cero: borra vehículos, fotos e ingresos, mantiene los perfiles y espera a que la IA esté lista.

| Dirección | Qué es |
|---|---|
| <http://localhost:5173/portal> | Portal UTP: registro de vehículos |
| <http://localhost:5173/app> | App UTP: QR del usuario (pensada para celular) |
| <http://localhost:5173/acceso> | Punto de acceso del guardia |
| <http://localhost:5173/espacios> | Monitoreo de espacios |
| <http://localhost:8000/docs> | Documentación interactiva de la API |

**Inicio de sesión simulado:** el Portal y la App piden solo un código UTP de ejemplo, sin contraseña; el guardia elige su usuario. Existe únicamente en modo desarrollo, porque en el sistema real autenticaría la UTP. Los perfiles de ejemplo aparecen en la pantalla de inicio.

La guía paso a paso para probar todo está en [`docs/27-GUIA-DEMO.md`](docs/27-GUIA-DEMO.md).

## Estructura

| Carpeta | Contenido |
|---|---|
| `backend/` | API, modelo de datos, migraciones y pruebas. Ver [`backend/README.md`](backend/README.md) |
| `ia_service/app/` | Servicio de IA: detector y comparador. Ver [`ia_service/README.md`](ia_service/README.md) |
| `ia_service/training/` | Cuaderno de Colab y herramientas para armar el dataset y entrenar |
| `ia_service/resultados/` | Reportes de evaluación generados por el cuaderno |
| `frontend/` | Portal, App, punto de acceso y monitoreo. Ver [`frontend/README.md`](frontend/README.md) |
| `docs/` | Documentación del proyecto (ver abajo) |
| `scripts/` | Utilidades para la demo |

## El modelo de IA

Modelo `E2-3clases`: YOLO26n entrenado en Colab con 3 clases. Evaluación sobre el conjunto de test (**785 imágenes**), tomada de [`ia_service/resultados/E2-3clases.md`](ia_service/resultados/E2-3clases.md):

| Clase | Objetos | Precisión | Recall | mAP50 | mAP50-95 |
|---|---|---|---|---|---|
| scooter | 408 | 0.906 | 0.893 | 0.936 | 0.665 |
| bicicleta | 200 | 0.952 | 0.975 | 0.981 | 0.743 |
| moto_electrica | 339 | 0.962 | 0.968 | 0.990 | 0.794 |
| **Global** | 947 | **0.940** | **0.945** | **0.969** | **0.734** |

**Advertencias:**

- El test sale de datasets externos, no de fotos tomadas en la Torre Arequipa: estas cifras no representan el desempeño en el lugar real.
- `moto_electrica` se entrenó con fotos de motos en general, muchas a gasolina.
- La semejanza compara la imagen completa (forma, color y fondo): no identifica «este vehículo exacto».
- Los umbrales (confianza 60 %, semejanza 70 %) son provisionales hasta medirlos con fotos propias.

## Pruebas

```powershell
cd backend;    pytest -q              # necesita PostgreSQL (ver backend/README.md)
cd ia_service; pytest -q
cd frontend;   npm test; npm run lint; npm run build
```

## Documentación

Las etiquetas de los documentos indican el origen de cada punto: **[DOC]** está en los entregables del curso (Avance 1 y 2), **[PROPUESTA]** es una propuesta técnica del equipo y **[PENDIENTE]** es una decisión abierta.

| Documento | Tema |
|---|---|
| [01 · Contexto](docs/01-CONTEXTO.md) | Problema, alcance y glosario |
| [02 · Requisitos](docs/02-REQUISITOS.md) | Requisitos funcionales, reglas de negocio y no funcionales |
| [03 · Historias de usuario](docs/03-BACKLOG-HU.md) | Backlog: 6 épicas y 24 historias |
| [04 · Arquitectura](docs/04-ARQUITECTURA.md) | Monolito modular y servicio de IA |
| [05 · Modelo de datos](docs/05-MODELO-DATOS.md) | Entidades y relaciones |
| [06 · IA](docs/06-IA-ML.md) | Detector, umbrales y evaluación |
| [07 · API y eventos](docs/07-API-EVENTOS.md) | Diseño de la API del producto completo |
| [08 · Pantallas](docs/08-PANTALLAS-PROTOTIPOS.md) | Pantallas y prototipos |
| [09 · DevOps](docs/09-DEVOPS-INFRA.md) | Infraestructura propuesta para producción |
| [10 · Seguridad y privacidad](docs/10-SEGURIDAD-PRIVACIDAD.md) | Datos personales, QR e imágenes |
| [11 · Pruebas y piloto](docs/11-PRUEBAS-PILOTO.md) | Estrategia de pruebas y piloto |
| [14 · Dataset](docs/14-DATASET-ROBOFLOW.md) | Armado y etiquetado del dataset |
| [17 · Entrenamiento](docs/17-ENTRENAMIENTO-COLAB.md) | Entrenamiento y evaluación en Colab |
| [18 · Backend del avance](docs/18-BACKEND-AVANCE.md) | Alcance y endpoints construidos |
| [19 · Requisitos del avance](docs/19-REQUISITOS-DEL-AVANCE.md) | Criterios de aceptación |
| [20 · Frontend del avance](docs/20-FRONTEND-AVANCE.md) | Pantallas construidas |
| [21 · Herramientas](docs/21-DEVOPS-HERRAMIENTAS.md) | Herramientas usadas y descartadas |
| [26 · Semejanza](docs/26-SEMEJANZA-CON-FOTO-REGISTRADA.md) | Comparación con la foto registrada |
| [27 · Guía de la demo](docs/27-GUIA-DEMO.md) | Cómo probar todo y grabar la demo |
| [Contrato de la IA](docs/IA-CONTRATO.md) | Contrato entre el backend y el servicio de IA |

## Limitaciones

- Simulación: los datos de la UTP vienen de un conector simulado, no de sus sistemas.
- El inicio de sesión sin contraseña solo existe en modo desarrollo.
- Todavía no hay cámaras en las casillas: el espacio se asigna al validar el ingreso y la salida la registra el guardia.
- El ensayo completo se hizo con una cámara simulada; falta medir con cámaras y vehículos reales en la sede.

## Equipo

- Raphael Saimon Caballero Castillo (Scrum Master)
- Giancarlo Jesus Condori Yucra
- José Alberto Huaraca Escobar (Product Owner)
- Miladia Paloma Villavicencio Huaman

## Atribuciones

Los datasets usados para entrenar (Roboflow Universe, licencia CC BY 4.0) se citan en [`ia_service/ATRIBUCIONES.md`](ia_service/ATRIBUCIONES.md). Los datasets, las imágenes y los pesos del modelo no se incluyen en el repositorio.
