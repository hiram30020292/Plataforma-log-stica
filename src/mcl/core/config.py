"""Configuración tipada de MCL.

La configuración se toma, de mayor a menor prioridad, de:

1. Argumentos pasados a ``Settings(...)`` (útil en tests).
2. Variables de entorno con prefijo ``MCL_`` (por ejemplo ``MCL_DATABASE_URL``).
3. El archivo ``.env`` del directorio actual, que nunca se sube al repositorio.
4. Los valores por defecto de este archivo, pensados para desarrollo local.

El resto del código obtiene la configuración solo con :func:`get_settings`.
"""

from enum import StrEnum
from functools import lru_cache
from typing import Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from mcl.core.exceptions import ConfiguracionError


class Environment(StrEnum):
    """Entorno en el que corre la aplicación."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Configuración de la aplicación. Es inmutable una vez creada."""

    model_config = SettingsConfigDict(
        env_prefix="MCL_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",  # el .env puede tener variables de otras herramientas
        frozen=True,
        hide_input_in_errors=True,
    )

    app_name: str = "MCL - Corregidora Móvil Logistics"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False

    # SQLite en desarrollo. En producción basta con apuntar a PostgreSQL.
    database_url: str = "sqlite:///./mcl.db"

    # Zona horaria para mostrar fechas y saber qué día es "hoy". Las fechas se guardan en UTC.
    timezone: str = "America/Mexico_City"

    # Datos de ejemplo: se cargan al arrancar si la base está vacía y se pueden restablecer
    # desde la app. En producción se apagan con MCL_DEMO_DATA=false.
    demo_data: bool = True

    # Avisos por correo con Gmail (SMTP con STARTTLS). La contraseña es una
    # "contraseña de aplicación" de Google, no la contraseña normal de la cuenta.
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_user: str | None = None
    smtp_password: SecretStr | None = None

    @field_validator("timezone")
    @classmethod
    def _check_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            msg = "MCL_TIMEZONE debe ser una zona horaria válida, por ejemplo America/Mexico_City."
            raise ValueError(msg) from exc
        return value

    @model_validator(mode="after")
    def _check_smtp_credentials(self) -> Self:
        if (self.smtp_user is None) != (self.smtp_password is None):
            msg = "MCL_SMTP_USER y MCL_SMTP_PASSWORD deben definirse juntas (o ninguna)."
            raise ValueError(msg)
        return self

    @property
    def tz(self) -> ZoneInfo:
        """Zona horaria configurada, lista para convertir fechas."""
        return ZoneInfo(self.timezone)

    @property
    def email_enabled(self) -> bool:
        """Indica si hay credenciales de Gmail para enviar avisos por correo."""
        return self.smtp_user is not None and self.smtp_password is not None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Devuelve la configuración de la aplicación, creada una sola vez.

    Raises:
        ConfiguracionError: si alguna variable tiene un valor inválido. El mensaje nunca
            incluye los valores recibidos, para no filtrar secretos en los logs.
    """
    try:
        return Settings()
    except ValidationError as exc:
        msg = f"Configuración inválida:\n{exc}"
        raise ConfiguracionError(msg) from exc
