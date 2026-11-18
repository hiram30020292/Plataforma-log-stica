"""Núcleo compartido de MCL: configuración, excepciones y tipos comunes.

Todos los módulos de tema dependen de ``core``; ``core`` nunca importa de ellos.
"""

from mcl.core.config import Environment, Settings, get_settings
from mcl.core.exceptions import (
    ConfiguracionError,
    ConflictoError,
    DatosInvalidosError,
    MCLError,
    PermisoDenegadoError,
    RecursoNoEncontradoError,
)
from mcl.core.types import CategoriaServicio, EstadoEnvio

__all__ = [
    "CategoriaServicio",
    "ConfiguracionError",
    "ConflictoError",
    "DatosInvalidosError",
    "Environment",
    "EstadoEnvio",
    "MCLError",
    "PermisoDenegadoError",
    "RecursoNoEncontradoError",
    "Settings",
    "get_settings",
]
