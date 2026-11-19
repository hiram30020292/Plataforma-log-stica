"""Esquema de la base de datos: migraciones versionadas con Alembic.

Cada cambio de esquema es una migración en ``migrations/versions``. La app aplica las
pendientes al arrancar (:func:`upgrade_database`); también se pueden aplicar a mano con
``alembic upgrade head``.
"""

from mcl.db._migraciones import MODELS, alembic_config, target_metadata, upgrade_database

__all__ = ["MODELS", "alembic_config", "target_metadata", "upgrade_database"]
