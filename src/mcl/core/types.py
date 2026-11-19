"""Tipos compartidos entre módulos de MCL.

Aquí viven los tipos que usan varios módulos a la vez; por ejemplo, ``catalogo``,
``envios`` y ``calificaciones`` comparten :class:`Ciudad` y :class:`EstadoEnvio`. Tenerlos
en ``core`` evita que esos módulos se importen entre sí y se formen importaciones
circulares.

Los valores de texto de los enums son parte del contrato con la app móvil: no se
cambian sin versionar la API. La propiedad ``etiqueta`` es solo el nombre que se muestra
en pantalla y sí puede ajustarse.
"""

from dataclasses import dataclass
from enum import StrEnum


class CategoriaServicio(StrEnum):
    """Tipo de servicio de transporte que se ofrece o se solicita."""

    CARGA_GENERAL = "carga_general"
    PAQUETERIA = "paqueteria"
    MUDANZAS = "mudanzas"
    CARGA_PESADA = "carga_pesada"

    @property
    def etiqueta(self) -> str:
        """Nombre para mostrar en pantalla."""
        return _ETIQUETAS_CATEGORIA[self]


class EstadoEnvio(StrEnum):
    """Etapas por las que pasa una solicitud de transporte hasta convertirse en envío."""

    PENDIENTE = "pendiente"
    CONFIRMADO = "confirmado"
    EN_TRANSITO = "en_transito"
    ENTREGADO = "entregado"
    CANCELADO = "cancelado"
    RECHAZADO = "rechazado"

    @property
    def etiqueta(self) -> str:
        """Nombre para mostrar en pantalla."""
        return _ETIQUETAS_ESTADO[self]

    @property
    def activo(self) -> bool:
        """Indica si el envío sigue en curso (aún no se entrega, cancela ni rechaza)."""
        return self in {EstadoEnvio.PENDIENTE, EstadoEnvio.CONFIRMADO, EstadoEnvio.EN_TRANSITO}


class Ciudad(StrEnum):
    """Ciudades donde opera la plataforma."""

    QUERETARO = "queretaro"
    CDMX = "cdmx"
    GUADALAJARA = "guadalajara"
    MONTERREY = "monterrey"
    PUEBLA = "puebla"
    LEON = "leon"
    SAN_LUIS_POTOSI = "san_luis_potosi"

    @property
    def etiqueta(self) -> str:
        """Nombre para mostrar en pantalla."""
        return _ETIQUETAS_CIUDAD[self]


class TipoVehiculo(StrEnum):
    """Tipo de vehículo con el que se presta el servicio."""

    CAMIONETA = "camioneta"
    VAN = "van"
    CAMION = "camion"
    TRAILER = "trailer"

    @property
    def etiqueta(self) -> str:
        """Nombre para mostrar en pantalla."""
        return _ETIQUETAS_VEHICULO[self]


class Rol(StrEnum):
    """Papel con el que una persona usa la plataforma."""

    CLIENTE = "cliente"
    TRANSPORTISTA = "transportista"
    ADMINISTRADOR = "administrador"

    @property
    def etiqueta(self) -> str:
        """Nombre para mostrar en pantalla."""
        return _ETIQUETAS_ROL[self]


@dataclass(frozen=True, slots=True)
class Actor:
    """Quién realiza una operación: su rol y a nombre de quién actúa.

    ``empresa`` es el cliente al que representa y ``transportista_id`` el transportista con
    el que opera. Cada regla del negocio mira solo el dato que corresponde a ``rol``.
    """

    rol: Rol
    empresa: str = ""
    transportista_id: int | None = None


_ETIQUETAS_CATEGORIA: dict[CategoriaServicio, str] = {
    CategoriaServicio.CARGA_GENERAL: "Carga general",
    CategoriaServicio.PAQUETERIA: "Paquetería",
    CategoriaServicio.MUDANZAS: "Mudanzas",
    CategoriaServicio.CARGA_PESADA: "Carga pesada",
}

_ETIQUETAS_ESTADO: dict[EstadoEnvio, str] = {
    EstadoEnvio.PENDIENTE: "Pendiente",
    EstadoEnvio.CONFIRMADO: "Confirmado",
    EstadoEnvio.EN_TRANSITO: "En tránsito",
    EstadoEnvio.ENTREGADO: "Entregado",
    EstadoEnvio.CANCELADO: "Cancelado",
    EstadoEnvio.RECHAZADO: "Rechazado",
}

_ETIQUETAS_CIUDAD: dict[Ciudad, str] = {
    Ciudad.QUERETARO: "Querétaro",
    Ciudad.CDMX: "CDMX",
    Ciudad.GUADALAJARA: "Guadalajara",
    Ciudad.MONTERREY: "Monterrey",
    Ciudad.PUEBLA: "Puebla",
    Ciudad.LEON: "León",
    Ciudad.SAN_LUIS_POTOSI: "San Luis Potosí",
}

_ETIQUETAS_VEHICULO: dict[TipoVehiculo, str] = {
    TipoVehiculo.CAMIONETA: "Camioneta",
    TipoVehiculo.VAN: "Van",
    TipoVehiculo.CAMION: "Camión",
    TipoVehiculo.TRAILER: "Tráiler",
}

_ETIQUETAS_ROL: dict[Rol, str] = {
    Rol.CLIENTE: "Cliente",
    Rol.TRANSPORTISTA: "Transportista",
    Rol.ADMINISTRADOR: "Administrador",
}
