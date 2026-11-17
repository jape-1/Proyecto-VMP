"""Esquema inicial del avance (docs/05 §4 + brechas aprobadas en docs/13 §F).

Revision ID: 0001
Revises:
Create Date: 2026-11-15

Diferencias conscientes con el DDL de docs/05 §4:
- TIMESTAMPTZ en lugar de TIMESTAMP: se guardan instantes en UTC y se muestran en
  America/Lima (docs/18 §6).
- `vehiculo_vmp.foto_referencia_url` es NULL hasta que se sube la foto (HU03).
- Columnas y enums de las brechas aprobadas 2026-11-15 (ver docs/13 §F).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIPOS = {
    "tipo_usuario": ("estudiante", "docente", "administrativo"),
    "estado_matricula": ("activo", "inactivo"),
    "origen_sync": ("login_portal", "consulta_qr_app"),
    "resultado_sync": ("exitoso", "fallido"),
    "tipo_vmp": ("bicicleta", "bicicleta_electrica", "scooter_electrico", "moto_electrica"),
    "estado_activo": ("activo", "inactivo"),
    "estado_qr": ("activo", "revocado", "expirado"),
    "estado_espacio": ("disponible", "ocupado", "mantenimiento"),
    "resultado_valid": ("validado", "rechazado"),
    "estado_sesion": ("en_curso", "finalizada", "con_incidencia"),
    "estado_validacion": ("pendiente", "validado", "verificar", "rechazado", "ia_no_disponible"),
    "tipo_evento_ia": ("validacion_ingreso", "ocupacion_espacio", "liberacion_espacio"),
    "turno_personal": ("manana", "tarde", "noche"),
    "rol_personal": ("seguridad", "administrador"),
    "tipo_incidencia": (
        "vehiculo_no_coincide",
        "sin_espacio_disponible",
        "error_lectura_qr",
        "otro",
    ),
    "estado_incidencia": ("abierta", "en_revision", "cerrada"),
    "tipo_notificacion": ("confirmacion_ingreso", "estacionamiento_lleno", "ingreso_rechazado"),
    "canal_notif": ("app_utp",),
}

# Orden de creación: respeta las claves foráneas (personal antes de sesión).
TABLAS = (
    "notificacion",
    "reporte_piloto",
    "incidencia",
    "evento_deteccion_ia",
    "intento_lectura_qr",
    "sesion_estacionamiento",
    "espacio_estacionamiento",
    "zona_estacionamiento",
    "personal_seguridad",
    "codigo_qr",
    "vehiculo_vmp",
    "sincronizacion_utp",
    "usuario_utp",
)


def upgrade() -> None:
    for nombre, valores in TIPOS.items():
        lista = ", ".join(f"'{v}'" for v in valores)
        op.execute(f"CREATE TYPE {nombre} AS ENUM ({lista})")

    # ===== Identidad y Accesos =====
    op.execute(
        """
        CREATE TABLE usuario_utp (
          id_usuario_utp              SERIAL PRIMARY KEY,
          codigo_utp                  VARCHAR(10)  NOT NULL UNIQUE,
          tipo_usuario                tipo_usuario NOT NULL,
          nombres                     VARCHAR(100) NOT NULL,
          apellidos                   VARCHAR(100) NOT NULL,
          correo_institucional        VARCHAR(120) NOT NULL UNIQUE,
          sede                        VARCHAR(50)  NOT NULL,
          estado_matricula            estado_matricula NOT NULL DEFAULT 'activo',
          fecha_ultima_sincronizacion TIMESTAMPTZ,
          acepta_tratamiento_datos    BOOLEAN NOT NULL DEFAULT FALSE,
          fecha_consentimiento        TIMESTAMPTZ,
          version_consentimiento      VARCHAR(20)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE sincronizacion_utp (
          id_sincronizacion SERIAL PRIMARY KEY,
          id_usuario_utp    INT NOT NULL REFERENCES usuario_utp(id_usuario_utp),
          origen            origen_sync NOT NULL,
          fecha_hora        TIMESTAMPTZ NOT NULL DEFAULT now(),
          resultado         resultado_sync NOT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_sync_usuario_fecha ON sincronizacion_utp(id_usuario_utp, fecha_hora DESC)"
    )

    op.execute(
        """
        CREATE TABLE vehiculo_vmp (
          id_vehiculo               SERIAL PRIMARY KEY,
          id_usuario_utp            INT NOT NULL REFERENCES usuario_utp(id_usuario_utp),
          tipo_vmp                  tipo_vmp NOT NULL,
          marca                     VARCHAR(50)  NOT NULL,
          modelo                    VARCHAR(50),
          color                     VARCHAR(50)  NOT NULL,
          caracteristica_distintiva VARCHAR(255),
          foto_referencia_url       VARCHAR(255),
          fecha_registro            TIMESTAMPTZ NOT NULL DEFAULT now(),
          estado                    estado_activo NOT NULL DEFAULT 'activo'
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_vehiculo_usuario ON vehiculo_vmp(id_usuario_utp) WHERE estado = 'activo'"
    )

    op.execute(
        """
        CREATE TABLE codigo_qr (
          id_qr             SERIAL PRIMARY KEY,
          id_usuario_utp    INT NOT NULL REFERENCES usuario_utp(id_usuario_utp),
          token_hash        VARCHAR(64) NOT NULL UNIQUE,
          fecha_generacion  TIMESTAMPTZ NOT NULL DEFAULT now(),
          fecha_expiracion  TIMESTAMPTZ NOT NULL,
          estado            estado_qr NOT NULL DEFAULT 'activo',
          CHECK (fecha_expiracion > fecha_generacion)
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX ux_qr_activo_por_usuario "
        "ON codigo_qr(id_usuario_utp) WHERE estado = 'activo'"
    )

    # ===== Estacionamiento (tablas creadas vacías, docs/18 §8) =====
    op.execute(
        """
        CREATE TABLE zona_estacionamiento (
          id_zona         SERIAL PRIMARY KEY,
          nombre_zona     VARCHAR(50) NOT NULL,
          sede            VARCHAR(50) NOT NULL,
          capacidad_total INT NOT NULL CHECK (capacidad_total > 0),
          UNIQUE (sede, nombre_zona)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE espacio_estacionamiento (
          id_espacio           SERIAL PRIMARY KEY,
          id_zona              INT NOT NULL REFERENCES zona_estacionamiento(id_zona),
          codigo_espacio       VARCHAR(10) NOT NULL,
          estado               estado_espacio NOT NULL DEFAULT 'disponible',
          ultima_actualizacion TIMESTAMPTZ NOT NULL DEFAULT now(),
          pos_x                NUMERIC(6,2),
          pos_y                NUMERIC(6,2),
          roi_json             JSONB,
          UNIQUE (id_zona, codigo_espacio)
        )
        """
    )

    # ===== Administración (personal antes de sesión: la sesión lo referencia) =====
    op.execute(
        """
        CREATE TABLE personal_seguridad (
          id_personal     SERIAL PRIMARY KEY,
          nombres         VARCHAR(100) NOT NULL,
          apellidos       VARCHAR(100) NOT NULL,
          usuario_acceso  VARCHAR(50)  NOT NULL UNIQUE,
          contrasena_hash VARCHAR(255) NOT NULL,
          turno           turno_personal NOT NULL,
          rol             rol_personal NOT NULL DEFAULT 'seguridad',
          estado          estado_activo NOT NULL DEFAULT 'activo'
        )
        """
    )

    op.execute(
        """
        CREATE TABLE sesion_estacionamiento (
          id_sesion            SERIAL PRIMARY KEY,
          id_vehiculo          INT REFERENCES vehiculo_vmp(id_vehiculo),
          id_usuario_utp       INT NOT NULL REFERENCES usuario_utp(id_usuario_utp),
          id_qr                INT NOT NULL REFERENCES codigo_qr(id_qr),
          id_espacio           INT REFERENCES espacio_estacionamiento(id_espacio),
          fecha_hora_ingreso   TIMESTAMPTZ NOT NULL DEFAULT now(),
          fecha_hora_salida    TIMESTAMPTZ,
          resultado_validacion resultado_valid,
          estado_sesion        estado_sesion NOT NULL DEFAULT 'en_curso',
          estado_validacion    estado_validacion NOT NULL DEFAULT 'pendiente',
          motivo               VARCHAR(50),
          mejor_confianza      NUMERIC(4,2) CHECK (
                                 mejor_confianza IS NULL
                                 OR (mejor_confianza >= 0 AND mejor_confianza <= 1)
                               ),
          id_personal_decision INT REFERENCES personal_seguridad(id_personal),
          fecha_decision       TIMESTAMPTZ,
          motivo_decision      VARCHAR(255),
          CHECK (fecha_hora_salida IS NULL OR fecha_hora_salida >= fecha_hora_ingreso)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_sesion_usuario_fecha "
        "ON sesion_estacionamiento(id_usuario_utp, fecha_hora_ingreso DESC)"
    )
    op.execute("CREATE INDEX ix_sesion_vehiculo ON sesion_estacionamiento(id_vehiculo)")
    op.execute(
        "CREATE UNIQUE INDEX ux_sesion_vehiculo_dentro ON sesion_estacionamiento(id_vehiculo) "
        "WHERE estado_sesion = 'en_curso' AND resultado_validacion = 'validado' "
        "AND fecha_hora_salida IS NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX ux_sesion_espacio_vigente ON sesion_estacionamiento(id_espacio) "
        "WHERE id_espacio IS NOT NULL AND fecha_hora_salida IS NULL"
    )

    # Registro simple de intentos fallidos (docs/13 #5, opción A).
    op.execute(
        """
        CREATE TABLE intento_lectura_qr (
          id_intento          SERIAL PRIMARY KEY,
          token_hash_parcial  VARCHAR(16) NOT NULL,
          motivo              VARCHAR(50) NOT NULL,
          codigo_camara       VARCHAR(20),
          id_personal         INT REFERENCES personal_seguridad(id_personal),
          fecha_hora          TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_intento_fecha ON intento_lectura_qr(fecha_hora DESC)")

    op.execute(
        """
        CREATE TABLE evento_deteccion_ia (
          id_evento            SERIAL PRIMARY KEY,
          id_sesion            INT REFERENCES sesion_estacionamiento(id_sesion),
          id_espacio           INT REFERENCES espacio_estacionamiento(id_espacio),
          tipo_evento          tipo_evento_ia NOT NULL,
          codigo_camara        VARCHAR(20) NOT NULL,
          imagen_capturada_url VARCHAR(255),
          score_confianza      NUMERIC(4,2) CHECK (
                                 score_confianza IS NULL
                                 OR (score_confianza >= 0 AND score_confianza <= 1)
                               ),
          fecha_hora           TIMESTAMPTZ NOT NULL DEFAULT now(),
          event_id             UUID NOT NULL UNIQUE,
          modelo_version       VARCHAR(50),
          detecciones          JSONB,
          motivo               VARCHAR(50)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_evento_espacio_fecha ON evento_deteccion_ia(id_espacio, fecha_hora DESC)"
    )
    op.execute("CREATE INDEX ix_evento_sesion ON evento_deteccion_ia(id_sesion)")

    op.execute(
        """
        CREATE TABLE incidencia (
          id_incidencia     SERIAL PRIMARY KEY,
          id_sesion         INT NOT NULL REFERENCES sesion_estacionamiento(id_sesion),
          id_personal       INT REFERENCES personal_seguridad(id_personal),
          tipo_incidencia   tipo_incidencia NOT NULL,
          descripcion       TEXT,
          fecha_hora        TIMESTAMPTZ NOT NULL DEFAULT now(),
          resuelta          BOOLEAN NOT NULL DEFAULT FALSE,
          estado            estado_incidencia NOT NULL DEFAULT 'abierta',
          evidencia_url     VARCHAR(255),
          comentario_cierre TEXT,
          fecha_cierre      TIMESTAMPTZ
        )
        """
    )
    op.execute("CREATE INDEX ix_incidencia_estado ON incidencia(estado, fecha_hora DESC)")

    # ===== Notificaciones y Reportes (sin flujo en este avance) =====
    op.execute(
        """
        CREATE TABLE notificacion (
          id_notificacion    SERIAL PRIMARY KEY,
          id_usuario_utp     INT NOT NULL REFERENCES usuario_utp(id_usuario_utp),
          id_sesion          INT REFERENCES sesion_estacionamiento(id_sesion),
          tipo_notificacion  tipo_notificacion NOT NULL,
          mensaje            VARCHAR(255) NOT NULL,
          fecha_envio        TIMESTAMPTZ NOT NULL DEFAULT now(),
          canal              canal_notif NOT NULL DEFAULT 'app_utp'
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_notif_usuario_fecha ON notificacion(id_usuario_utp, fecha_envio DESC)"
    )

    op.execute(
        """
        CREATE TABLE reporte_piloto (
          id_reporte                  SERIAL PRIMARY KEY,
          periodo_inicio              DATE NOT NULL,
          periodo_fin                 DATE NOT NULL,
          tiempo_promedio_ingreso_seg INT,
          total_incidencias           INT NOT NULL DEFAULT 0,
          nivel_satisfaccion_promedio NUMERIC(3,2),
          generado_en                 TIMESTAMPTZ NOT NULL DEFAULT now(),
          CHECK (periodo_fin >= periodo_inicio)
        )
        """
    )


def downgrade() -> None:
    for tabla in TABLAS:
        op.execute(f"DROP TABLE IF EXISTS {tabla}")
    for nombre in reversed(list(TIPOS)):
        op.execute(f"DROP TYPE IF EXISTS {nombre}")
