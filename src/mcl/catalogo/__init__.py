"""Catálogo de transportistas: perfiles, búsqueda, registro y verificación."""

from mcl.catalogo._busqueda import FiltroCatalogo, OrdenCatalogo, filtrar_transportistas
from mcl.catalogo._modelos import Transportista
from mcl.catalogo._servicio import (
    DatosRegistro,
    buscar_transportistas,
    cambiar_destacado,
    cambiar_verificacion,
    listar_transportistas,
    obtener_transportista,
    registrar_transportista,
    transportistas_destacados,
)
from mcl.catalogo._vehiculos import ESPECIFICACIONES_VEHICULO, EspecificacionVehiculo

__all__ = [
    "ESPECIFICACIONES_VEHICULO",
    "DatosRegistro",
    "EspecificacionVehiculo",
    "FiltroCatalogo",
    "OrdenCatalogo",
    "Transportista",
    "buscar_transportistas",
    "cambiar_destacado",
    "cambiar_verificacion",
    "filtrar_transportistas",
    "listar_transportistas",
    "obtener_transportista",
    "registrar_transportista",
    "transportistas_destacados",
]
