"""Tests de las migraciones de la base de datos."""

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from mcl.core import get_engine
from mcl.db import MODELS, alembic_config, target_metadata, upgrade_database


def test_las_migraciones_crean_todas_las_tablas() -> None:
    upgrade_database()

    tablas = set(inspect(get_engine()).get_table_names())
    assert {modelo.__tablename__ for modelo in MODELS} <= tablas
    assert "alembic_version" in tablas


def test_las_migraciones_coinciden_con_los_modelos() -> None:
    """Si falla, a algún cambio de modelo le falta su migración.

    Se genera con ``alembic revision --autogenerate -m "descripción"``.
    """
    upgrade_database()

    with get_engine().connect() as conexion:
        diferencias = compare_metadata(MigrationContext.configure(conexion), target_metadata())

    assert diferencias == []


def test_aplicar_dos_veces_no_cambia_nada() -> None:
    upgrade_database()
    upgrade_database()

    assert "transportistas" in inspect(get_engine()).get_table_names()


def test_se_pueden_revertir() -> None:
    upgrade_database()

    command.downgrade(alembic_config(), "base")

    assert inspect(get_engine()).get_table_names() == ["alembic_version"]
