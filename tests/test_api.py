"""Tests de la capa HTTP (FastAPI)."""

import pytest
from fastapi.testclient import TestClient

from mcl import __version__
from mcl.api import create_app
from mcl.core import (
    ConfiguracionError,
    ConflictoError,
    DatosInvalidosError,
    MCLError,
    PermisoDenegadoError,
    RecursoNoEncontradoError,
)


def _cliente_con_ruta_que_falla(error: MCLError) -> TestClient:
    """Crea la app con una ruta de prueba que lanza ``error``."""
    app = create_app()

    @app.get("/prueba/error")
    def ruta_que_falla() -> None:
        raise error

    return TestClient(app)


def test_health_indica_que_el_servicio_esta_vivo() -> None:
    respuesta = TestClient(create_app()).get("/health")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "status": "ok",
        "app": "MCL - Corregidora Móvil Logistics",
        "version": __version__,
        "environment": "development",
    }


def test_la_raiz_lleva_a_la_documentacion() -> None:
    respuesta = TestClient(create_app()).get("/", follow_redirects=False)

    assert respuesta.status_code == 307
    assert respuesta.headers["location"] == "/docs"


def test_la_documentacion_interactiva_esta_disponible() -> None:
    respuesta = TestClient(create_app()).get("/docs")

    assert respuesta.status_code == 200


@pytest.mark.parametrize(
    ("error", "status_esperado"),
    [
        (DatosInvalidosError("El peso debe ser mayor a cero."), 422),
        (RecursoNoEncontradoError("Vehículo", 7), 404),
        (ConflictoError("El vehículo ya está asignado en ese horario."), 409),
        (PermisoDenegadoError("Solo un administrador puede aprobar gastos."), 403),
    ],
)
def test_los_errores_del_dominio_se_responden_como_json(
    error: MCLError, status_esperado: int
) -> None:
    respuesta = _cliente_con_ruta_que_falla(error).get("/prueba/error")

    assert respuesta.status_code == status_esperado
    assert respuesta.json() == {"codigo": error.codigo, "mensaje": error.mensaje}


def test_un_error_interno_no_muestra_el_detalle_al_cliente(
    caplog: pytest.LogCaptureFixture,
) -> None:
    error = ConfiguracionError("detalle interno que el cliente no debe ver")

    respuesta = _cliente_con_ruta_que_falla(error).get("/prueba/error")

    assert respuesta.status_code == 500
    assert respuesta.json() == {
        "codigo": "configuracion_invalida",
        "mensaje": "Ocurrió un error interno. Inténtalo de nuevo más tarde.",
    }
    assert "detalle interno que el cliente no debe ver" in caplog.text
