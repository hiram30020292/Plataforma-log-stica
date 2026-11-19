"""Distancias entre ciudades y cotización de un viaje."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from mcl.catalogo import Transportista
from mcl.core import CategoriaServicio, Ciudad
from mcl.utils import haversine_km, round_half_up, round_to_multiple

# Latitud y longitud aproximadas del centro de cada ciudad.
COORDENADAS: Mapping[Ciudad, tuple[float, float]] = MappingProxyType(
    {
        Ciudad.QUERETARO: (20.59, -100.39),
        Ciudad.CDMX: (19.43, -99.13),
        Ciudad.GUADALAJARA: (20.67, -103.35),
        Ciudad.MONTERREY: (25.69, -100.32),
        Ciudad.PUEBLA: (19.04, -98.21),
        Ciudad.LEON: (21.12, -101.68),
        Ciudad.SAN_LUIS_POTOSI: (22.15, -100.98),
    }
)

# Las carreteras no van en línea recta: se estima un 25 % más que la distancia directa.
FACTOR_CARRETERA = 1.25
# Recorrido promedio de un servicio dentro de la misma ciudad.
DISTANCIA_LOCAL_KM = 25
# Los precios se redondean a múltiplos de 50 pesos.
REDONDEO_PRECIO = 50


@dataclass(frozen=True, slots=True)
class Cotizacion:
    """Precio estimado de un viaje y los motivos por los que no se puede solicitar."""

    distancia_km: int
    precio: int
    advertencias: tuple[str, ...] = ()

    @property
    def valida(self) -> bool:
        """Indica si la solicitud se puede enviar tal como está."""
        return not self.advertencias


def distancia_km(origen: Ciudad, destino: Ciudad) -> int:
    """Distancia aproximada por carretera entre dos ciudades."""
    if origen is destino:
        return DISTANCIA_LOCAL_KM
    lat1, lng1 = COORDENADAS[origen]
    lat2, lng2 = COORDENADAS[destino]
    return round_half_up(haversine_km(lat1, lng1, lat2, lng2) * FACTOR_CARRETERA)


def cotizar(
    transportista: Transportista,
    origen: Ciudad,
    destino: Ciudad,
    peso_kg: int,
    categoria: CategoriaServicio | None = None,
) -> Cotizacion:
    """Calcula el precio de un viaje con un transportista.

    Precio = tarifa base + km x tarifa por km del vehículo x (0.8 + 0.4 x carga), donde
    carga es la fracción de la capacidad del transportista que se ocupa (de 0 a 1). Así un
    vehículo lleno cuesta un 50 % más por kilómetro que uno casi vacío.
    """
    capacidad = transportista.capacidad_kg
    km = distancia_km(origen, destino)
    carga = min(1.0, max(peso_kg, 0) / capacidad)
    tarifa_km = transportista.especificacion.tarifa_km
    bruto = transportista.tarifa_base + km * tarifa_km * (0.8 + carga * 0.4)

    advertencias: list[str] = []
    if peso_kg <= 0:
        advertencias.append("El peso debe ser mayor a cero.")
    elif peso_kg > capacidad:
        advertencias.append(
            f"El peso supera la capacidad del vehículo ({capacidad:,} kg). "
            "Elige otro transportista."
        )
    if origen is destino:
        advertencias.append("El origen y el destino deben ser distintos.")
    if categoria is not None and categoria not in transportista.categorias:
        advertencias.append(
            f"{transportista.nombre} no ofrece el servicio de {categoria.etiqueta.lower()}."
        )
    return Cotizacion(
        distancia_km=km,
        precio=round_to_multiple(bruto, REDONDEO_PRECIO),
        advertencias=tuple(advertencias),
    )
