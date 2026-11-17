# 04 · Arquitectura

> **[DOC]** = decisión del Avance 2 / documento de arquitectura. **[PROPUESTA]** = diseño nuestro para poder implementarlo. La arquitectura documentada llega hasta el nivel de componentes; lo que hay por debajo (carpetas, protocolos, flujos detallados) es propuesta.

## 1. Decisión central [DOC]

**Monolito modular**: una sola aplicación, una sola base de datos, organizada en **4 módulos por dominio de negocio** (no por capas técnicas tipo MVC). Solo la **detección con IA** vive aparte (otro stack y otra carga). Un **Conector/Adaptador UTP** simulado aísla los sistemas de la UTP.

| Pregunta | Respuesta del equipo |
|---|---|
| ¿Por qué monolito modular y no microservicios? | Piloto de una sola sede con 40 espacios; una sola BD con un ER coherente; menor costo y riesgo para 4 personas; patrón *monolith first* (Fowler): se separa cuando haga falta. |
| ¿Por qué no MVC? | MVC divide por capa técnica; aquí se divide por capacidad de negocio y además hay un servicio de IA independiente y un adaptador a un sistema externo. |
| ¿Cómo escala? | Los módulos ya están separados por dominio; el primer candidato a extraerse es el servicio de IA (carga de video de muchas sedes). `sede` en `USUARIO_UTP` y `ZONA_ESTACIONAMIENTO` prepara multi-sede. |
| ¿Y si la UTP no da acceso? | Solo cambia el Conector/Adaptador. El resto no se toca. |
| ¿Qué pasa si falla la IA? | La comunicación es asíncrona; el resto sigue vivo. Seguridad valida manualmente desde el panel y registra incidencia. |

Disparadores para pasar a microservicios más adelante: escalado independiente (IA), equipos distintos estorbándose, tecnologías distintas por módulo, aislamiento de fallas.

## 2. Componentes [DOC]

| Componente | Naturaleza | Función |
|---|---|---|
| App UTP | Externa (simulada) | Muestra el QR del usuario; recibe notificaciones push |
| Portal UTP | Externa (simulada) | Login, registro de datos y de hasta 3 VMP con foto |
| Conector / Adaptador UTP | Propio, simulado | Único componente que habla con la UTP; deja rastro en `SINCRONIZACION_UTP` |
| Panel Web de Seguridad y Administración | Propio | Monitoreo de cámaras, mapa de espacios, ingresos/salidas, incidencias, historial, reportes |
| API Gateway interno | Propio | Entrada única; enruta al módulo correcto; centraliza autenticación/autorización |
| Identidad y Accesos | Módulo | Valida usuario y QR; gestiona vehículos |
| Estacionamiento e IA | Módulo | Zonas, espacios, sesiones, eventos de IA |
| Administración e Incidencias | Módulo | Personal de seguridad; seguimiento de incidencias |
| Notificaciones y Reportes | Módulo | Push al usuario; indicadores del piloto |
| Servicio de IA – Detección | Servicio aparte (Python + YOLOv8 + OpenCV) | Detecta vehículos, compara con la foto registrada, detecta ocupación/liberación |
| Base de datos única | Compartida por los 4 módulos | Las 12 tablas del ER |
| Infraestructura en la nube | Contenedor exterior | Cómputo, almacenamiento, balanceo |

### Propiedad de tablas por módulo [DOC]

| Módulo | Tablas que le pertenecen |
|---|---|
| Identidad y Accesos | `usuario_utp`, `sincronizacion_utp`, `vehiculo_vmp`, `codigo_qr` |
| Estacionamiento e IA | `zona_estacionamiento`, `espacio_estacionamiento`, `sesion_estacionamiento`, `evento_deteccion_ia` |
| Administración e Incidencias | `personal_seguridad`, `incidencia` |
| Notificaciones y Reportes | `notificacion`, `reporte_piloto` |

## 3. Tipos de comunicación [DOC]

| Tipo | Dónde | Por qué |
|---|---|---|
| **Llamada interna (síncrona)** | Entre los 4 módulos del monolito | Misma aplicación; sin red; más simple |
| **Evento (asíncrono)** | Servicio de IA → módulo Estacionamiento e IA (línea punteada) | Las cámaras generan datos continuamente; la IA no debe esperar respuesta en cada detección |

## 4. Flujo de un ingreso, según el documento [DOC]

1. El usuario muestra el QR en la App UTP en el punto de acceso.
2. La lectura entra por el API Gateway a **Identidad y Accesos**.
3. Se valida QR y usuario; los datos de la UTP llegan por el Conector.
4. Se captura la imagen del VMP; el **Servicio de IA** la compara con la foto de referencia.
5. El resultado llega a **Estacionamiento e IA** como **evento asíncrono**: se crea la sesión y se actualiza el espacio.
6. Todo se guarda en la BD única.
7. **Notificaciones** envía el push «Ingreso registrado».
8. Si no coincide, **Administración e Incidencias** abre incidencia para seguridad.

### Salida [DOC]
La cámara de zona detecta el espacio vacío → evento de liberación → espacio `disponible`, la sesión registra `fecha_hora_salida` y pasa a `finalizada`. Permanencia = salida − ingreso.

## 5. Reconciliar «evento asíncrono» con «respuesta rápida» **[PROPUESTA]**

El guardia necesita ver «puede ingresar / rechazado» en segundos, pero el documento dice que el resultado de la IA llega por evento asíncrono. Se resuelve así (no contradice el diseño; lo concreta):

1. `POST /acceso/qr` (síncrono) valida el QR y crea una **sesión preliminar** (`estado_sesion = en_curso`, `resultado_validacion = NULL`) → devuelve `id_sesion` y la lista de vehículos del usuario.
2. `POST /acceso/{id_sesion}/captura` sube la foto → el monolito publica `ia.solicitud_validacion` (evento) y responde **202 Accepted**.
3. El servicio de IA procesa y publica `ia.validacion_completada` (evento) con puntajes por vehículo.
4. El monolito consume el evento, aplica el umbral/regla, actualiza la sesión, crea incidencia si corresponde y emite un evento de UI.
5. La tablet del acceso recibe el resultado por **SSE** (Server-Sent Events) o, como alternativa más simple, **polling corto** a `GET /acceso/{id_sesion}`.

Alternativa si el bus asíncrono complica el prototipo: llamada HTTP directa monolito→IA con timeout corto para la validación de ingreso, y eventos solo para ocupación/liberación. **[PENDIENTE]** decidir (`docs/13` #6). El bus de eventos **es** lo documentado; la HTTP directa sería una desviación consciente.

## 6. Estructura del repositorio **[PROPUESTA]**

```
estacionamiento-vmp/
├── docs/                          # estos .md
├── docker-compose.yml
├── .env.example
├── backend/                       # monolito modular (FastAPI)
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/versions/
│   ├── app/
│   │   ├── main.py                # crea la app, monta routers, middlewares
│   │   ├── core/                  # config, db, seguridad, logging, eventos (bus)
│   │   │   ├── config.py          # Settings (pydantic-settings)
│   │   │   ├── db.py              # engine, SessionLocal, Base
│   │   │   ├── security.py        # JWT, hash bcrypt, hash SHA-256 de tokens
│   │   │   ├── events.py          # publicar/consumir en Redis Streams
│   │   │   └── storage.py         # S3/MinIO: subir foto, URL firmada
│   │   ├── gateway/               # API Gateway interno: auth, roles, rutas
│   │   ├── modules/
│   │   │   ├── identidad/         # usuario_utp, sincronizacion_utp, vehiculo_vmp, codigo_qr
│   │   │   │   ├── models.py  schemas.py  repository.py  service.py  router.py
│   │   │   │   └── conector_utp/  # interfaz + implementación simulada
│   │   │   ├── estacionamiento/   # zona, espacio, sesion, evento_deteccion_ia
│   │   │   ├── administracion/    # personal_seguridad, incidencia
│   │   │   └── notificaciones/    # notificacion, reporte_piloto
│   │   └── tests/                 # unit/ integration/ e2e/
│   └── Dockerfile
├── ia_service/                    # servicio de IA (detector + comparador)
│   ├── demo/                      # detectar.py, comparar_modelos.py   (docs/16 §4–§5)
│   ├── training/                  # split_dataset.py, entrenamiento y evaluación (docs/16 §3, §6)
│   ├── notebooks/                 # cuaderno de Colab (docs/17)
│   ├── tests/                     # pruebas automáticas (docs/16 §8)
│   ├── resultados/                # E1.md, E2.md… generados por script (se versionan)
│   ├── app/                       # consumidor de eventos, endpoints de salud   (por hacer)
│   ├── detector/                  # carga el modelo, inferencia                 (por hacer)
│   ├── matcher/                   # comparación con foto de referencia          (por hacer)
│   ├── zonas/                     # ROIs por cámara (casillas), estabilidad     (por hacer)
│   ├── models/                    # best.pt (NO se versiona; va a S3)
│   └── Dockerfile
├── panel/                         # React + Vite (seguridad/admin)
├── simulador_utp/                 # Portal UTP + App UTP simulados (Vite/React o HTML)
├── simulador_camaras/             # reproduce videos/imágenes como cámaras
├── infra/                         # Terraform, nginx.conf, scripts de despliegue
└── .github/workflows/             # ci.yml, cd.yml
```

### Reglas de dependencia entre módulos **[PROPUESTA]**

```
router → service → repository → models
             │
             └── (otros módulos) solo vía  <modulo>.service  (interfaz pública)
```

- `identidad` puede ser llamado por todos (validar QR, obtener usuario/vehículos).
- `estacionamiento` llama a `identidad` (validar QR, vehículos) y publica eventos para `notificaciones` y `administracion`.
- `administracion` llama a `estacionamiento` (sesión) para crear incidencias.
- `notificaciones` **escucha** eventos; no es llamado directamente por flujos críticos (si falla, no rompe el ingreso).
- Prohibido: importar `models` o `repository` de otro módulo; hacer JOIN entre tablas de módulos distintos en un repositorio (para lecturas combinadas del panel se crea un servicio de **consulta** en `administracion` o `estacionamiento` que compone llamadas públicas, o una vista SQL de solo lectura documentada).

> Nota: el ER tiene FKs entre módulos (p. ej. `sesion_estacionamiento.id_usuario_utp`). Eso es aceptable en la BD única; la regla de arriba limita el **acoplamiento de código**, no las claves foráneas.

## 7. Eventos y colas **[PROPUESTA]**

Resumen (detalle de contratos en `docs/07-API-EVENTOS.md`):

| Stream (Redis) | Productor | Consumidor | Cuándo |
|---|---|---|---|
| `ia.validacion.solicitada` | Monolito (estacionamiento) | Servicio IA | Se subió la foto del ingreso |
| `ia.validacion.completada` | Servicio IA | Monolito (estacionamiento) | La IA terminó de comparar |
| `ia.espacio.ocupado` | Servicio IA | Monolito (estacionamiento) | Casilla confirmada ocupada |
| `ia.espacio.liberado` | Servicio IA | Monolito (estacionamiento) | Casilla confirmada libre |
| `parking.ingreso.validado` | Monolito | Notificaciones | Ingreso validado (push) |
| `parking.ingreso.rechazado` | Monolito | Administración, Notificaciones | Crea incidencia + aviso |
| `parking.zona.llena` | Monolito | Notificaciones | Ocupación 100 % |
| `parking.espacio.cambio` | Monolito | Panel (SSE) | Para refrescar el mapa |

Garantías: *at-least-once* con **idempotencia** (cada evento lleva `event_id` UUID; el consumidor ignora duplicados). Cola de mensajes muertos `*.dlq` tras 3 reintentos.

## 8. Despliegue (vista lógica) **[PROPUESTA]**

```
Internet ── Nginx (TLS, rate limit) ── backend (FastAPI + gateway) ──┬── PostgreSQL
                                                     │              ├── Redis (streams)
                                         panel (estático)           └── S3/MinIO (fotos)
Cámaras / simulador ── RTSP/HTTP ── ia_service (GPU opcional) ── Redis / S3
```

Detalle de infraestructura en `docs/09-DEVOPS-INFRA.md`.

## 9. Riesgos arquitectónicos

| Riesgo | Mitigación |
|---|---|
| IA bloquea la validación de ingreso | Timeout, modo manual desde panel, estado «pendiente de IA» visible |
| Eventos duplicados o desordenados | `event_id` + idempotencia; `ultima_actualizacion` con *compare-and-set* |
| Dos sesiones apuntan al mismo espacio | Restricción: solo una sesión `en_curso` por `id_espacio` (índice único parcial, ver docs/05) |
| Conector UTP inestable en producción | Interfaz `ConectorUTP` + registro en `sincronizacion_utp` + caché corta de usuario |
| Latencia de la IA en CPU | Redimensionar entrada, `yolov8n/s`, procesar 1 de N cuadros en cámaras de zona |
