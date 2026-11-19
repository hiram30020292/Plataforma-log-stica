"""Recorridos completos por la interfaz web: formularios, cambios de estado y modos."""

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Protocol
from urllib.parse import unquote

import pytest
from fastapi.testclient import TestClient

from mcl.catalogo import obtener_transportista
from mcl.core import EstadoEnvio, get_settings, new_session
from mcl.demo import CLIENTE_DE_EJEMPLO
from mcl.envios import Envio, envios_del_cliente, obtener_envio


def _envio(estado: EstadoEnvio, cliente: str = CLIENTE_DE_EJEMPLO) -> Envio:
    with new_session() as sesion:
        return next(e for e in envios_del_cliente(sesion, cliente) if e.estado is estado)


def _estado_de(envio_id: int) -> EstadoEnvio:
    with new_session() as sesion:
        return obtener_envio(sesion, envio_id).estado


class _ConCookies(Protocol):
    @property
    def cookies(self) -> Mapping[str, str]: ...


def _aviso(respuesta: _ConCookies) -> str:
    """Texto del aviso que deja una acción para la página siguiente."""
    return unquote(respuesta.cookies.get("mcl_aviso", "")).partition("|")[2]


def _fecha_futura() -> str:
    hoy = datetime.now(UTC).astimezone(get_settings().tz).date()
    return (hoy + timedelta(days=5)).isoformat()


def _solicitud(**cambios: str) -> dict[str, str]:
    datos = {
        "transportista": "2",
        "origen": "queretaro",
        "destino": "leon",
        "categoria": "paqueteria",
        "peso": "1,200",
        "fecha": _fecha_futura(),
        "notas": "20 cajas",
    }
    return datos | cambios


class TestSolicitud:
    def test_enviar_una_solicitud(self, navegador: TestClient) -> None:
        respuesta = navegador.post("/solicitar", data=_solicitud(), follow_redirects=False)

        assert respuesta.status_code == 303
        envio_id = int(respuesta.headers["location"].rsplit("/", 1)[1])
        with new_session() as sesion:
            envio = obtener_envio(sesion, envio_id)
            assert envio.cliente == CLIENTE_DE_EJEMPLO
            assert envio.peso_kg == 1200
            assert envio.estado is EstadoEnvio.PENDIENTE
        assert _aviso(respuesta) == f"Solicitud {envio.folio} enviada"

    def test_el_aviso_se_muestra_una_sola_vez(self, navegador: TestClient) -> None:
        primera = navegador.post("/solicitar", data=_solicitud())
        segunda = navegador.get(primera.url)

        assert "enviada" in primera.text
        assert "enviada" not in segunda.text

    def test_datos_invalidos_vuelven_al_formulario(self, navegador: TestClient) -> None:
        respuesta = navegador.post("/solicitar", data=_solicitud(destino="queretaro"))

        assert respuesta.status_code == 422
        assert "El origen y el destino deben ser distintos." in respuesta.text
        assert 'value="20 cajas"' not in respuesta.text
        assert "20 cajas" in respuesta.text

    def test_peso_que_no_es_numero(self, navegador: TestClient) -> None:
        respuesta = navegador.post("/solicitar", data=_solicitud(peso="mucho"))

        assert respuesta.status_code == 422
        assert "El peso debe ser un número entero." in respuesta.text

    def test_actualizar_la_cotizacion_sin_javascript(self, navegador: TestClient) -> None:
        respuesta = navegador.get("/solicitar", params=_solicitud(peso="5001"))

        assert "supera la capacidad" in respuesta.text
        assert "data-bloqueable disabled" in respuesta.text


class TestCicloDeVida:
    def test_el_transportista_atiende_la_solicitud(self, navegador: TestClient) -> None:
        envio = _envio(EstadoEnvio.PENDIENTE)
        navegador.cookies.set("mcl_rol", "transportista")
        navegador.cookies.set("mcl_transportista", str(envio.transportista_id))

        for estado, aviso in [
            ("confirmado", "Viaje aceptado"),
            ("en_transito", "Viaje iniciado"),
            ("entregado", "Envío marcado como entregado"),
        ]:
            respuesta = navegador.post(
                f"/envios/{envio.id}/estado",
                data={"estado": estado, "volver": "/panel"},
                follow_redirects=False,
            )
            assert respuesta.headers["location"] == "/panel"
            assert _aviso(respuesta) == aviso

        assert _estado_de(envio.id) is EstadoEnvio.ENTREGADO

    def test_el_cliente_cancela(self, navegador: TestClient) -> None:
        envio = _envio(EstadoEnvio.PENDIENTE)

        respuesta = navegador.post(
            f"/envios/{envio.id}/estado", data={"estado": "cancelado"}, follow_redirects=False
        )

        assert respuesta.headers["location"] == f"/envios/{envio.id}"
        assert _aviso(respuesta) == "Solicitud cancelada"
        assert _estado_de(envio.id) is EstadoEnvio.CANCELADO

    def test_una_accion_no_permitida_avisa_el_error(self, navegador: TestClient) -> None:
        envio = _envio(EstadoEnvio.PENDIENTE)

        respuesta = navegador.post(f"/envios/{envio.id}/estado", data={"estado": "confirmado"})

        assert "Como cliente no puedes" in respuesta.text
        assert "toast-error" in respuesta.text
        assert _estado_de(envio.id) is EstadoEnvio.PENDIENTE

    def test_estado_desconocido(self, navegador: TestClient) -> None:
        envio = _envio(EstadoEnvio.PENDIENTE)

        respuesta = navegador.post(f"/envios/{envio.id}/estado", data={"estado": "volando"})

        assert "Elige el nuevo estado." in respuesta.text

    @pytest.mark.parametrize("volver", ["https://otro-sitio.example", "//otro-sitio.example", ""])
    def test_no_redirige_fuera_de_la_app(self, navegador: TestClient, volver: str) -> None:
        envio = _envio(EstadoEnvio.PENDIENTE)

        respuesta = navegador.post(
            f"/envios/{envio.id}/estado",
            data={"estado": "cancelado", "volver": volver},
            follow_redirects=False,
        )

        assert respuesta.headers["location"] == f"/envios/{envio.id}"

    def test_calificar_un_envio_entregado(self, navegador: TestClient) -> None:
        envio = _envio(EstadoEnvio.EN_TRANSITO)
        navegador.post(f"/admin/envios/{envio.id}/estado", data={"estado": "entregado"})
        assert "Enviar calificación" in navegador.get(f"/envios/{envio.id}").text

        respuesta = navegador.post(
            f"/envios/{envio.id}/calificacion",
            data={"estrellas": "4", "texto": "Todo en orden"},
            follow_redirects=False,
        )

        assert _aviso(respuesta) == "Gracias por tu calificación"
        perfil = navegador.get(f"/transportistas/{envio.transportista_id}").text
        assert "Todo en orden" in perfil

    def test_calificar_dos_veces_avisa_el_error(self, navegador: TestClient) -> None:
        envio = _envio(EstadoEnvio.ENTREGADO)

        respuesta = navegador.post(f"/envios/{envio.id}/calificacion", data={"estrellas": "5"})

        assert "Este envío ya fue calificado." in respuesta.text


class TestModosYPerfil:
    def test_cambiar_de_modo(self, navegador: TestClient) -> None:
        respuesta = navegador.get("/modo/transportista", follow_redirects=False)

        assert respuesta.headers["location"] == "/panel"
        assert respuesta.cookies["mcl_rol"] == "transportista"
        assert _aviso(respuesta) == "Modo transportista activado"

    def test_cambiar_de_modo_y_volver_a_una_pagina(self, navegador: TestClient) -> None:
        respuesta = navegador.get(
            "/modo/administrador", params={"siguiente": "/perfil"}, follow_redirects=False
        )

        assert respuesta.headers["location"] == "/perfil"

    def test_el_modo_nunca_redirige_fuera(self, navegador: TestClient) -> None:
        respuesta = navegador.get(
            "/modo/cliente", params={"siguiente": "//otro-sitio.example"}, follow_redirects=False
        )

        assert respuesta.headers["location"] == "/envios"

    def test_la_navegacion_cambia_con_el_rol(self, navegador: TestClient) -> None:
        assert 'href="/envios"' in navegador.get("/").text

        navegador.cookies.set("mcl_rol", "transportista")

        assert 'href="/panel"' in navegador.get("/").text

    def test_guardar_el_perfil_renombra_la_empresa(self, navegador: TestClient) -> None:
        respuesta = navegador.post(
            "/perfil", data={"empresa": "Abarrotes Pérez", "transportista": "3"}
        )

        assert "Cambios guardados" in respuesta.text
        assert 'value="Abarrotes Pérez"' in respuesta.text
        mis_envios = navegador.get("/envios").text
        assert "Abarrotes Pérez" in mis_envios
        assert "Activas (3)" in mis_envios
        navegador.cookies.set("mcl_rol", "transportista")
        assert "Logística Express" in navegador.get("/panel").text

    def test_perfil_con_empresa_vacia(self, navegador: TestClient) -> None:
        respuesta = navegador.post("/perfil", data={"empresa": " ", "transportista": "3"})

        assert "Escribe el nombre de tu empresa." in respuesta.text

    @pytest.mark.parametrize(
        ("cookie", "valor"),
        [("mcl_rol", "superusuario"), ("mcl_transportista", "abc"), ("mcl_empresa", "x" * 99)],
    )
    def test_cookies_alteradas_usan_valores_por_defecto(
        self, navegador: TestClient, cookie: str, valor: str
    ) -> None:
        navegador.cookies.set(cookie, valor)

        respuesta = navegador.get("/envios")

        assert respuesta.status_code == 200
        assert CLIENTE_DE_EJEMPLO in respuesta.text

    def test_registrar_un_transportista(self, navegador: TestClient) -> None:
        datos = {
            "nombre": "Fletes Corregidora",
            "ciudad": "queretaro",
            "telefono": "442 111 2233",
            "vehiculo": "camion",
            "capacidad": "8000",
            "tarifa": "1900",
            "categorias": ["carga_general", "mudanzas"],
            "zonas": ["cdmx", "leon"],
            "descripcion": "",
        }

        respuesta = navegador.post("/registro", data=datos, follow_redirects=False)

        transportista_id = int(respuesta.headers["location"].rsplit("/", 1)[1])
        assert respuesta.cookies["mcl_rol"] == "transportista"
        assert respuesta.cookies["mcl_transportista"] == str(transportista_id)
        with new_session() as sesion:
            nuevo = obtener_transportista(sesion, transportista_id)
            assert nuevo.capacidad == "8 t"
            assert not nuevo.verificado
        assert "En revisión" in navegador.get(respuesta.headers["location"]).text

    def test_registro_invalido_conserva_lo_capturado(self, navegador: TestClient) -> None:
        datos = {
            "nombre": "Fletes Corregidora",
            "ciudad": "queretaro",
            "telefono": "442 111 2233",
            "vehiculo": "van",
            "capacidad": "9000",
            "tarifa": "1900",
        }

        respuesta = navegador.post("/registro", data=datos)

        assert respuesta.status_code == 422
        assert "entre 100 y 1,500 kg" in respuesta.text
        assert "Elige" not in respuesta.text
        assert 'value="Fletes Corregidora"' in respuesta.text

    def test_restablecer_los_datos_de_ejemplo(self, navegador: TestClient) -> None:
        navegador.post("/perfil", data={"empresa": "Otra Empresa", "transportista": "1"})

        respuesta = navegador.post("/perfil/restablecer", follow_redirects=False)

        assert respuesta.headers["location"] == "/"
        assert _aviso(respuesta) == "Datos de ejemplo restablecidos"
        assert "Activas (3)" in navegador.get("/envios").text

    def test_restablecer_requiere_la_demo_activada(
        self, navegador: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MCL_DEMO_DATA", "false")
        get_settings.cache_clear()

        respuesta = navegador.post("/perfil/restablecer")

        assert respuesta.status_code == 403
        assert "desactivados" in respuesta.text


class TestAdministrador:
    def test_corregir_el_estado_desde_la_tabla(self, navegador: TestClient) -> None:
        envio = _envio(EstadoEnvio.ENTREGADO)

        respuesta = navegador.post(
            f"/admin/envios/{envio.id}/estado", data={"estado": "cancelado"}, follow_redirects=False
        )

        assert respuesta.headers["location"] == "/admin/envios"
        assert _aviso(respuesta) == f"{envio.folio}: Cancelado"
        assert _estado_de(envio.id) is EstadoEnvio.CANCELADO

    def test_mismo_estado_avisa_el_error(self, navegador: TestClient) -> None:
        envio = _envio(EstadoEnvio.ENTREGADO)

        respuesta = navegador.post(f"/admin/envios/{envio.id}/estado", data={"estado": "entregado"})

        assert "ya está entregado" in respuesta.text

    def test_verificar_y_destacar(self, navegador: TestClient) -> None:
        verificar = navegador.post(
            "/admin/transportistas/5/marcas",
            data={"campo": "verificado", "valor": "1"},
            follow_redirects=False,
        )
        destacar = navegador.post(
            "/admin/transportistas/5/marcas",
            data={"campo": "destacado", "valor": "1"},
            follow_redirects=False,
        )

        assert _aviso(verificar) == "Fletes Tapatíos: verificado"
        assert _aviso(destacar) == "Fletes Tapatíos: destacado"
        assert "Fletes Tapatíos" in navegador.get("/").text

    def test_apagar_un_interruptor(self, navegador: TestClient) -> None:
        respuesta = navegador.post(
            "/admin/transportistas/1/marcas", data={"campo": "destacado"}, follow_redirects=False
        )

        assert _aviso(respuesta) == "Transporte López: ya no destacado"
        with new_session() as sesion:
            assert obtener_transportista(sesion, 1).destacado is False

    def test_campo_desconocido(self, navegador: TestClient) -> None:
        respuesta = navegador.post("/admin/transportistas/1/marcas", data={"campo": "favorito"})

        assert "No se reconoce el cambio solicitado." in respuesta.text
