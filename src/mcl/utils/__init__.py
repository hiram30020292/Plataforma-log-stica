"""Funciones auxiliares puras y reutilizables.

Reglas: sin estado, sin entrada/salida (archivos, red, base de datos) y sin importar nada
de ``mcl``; solo la biblioteca estándar. Si una función necesita algo del dominio, no
pertenece aquí.
"""

from mcl.utils._geo import haversine_km
from mcl.utils._numbers import round_half_up, round_to_multiple
from mcl.utils._text import normalize_text

__all__ = ["haversine_km", "normalize_text", "round_half_up", "round_to_multiple"]
