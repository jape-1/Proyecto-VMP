# 09 · DevOps e infraestructura

> **[DOC]** (ya definido en el Avance 2): Python, YOLOv8, OpenCV, Trello (Kanban), Scrum, Lucidchart, la nube, notificaciones push a la App UTP.
> **[PROPUESTA]** (nuestro documento «Ciclo DevOps», 8 fases): FastAPI, React, PostgreSQL, Redis, Docker, GitHub Actions, Terraform, AWS, etc. Si el equipo ya eligió otra herramienta, se cambia solo la fila correspondiente.

## 1. Ciclo y herramientas por fase **[PROPUESTA]**

| Fase | Herramientas | Qué resuelve en este proyecto |
|---|---|---|
| **Plan** | Trello (Kanban RF01–RF22), Scrum (4 sprints, 24 HU), Lucidchart (ER y arquitectura), encuesta del piloto | Backlog y fuente de verdad de diagramas; el feedback del piloto vuelve como nuevas HU |
| **Code** | Python 3.11, VS Code, YOLOv8, OpenCV, FastAPI + Pydantic, SQLAlchemy + Alembic, React, `qrcode`, `hashlib`, `bcrypt`, Firebase Cloud Messaging | Un solo lenguaje para API e IA; migraciones versionadas; push de HU22/HU23 |
| **Build** | Git + GitHub (main/develop/feature), GitHub Actions (CI), Docker, Docker Compose, GHCR, Vite + npm, Roboflow + entrenamiento YOLOv8 | Entorno reproducible (OpenCV/YOLO tienen dependencias pesadas); todo el sistema con un comando |
| **Test** | pytest + httpx, Ruff, Bandit + Dependabot, Playwright, `ultralytics val` + clips de video, UAT con usuarios | Reglas (3 VMP, QR expirado), seguridad, panel E2E, precisión de IA, aceptación |
| **Release** | Git tags SemVer, GitHub Releases, GitHub Environments (aprobación manual), modelo `best.pt` versionado en S3 | Versión identificable; modelo versionado por separado del código |
| **Deploy** | GitHub Actions (CD), Terraform, AWS EC2, Amazon RDS (PostgreSQL), S3, Nginx + HTTPS | Sin despliegues manuales; réplica por sede |
| **Operate** | Redis Streams, Docker Compose healthchecks, AWS Secrets Manager, RDS backups + KMS, S3 Lifecycle + IAM, runbook + rollback | Eventos IA→Estacionamiento; recuperación; retención de fotos |
| **Monitor** | CloudWatch (logs/métricas), CloudWatch Alarms + SNS, logs JSON, reportes del piloto (HU24), métricas de IA | Alertas (cámara sin señal), trazabilidad por sesión, detección de deriva del modelo |

**Descartado a propósito:** Kubernetes (una sede, 40 espacios; Compose basta), Jenkins/GitLab CI (Actions vive junto al repo), Kafka/RabbitMQ (Redis cubre el volumen del piloto), Prometheus + Grafana (CloudWatch da métricas y alarmas), Ansible (Docker + Terraform bastan).

## 2. Entornos

| Entorno | Dónde | Datos | Cámaras |
|---|---|---|---|
| **local** | Laptop de cada integrante, `docker compose up` | Seeds ficticios (docs/05 §6) | `simulador_camaras` (videos/imágenes/webcam) |
| **staging** | EC2 pequeña (o la misma instancia con otro compose project) | Seeds + datos de prueba | Videos grabados del estacionamiento |
| **producción (piloto)** | EC2 + RDS + S3 | Reales (con consentimiento) | Cámaras IP reales vía RTSP |

## 3. Docker Compose (desarrollo) **[PROPUESTA]**

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16
    environment: { POSTGRES_DB: vmp, POSTGRES_USER: vmp, POSTGRES_PASSWORD: ${DB_PASSWORD} }
    volumes: [ "pgdata:/var/lib/postgresql/data" ]
    healthcheck: { test: ["CMD-SHELL","pg_isready -U vmp"], interval: 5s, retries: 10 }

  redis:
    image: redis:7
    healthcheck: { test: ["CMD","redis-cli","ping"], interval: 5s, retries: 10 }

  minio:                     # S3 local
    image: minio/minio
    command: server /data --console-address ":9001"
    environment: { MINIO_ROOT_USER: ${S3_ACCESS_KEY}, MINIO_ROOT_PASSWORD: ${S3_SECRET_KEY} }
    volumes: [ "miniodata:/data" ]
    ports: [ "9000:9000", "9001:9001" ]

  backend:
    build: ./backend
    env_file: .env
    depends_on: { db: { condition: service_healthy }, redis: { condition: service_healthy } }
    command: sh -c "alembic upgrade head && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"
    ports: [ "8000:8000" ]
    healthcheck: { test: ["CMD","curl","-f","http://localhost:8000/health"], interval: 10s, retries: 6 }

  ia_service:
    build: ./ia_service
    env_file: .env
    depends_on: { redis: { condition: service_healthy }, minio: { condition: service_started } }
    volumes: [ "./ia_service/models:/models:ro" ]
    healthcheck: { test: ["CMD","curl","-f","http://localhost:8100/ia/salud"], interval: 15s, retries: 6 }

  simulador_camaras:
    build: ./simulador_camaras
    env_file: .env
    depends_on: [ ia_service ]
    volumes: [ "./simulador_camaras/videos:/videos:ro" ]

  panel:
    build: ./panel
    ports: [ "5173:80" ]
    depends_on: [ backend ]

  simulador_utp:
    build: ./simulador_utp
    ports: [ "5174:80" ]
    depends_on: [ backend ]

volumes: { pgdata: {}, miniodata: {} }
```

## 4. Variables de entorno (`.env.example`) **[PROPUESTA]**

```dotenv
# --- Base de datos ---
DB_PASSWORD=cambiar
DATABASE_URL=postgresql+psycopg://vmp:${DB_PASSWORD}@db:5432/vmp
# --- Redis / eventos ---
REDIS_URL=redis://redis:6379/0
# --- Almacenamiento (S3/MinIO) ---
S3_ENDPOINT=http://minio:9000
S3_BUCKET=vmp
S3_ACCESS_KEY=cambiar
S3_SECRET_KEY=cambiar
S3_URL_EXPIRA_SEG=300
# --- Seguridad ---
JWT_SECRET=cambiar_largo_y_aleatorio
JWT_EXPIRA_MIN=30
QR_TTL_DIAS=120           # ≈ ciclo académico; calibrar
QR_TOKEN_BYTES=32         # 256 bits
# --- IA ---
MODEL_PATH=/models/best.pt
MODEL_VERSION=vmp-v0
CONF_MIN=0.25
UMBRAL_ALTO=0.80          # PROVISIONAL – calibrar en E5
UMBRAL_BAJO=0.50          # PROVISIONAL – calibrar en E5
N_OCUPAR=10               # PROVISIONAL – calibrar en E6
T_LIBERAR_SEG=15          # PROVISIONAL – calibrar en E6
OVERLAP_MIN=0.5
FRAME_STRIDE=5
IA_TIMEOUT_SEG=5
# --- Push / UTP ---
CONECTOR_UTP=simulado     # simulado | real
SIMULADOR_UTP_URL=http://simulador_utp
FCM_CREDENTIALS_JSON=     # vacío en local → push simulado
# --- Negocio ---
MAX_VMP_POR_USUARIO=3
SEDE_PILOTO=Torre Arequipa
```

> Los valores marcados PROVISIONAL **no** son resultados de medición; son semillas para arrancar. No los cites como umbrales “del proyecto”.

## 5. CI/CD **[PROPUESTA]**

### 5.1 Ramas y revisión
- `main` (producción, protegida), `develop` (integración), `feature/HUxx-descripcion`.
- PR obligatorio a `develop`, mínimo 1 revisión de otro integrante, CI verde. Release: `develop → main` con etiqueta SemVer (`v0.1.0`…).
- Commits convencionales (`feat|fix|test|docs|chore(modulo): mensaje (HUxx)`).

### 5.2 `ci.yml` (en cada PR)
```yaml
name: ci
on: { pull_request: { branches: [develop, main] } }
jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres: { image: "postgres:16", env: { POSTGRES_PASSWORD: test, POSTGRES_DB: vmp_test }, ports: ["5432:5432"], options: --health-cmd pg_isready }
      redis:    { image: "redis:7", ports: ["6379:6379"] }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11", cache: pip }
      - run: pip install -r backend/requirements-dev.txt
      - run: ruff check backend && ruff format --check backend
      - run: bandit -r backend/app -q
      - run: cd backend && alembic upgrade head && pytest -q --cov=app --cov-fail-under=70
  ia:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11", cache: pip }
      - run: pip install -r ia_service/requirements-dev.txt
      - run: cd ia_service && pytest -q          # pruebas con imágenes de ejemplo pequeñas
  panel:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: npm, cache-dependency-path: panel/package-lock.json }
      - run: cd panel && npm ci && npm run lint && npm run build
  images:
    needs: [backend, ia, panel]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t test-backend ./backend && docker build -t test-ia ./ia_service
```
*(La cobertura de 70 % es un punto de partida **[PROPUESTA]**; ajustar.)*

### 5.3 `cd.yml` (merge a `main` / tag)
1. Construir imágenes → publicarlas en **GHCR** con tag `vX.Y.Z` y `sha`.
2. Desplegar a **staging** (SSH o SSM a EC2: `docker compose pull && up -d`) → pruebas de humo (`/health`, flujo de ingreso simulado).
3. **Aprobación manual** (GitHub Environment `production`) → desplegar a producción.
4. Migraciones: `alembic upgrade head` como paso previo; **siempre compatibles hacia atrás** (expand/contract).
5. Rollback: re-desplegar el tag anterior (`IMAGE_TAG=vX.Y.(Z-1)`), y `MODEL_VERSION` anterior si el problema es del modelo.

## 6. Infraestructura (Terraform) **[PROPUESTA]**

| Recurso | Detalle | Notas |
|---|---|---|
| VPC + subredes | Pública (EC2/ALB), privada (RDS) | Un módulo `sede` replicable |
| EC2 | 1 instancia (Docker Compose): backend + ia_service + redis + nginx | Tamaño según E3; si se usa GPU, instancia aparte para IA |
| RDS PostgreSQL | Instancia pequeña, cifrada (KMS), backups automáticos | Sin acceso público |
| S3 | Buckets `vmp-referencias`, `vmp-evidencias`, `vmp-modelos` | Privados; versionado en `modelos`; *Lifecycle* de evidencias (ver §8) |
| Secrets Manager | `DATABASE_URL`, `JWT_SECRET`, `FCM`, credenciales de cámaras | Inyección al arrancar |
| CloudWatch + SNS | Logs, métricas, alarmas por correo | |
| IAM | Roles mínimos: EC2→S3 (solo sus buckets), EC2→Secrets | Principio de menor privilegio |
| Nginx | TLS (ACM/Let's Encrypt), *rate limit*, proxy a `backend` y estáticos de `panel` | Es el «API Gateway» físico |

El módulo Terraform recibe `sede` como variable → reutilizable para multi-sede.

## 7. Observabilidad **[PROPUESTA]**

### 7.1 Logs JSON
Campos comunes: `ts`, `nivel`, `servicio`, `modulo`, `request_id`, `id_sesion`, `id_usuario_utp` (solo ID, nunca nombres), `evento`, `latencia_ms`, `codigo_error`. Permite reconstruir un ingreso de punta a punta: QR → sesión → solicitud IA → resultado → notificación.

### 7.2 Métricas clave
| Métrica | Fuente | Alarma sugerida |
|---|---|---|
| Latencia p95 de validación de ingreso (QR→resultado) | backend | > objetivo tras línea base |
| Cámara sin señal / sin cuadros recientes | ia_service | > 60 s sin cuadro |
| Latencia de inferencia | ia_service | aumento sostenido |
| Eventos en DLQ | Redis | > 0 |
| Tasa de `vehiculo_no_coincide` | backend | subida sostenida (posible deriva del modelo) |
| Overrides del guardia sobre decisión de IA | backend | subida sostenida |
| Espacios “pegados” (sin cambio por horas) | backend | revisar cámara/ROI |
| Errores 5xx | Nginx/backend | > umbral |
| Espacio en disco S3/EC2, backups RDS | CloudWatch | fallo de backup |

### 7.3 Salud
`GET /health` (backend: BD, Redis, S3), `GET /ia/salud` (modelo cargado + versión + último cuadro por cámara). Docker `healthcheck` reinicia piezas caídas.

## 8. Retención y privacidad operativa **[PROPUESTA]**

- **Fotos de referencia:** mientras el vehículo esté `activo`; se borran al dar de baja al usuario o al vehículo (más un periodo de gracia corto).
- **Imágenes de evidencia** (ingreso, eventos): retención limitada, p. ej. **N días** definidos por el equipo/UTP **[PENDIENTE docs/13 #10]**; `S3 Lifecycle` borra al vencer. Las ligadas a **incidencias abiertas** se conservan hasta el cierre.
- **Logs:** sin datos personales; retención corta (p. ej. 30–90 días) **[PENDIENTE]**.
- Backups de RDS cifrados. Prueba de restauración antes del piloto.

## 9. Runbook (esqueleto) **[PROPUESTA]**

| Síntoma | Causa probable | Acción |
|---|---|---|
| Tablet no lee QR | Lector desconectado / brillo del móvil | Revisar estado de dispositivos en pantalla; reconectar; usar entrada manual del token |
| «IA no disponible» | `ia_service` caído o modelo no cargado | `docker compose ps`; ver logs; reiniciar; mientras tanto **modo manual** desde panel |
| Cámara de zona sin señal | Red/alimentación/RTSP | Alarma SNS; verificar URL/credenciales; marcar espacios de esa cámara como `mantenimiento` |
| Casilla “pegada” en ocupada | ROI movido / sombra | Revisar snapshot; recalibrar ROI; forzar estado desde panel (admin) con auditoría |
| Eventos acumulados en Redis | Consumidor caído | Reiniciar backend; revisar DLQ; reprocesar |
| Más falsos rechazos | Deriva del modelo / cambio de luz | Subir a modo asistido; recolectar casos; reentrenar (docs/06 §12) |
| Despliegue malo | Bug en la nueva versión | Rollback al tag anterior; `alembic downgrade` solo si la migración es reversible |
