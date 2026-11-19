"""Tests de las calificaciones de los clientes."""

from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from mcl.calificaciones import DatosCalificacion, calificar_envio, opiniones_de
from mcl.catalogo import obtener_transportista
from mcl.core import (
    Actor,
    ConflictoError,
    DatosInvalidosError,
    EstadoEnvio,
    PermisoDenegadoError,
    Rol,
)
from mcl.demo import CLIENTE_DE_EJEMPLO
from mcl.envios import Envio, cambiar_estado, envios_del_cliente

CLIENTE = Actor(rol=Rol.CLIENTE, empresa=CLIENTE_DE_EJEMPLO)


def _entregado_sin_calificar(sesion: Session) -> Envio:
    """El envío en tránsito de la demo, ya entregado (el entregado de ejemplo ya se calificó)."""
    envio = next(
        e
        for e in envios_del_cliente(sesion, CLIENTE_DE_EJEMPLO)
        if e.estado is EstadoEnvio.EN_TRANSITO
    )
    return cambiar_estado(sesion, envio.id, EstadoEnvio.ENTREGADO, Actor(rol=Rol.ADMINISTRADOR))


def test_calificar_suma_la_opinion_al_transportista(sesion_demo: Session, ahora: datetime) -> None:
    envio = _entregado_sin_calificar(sesion_demo)
    transportista = obtener_transportista(sesion_demo, envio.transportista_id)
    antes = (transportista.suma_estrellas, transportista.num_opiniones)

    opinion = calificar_envio(
        sesion_demo, envio.id, DatosCalificacion(4, " Puntuales "), CLIENTE, ahora
    )

    assert envio.calificacion == 4
    assert (transportista.suma_estrellas, transportista.num_opiniones) == (
        antes[0] + 4,
        antes[1] + 1,
    )
    assert opinion.autor == CLIENTE_DE_EJEMPLO
    assert opinion.texto == "Puntuales"
    assert opinion.envio_id == envio.id
    assert opiniones_de(sesion_demo, envio.transportista_id)[0] is opinion


def test_sin_comentario_se_guarda_un_texto_por_defecto(sesion_demo: Session) -> None:
    envio = _entregado_sin_calificar(sesion_demo)

    opinion = calificar_envio(sesion_demo, envio.id, DatosCalificacion(5), CLIENTE)

    assert opinion.texto == "Sin comentarios."


def test_solo_el_cliente_del_envio_califica(sesion_demo: Session) -> None:
    envio = _entregado_sin_calificar(sesion_demo)

    for actor in (
        Actor(rol=Rol.CLIENTE, empresa="Otra Empresa"),
        Actor(rol=Rol.TRANSPORTISTA, empresa=CLIENTE_DE_EJEMPLO, transportista_id=2),
        Actor(rol=Rol.ADMINISTRADOR, empresa=CLIENTE_DE_EJEMPLO),
    ):
        with pytest.raises(PermisoDenegadoError):
            calificar_envio(sesion_demo, envio.id, DatosCalificacion(5), actor)


def test_solo_envios_entregados(sesion_demo: Session) -> None:
    pendiente = next(
        e
        for e in envios_del_cliente(sesion_demo, CLIENTE_DE_EJEMPLO)
        if e.estado is EstadoEnvio.PENDIENTE
    )

    with pytest.raises(ConflictoError, match="entregados"):
        calificar_envio(sesion_demo, pendiente.id, DatosCalificacion(5), CLIENTE)


def test_un_envio_se_califica_una_sola_vez(sesion_demo: Session) -> None:
    envio = _entregado_sin_calificar(sesion_demo)
    calificar_envio(sesion_demo, envio.id, DatosCalificacion(5), CLIENTE)

    with pytest.raises(ConflictoError, match="ya fue calificado"):
        calificar_envio(sesion_demo, envio.id, DatosCalificacion(3), CLIENTE)


@pytest.mark.parametrize(
    ("datos", "mensaje"),
    [
        (DatosCalificacion(0), "de 1 a 5"),
        (DatosCalificacion(6), "de 1 a 5"),
        (DatosCalificacion(5, "x" * 501), "500 caracteres"),
    ],
)
def test_datos_invalidos(sesion_demo: Session, datos: DatosCalificacion, mensaje: str) -> None:
    envio = _entregado_sin_calificar(sesion_demo)

    with pytest.raises(DatosInvalidosError, match=mensaje):
        calificar_envio(sesion_demo, envio.id, datos, CLIENTE)


def test_opiniones_de_la_mas_reciente_a_la_mas_antigua(sesion_demo: Session) -> None:
    opiniones = opiniones_de(sesion_demo, 1)

    assert [o.autor for o in opiniones] == ["Comercial Ríos", "Aceros del Centro"]
    assert opiniones_de(sesion_demo, 7) == []
