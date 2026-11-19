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


def test_la_raiz_muestra_la_app_web() -> None:
    respuesta = TestClient(create_app()).get("/")

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/html")
    assert "Conectamos negocios con transportistas" in respuesta.text


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


def test_los_errores_del_dominio_son_paginas_para_el_navegador() -> None:
    cliente = _cliente_con_ruta_que_falla(RecursoNoEncontradoError("Vehículo", 7))

    respuesta = cliente.get("/prueba/error", headers={"Accept": "text/html"})

    assert respuesta.status_code == 404
    assert respuesta.headers["content-type"].startswith("text/html")
    assert "Vehículo con identificador 7 no existe." in respuesta.text


def test_las_rutas_de_la_api_siempre_responden_json() -> None:
    respuesta = TestClient(create_app()).get(
        "/api/v1/transportistas/999", headers={"Accept": "text/html"}
    )

    assert respuesta.status_code == 404
    assert respuesta.json() == {
        "codigo": "no_encontrado",
        "mensaje": "Transportista con identificador 999 no existe.",
    }


def test_un_error_inesperado_tampoco_muestra_el_detalle() -> None:
    app = create_app()

    @app.get("/prueba/fallo")
    def ruta_con_un_error_de_programacion() -> None:
        msg = "detalle de un error de programación"
        raise RuntimeError(msg)

    cliente = TestClient(app, raise_server_exceptions=False)
    como_json = cliente.get("/prueba/fallo")
    como_pagina = cliente.get("/prueba/fallo", headers={"Accept": "text/html"})

    assert como_json.status_code == 500
    assert como_json.json() == {
        "codigo": "error_interno",
        "mensaje": "Ocurrió un error interno. Inténtalo de nuevo más tarde.",
    }
    assert como_pagina.status_code == 500
    assert "Algo salió mal" in como_pagina.text
    assert "detalle de un error de programación" not in como_pagina.text


def test_un_formulario_malformado_muestra_una_pagina() -> None:
    respuesta = TestClient(create_app()).post(
        "/envios/abc/estado", data={"estado": "cancelado"}, headers={"Accept": "text/html"}
    )

    assert respuesta.status_code == 422
    assert "Revisa los datos" in respuesta.text


def test_una_ruta_inexistente_de_la_api_responde_json() -> None:
    respuesta = TestClient(create_app()).get("/api/v1/no-existe")

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detail": "Not Found"}


class TestApiV1:
    def test_listar_transportistas(self) -> None:
        respuesta = TestClient(create_app()).get("/api/v1/transportistas")

        assert respuesta.status_code == 200
        transportistas = respuesta.json()
        assert len(transportistas) == 8
        assert transportistas[0] == {
            "id": 2,
            "nombre": "Rápidos del Bajío",
            "ciudad": "queretaro",
            "zonas": ["queretaro", "leon", "cdmx", "guadalajara"],
            "vehiculo": "camion",
            "capacidad_kg": 5000,
            "categorias": ["carga_general", "paqueteria"],
            "tarifa_base": 1800,
            "calificacion": 4.9,
            "num_opiniones": 250,
            "verificado": True,
            "telefono": "442 987 6543",
            "descripcion": transportistas[0]["descripcion"],
        }

    def test_filtrar_transportistas(self) -> None:
        respuesta = TestClient(create_app()).get(
            "/api/v1/transportistas", params={"ciudad": "monterrey", "orden": "precio"}
        )

        assert [t["nombre"] for t in respuesta.json()] == ["Transporte López", "Norte Cargo"]

    def test_filtro_con_valor_desconocido(self) -> None:
        respuesta = TestClient(create_app()).get(
            "/api/v1/transportistas", params={"vehiculo": "cohete"}
        )

        assert respuesta.status_code == 422

    def test_detalle_con_opiniones(self) -> None:
        respuesta = TestClient(create_app()).get("/api/v1/transportistas/1")

        detalle = respuesta.json()
        assert detalle["nombre"] == "Transporte López"
        assert detalle["viajes_entregados"] >= 0
        assert [o["autor"] for o in detalle["opiniones"]] == ["Comercial Ríos", "Aceros del Centro"]

    def test_cotizar(self) -> None:
        respuesta = TestClient(create_app()).post(
            "/api/v1/cotizaciones",
            json={"transportista_id": 1, "origen": "queretaro", "destino": "cdmx", "peso_kg": 2000},
        )

        assert respuesta.status_code == 200
        assert respuesta.json() == {
            "distancia_km": 230,
            "precio": 6400,
            "moneda": "MXN",
            "valida": True,
            "advertencias": [],
        }

    def test_cotizacion_con_advertencias(self) -> None:
        respuesta = TestClient(create_app()).post(
            "/api/v1/cotizaciones",
            json={
                "transportista_id": 7,
                "origen": "cdmx",
                "destino": "puebla",
                "peso_kg": 500,
                "categoria": "paqueteria",
            },
        )

        cotizacion = respuesta.json()
        assert cotizacion["valida"] is False
        assert cotizacion["advertencias"] == [
            "Mudanzas Capital no ofrece el servicio de paquetería."
        ]

    @pytest.mark.parametrize(
        "cuerpo",
        [
            {"transportista_id": 1, "origen": "queretaro", "destino": "cdmx", "peso_kg": 0},
            {"transportista_id": 1, "origen": "marte", "destino": "cdmx", "peso_kg": 10},
        ],
    )
    def test_cotizacion_invalida(self, cuerpo: dict[str, object]) -> None:
        respuesta = TestClient(create_app()).post("/api/v1/cotizaciones", json=cuerpo)

        assert respuesta.status_code == 422

    def test_la_documentacion_lista_la_api_y_no_las_paginas(self) -> None:
        esquema = TestClient(create_app()).get("/openapi.json").json()

        assert set(esquema["paths"]) == {
            "/health",
            "/api/v1/transportistas",
            "/api/v1/transportistas/{transportista_id}",
            "/api/v1/cotizaciones",
        }
