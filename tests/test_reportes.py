"""Tests de los indicadores del panel administrativo."""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from mcl.catalogo import listar_transportistas
from mcl.core import EstadoEnvio, get_settings
from mcl.envios import listar_envios
from mcl.reportes import calcular_indicadores, indicadores


def test_indicadores_de_los_datos_de_ejemplo(sesion_demo: Session, ahora: datetime) -> None:
    datos = indicadores(sesion_demo, ahora)
    envios = listar_envios(sesion_demo)

    assert datos.total == 50
    assert datos.transportistas == 8
    assert datos.verificados == 6
    assert sum(datos.por_estado.values()) == 50
    assert datos.pendientes == datos.por_estado[EstadoEnvio.PENDIENTE]
    assert datos.en_transito == datos.por_estado[EstadoEnvio.EN_TRANSITO]
    assert datos.activos == datos.por_estado[EstadoEnvio.CONFIRMADO] + datos.en_transito
    assert datos.valor_entregado == sum(
        e.precio for e in envios if e.estado is EstadoEnvio.ENTREGADO
    )


def test_serie_de_los_ultimos_21_dias(sesion_demo: Session, ahora: datetime) -> None:
    datos = indicadores(sesion_demo, ahora)
    hoy = ahora.astimezone(get_settings().tz).date()

    assert len(datos.serie_diaria) == 21
    assert datos.serie_diaria[-1].fecha == hoy
    assert datos.serie_diaria[0].fecha == hoy - timedelta(days=20)
    assert datos.ultimos_7_dias == sum(p.solicitudes for p in datos.serie_diaria[-7:])


def test_ranking_por_viajes_entregados(sesion_demo: Session, ahora: datetime) -> None:
    ranking = indicadores(sesion_demo, ahora).ranking

    assert len(ranking) == 5
    viajes = [lugar.viajes for lugar in ranking]
    assert viajes == sorted(viajes, reverse=True)


def test_sin_datos_todo_en_cero(ahora: datetime) -> None:
    zona = get_settings().tz

    datos = calcular_indicadores([], [], ahora.astimezone(zona).date(), zona)

    assert datos.total == datos.valor_entregado == datos.ultimos_7_dias == 0
    assert datos.ranking == ()
    assert all(p.solicitudes == 0 for p in datos.serie_diaria)


def test_calcular_con_datos_cargados(sesion_demo: Session, ahora: datetime) -> None:
    zona = get_settings().tz
    envios = listar_envios(sesion_demo)[:10]

    datos = calcular_indicadores(
        envios, listar_transportistas(sesion_demo), ahora.astimezone(zona).date(), zona
    )

    assert datos.total == 10
