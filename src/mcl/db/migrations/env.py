"""Entorno de Alembic: conecta con la base de ``MCL_DATABASE_URL`` y aplica migraciones."""

from typing import Any, Literal

from alembic import context
from alembic.autogenerate.api import AutogenContext
from sqlalchemy.types import TypeDecorator

from mcl.core import get_engine, get_settings
from mcl.db import target_metadata as _todas_las_tablas

# Todas las tablas de la app: contra ellas compara ``alembic revision --autogenerate``.
target_metadata = _todas_las_tablas()


def render_item(type_: str, obj: Any, _autogen_context: AutogenContext) -> str | Literal[False]:
    """Escribe los tipos propios de la app con su tipo estándar de SQLAlchemy.

    Así las migraciones no dependen del código de la app, que puede cambiar después.
    """
    if type_ == "type" and isinstance(obj, TypeDecorator):
        return f"sa.{obj.impl!r}"
    return False


def run_migrations_offline() -> None:
    """Escribe el SQL de las migraciones sin conectarse (``alembic upgrade head --sql``)."""
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Aplica las migraciones sobre la base configurada."""
    with get_engine().connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # SQLite no sabe modificar columnas: Alembic recrea la tabla en esos casos.
            render_as_batch=True,
            render_item=render_item,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
