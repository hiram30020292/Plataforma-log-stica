"""Cómo se presenta cada cambio de estado de un envío: botón y aviso."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType

from mcl.core import EstadoEnvio
from mcl.envios import Envio


@dataclass(frozen=True, slots=True)
class Accion:
    """Botón que lleva un envío a un estado y el aviso que se muestra después."""

    texto: str
    texto_corto: str
    clase: str
    aviso: str


ACCIONES: Mapping[EstadoEnvio, Accion] = MappingProxyType(
    {
        EstadoEnvio.CONFIRMADO: Accion("Aceptar viaje", "Aceptar", "btn-primary", "Viaje aceptado"),
        EstadoEnvio.RECHAZADO: Accion(
            "Rechazar", "Rechazar", "btn-ghost-danger", "Solicitud rechazada"
        ),
        EstadoEnvio.EN_TRANSITO: Accion(
            "Iniciar viaje", "Iniciar viaje", "btn-primary", "Viaje iniciado"
        ),
        EstadoEnvio.ENTREGADO: Accion(
            "Marcar como entregado", "Entregado", "btn-success", "Envío marcado como entregado"
        ),
        EstadoEnvio.CANCELADO: Accion(
            "Cancelar solicitud", "Cancelar", "btn-ghost-danger", "Solicitud cancelada"
        ),
        EstadoEnvio.PENDIENTE: Accion(
            "Volver a pendiente", "Pendiente", "btn-ghost", "El envío volvió a pendiente"
        ),
    }
)

_FLUJO = (
    EstadoEnvio.PENDIENTE,
    EstadoEnvio.CONFIRMADO,
    EstadoEnvio.EN_TRANSITO,
    EstadoEnvio.ENTREGADO,
)


@dataclass(frozen=True, slots=True)
class PasoSeguimiento:
    """Etapa de la línea de tiempo de un envío."""

    estado: EstadoEnvio
    momento: datetime | None
    actual: bool

    @property
    def alcanzado(self) -> bool:
        """Indica si el envío ya pasó por esta etapa."""
        return self.momento is not None


def linea_de_tiempo(envio: Envio) -> list[PasoSeguimiento]:
    """Etapas del flujo normal; si se canceló o rechazó, solo las que alcanzó y el cierre."""
    if envio.estado.activo or envio.estado is EstadoEnvio.ENTREGADO:
        estados = list(_FLUJO)
    else:
        estados = [e for e in _FLUJO if envio.momento_de(e)] + [envio.estado]
    return [
        PasoSeguimiento(estado=e, momento=envio.momento_de(e), actual=e is envio.estado)
        for e in estados
    ]
