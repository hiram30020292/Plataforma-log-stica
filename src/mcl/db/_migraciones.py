"""Aplicación de las migraciones de Alembic."""

from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData

from mcl.calificaciones import Opinion
from mcl.catalogo import Transportista
from mcl.core import Base
from mcl.envios import Envio, EventoEnvio

# Todos los modelos de la app. Importarlos registra sus tablas en ``Base.metadata``, que
# es contra lo que Alembic compara al generar migraciones nuevas.
MODELS: tuple[type[Base], ...] = (Transportista, Envio, EventoEnvio, Opinion)

_SCRIPT_LOCATION = "mcl.db:migrations"


def target_metadata() -> MetaData:
    """Metadatos con todas las tablas de la app (las de :data:`MODELS`)."""
    return Base.metadata


def alembic_config() -> Config:
    """Configuración de Alembic que apunta a las migraciones de este paquete."""
    config = Config()
    config.set_main_option("script_location", _SCRIPT_LOCATION)
    config.set_main_option("path_separator", "os")
    return config


def upgrade_database() -> None:
    """Aplica las migraciones pendientes a la base de ``MCL_DATABASE_URL``."""
    command.upgrade(alembic_config(), "head")
