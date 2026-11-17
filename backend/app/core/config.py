"""Configuración del backend, leída de variables de entorno (`.env` en desarrollo)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


# Orígenes de la red local (solo en desarrollo): localhost y rangos privados.
REGEX_RED_LOCAL = (
    r"^http://(localhost|127\.0\.0\.1|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|192\.168\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(:\d{1,5})?$"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Entorno -------------------------------------------------------
    entorno: str = "dev"  # dev | test | prod
    app_nombre: str = "Servicio de estacionamiento VMP - UTP"
    app_version: str = "0.1.0"
    api_prefijo: str = "/api/v1"

    # --- Base de datos -------------------------------------------------
    database_url: str = "postgresql+psycopg://postgres@localhost:5432/vmp"
    db_echo: bool = False

    # --- Sesión --------------------------------------------------------
    jwt_secreto: str = "cambiar-en-produccion"
    jwt_algoritmo: str = "HS256"
    jwt_expira_min: int = 720

    # --- Código QR -----------------------------------------------------
    qr_secreto: str = "cambiar-en-produccion-qr"
    qr_vigencia_dias: int = 180

    # --- Imágenes ------------------------------------------------------
    media_root: Path = BACKEND_DIR / "media"
    media_secreto: str = "cambiar-en-produccion-media"
    media_url_expira_seg: int = 900
    foto_max_mb: int = 5

    # --- Servicio de IA ------------------------------------------------
    ia_modo: str = "stub"  # stub | http
    ia_url: str = "http://localhost:8001"
    ia_timeout_seg: float = 8.0
    ia_umbral_validado: float = 0.60  # PROVISIONAL: calibrar con E5 (docs/06 §8)
    # PROVISIONAL: se mide con pares de fotos propias (experimento E4, docs/26 §5).
    ia_umbral_semejanza: float = 0.70

    # --- Conector UTP --------------------------------------------------
    conector_utp: str = "simulado"

    # --- CORS ----------------------------------------------------------
    cors_origenes: str = "http://localhost:5173,http://localhost:3000"
    # Expresión regular adicional, p. ej. `https://[a-z0-9-]+\.vercel\.app`.
    # Vacía en desarrollo = se aceptan direcciones de la red local, para abrir la
    # App desde un celular en la misma Wi-Fi (http://192.168.x.x:5173).
    cors_regex: str = ""

    # --- Zona horaria de negocio --------------------------------------
    tz_negocio: str = "America/Lima"

    @property
    def origenes_cors(self) -> list[str]:
        return [o.strip() for o in self.cors_origenes.split(",") if o.strip()]

    @property
    def regex_cors(self) -> str | None:
        if self.cors_regex:
            return self.cors_regex
        if self.es_dev:
            return REGEX_RED_LOCAL
        return None

    @property
    def es_dev(self) -> bool:
        return self.entorno.lower() in {"dev", "test"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
