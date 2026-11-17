# 05 · Modelo de datos

> Base: ER documentado (12 entidades, 14 relaciones 1:N). **[DOC]** = campo/relación/enumeración del ER. **[PROPUESTA]** = columna, índice, tabla o restricción que agregamos para poder implementar. **[PENDIENTE]** = discrepancia a decidir (docs/13). **No agregues nada marcado [PROPUESTA] sin dejarlo anotado en docs/13 si cambia el ER**.

## 1. Mapa del modelo [DOC]

`SESION_ESTACIONAMIENTO` es el centro: recibe 4 FKs (usuario, vehículo, QR, espacio) y de ella cuelgan eventos de IA, incidencias y notificaciones. `USUARIO_UTP` es el otro centro (5 relaciones). `REPORTE_PILOTO` no se relaciona con nadie (agregado calculado).

| # | Padre (1) | Hija (N) | FK | Lectura |
|---|---|---|---|---|
| 1 | USUARIO_UTP | VEHICULO_VMP | id_usuario_utp | Un usuario registra varios vehículos |
| 2 | USUARIO_UTP | CODIGO_QR | id_usuario_utp | Un usuario tiene varios QR a lo largo del tiempo |
| 3 | USUARIO_UTP | SINCRONIZACION_UTP | id_usuario_utp | Un usuario genera muchas sincronizaciones |
| 4 | USUARIO_UTP | SESION_ESTACIONAMIENTO | id_usuario_utp | Un usuario tiene muchas sesiones |
| 5 | USUARIO_UTP | NOTIFICACION | id_usuario_utp | Un usuario recibe muchas notificaciones |
| 6 | VEHICULO_VMP | SESION_ESTACIONAMIENTO | id_vehiculo | Un vehículo ingresa muchas veces |
| 7 | CODIGO_QR | SESION_ESTACIONAMIENTO | id_qr | Un QR se usa en varios ingresos mientras esté vigente |
| 8 | ZONA_ESTACIONAMIENTO | ESPACIO_ESTACIONAMIENTO | id_zona | Una zona contiene varios espacios |
| 9 | ESPACIO_ESTACIONAMIENTO | SESION_ESTACIONAMIENTO | id_espacio | Un espacio se ocupa en muchas sesiones (una a la vez) |
| 10 | ESPACIO_ESTACIONAMIENTO | EVENTO_DETECCION_IA | id_espacio | Un espacio genera muchos eventos |
| 11 | SESION_ESTACIONAMIENTO | EVENTO_DETECCION_IA | id_sesion | Una sesión tiene varios eventos |
| 12 | SESION_ESTACIONAMIENTO | INCIDENCIA | id_sesion | Una sesión puede originar incidencias |
| 13 | SESION_ESTACIONAMIENTO | NOTIFICACION | id_sesion | Una sesión dispara notificaciones |
| 14 | PERSONAL_SEGURIDAD | INCIDENCIA | id_personal | Un agente atiende muchas incidencias |

## 2. Entidades campo por campo [DOC]

Convención del ER: PK `INT`. El ER usa nombres como `fecha_ultima_sincronizacion`, `tiempo_promedio_ingreso_seg`, `nivel_satisfaccion_promedio` (en el PDF se parten por el ancho de columna; son un solo nombre).

### 2.1 Identidad y Accesos

**USUARIO_UTP** *(simulado: en producción vendría de la UTP)*

| Campo | Tipo | Notas |
|---|---|---|
| id_usuario_utp (PK) | INT | |
| codigo_utp | VARCHAR(10) | p. ej. `U20231234`. [PROPUESTA] UNIQUE |
| tipo_usuario | ENUM | `estudiante`, `docente`, `administrativo` |
| nombres, apellidos | VARCHAR(100) | |
| correo_institucional | VARCHAR(120) | [PROPUESTA] UNIQUE |
| sede | VARCHAR(50) | habilita multi-sede |
| estado_matricula | ENUM | `activo`, `inactivo` |
| fecha_ultima_sincronizacion | TIMESTAMP | última actualización desde la UTP |

**SINCRONIZACION_UTP** *(simulado; bitácora del conector)*

| Campo | Tipo | Notas |
|---|---|---|
| id_sincronizacion (PK) | INT | |
| id_usuario_utp (FK) | INT | |
| origen | ENUM | `login_portal`, `consulta_qr_app` (el ER dice «login en el Portal UTP o consulta del QR en la App UTP») |
| fecha_hora | TIMESTAMP | |
| resultado | ENUM | `exitoso`, `fallido` |

**VEHICULO_VMP**

| Campo | Tipo | Notas |
|---|---|---|
| id_vehiculo (PK) | INT | |
| id_usuario_utp (FK) | INT | dueño |
| tipo_vmp | ENUM | `bicicleta`, `bicicleta_electrica`, `scooter_electrico`, `moto_electrica` **[PENDIENTE]** (docs/13 #1: otras secciones solo listan scooters/bicicletas eléctricas o motos+scooters+bicicletas eléctricas) |
| marca, color | VARCHAR | longitud no documentada → [PROPUESTA] 50 |
| caracteristica_distintiva | VARCHAR(255) | calcomanía, accesorio… |
| foto_referencia_url | VARCHAR(255) | foto de comparación de la IA |
| fecha_registro | TIMESTAMP | |
| estado | ENUM | `activo`, `inactivo` |

Regla: máx. **3 vehículos activos** por usuario (capa de aplicación). El «Modelo» del vehículo aparece en el formulario de HU02 pero **no** en el ER **[PENDIENTE]** #2.

**CODIGO_QR**

| Campo | Tipo | Notas |
|---|---|---|
| id_qr (PK) | INT | |
| id_usuario_utp (FK) | INT | un QR identifica al usuario y agrupa sus vehículos |
| token_hash | VARCHAR(64) | hash del token (SHA-256 hex = 64 chars) |
| fecha_generacion, fecha_expiracion | TIMESTAMP | vigencia (ciclo académico) |
| estado | ENUM | `activo`, `revocado`, `expirado` |

### 2.2 Estacionamiento e IA

**ZONA_ESTACIONAMIENTO**: `id_zona` PK INT · `nombre_zona` VARCHAR(50) · `sede` VARCHAR(50) · `capacidad_total` INT.

**ESPACIO_ESTACIONAMIENTO**: `id_espacio` PK INT · `id_zona` FK · `codigo_espacio` VARCHAR(10) (p. ej. `A-05`) · `estado` ENUM (`disponible`, `ocupado`, `mantenimiento`) · `ultima_actualizacion` TIMESTAMP.

**SESION_ESTACIONAMIENTO** (la tabla central)

| Campo | Tipo | Notas |
|---|---|---|
| id_sesion (PK) | INT | |
| id_vehiculo (FK) | INT | con qué. Para un rechazo en que ningún vehículo coincide, puede quedar sin identificar → [PROPUESTA] **NULL permitido** |
| id_usuario_utp (FK) | INT | quién |
| id_qr (FK) | INT | qué QR |
| id_espacio (FK) | INT | dónde quedó. [PROPUESTA] NULL hasta que la IA confirma la ocupación (y siempre NULL en rechazos) |
| fecha_hora_ingreso | TIMESTAMP | |
| fecha_hora_salida | TIMESTAMP | NULL mientras esté dentro |
| resultado_validacion | ENUM | `validado`, `rechazado`. [PROPUESTA] NULL mientras la IA no responde |
| estado_sesion | ENUM | `en_curso`, `finalizada`, `con_incidencia` |

**EVENTO_DETECCION_IA**

| Campo | Tipo | Notas |
|---|---|---|
| id_evento (PK) | INT | |
| id_sesion (FK) | INT | [PROPUESTA] NULL permitido en eventos de zona sin sesión asociada (p. ej. un vehículo detectado ocupando sin sesión = anomalía) |
| id_espacio (FK) | INT | NULL en `validacion_ingreso` |
| tipo_evento | ENUM | `validacion_ingreso`, `ocupacion_espacio`, `liberacion_espacio` |
| codigo_camara | VARCHAR(20) | |
| imagen_capturada_url | VARCHAR(255) | evidencia |
| score_confianza | DECIMAL(4,2) | 0.00–1.00 (p. ej. 0.91) |
| fecha_hora | TIMESTAMP | |

### 2.3 Administración e Incidencias

**PERSONAL_SEGURIDAD**: `id_personal` PK · `nombres`, `apellidos` VARCHAR(100) · `usuario_acceso` VARCHAR(50) · `contrasena_hash` VARCHAR(255) · `turno` ENUM (`manana`, `tarde`, `noche`) · `estado` ENUM (`activo`, `inactivo`).

**INCIDENCIA**: `id_incidencia` PK · `id_sesion` FK · `id_personal` FK · `tipo_incidencia` ENUM (`vehiculo_no_coincide`, `sin_espacio_disponible`, `error_lectura_qr`, `otro`) · `descripcion` TEXT · `fecha_hora` TIMESTAMP · `resuelta` BOOLEAN.

### 2.4 Notificaciones y Reportes

**NOTIFICACION**: `id_notificacion` PK · `id_usuario_utp` FK · `id_sesion` FK · `tipo_notificacion` ENUM (`confirmacion_ingreso`, `estacionamiento_lleno`) · `mensaje` VARCHAR(255) · `fecha_envio` TIMESTAMP · `canal` ENUM (`app_utp`).

**REPORTE_PILOTO**: `id_reporte` PK · `periodo_inicio`, `periodo_fin` DATE · `tiempo_promedio_ingreso_seg` INT · `total_incidencias` INT · `nivel_satisfaccion_promedio` DECIMAL(3,2) · `generado_en` TIMESTAMP.

> Nota del propio documento: la satisfacción del reporte se calcula a partir de **encuestas**, pero el ER **no tiene tabla de encuestas** **[PENDIENTE]** #3.

## 3. Brechas entre el ER y lo que piden las HU **[PENDIENTE: ver docs/13]**

| # | Brecha | Qué pide la HU | Propuesta mínima |
|---|---|---|---|
| 1 | Lista de tipos de VMP inconsistente | HU02/HU08/HU14: scooters y bicicletas eléctricas; delimitación: +motos | Mantener las 4 del ER; validar en app según lo que confirme el equipo |
| 2 | Falta `modelo` | HU02 formulario: marca, **modelo**, color | Agregar `modelo VARCHAR(50) NULL` a `vehiculo_vmp` |
| 3 | No hay encuestas | HU24 satisfacción; ER: «encuestas» | Tabla `encuesta_satisfaccion(id_encuesta, id_usuario_utp, id_sesion NULL, puntaje SMALLINT 1–5, comentario, fecha_hora)` |
| 4 | No hay consentimiento | HU01 (4): consentimiento obligatorio | Columnas en `usuario_utp`: `acepta_tratamiento_datos BOOLEAN`, `fecha_consentimiento TIMESTAMP` |
| 5 | Incidencias solo tienen `resuelta` | HU20: abierta/en revisión/cerrada, evidencia, comentario de cierre, línea de tiempo | Agregar `estado ENUM`, `evidencia_url`, `comentario_cierre`, `fecha_cierre`; opcional tabla `incidencia_historial` |
| 6 | No hay cámaras | HU13: monitoreo; `codigo_camara` solo es texto | Tabla opcional `camara(codigo_camara PK, tipo ENUM ingreso/zona, id_zona NULL, url_stream, estado)` |
| 7 | No hay suscripción a «espacio libre» | HU23 (3) | Tabla `suscripcion_aviso(id_usuario_utp, id_zona NULL, activa)` o bandera en usuario |
| 8 | `ESPACIO` y `ZONA` sin coordenadas | HU17: ubicación exacta, mapa | `pos_x`, `pos_y` o polígono ROI por espacio (se necesita también para la IA, ver docs/06 §ROIs) |
| 9 | Tipos de notificación solo 2 | HU22 (3): aviso de ingreso **rechazado** | Agregar valor `ingreso_rechazado` al ENUM |
| 10 | Falta rol de administración | HU21/HU24: «personal administrativo» distinto de «personal de seguridad» | Agregar `rol ENUM('seguridad','administrador')` a `personal_seguridad` |
| 11 | Un QR por usuario vs. N QR en el tiempo | HU05: «un QR único por usuario»; ER: 1:N | Regla: **un solo QR `activo` por usuario**; los anteriores quedan `revocado`/`expirado` (índice único parcial) |

### 3.1 Brechas aprobadas el 2026-11-15 (implementadas en la migración `0001`)

Estas no estaban en el ER y se aprobaron en sesión para poder construir el avance
(`docs/18` §5–§7). El registro de la decisión está en `docs/13` §F.

| # | Brecha | Qué se agregó | Por qué |
|---|---|---|---|
| 12 | `resultado_validacion` solo tiene 2 valores | ENUM `estado_validacion` (`pendiente`, `validado`, `verificar`, `rechazado`, `ia_no_disponible`) en `sesion_estacionamiento` | El ER no puede representar «pendiente de IA», «zona gris» ni «IA caída» (docs/18 §5). `resultado_validacion` se conserva y se sincroniza para no romper consultas del ER |
| 13 | No hay motivo, confianza ni auditoría de la decisión | `motivo VARCHAR(50)`, `mejor_confianza NUMERIC(4,2)`, `id_personal_decision FK`, `fecha_decision`, `motivo_decision` en `sesion_estacionamiento` | HU10–HU12: mostrar por qué y registrar quién autorizó |
| 14 | `evento_deteccion_ia` no guarda evidencia suficiente | `modelo_version VARCHAR(50)`, `detecciones JSONB`, `motivo VARCHAR(50)` | docs/18 §5 exige guardar versión del modelo, detecciones y motivo |
| 15 | No hay registro de intentos con QR inválido | Tabla `intento_lectura_qr` (fragmento de hash, motivo, cámara, personal, fecha) | docs/18 §7.5: los intentos fallidos también se registran (`docs/13` #5, opción A) |
| 16 | `vehiculo_vmp.foto_referencia_url` era `NOT NULL` | Pasa a **NULL** hasta que se sube la foto | HU03: el vehículo se crea en un paso y la foto en otro |
| 17 | El consentimiento no tenía versión del texto | `version_consentimiento VARCHAR(20)` en `usuario_utp` | Poder demostrar **qué** texto aceptó el usuario (Ley 29733) |
| 18 | Tipo de las marcas de tiempo | `TIMESTAMPTZ` en todas las columnas de fecha (el DDL de §4 usaba `TIMESTAMP`) | Guardar en UTC y mostrar en America/Lima sin ambigüedad (S3) |

**Sobre el token del QR:** no se agrega ninguna columna. El token se deriva con
HMAC-SHA-256 de `id_qr:id_usuario_utp` y un secreto del servidor, y en
`codigo_qr` solo queda su SHA-256 (`token_hash`). Así el QR se puede volver a
dibujar sin almacenar el token en claro.


## 4. DDL de referencia (PostgreSQL) **[PROPUESTA]**

Refleja el ER + las columnas mínimas ya indicadas como **[PROPUESTA]** arriba. Las líneas con `-- BRECHA n` implementan las brechas de la tabla; si el equipo las rechaza, se quitan. Se implementa con Alembic, no con este archivo a mano.

```sql
-- ===== Tipos enumerados =====
CREATE TYPE tipo_usuario       AS ENUM ('estudiante','docente','administrativo');
CREATE TYPE estado_matricula   AS ENUM ('activo','inactivo');
CREATE TYPE origen_sync        AS ENUM ('login_portal','consulta_qr_app');
CREATE TYPE resultado_sync     AS ENUM ('exitoso','fallido');
CREATE TYPE tipo_vmp           AS ENUM ('bicicleta','bicicleta_electrica','scooter_electrico','moto_electrica');
CREATE TYPE estado_activo      AS ENUM ('activo','inactivo');
CREATE TYPE estado_qr          AS ENUM ('activo','revocado','expirado');
CREATE TYPE estado_espacio     AS ENUM ('disponible','ocupado','mantenimiento');
CREATE TYPE resultado_valid    AS ENUM ('validado','rechazado');
CREATE TYPE estado_sesion      AS ENUM ('en_curso','finalizada','con_incidencia');
CREATE TYPE tipo_evento_ia     AS ENUM ('validacion_ingreso','ocupacion_espacio','liberacion_espacio');
CREATE TYPE turno_personal     AS ENUM ('manana','tarde','noche');
CREATE TYPE rol_personal       AS ENUM ('seguridad','administrador');              -- BRECHA 10
CREATE TYPE tipo_incidencia    AS ENUM ('vehiculo_no_coincide','sin_espacio_disponible','error_lectura_qr','otro');
CREATE TYPE estado_incidencia  AS ENUM ('abierta','en_revision','cerrada');        -- BRECHA 5
CREATE TYPE tipo_notificacion  AS ENUM ('confirmacion_ingreso','estacionamiento_lleno','ingreso_rechazado'); -- BRECHA 9
CREATE TYPE canal_notif        AS ENUM ('app_utp');

-- ===== Identidad y Accesos =====
CREATE TABLE usuario_utp (
  id_usuario_utp              SERIAL PRIMARY KEY,
  codigo_utp                  VARCHAR(10)  NOT NULL UNIQUE,
  tipo_usuario                tipo_usuario NOT NULL,
  nombres                     VARCHAR(100) NOT NULL,
  apellidos                   VARCHAR(100) NOT NULL,
  correo_institucional        VARCHAR(120) NOT NULL UNIQUE,
  sede                        VARCHAR(50)  NOT NULL,
  estado_matricula            estado_matricula NOT NULL DEFAULT 'activo',
  fecha_ultima_sincronizacion TIMESTAMP,
  acepta_tratamiento_datos    BOOLEAN NOT NULL DEFAULT FALSE,                     -- BRECHA 4
  fecha_consentimiento        TIMESTAMP                                           -- BRECHA 4
);

CREATE TABLE sincronizacion_utp (
  id_sincronizacion SERIAL PRIMARY KEY,
  id_usuario_utp    INT NOT NULL REFERENCES usuario_utp(id_usuario_utp),
  origen            origen_sync NOT NULL,
  fecha_hora        TIMESTAMP NOT NULL DEFAULT now(),
  resultado         resultado_sync NOT NULL
);
CREATE INDEX ix_sync_usuario_fecha ON sincronizacion_utp(id_usuario_utp, fecha_hora DESC);

CREATE TABLE vehiculo_vmp (
  id_vehiculo               SERIAL PRIMARY KEY,
  id_usuario_utp            INT NOT NULL REFERENCES usuario_utp(id_usuario_utp),
  tipo_vmp                  tipo_vmp NOT NULL,
  marca                     VARCHAR(50)  NOT NULL,
  modelo                    VARCHAR(50),                                          -- BRECHA 2
  color                     VARCHAR(50)  NOT NULL,
  caracteristica_distintiva VARCHAR(255),
  foto_referencia_url       VARCHAR(255) NOT NULL,
  fecha_registro            TIMESTAMP NOT NULL DEFAULT now(),
  estado                    estado_activo NOT NULL DEFAULT 'activo'
);
CREATE INDEX ix_vehiculo_usuario ON vehiculo_vmp(id_usuario_utp) WHERE estado = 'activo';
-- El límite de 3 se valida en la aplicación (RF02). Opcional: trigger de defensa en profundidad.

CREATE TABLE codigo_qr (
  id_qr             SERIAL PRIMARY KEY,
  id_usuario_utp    INT NOT NULL REFERENCES usuario_utp(id_usuario_utp),
  token_hash        VARCHAR(64) NOT NULL UNIQUE,
  fecha_generacion  TIMESTAMP NOT NULL DEFAULT now(),
  fecha_expiracion  TIMESTAMP NOT NULL,
  estado            estado_qr NOT NULL DEFAULT 'activo',
  CHECK (fecha_expiracion > fecha_generacion)
);
CREATE UNIQUE INDEX ux_qr_activo_por_usuario ON codigo_qr(id_usuario_utp) WHERE estado = 'activo';  -- BRECHA 11

-- ===== Estacionamiento e IA =====
CREATE TABLE zona_estacionamiento (
  id_zona         SERIAL PRIMARY KEY,
  nombre_zona     VARCHAR(50) NOT NULL,
  sede            VARCHAR(50) NOT NULL,
  capacidad_total INT NOT NULL CHECK (capacidad_total > 0),
  UNIQUE (sede, nombre_zona)
);

CREATE TABLE espacio_estacionamiento (
  id_espacio           SERIAL PRIMARY KEY,
  id_zona              INT NOT NULL REFERENCES zona_estacionamiento(id_zona),
  codigo_espacio       VARCHAR(10) NOT NULL,
  estado               estado_espacio NOT NULL DEFAULT 'disponible',
  ultima_actualizacion TIMESTAMP NOT NULL DEFAULT now(),
  pos_x                NUMERIC(6,2),                                              -- BRECHA 8 (mapa del panel)
  pos_y                NUMERIC(6,2),
  roi_json             JSONB,                                                     -- BRECHA 8 (polígono en la cámara)
  UNIQUE (id_zona, codigo_espacio)
);

CREATE TABLE sesion_estacionamiento (
  id_sesion            SERIAL PRIMARY KEY,
  id_vehiculo          INT REFERENCES vehiculo_vmp(id_vehiculo),                  -- NULL si no se identificó
  id_usuario_utp       INT NOT NULL REFERENCES usuario_utp(id_usuario_utp),
  id_qr                INT NOT NULL REFERENCES codigo_qr(id_qr),
  id_espacio           INT REFERENCES espacio_estacionamiento(id_espacio),        -- NULL hasta ocupación confirmada
  fecha_hora_ingreso   TIMESTAMP NOT NULL DEFAULT now(),
  fecha_hora_salida    TIMESTAMP,
  resultado_validacion resultado_valid,                                           -- NULL = pendiente de IA
  estado_sesion        estado_sesion NOT NULL DEFAULT 'en_curso',
  CHECK (fecha_hora_salida IS NULL OR fecha_hora_salida >= fecha_hora_ingreso)
);
CREATE INDEX ix_sesion_usuario_fecha ON sesion_estacionamiento(id_usuario_utp, fecha_hora_ingreso DESC);
CREATE INDEX ix_sesion_vehiculo      ON sesion_estacionamiento(id_vehiculo);
-- Un vehículo no puede estar dentro dos veces a la vez:
CREATE UNIQUE INDEX ux_sesion_vehiculo_dentro ON sesion_estacionamiento(id_vehiculo)
  WHERE estado_sesion = 'en_curso' AND resultado_validacion = 'validado' AND fecha_hora_salida IS NULL;
-- Un espacio no puede tener dos sesiones vigentes:
CREATE UNIQUE INDEX ux_sesion_espacio_vigente ON sesion_estacionamiento(id_espacio)
  WHERE id_espacio IS NOT NULL AND fecha_hora_salida IS NULL;

CREATE TABLE evento_deteccion_ia (
  id_evento            SERIAL PRIMARY KEY,
  id_sesion            INT REFERENCES sesion_estacionamiento(id_sesion),
  id_espacio           INT REFERENCES espacio_estacionamiento(id_espacio),
  tipo_evento          tipo_evento_ia NOT NULL,
  codigo_camara        VARCHAR(20) NOT NULL,
  imagen_capturada_url VARCHAR(255),
  score_confianza      NUMERIC(4,2) CHECK (score_confianza BETWEEN 0 AND 1),
  fecha_hora           TIMESTAMP NOT NULL DEFAULT now(),
  event_id             UUID UNIQUE                                                -- idempotencia (propuesta)
);
CREATE INDEX ix_evento_espacio_fecha ON evento_deteccion_ia(id_espacio, fecha_hora DESC);
CREATE INDEX ix_evento_sesion        ON evento_deteccion_ia(id_sesion);

-- ===== Administración e Incidencias =====
CREATE TABLE personal_seguridad (
  id_personal     SERIAL PRIMARY KEY,
  nombres         VARCHAR(100) NOT NULL,
  apellidos       VARCHAR(100) NOT NULL,
  usuario_acceso  VARCHAR(50)  NOT NULL UNIQUE,
  contrasena_hash VARCHAR(255) NOT NULL,
  turno           turno_personal NOT NULL,
  rol             rol_personal NOT NULL DEFAULT 'seguridad',                      -- BRECHA 10
  estado          estado_activo NOT NULL DEFAULT 'activo'
);

CREATE TABLE incidencia (
  id_incidencia    SERIAL PRIMARY KEY,
  id_sesion        INT NOT NULL REFERENCES sesion_estacionamiento(id_sesion),
  id_personal      INT REFERENCES personal_seguridad(id_personal),                -- NULL hasta asignar
  tipo_incidencia  tipo_incidencia NOT NULL,
  descripcion      TEXT,
  fecha_hora       TIMESTAMP NOT NULL DEFAULT now(),
  resuelta         BOOLEAN NOT NULL DEFAULT FALSE,
  estado           estado_incidencia NOT NULL DEFAULT 'abierta',                  -- BRECHA 5
  evidencia_url    VARCHAR(255),                                                  -- BRECHA 5
  comentario_cierre TEXT,                                                         -- BRECHA 5
  fecha_cierre     TIMESTAMP                                                      -- BRECHA 5
);
CREATE INDEX ix_incidencia_estado ON incidencia(estado, fecha_hora DESC);

-- ===== Notificaciones y Reportes =====
CREATE TABLE notificacion (
  id_notificacion  SERIAL PRIMARY KEY,
  id_usuario_utp   INT NOT NULL REFERENCES usuario_utp(id_usuario_utp),
  id_sesion        INT REFERENCES sesion_estacionamiento(id_sesion),              -- NULL en «lleno» (no depende de una sesión concreta)
  tipo_notificacion tipo_notificacion NOT NULL,
  mensaje          VARCHAR(255) NOT NULL,
  fecha_envio      TIMESTAMP NOT NULL DEFAULT now(),
  canal            canal_notif NOT NULL DEFAULT 'app_utp'
);
CREATE INDEX ix_notif_usuario_fecha ON notificacion(id_usuario_utp, fecha_envio DESC);

CREATE TABLE reporte_piloto (
  id_reporte                  SERIAL PRIMARY KEY,
  periodo_inicio              DATE NOT NULL,
  periodo_fin                 DATE NOT NULL,
  tiempo_promedio_ingreso_seg INT,
  total_incidencias           INT NOT NULL DEFAULT 0,
  nivel_satisfaccion_promedio NUMERIC(3,2),
  generado_en                 TIMESTAMP NOT NULL DEFAULT now(),
  CHECK (periodo_fin >= periodo_inicio)
);

-- ===== Tablas nuevas (BRECHAS 3, 6, 7) – solo si el equipo las aprueba =====
CREATE TABLE encuesta_satisfaccion (
  id_encuesta     SERIAL PRIMARY KEY,
  id_usuario_utp  INT NOT NULL REFERENCES usuario_utp(id_usuario_utp),
  id_sesion       INT REFERENCES sesion_estacionamiento(id_sesion),
  puntaje         SMALLINT NOT NULL CHECK (puntaje BETWEEN 1 AND 5),
  comentario      VARCHAR(255),
  fecha_hora      TIMESTAMP NOT NULL DEFAULT now()
);
CREATE TABLE camara (
  codigo_camara VARCHAR(20) PRIMARY KEY,
  tipo          VARCHAR(10) NOT NULL CHECK (tipo IN ('ingreso','zona')),
  id_zona       INT REFERENCES zona_estacionamiento(id_zona),
  url_stream    VARCHAR(255),
  estado        estado_activo NOT NULL DEFAULT 'activo'
);
CREATE TABLE suscripcion_aviso (
  id_usuario_utp INT NOT NULL REFERENCES usuario_utp(id_usuario_utp),
  id_zona        INT REFERENCES zona_estacionamiento(id_zona),
  activa         BOOLEAN NOT NULL DEFAULT TRUE,
  PRIMARY KEY (id_usuario_utp, id_zona)
);
```

## 5. Reglas de integridad que la **aplicación** debe cubrir

| Regla | Dónde | Cómo |
|---|---|---|
| Máx. 3 VMP activos por usuario | `identidad.service` | `COUNT(*) WHERE estado='activo'` dentro de la transacción con `SELECT … FOR UPDATE` del usuario para evitar carreras |
| No eliminar VMP con sesión en curso | `identidad.service` | Preguntar a `estacionamiento.service.vehiculo_esta_dentro(id)`; «eliminar» = `estado='inactivo'` (baja lógica) |
| Un solo QR activo por usuario | `identidad.service.generar_qr` | Revocar el anterior y crear el nuevo en la misma transacción |
| El vehículo de la sesión pertenece al usuario de la sesión | `estacionamiento.service` | Verificar `vehiculo.id_usuario_utp == sesion.id_usuario_utp` |
| `capacidad_total` de zona = nº de espacios de la zona | Seed y panel | Validar al crear/editar espacios |
| El espacio pasa a `ocupado` solo si la sesión está `validado` | `estacionamiento.service` | Evento de ocupación sin sesión validada → anomalía (evento con `id_sesion NULL`) + alerta |
| Transiciones de `estado_sesion` | `estacionamiento.service` | `en_curso → finalizada` (salida), `en_curso → con_incidencia` (rechazo/anomalía), `con_incidencia → finalizada` (cierre de incidencia o salida manual) |

## 6. Seeds del piloto **[PROPUESTA]**

- **Zonas:** 5 zonas (`A`…`E`) en la sede `Torre Arequipa`, `capacidad_total = 8` cada una. Los nombres reales de las zonas no están en el Avance **[PENDIENTE]** #8.
- **Espacios:** 40 = `A-01…A-08`, `B-01…B-08`, … `E-01…E-08`, todos `disponible`.
- **Personal de seguridad:** 3 agentes (uno por turno `manana`, `tarde`, `noche`) + 1 `administrador` para pruebas.
- **Usuarios simulados:** ~20 con mezcla de `estudiante`/`docente`/`administrativo`, 3 con `estado_matricula = inactivo` (prueba BR-08).
- **Vehículos simulados:** 1–3 por usuario, con fotos reales de scooters, bicicletas eléctricas y motos (mismas que servirán para el dataset, ver docs/06).
- **Casos límite sembrados:** usuario con 3 VMP (probar el cuarto), QR expirado, QR revocado, usuario inactivo, vehículo dentro (probar baja).

## 7. Consultas clave

```sql
-- Ocupación en tiempo real por zona (panel y aviso «lleno»)
SELECT z.nombre_zona,
       COUNT(*) FILTER (WHERE e.estado='ocupado')    AS ocupados,
       COUNT(*) FILTER (WHERE e.estado='disponible') AS disponibles,
       COUNT(*) FILTER (WHERE e.estado='mantenimiento') AS mantenimiento
FROM zona_estacionamiento z JOIN espacio_estacionamiento e USING (id_zona)
GROUP BY z.nombre_zona ORDER BY z.nombre_zona;

-- Tiempo promedio de ingreso (indicador del piloto). Definición [PROPUESTA]:
-- del momento en que se lee el QR (fecha_hora_ingreso de la sesión) hasta que la validación se completa.
-- Requiere guardar el instante de validación: usar el evento de tipo 'validacion_ingreso'.
SELECT AVG(EXTRACT(EPOCH FROM (ev.fecha_hora - s.fecha_hora_ingreso)))::int AS seg
FROM sesion_estacionamiento s
JOIN evento_deteccion_ia ev ON ev.id_sesion = s.id_sesion AND ev.tipo_evento='validacion_ingreso'
WHERE s.fecha_hora_ingreso::date BETWEEN :ini AND :fin;

-- Permanencia por sesión
SELECT id_sesion, fecha_hora_salida - fecha_hora_ingreso AS permanencia
FROM sesion_estacionamiento WHERE fecha_hora_salida IS NOT NULL;

-- Historial filtrable (HU21)
SELECT s.id_sesion, u.codigo_utp, v.tipo_vmp, v.marca, s.fecha_hora_ingreso, s.fecha_hora_salida, s.resultado_validacion
FROM sesion_estacionamiento s
JOIN usuario_utp u USING (id_usuario_utp)
LEFT JOIN vehiculo_vmp v USING (id_vehiculo)
WHERE (:codigo IS NULL OR u.codigo_utp = :codigo)
  AND s.fecha_hora_ingreso BETWEEN :desde AND :hasta
  AND (:id_vehiculo IS NULL OR s.id_vehiculo = :id_vehiculo)
ORDER BY s.fecha_hora_ingreso DESC;
```

> **Cuidado de definición:** el Avance no define exactamente qué es «tiempo de ingreso». La propuesta de arriba (QR leído → validación completada) mide lo que el sistema controla. Anotado en docs/13 #7.
