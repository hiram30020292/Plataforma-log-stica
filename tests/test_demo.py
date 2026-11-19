"""Tests de los datos de ejemplo."""

from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from mcl.calificaciones import opiniones_de
from mcl.catalogo import listar_transportistas, obtener_transportista
from mcl.core import ConflictoError, EstadoEnvio
from mcl.demo import (
    CLIENTE_DE_EJEMPLO,
    hay_datos,
    restablecer_datos_de_ejemplo,
    sembrar_datos_de_ejemplo,
    sembrar_si_esta_vacia,
)
from mcl.envios import envios_del_cliente, listar_envios


def test_carga_transportistas_opiniones_y_envios(sesion_demo: Session) -> None:
    assert len(listar_transportistas(sesion_demo)) == 8
    assert (
        sum(len(opiniones_de(sesion_demo, t.id)) for t in listar_transportistas(sesion_demo)) == 7
    )
    assert len(listar_envios(sesion_demo)) == 50


def test_la_empresa_de_la_demo_tiene_un_envio_en_cada_etapa(sesion_demo: Session) -> None:
    estados = {e.estado for e in envios_del_cliente(sesion_demo, CLIENTE_DE_EJEMPLO)}

    assert estados == {
        EstadoEnvio.PENDIENTE,
        EstadoEnvio.CONFIRMADO,
        EstadoEnvio.EN_TRANSITO,
        EstadoEnvio.ENTREGADO,
    }


def test_los_datos_son_coherentes(sesion_demo: Session, ahora: datetime) -> None:
    for envio in listar_envios(sesion_demo):
        transportista = envio.transportista
        assert envio.origen is not envio.destino
        assert envio.peso_kg <= transportista.capacidad_kg
        assert envio.categoria in transportista.categorias
        assert envio.historial[0].estado is EstadoEnvio.PENDIENTE
        assert envio.historial[-1].estado is envio.estado
        assert all(e.ocurrido_en <= ahora for e in envio.historial)


def test_siempre_genera_los_mismos_datos(sesion_demo: Session, ahora: datetime) -> None:
    primera = [(e.cliente, e.origen, e.precio) for e in listar_envios(sesion_demo)]

    restablecer_datos_de_ejemplo(sesion_demo, ahora)

    segunda = [(e.cliente, e.origen, e.precio) for e in listar_envios(sesion_demo)]
    assert segunda == primera


def test_restablecer_deshace_los_cambios(sesion_demo: Session, ahora: datetime) -> None:
    obtener_transportista(sesion_demo, 1).nombre = "Otro nombre"
    sesion_demo.commit()

    restablecer_datos_de_ejemplo(sesion_demo, ahora)

    assert obtener_transportista(sesion_demo, 1).nombre == "Transporte López"


def test_no_se_siembra_dos_veces(sesion_demo: Session, ahora: datetime) -> None:
    assert hay_datos(sesion_demo)
    assert sembrar_si_esta_vacia(sesion_demo, ahora) is False
    with pytest.raises(ConflictoError):
        sembrar_datos_de_ejemplo(sesion_demo, ahora)


def test_sembrar_si_esta_vacia(sesion: Session, ahora: datetime) -> None:
    assert not hay_datos(sesion)

    assert sembrar_si_esta_vacia(sesion, ahora) is True
    assert hay_datos(sesion)
