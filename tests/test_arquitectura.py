"""Verifica automáticamente las reglas de arquitectura de CLAUDE.md."""

import ast
import importlib
import pkgutil
from pathlib import Path

import pytest

import mcl

_RAIZ = Path(mcl.__file__).parent

# Qué partes de ``mcl`` puede importar cada capa base ("Dirección de dependencias").
_DEPENDENCIAS_PERMITIDAS: dict[str, tuple[str, ...]] = {
    "core": ("mcl.core",),
    "utils": (),
}


def _paquetes() -> list[str]:
    paquetes = ["mcl"]
    for info in pkgutil.walk_packages([str(_RAIZ)], prefix="mcl."):
        if info.ispkg:
            paquetes.append(info.name)
    return paquetes


def _imports_de_mcl(archivo: Path) -> set[str]:
    """Devuelve los módulos de ``mcl`` que importa ``archivo``."""
    modulos: set[str] = set()
    for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
        if isinstance(nodo, ast.Import):
            modulos.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            modulos.add(nodo.module)
    return {m for m in modulos if m == "mcl" or m.startswith("mcl.")}


@pytest.mark.parametrize("nombre", _paquetes())
def test_cada_paquete_declara_su_interfaz_publica(nombre: str) -> None:
    paquete = importlib.import_module(nombre)
    interfaz = getattr(paquete, "__all__", None)

    assert isinstance(interfaz, list), f"{nombre}/__init__.py debe definir __all__ como lista"
    assert len(interfaz) == len(set(interfaz)), f"{nombre}.__all__ tiene nombres repetidos"
    faltantes = [n for n in interfaz if not hasattr(paquete, n)]
    assert not faltantes, f"{nombre}.__all__ declara nombres que no existen: {faltantes}"


@pytest.mark.parametrize("capa", sorted(_DEPENDENCIAS_PERMITIDAS))
def test_las_capas_base_respetan_la_direccion_de_dependencias(capa: str) -> None:
    permitidos = _DEPENDENCIAS_PERMITIDAS[capa]
    violaciones = {
        f"{archivo.relative_to(_RAIZ)} importa {modulo}"
        for archivo in (_RAIZ / capa).rglob("*.py")
        for modulo in _imports_de_mcl(archivo)
        if not any(modulo == p or modulo.startswith(f"{p}.") for p in permitidos)
    }

    assert not violaciones, f"{capa} importa algo que no debe: {sorted(violaciones)}"


def test_solo_la_capa_api_importa_de_api() -> None:
    violaciones = {
        f"{archivo.relative_to(_RAIZ)} importa {modulo}"
        for archivo in _RAIZ.rglob("*.py")
        if archivo.relative_to(_RAIZ).parts[0] != "api"
        for modulo in _imports_de_mcl(archivo)
        if modulo == "mcl.api" or modulo.startswith("mcl.api.")
    }

    assert not violaciones, f"Solo mcl.api puede importar de mcl.api: {sorted(violaciones)}"
