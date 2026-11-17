# 21 · Herramientas del ciclo DevOps para el avance

> **[PROPUESTA]**. Revisión de `docs/09` (8 fases: Plan, Code, Build, Test, Release, Deploy, Operate, Monitor) frente al alcance de `docs/18`–`docs/20` y a la meta de **probar el sistema el 17-nov-2026**. Para cada herramienta: ✅ **necesaria para la prueba** · 🟡 **recomendable** (si hay tiempo) · ⏳ **después** (producto completo, no ahora) · ⛔ **descartada**. Las versiones concretas **no se fijan aquí**: quedan en los archivos de bloqueo al instalar.

## 1. Auditoría rápida de `docs/09` frente al alcance

| Punto de `docs/09` | Veredicto para el avance |
|---|---|
| Compose con `db`, `redis`, `minio`, `backend`, `ia_service`, `simulador_camaras`, `panel`, `simulador_utp` | **Se reduce** a `db`, `backend`, `ia_service`, `app_usuario`, `punto_acceso` (§3). `redis`, `minio`, `simulador_camaras` salen; `simulador_utp` pasa a ser un módulo del backend; `panel` se reemplaza por las dos apps |
| Variables de entorno | Se conservan las de base de datos, JWT, QR, IA y negocio; se **eliminan** Redis, S3, FCM y las de ocupación/casillas. Se **añade** `ENTORNO` (`dev` activa `/dev/sesion/*`), `IA_URL` y `CORS_ORIGINS` |
| IA por Redis Streams | **HTTP con tiempo límite** (`docs/18` §3); Redis queda para después |
| Almacenamiento S3/MinIO | **Disco local con volumen** (`docs/18` §3) |
| CI (`ci.yml`): backend, ia, panel, images | Se conserva con `app_usuario` y `punto_acceso` en lugar de `panel` |
| CD, Terraform, AWS, CloudWatch, SNS | ⏳ Fuera del avance |
| `docs/09` menciona **YOLOv8** | El equipo usa **YOLO26** (`docs/13` #20) |
| Cobertura mínima 70 % | Punto de partida; **no** bloquear la prueba de mañana por este número |

## 2. Herramientas por fase

| Fase | Herramienta | Estado | Para qué en este avance |
|---|---|---|---|
| **Plan** | Trello (Kanban de RF) | ✅ ya existe | Seguimiento; mover tarjetas según `docs/19` |
| | Scrum | ⏳ | Ya planificado (`docs/03`) |
| | Lucidchart (ER y arquitectura) | ✅ ya existen | Fuente de verdad de los diagramas; actualizar si cambia el ER |
| **Code** | Python 3.11 | ✅ | Backend e IA |
| | FastAPI + Pydantic | ✅ | API y OpenAPI automático (contrato con el frontend) |
| | SQLAlchemy + Alembic + PostgreSQL 16 | ✅ | Datos y migraciones (DDL validado en `docs/05`) |
| | Ultralytics (YOLO26) + OpenCV | ✅ | Detector (Fase 1) |
| | `qrcode`, `hashlib`/SHA-256, `bcrypt` | ✅ | QR, hash de token, hash de contraseñas |
| | React + Vite + TypeScript | ✅ | Dos apps (`docs/20`) |
| | Librería de lectura de QR en navegador | 🟡 | Con respaldo de ingreso manual del token |
| | VS Code | ✅ | Desarrollo |
| | Firebase Cloud Messaging | ⏳ | Push al usuario (fuera) |
| **Build** | Git + GitHub (`main`/`develop`/`feature`) | ✅ | Control de versiones y revisión |
| | Docker + Docker Compose | ✅ | **Todo con un comando** (RNF-11) |
| | npm + Vite | ✅ | Compilar los frontends |
| | GHCR | ⏳ | Publicar imágenes (solo si hay despliegue) |
| | Roboflow + Colab | ✅ (Fase 1) | Dataset y entrenamiento del detector |
| **Test** | pytest + httpx | ✅ | Reglas de negocio y API (`docs/19` §4) |
| | Ruff | ✅ | Estilo y errores simples |
| | Bandit, Dependabot | 🟡 | Seguridad básica; no bloquea la prueba |
| | Playwright | 🟡 | Recorrido de punta a punta si hay tiempo |
| | `ultralytics val` | ✅ (Fase 1) | Evaluación del detector (`docs/16` §6) |
| | UAT | ✅ | La prueba de mañana con el equipo (§5) |
| **Release** | Etiquetas SemVer + GitHub Releases | 🟡 | `v0.1.0` al terminar la prueba |
| | Modelo `best.pt` versionado | ✅ | Guardar el archivo **fuera de Git** (Drive) con su versión en `MODEL_VERSION` |
| **Deploy** | **`docker compose up` en una laptop** | ✅ | **Es el «despliegue» de mañana** |
| | Túnel HTTPS temporal o certificado local | 🟡 | Solo si se usan celular/tablet con cámara (`docs/20` §4) |
| | GitHub Actions CD, Terraform, AWS (EC2, RDS, S3), Nginx + TLS | ⏳ | Producto completo |
| **Operate** | Healthchecks de Compose | ✅ | `db`, `backend`, `ia_service` |
| | Secrets Manager, KMS, S3 Lifecycle, IAM | ⏳ | Nube |
| | Runbook y rollback | 🟡 | Versión corta de `docs/09` §9 |
| **Monitor** | Logs JSON con `request_id` | ✅ | Reconstruir un ingreso de punta a punta, sin datos personales |
| | `GET /salud` (backend, BD, IA) | ✅ | Semáforo del punto de acceso |
| | CloudWatch, SNS, alarmas | ⏳ | Nube |
| | Tiempo QR→resultado y tasa de `verificar`/`rechazado` | ✅ | Se mide y se muestra (RNF-01), sin prometer cifras |

**Descartado a propósito (sin cambios):** Kubernetes, Jenkins/GitLab CI, Kafka/RabbitMQ, Prometheus + Grafana, Ansible.

## 3. Compose del avance (servicios)

| Servicio | Contenido | Notas |
|---|---|---|
| `db` | PostgreSQL 16 con volumen | Healthcheck `pg_isready` |
| `backend` | FastAPI; al arrancar aplica migraciones y carga datos de ejemplo | Healthcheck en `/salud`; `ENTORNO=dev` |
| `ia_service` | Detector con el `best.pt` montado como volumen de solo lectura | **CPU basta** (`docs/17` §1); healthcheck propio |
| `app_usuario` | Frontend del usuario | `:5173` |
| `punto_acceso` | Frontend del guardia | `:5174` |
| volúmenes | `pgdata`, `imagenes` (fotos de referencia y evidencias) | Ninguno va a Git |

**Variables nuevas respecto a `docs/09` §4:** `ENTORNO`, `IA_URL`, `IA_TIMEOUT_SEG`, `CORS_ORIGINS`, `UMBRAL_*` (provisionales, a calibrar con fotos reales), `QR_TTL_DIAS`, `MAX_VMP_POR_USUARIO`, `MODEL_PATH`, `MODEL_VERSION`. **`.env.example` versionado, `.env` no.**

## 4. Riesgos de infraestructura para mañana

| Riesgo | Qué hacer |
|---|---|
| **La primera construcción de la imagen de IA es lenta y pesada** (PyTorch/Ultralytics, varios GB) | Construirla **hoy**, no mañana; usar la variante de PyTorch para CPU; no reconstruir sin necesidad |
| **Sin el `best.pt` el sistema no valida** | Confirmar hoy dónde está el archivo y que carga; plan B: modelo preentrenado solo para pruebas de flujo, **dicho claramente** (no reconoce `scooter`) |
| **La cámara del navegador exige HTTPS o `localhost`** | Respaldo de subida de foto e ingreso manual del token (`docs/20` §4) |
| **Puertos ocupados o Docker sin recursos** | Probar `docker compose up` en la laptop de la demo; cerrar otras cargas; dejar los puertos en variables |
| **Datos de ejemplo incompletos** | Crear usuarios, vehículos y fotos de demostración con el script de seed y repetirlo desde cero |
| **Migración o seed rompe a medio camino** | `docker compose down -v` y arrancar de nuevo debe funcionar siempre; probarlo |
| **Dependencias sin versión fijada** | Archivos de bloqueo (`requirements` con versiones, `package-lock.json`) |
| **Secretos en el repositorio** | `.env` fuera de Git; revisar antes del primer commit |

## 5. «Prueba» de mañana: qué significa

1. Una persona clona el repositorio **limpio** en la laptop de la demo.
2. Copia `.env.example` a `.env` y deja el `best.pt` en su carpeta.
3. Ejecuta `docker compose up` y espera a que los healthchecks pasen.
4. Recorre los escenarios de `docs/19` §4 con los datos de ejemplo.
5. Se anotan: qué funcionó, qué no, los tiempos medidos y los errores.

Eso es una **prueba de aceptación del avance**, no un piloto con usuarios reales.
