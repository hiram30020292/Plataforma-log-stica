"""Fixtures compartidas por toda la suite de tests."""

from collections.abc import Iterator
from pathlib import Path

import pytest

from mcl.core import Settings, get_settings


@pytest.fixture(autouse=True)
def _configuracion_aislada(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    """Aísla cada test de las variables ``MCL_*`` reales y del ``.env`` del proyecto.

    Cada test corre en una carpeta temporal vacía (sin ``.env``) y con la caché de
    :func:`get_settings` limpia, así ningún test ve la configuración de otro.
    """
    for campo in Settings.model_fields:
        monkeypatch.delenv(f"MCL_{campo.upper()}", raising=False)
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
