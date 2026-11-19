"""Redondeos de cantidades."""

import math


def round_half_up(value: float) -> int:
    """Redondea al entero más cercano; los empates (x.5) suben, como se redondea a mano.

    ``round()`` de Python redondea los empates al número par (``round(2.5) == 2``), lo que
    sorprende en precios y distancias.
    """
    return math.floor(value + 0.5)


def round_to_multiple(value: float, multiple: int) -> int:
    """Redondea ``value`` al múltiplo de ``multiple`` más cercano (los empates suben)."""
    if multiple <= 0:
        msg = "El múltiplo debe ser un entero positivo."
        raise ValueError(msg)
    return round_half_up(value / multiple) * multiple
