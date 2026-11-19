"""Características de cada tipo de vehículo que usan las cotizaciones."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from mcl.core import TipoVehiculo


@dataclass(frozen=True, slots=True)
class EspecificacionVehiculo:
    """Tarifa por kilómetro (MXN) y carga máxima (kg) de un tipo de vehículo."""

    tarifa_km: int
    capacidad_kg: int


ESPECIFICACIONES_VEHICULO: Mapping[TipoVehiculo, EspecificacionVehiculo] = MappingProxyType(
    {
        TipoVehiculo.CAMIONETA: EspecificacionVehiculo(tarifa_km=7, capacidad_kg=1_000),
        TipoVehiculo.VAN: EspecificacionVehiculo(tarifa_km=9, capacidad_kg=1_500),
        TipoVehiculo.CAMION: EspecificacionVehiculo(tarifa_km=14, capacidad_kg=10_000),
        TipoVehiculo.TRAILER: EspecificacionVehiculo(tarifa_km=22, capacidad_kg=30_000),
    }
)
