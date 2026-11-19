"""Búsqueda y filtros del catálogo de transportistas."""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from mcl.catalogo._modelos import Transportista
from mcl.core import CategoriaServicio, Ciudad, TipoVehiculo
from mcl.utils import normalize_text


class OrdenCatalogo(StrEnum):
    """Cómo se ordenan los resultados del catálogo."""

    MEJOR_CALIFICADOS = "calificacion"
    MENOR_PRECIO = "precio"

    @property
    def etiqueta(self) -> str:
        """Nombre para mostrar en pantalla."""
        if self is OrdenCatalogo.MENOR_PRECIO:
            return "Menor precio"
        return "Mejor calificados"


@dataclass(frozen=True, slots=True)
class FiltroCatalogo:
    """Criterios de búsqueda. Los que quedan en ``None`` (o vacíos) no filtran."""

    texto: str = ""
    categoria: CategoriaServicio | None = None
    ciudad: Ciudad | None = None
    vehiculo: TipoVehiculo | None = None
    orden: OrdenCatalogo = OrdenCatalogo.MEJOR_CALIFICADOS


def filtrar_transportistas(
    transportistas: Iterable[Transportista], filtro: FiltroCatalogo
) -> list[Transportista]:
    """Devuelve los transportistas que cumplen ``filtro``, ya ordenados.

    El texto se busca sin importar mayúsculas ni acentos en el nombre, la ciudad, el
    vehículo, la descripción, la cobertura y los servicios; cada palabra debe aparecer.
    Una ciudad coincide con la ciudad base del transportista o con su cobertura.
    """
    palabras = normalize_text(filtro.texto).split()
    resultado = [t for t in transportistas if _cumple(t, filtro, palabras)]
    if filtro.orden is OrdenCatalogo.MENOR_PRECIO:
        resultado.sort(key=lambda t: (t.tarifa_base, -t.calificacion, t.nombre))
    else:
        resultado.sort(key=lambda t: (-t.calificacion, -t.num_opiniones, t.nombre))
    return resultado


def _cumple(transportista: Transportista, filtro: FiltroCatalogo, palabras: list[str]) -> bool:
    if filtro.categoria is not None and filtro.categoria not in transportista.categorias:
        return False
    if filtro.ciudad is not None and filtro.ciudad not in {
        transportista.ciudad,
        *transportista.zonas,
    }:
        return False
    if filtro.vehiculo is not None and transportista.vehiculo is not filtro.vehiculo:
        return False
    if not palabras:
        return True
    texto = normalize_text(
        " ".join(
            [
                transportista.nombre,
                transportista.ciudad.etiqueta,
                transportista.vehiculo.etiqueta,
                transportista.descripcion,
                *(zona.etiqueta for zona in transportista.zonas),
                *(categoria.etiqueta for categoria in transportista.categorias),
            ]
        )
    )
    return all(palabra in texto for palabra in palabras)
