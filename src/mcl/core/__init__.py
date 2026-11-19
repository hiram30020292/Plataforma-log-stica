"""Núcleo compartido de MCL: configuración, base de datos, excepciones y tipos comunes.

Todos los módulos de tema dependen de ``core``; ``core`` nunca importa de ellos.
"""

from mcl.core.config import Environment, Settings, get_settings
from mcl.core.database import (
    Base,
    EnumList,
    EnumText,
    UTCDateTime,
    dispose_engines,
    get_engine,
    get_session,
    new_session,
)
from mcl.core.exceptions import (
    ConfiguracionError,
    ConflictoError,
    DatosInvalidosError,
    MCLError,
    PermisoDenegadoError,
    RecursoNoEncontradoError,
)
from mcl.core.types import Actor, CategoriaServicio, Ciudad, EstadoEnvio, Rol, TipoVehiculo

__all__ = [
    "Actor",
    "Base",
    "CategoriaServicio",
    "Ciudad",
    "ConfiguracionError",
    "ConflictoError",
    "DatosInvalidosError",
    "EnumList",
    "EnumText",
    "Environment",
    "EstadoEnvio",
    "MCLError",
    "PermisoDenegadoError",
    "RecursoNoEncontradoError",
    "Rol",
    "Settings",
    "TipoVehiculo",
    "UTCDateTime",
    "dispose_engines",
    "get_engine",
    "get_session",
    "get_settings",
    "new_session",
]
