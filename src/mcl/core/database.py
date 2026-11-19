"""Acceso a la base de datos con SQLAlchemy.

La URL sale de ``MCL_DATABASE_URL``: SQLite en desarrollo y PostgreSQL en producción, sin
cambiar el código. Cada tema define sus tablas heredando de :class:`Base`, y los cambios
de esquema van siempre en migraciones de Alembic (paquete ``mcl.db``).

Las clases de modelo son *dataclasses*: su constructor está tipado (mypy revisa cada campo)
y solo acepta argumentos por nombre.
"""

import threading
from collections.abc import Iterator
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, override

from sqlalchemy import JSON, DateTime, Dialect, Engine, MetaData, String, create_engine, event
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, Session
from sqlalchemy.types import TypeDecorator

from mcl.core.config import get_settings

_engines: dict[str, Engine] = {}
_engines_lock = threading.Lock()

# Nombres fijos para índices y restricciones: las migraciones pueden referirse a ellos en
# cualquier base de datos.
_NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(MappedAsDataclass, DeclarativeBase, kw_only=True, eq=False):
    """Base de todos los modelos (tablas) de MCL.

    ``eq=False`` conserva la identidad de los objetos: dos filas distintas nunca son
    "iguales" aunque tengan los mismos datos, y los modelos se pueden usar en conjuntos.
    """

    metadata = MetaData(naming_convention=_NAMING_CONVENTION)


class UTCDateTime(TypeDecorator[datetime]):
    """Fecha y hora con zona horaria, guardada en UTC.

    SQLite no guarda zonas horarias: esta columna exige fechas con zona al guardar, las
    convierte a UTC y las devuelve siempre con ``tzinfo=UTC``.
    """

    impl = DateTime
    cache_ok = True

    @override
    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            msg = "Las fechas que se guardan deben llevar zona horaria."
            raise ValueError(msg)
        return value.astimezone(UTC).replace(tzinfo=None)

    @override
    def process_result_value(self, value: Any, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if not isinstance(value, datetime):
            msg = f"Se esperaba una fecha y hora, llegó {type(value).__name__}."
            raise TypeError(msg)
        return value.replace(tzinfo=UTC)


class EnumText[E: StrEnum](TypeDecorator[E]):
    """Guarda un ``StrEnum`` como su valor de texto y lo devuelve como miembro del enum."""

    impl = String
    cache_ok = True

    def __init__(self, enum_class: type[E], length: int = 30) -> None:
        super().__init__(length)
        self.enum_class = enum_class

    @override
    def process_bind_param(self, value: E | None, dialect: Dialect) -> str | None:
        return None if value is None else self.enum_class(value).value

    @override
    def process_result_value(self, value: Any, dialect: Dialect) -> E | None:
        return None if value is None else self.enum_class(value)


class EnumList[E: StrEnum](TypeDecorator[list[E]]):
    """Guarda una lista de ``StrEnum`` como JSON con sus valores de texto.

    La lista se reemplaza completa al modificarla (``modelo.campo = [...]``): los cambios
    hechos con ``append`` no se detectan.
    """

    impl = JSON
    cache_ok = True

    def __init__(self, enum_class: type[E]) -> None:
        super().__init__()
        self.enum_class = enum_class

    @override
    def process_bind_param(self, value: list[E] | None, dialect: Dialect) -> list[str] | None:
        return None if value is None else [self.enum_class(v).value for v in value]

    @override
    def process_result_value(self, value: Any, dialect: Dialect) -> list[E] | None:
        return None if value is None else [self.enum_class(v) for v in value]


def get_engine() -> Engine:
    """Devuelve el motor de base de datos de la URL configurada (uno por URL)."""
    url = get_settings().database_url
    with _engines_lock:
        engine = _engines.get(url)
        if engine is None:
            engine = _create_engine(url)
            _engines[url] = engine
        return engine


def dispose_engines() -> None:
    """Cierra todas las conexiones abiertas (al apagar la app y entre tests)."""
    with _engines_lock:
        for engine in _engines.values():
            engine.dispose()
        _engines.clear()


def new_session() -> Session:
    """Abre una sesión nueva. Úsala con ``with new_session() as sesion:``."""
    return Session(get_engine(), expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """Dependencia de FastAPI: una sesión por petición, que se cierra al terminar."""
    with new_session() as session:
        yield session


def _create_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        # FastAPI atiende cada petición en un hilo distinto; SQLite lo permite con esta opción.
        engine = create_engine(url, connect_args={"check_same_thread": False})
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
        return engine
    return create_engine(url, pool_pre_ping=True)


def _enable_sqlite_foreign_keys(dbapi_connection: Any, _connection_record: Any) -> None:
    """SQLite solo respeta las claves foráneas si se le pide en cada conexión."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
