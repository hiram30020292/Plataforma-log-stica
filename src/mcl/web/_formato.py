"""Filtros de las plantillas para mostrar cantidades y fechas al estilo de México."""

from datetime import date, datetime

from mcl.core import get_settings
from mcl.utils import round_half_up

_MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


def dinero(valor: float) -> str:
    """Pesos sin centavos y con separador de miles: ``2200`` → ``"$2,200"``."""
    return f"${round_half_up(valor):,}"


def numero(valor: float) -> str:
    """Entero con separador de miles: ``18000`` → ``"18,000"``."""
    return f"{round_half_up(valor):,}"


def fecha(valor: date) -> str:
    """Fecha corta: ``"21/11/2026"``. Las fechas con hora se pasan a la zona local."""
    return f"{_local(valor):%d/%m/%Y}"


def fecha_hora(valor: datetime) -> str:
    """Día, mes y hora local: ``"18 nov · 14:30"``."""
    local = valor.astimezone(get_settings().tz)
    return f"{local.day:02d} {_MESES[local.month - 1]} · {local:%H:%M}"


def dia_mes(valor: date) -> str:
    """Día y mes, para los ejes de las gráficas: ``"05 nov"``."""
    local = _local(valor)
    return f"{local.day:02d} {_MESES[local.month - 1]}"


def _local(valor: date) -> date:
    if isinstance(valor, datetime):
        return valor.astimezone(get_settings().tz).date()
    return valor
