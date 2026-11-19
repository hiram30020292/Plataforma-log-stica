"""Íconos SVG (trazos de 24 x 24) que usan las plantillas con la macro ``icono``."""

from collections.abc import Mapping
from types import MappingProxyType

from mcl.core import CategoriaServicio

ICONOS: Mapping[str, str] = MappingProxyType(
    {
        "home": '<path d="M3 11.5 12 4l9 7.5"/><path d="M5 10v10h5v-6h4v6h5V10"/>',
        "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
        "box": (
            '<path d="M3 7.5 12 3l9 4.5v9L12 21l-9-4.5z"/><path d="M3 7.5 12 12l9-4.5M12 12v9"/>'
        ),
        "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21c1-4 4.5-6 8-6s7 2 8 6"/>',
        "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
        "close": '<path d="M6 6l12 12M18 6 6 18"/>',
        "back": '<path d="M15 5l-7 7 7 7"/>',
        "chev": '<path d="m9 5 7 7-7 7"/>',
        "bell": '<path d="M6 16V11a6 6 0 1 1 12 0v5l2 2H4z"/><path d="M10 20a2 2 0 0 0 4 0"/>',
        "pin": (
            '<path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z"/>'
            '<circle cx="12" cy="9.5" r="2.5"/>'
        ),
        "star": (
            '<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>'
        ),
        "plus": '<path d="M12 5v14M5 12h14"/>',
        "check": '<path d="m5 12.5 4.5 4.5L19 7"/>',
        "shield": (
            '<path d="M12 3 4 6v6c0 4.5 3.4 8.3 8 9 4.6-.7 8-4.5 8-9V6z"/>'
            '<path d="m8.5 12 2.5 2.5 4.5-5"/>'
        ),
        "building": (
            '<path d="M4 21V5l8-2v18M12 8h8v13M4 21h16"/>'
            '<path d="M7 8h2M7 12h2M7 16h2M15 12h2M15 16h2"/>'
        ),
        "chart": '<path d="M4 20V4M4 20h16"/><path d="m7 15 4-4 3 3 5-6"/>',
        "list": '<path d="M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01"/>',
        "truck": (
            '<path d="M2 6h11v10H2zM13 9h4l4 4v3h-8z"/>'
            '<circle cx="6" cy="17.5" r="1.8"/><circle cx="17" cy="17.5" r="1.8"/>'
        ),
        "parcel": (
            '<rect x="3" y="7" width="18" height="13" rx="1.5"/>'
            '<path d="M3 11h18M12 7v13M8 3h8l2 4H6z"/>'
        ),
        "house": '<path d="M3 11 12 4l9 7"/><path d="M5 9.5V20h14V9.5"/><path d="M10 20v-5h4v5"/>',
        "phone": (
            '<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a1 1 0 0 1-1 1'
            'A16 16 0 0 1 4 5a1 1 0 0 1 1-1z"/>'
        ),
        "logout": '<path d="M14 4h5v16h-5M10 8l-4 4 4 4M6 12h10"/>',
        "refresh": '<path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 4v7h-7"/>',
    }
)

# Ícono que representa cada categoría de servicio.
ICONO_CATEGORIA: Mapping[CategoriaServicio, str] = MappingProxyType(
    {
        CategoriaServicio.CARGA_GENERAL: "box",
        CategoriaServicio.PAQUETERIA: "parcel",
        CategoriaServicio.MUDANZAS: "house",
        CategoriaServicio.CARGA_PESADA: "truck",
    }
)
