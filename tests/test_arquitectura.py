"""Verifica automáticamente las reglas de arquitectura de CLAUDE.md."""

import ast
import importlib
import pkgutil
from pathlib import Path

import pytest

import mcl

_RAIZ = Path(mcl.__file__).parent

# Qué partes de ``mcl`` puede importar cada capa base ("Dirección de dependencias"), además
# de sus propios módulos internos.
_DEPENDENCIAS_PERMITIDAS: dict[str, tuple[str, ...]] = {
    "core": ("mcl.core",),
    "utils": ("mcl.utils",),
}
# Capas externas: conocen a los temas, pero ningún tema las conoce a ellas.
_CAPAS_EXTERNAS = ("api", "web", "db")


def _paquetes() -> list[str]:
    paquetes = ["mcl"]
    for info in pkgutil.walk_packages([str(_RAIZ)], prefix="mcl."):
        if info.ispkg:
            paquetes.append(info.name)
    return paquetes


def _paquetes_de_primer_nivel() -> list[str]:
    return sorted(p.parent.name for p in _RAIZ.glob("*/__init__.py"))


def _temas() -> list[str]:
    capas = {*_DEPENDENCIAS_PERMITIDAS, *_CAPAS_EXTERNAS}
    return [p for p in _paquetes_de_primer_nivel() if p not in capas]


def _paquete_de(modulo: str) -> str | None:
    """``mcl.envios._servicio`` → ``envios``; ``mcl`` → ``None``."""
    partes = modulo.split(".")
    return partes[1] if len(partes) > 1 else None


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


def test_hay_temas_y_capas_externas() -> None:
    assert set(_CAPAS_EXTERNAS) <= set(_paquetes_de_primer_nivel())
    assert {"catalogo", "envios", "calificaciones", "reportes", "demo"} <= set(_temas())


@pytest.mark.parametrize("tema", _temas())
def test_los_temas_no_importan_las_capas_externas(tema: str) -> None:
    violaciones = {
        f"{archivo.relative_to(_RAIZ)} importa {modulo}"
        for archivo in (_RAIZ / tema).rglob("*.py")
        for modulo in _imports_de_mcl(archivo)
        if _paquete_de(modulo) in _CAPAS_EXTERNAS
    }

    assert not violaciones, f"{tema} solo puede usar core, utils y otros temas: {violaciones}"


@pytest.mark.parametrize("capa", ["web", "db"])
def test_solo_la_capa_api_importa_web_y_db(capa: str) -> None:
    violaciones = {
        f"{archivo.relative_to(_RAIZ)} importa {modulo}"
        for archivo in _RAIZ.rglob("*.py")
        if archivo.relative_to(_RAIZ).parts[0] not in {"api", capa}
        for modulo in _imports_de_mcl(archivo)
        if _paquete_de(modulo) == capa
    }

    assert not violaciones, f"Solo mcl.api puede importar de mcl.{capa}: {sorted(violaciones)}"


def test_entre_paquetes_solo_se_usa_la_interfaz_publica() -> None:
    """``from mcl.contratos import Contrato`` sí; ``from mcl.contratos._servicio import ...`` no."""
    violaciones = {
        f"{archivo.relative_to(_RAIZ)} importa {modulo}"
        for archivo in _RAIZ.rglob("*.py")
        for modulo in _imports_de_mcl(archivo)
        if len(modulo.split(".")) > 2 and _paquete_de(modulo) != archivo.relative_to(_RAIZ).parts[0]
    }

    assert not violaciones, f"Importa por la interfaz pública del paquete: {sorted(violaciones)}"


def test_no_hay_importaciones_circulares_entre_paquetes() -> None:
    dependencias: dict[str, set[str]] = {p: set() for p in _paquetes_de_primer_nivel()}
    for paquete, destinos in dependencias.items():
        for archivo in (_RAIZ / paquete).rglob("*.py"):
            for modulo in _imports_de_mcl(archivo):
                destino = _paquete_de(modulo)
                if destino is not None and destino != paquete:
                    destinos.add(destino)

    def ciclo_desde(paquete: str, camino: tuple[str, ...]) -> tuple[str, ...] | None:
        for destino in sorted(dependencias[paquete]):
            if destino in camino:
                return (*camino, destino)
            encontrado = ciclo_desde(destino, (*camino, destino))
            if encontrado:
                return encontrado
        return None

    ciclos = [c for p in dependencias if (c := ciclo_desde(p, (p,)))]
    assert not ciclos, f"Importación circular: {' → '.join(ciclos[0])}"
