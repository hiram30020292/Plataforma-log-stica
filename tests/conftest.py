"""Fixtures compartidas por toda la suite de tests."""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from mcl.api import create_app
from mcl.core import Settings, dispose_engines, get_engine, get_settings, new_session
from mcl.db import target_metadata
from mcl.demo import sembrar_datos_de_ejemplo

# Momento fijo para los tests del dominio: 18 de noviembre de 2026, 12:00 en Querétaro.
AHORA = datetime(2026, 11, 18, 18, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _configuracion_aislada(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    """Aísla cada test de las variables ``MCL_*`` reales y del ``.env`` del proyecto.

    Cada test corre en una carpeta temporal vacía (sin ``.env``) y con la caché de
    :func:`get_settings` limpia, así ningún test ve la configuración de otro. La base de
    datos por defecto (``sqlite:///./mcl.db``) también queda en esa carpeta.
    """
    for campo in Settings.model_fields:
        monkeypatch.delenv(f"MCL_{campo.upper()}", raising=False)
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    yield
    dispose_engines()
    get_settings.cache_clear()


@pytest.fixture
def ahora() -> datetime:
    """El momento fijo con el que se siembran y prueban los datos del dominio."""
    return AHORA


@pytest.fixture
def sesion() -> Iterator[Session]:
    """Sesión sobre una base SQLite vacía, con todas las tablas creadas."""
    target_metadata().create_all(get_engine())
    with new_session() as sesion:
        yield sesion


@pytest.fixture
def sesion_demo(sesion: Session, ahora: datetime) -> Session:
    """Sesión con los datos de ejemplo cargados en el momento :data:`AHORA`."""
    sembrar_datos_de_ejemplo(sesion, ahora)
    return sesion


@pytest.fixture
def navegador() -> Iterator[TestClient]:
    """Cliente que se presenta como navegador (pide páginas HTML) sobre la app completa.

    La app aplica las migraciones y carga los datos de ejemplo al crearse, como al
    arrancar el servidor de verdad.
    """
    with TestClient(create_app(), headers={"Accept": "text/html"}) as cliente:
        yield cliente
