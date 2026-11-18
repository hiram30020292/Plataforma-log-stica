"""Tipos compartidos entre módulos de MCL.

Aquí viven los tipos que usan varios módulos a la vez; por ejemplo, ``solicitudes``,
``envios`` y ``agenda`` comparten :class:`EstadoEnvio`. Tenerlos en ``core`` evita que
esos módulos se importen entre sí y se formen importaciones circulares.

Los valores de texto de los enums son parte del contrato con la app móvil: no se
cambian sin versionar la API.
"""

from enum import StrEnum


class CategoriaServicio(StrEnum):
    """Tipo de servicio de transporte que se ofrece o se solicita."""

    CARGA_GENERAL = "carga_general"
    PAQUETERIA = "paqueteria"
    MUDANZAS = "mudanzas"
    CARGA_PESADA = "carga_pesada"


class EstadoEnvio(StrEnum):
    """Etapas por las que pasa un envío."""

    PENDIENTE = "pendiente"
    CONFIRMADO = "confirmado"
    EN_TRANSITO = "en_transito"
    ENTREGADO = "entregado"
    CANCELADO = "cancelado"
