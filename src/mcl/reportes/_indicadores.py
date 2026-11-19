"""Indicadores de la operación para el panel administrativo."""

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from types import MappingProxyType
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from mcl.catalogo import Transportista, listar_transportistas
from mcl.core import EstadoEnvio, get_settings
from mcl.envios import Envio, listar_envios

DIAS_DE_LA_SERIE = 21
DIAS_RECIENTES = 7
LUGARES_DEL_RANKING = 5


@dataclass(frozen=True, slots=True)
class PuntoDiario:
    """Solicitudes recibidas en un día."""

    fecha: date
    solicitudes: int


@dataclass(frozen=True, slots=True)
class LugarRanking:
    """Transportista y cuántos viajes ha entregado."""

    transportista: Transportista
    viajes: int


@dataclass(frozen=True, slots=True)
class Indicadores:
    """Resumen de la plataforma que muestra el panel administrativo."""

    total: int
    ultimos_7_dias: int
    activos: int
    en_transito: int
    pendientes: int
    transportistas: int
    verificados: int
    por_estado: Mapping[EstadoEnvio, int]
    serie_diaria: tuple[PuntoDiario, ...]
    ranking: tuple[LugarRanking, ...]
    valor_entregado: int


def calcular_indicadores(
    envios: Sequence[Envio],
    transportistas: Sequence[Transportista],
    hoy: date,
    zona: ZoneInfo,
) -> Indicadores:
    """Calcula los indicadores a partir de los datos ya cargados.

    ``hoy`` es la fecha local; la serie diaria cubre los últimos 21 días hasta ``hoy`` y
    agrupa cada solicitud por su fecha de creación en ``zona``.
    """
    por_estado = Counter(envio.estado for envio in envios)
    por_dia = Counter(envio.creado_en.astimezone(zona).date() for envio in envios)
    serie = tuple(
        PuntoDiario(fecha=dia, solicitudes=por_dia[dia])
        for dia in (hoy - timedelta(days=atras) for atras in range(DIAS_DE_LA_SERIE - 1, -1, -1))
    )
    entregados = [envio for envio in envios if envio.estado is EstadoEnvio.ENTREGADO]
    viajes = Counter(envio.transportista_id for envio in entregados)
    ranking = sorted(transportistas, key=lambda t: (-viajes[t.id], -t.calificacion, t.nombre))
    return Indicadores(
        total=len(envios),
        ultimos_7_dias=sum(punto.solicitudes for punto in serie[-DIAS_RECIENTES:]),
        activos=por_estado[EstadoEnvio.CONFIRMADO] + por_estado[EstadoEnvio.EN_TRANSITO],
        en_transito=por_estado[EstadoEnvio.EN_TRANSITO],
        pendientes=por_estado[EstadoEnvio.PENDIENTE],
        transportistas=len(transportistas),
        verificados=sum(t.verificado for t in transportistas),
        por_estado=MappingProxyType({estado: por_estado[estado] for estado in EstadoEnvio}),
        serie_diaria=serie,
        ranking=tuple(
            LugarRanking(transportista=t, viajes=viajes[t.id])
            for t in ranking[:LUGARES_DEL_RANKING]
        ),
        valor_entregado=sum(envio.precio for envio in entregados),
    )


def indicadores(sesion: Session, ahora: datetime | None = None) -> Indicadores:
    """Indicadores actuales de la plataforma."""
    zona = get_settings().tz
    hoy = (ahora or datetime.now(UTC)).astimezone(zona).date()
    return calcular_indicadores(listar_envios(sesion), listar_transportistas(sesion), hoy, zona)
