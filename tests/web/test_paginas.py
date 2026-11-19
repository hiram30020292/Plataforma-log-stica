"""Cada pantalla se muestra con sus datos principales."""

import pytest
from fastapi.testclient import TestClient

from mcl import __version__
from mcl.core import EstadoEnvio, new_session
from mcl.demo import CLIENTE_DE_EJEMPLO
from mcl.envios import Envio, envios_del_cliente


def _envio(estado: EstadoEnvio) -> Envio:
    with new_session() as sesion:
        return next(e for e in envios_del_cliente(sesion, CLIENTE_DE_EJEMPLO) if e.estado is estado)


def test_inicio(navegador: TestClient) -> None:
    respuesta = navegador.get("/")

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/html")
    html = respuesta.text
    assert "MCL" in html
    assert "Corregidora Móvil Logistics" in html
    assert "Conectamos negocios con transportistas" in html
    assert "Rápidos del Bajío" in html
    assert 'href="/buscar?categoria=mudanzas"' in html


def test_catalogo_con_filtros(navegador: TestClient) -> None:
    html = navegador.get("/buscar", params={"categoria": "mudanzas", "orden": "precio"}).text

    assert "3 transportistas disponibles" in html
    assert html.index("Fletes Tapatíos") < html.index("Logística Express")
    assert '<option value="mudanzas" selected>' in html


def test_catalogo_ignora_filtros_desconocidos(navegador: TestClient) -> None:
    html = navegador.get("/buscar", params={"categoria": "cohetes", "orden": "x"}).text

    assert "8 transportistas disponibles" in html


def test_resultados_del_catalogo_sin_el_resto_de_la_pagina(navegador: TestClient) -> None:
    html = navegador.get("/buscar/resultados", params={"q": "tapatios"}).text

    assert "1 transportista disponible" in html
    assert "Fletes Tapatíos" in html
    assert "<html" not in html


def test_catalogo_sin_resultados(navegador: TestClient) -> None:
    html = navegador.get("/buscar", params={"q": "submarino"}).text

    assert "Sin resultados" in html
    assert "Quitar filtros" in html


def test_perfil_del_transportista(navegador: TestClient) -> None:
    html = navegador.get("/transportistas/1").text

    assert "Transporte López" in html
    assert "Verificado" in html
    assert "Tráiler · 30 t" in html
    assert "$2,200" in html
    assert "Llegaron a tiempo y la carga sin un rasguño." in html
    assert 'href="/solicitar?transportista=1"' in html


def test_perfil_de_un_transportista_sin_verificar(navegador: TestClient) -> None:
    assert "En revisión" in navegador.get("/transportistas/5").text


def test_formulario_de_solicitud_con_cotizacion(navegador: TestClient) -> None:
    html = navegador.get("/solicitar", params={"transportista": "1"}).text

    assert "Nueva solicitud" in html
    assert '<option value="1" selected>' in html
    assert "230 km" in html
    assert "MXN" in html
    assert 'href="/transportistas/1"' in html


def test_cotizacion_en_vivo_con_advertencias(navegador: TestClient) -> None:
    respuesta = navegador.get(
        "/solicitar/cotizacion",
        params={"transportista": "3", "origen": "cdmx", "destino": "cdmx", "peso": "99999"},
    )

    assert "supera la capacidad" in respuesta.text
    assert "distintos" in respuesta.text
    assert respuesta.text.count("data-bloquea") == 2


def test_mis_envios(navegador: TestClient) -> None:
    html = navegador.get("/envios").text

    assert CLIENTE_DE_EJEMPLO in html
    assert "Activas (3)" in html
    assert "Historial (1)" in html
    assert "Crear nueva solicitud" in html


def test_historial_de_envios(navegador: TestClient) -> None:
    html = navegador.get("/envios", params={"vista": "historial"}).text

    assert "Entregado" in html
    assert _envio(EstadoEnvio.ENTREGADO).folio in html


def test_detalle_de_un_envio_en_transito(navegador: TestClient) -> None:
    envio = _envio(EstadoEnvio.EN_TRANSITO)

    html = navegador.get(f"/envios/{envio.id}").text

    assert f"Envío {envio.folio}" in html
    assert "avance estimado" in html
    assert "map-truck" in html
    assert "Seguimiento" in html
    assert f"${envio.precio:,} MXN" in html


def test_el_cliente_puede_cancelar_su_solicitud_pendiente(navegador: TestClient) -> None:
    html = navegador.get(f"/envios/{_envio(EstadoEnvio.PENDIENTE).id}").text

    assert "Cancelar solicitud" in html
    assert "Aceptar viaje" not in html


def test_envio_entregado_y_calificado(navegador: TestClient) -> None:
    html = navegador.get(f"/envios/{_envio(EstadoEnvio.ENTREGADO).id}").text

    assert "calificó este servicio" in html
    assert "Enviar calificación" not in html


def test_panel_del_transportista(navegador: TestClient) -> None:
    navegador.cookies.set("mcl_rol", "transportista")

    html = navegador.get("/panel").text

    assert "Panel del transportista" in html
    assert "Transporte López" in html
    assert "Solicitudes nuevas" in html
    assert "Aceptar" in html


def test_perfil_y_modos(navegador: TestClient) -> None:
    html = navegador.get("/perfil").text

    assert "Modo de uso" in html
    assert 'href="/modo/administrador?siguiente=/perfil"' in html
    assert "Restablecer datos de ejemplo" in html
    assert __version__ in html


def test_registro(navegador: TestClient) -> None:
    html = navegador.get("/registro").text

    assert "Registro de transportista" in html
    assert 'name="categorias" value="carga_general" checked' in html


def test_tablero_administrativo(navegador: TestClient) -> None:
    html = navegador.get("/admin").text

    assert "Tablero" in html
    assert "Solicitudes totales" in html
    assert ">50<" in html
    assert 'class="line"' in html
    assert 'class="seg' in html
    assert "Mejores transportistas" in html


def test_solicitudes_del_administrador(navegador: TestClient) -> None:
    html = navegador.get("/admin/envios").text

    assert "50 registros" in html
    assert html.count('class="status-form"') == 50


def test_transportistas_del_administrador(navegador: TestClient) -> None:
    html = navegador.get("/admin/transportistas").text

    assert html.count('name="campo" value="verificado"') == 8
    assert "Paquetería Ágil" in html


@pytest.mark.parametrize(
    "ruta", ["/no-existe", "/transportistas/999", "/envios/999", "/envios/abc", "/modo/piloto"]
)
def test_pagina_no_encontrada(navegador: TestClient, ruta: str) -> None:
    respuesta = navegador.get(ruta)

    assert respuesta.status_code == 404
    assert "No encontramos esta página" in respuesta.text
    assert "Ir al inicio" in respuesta.text


def test_archivos_estaticos(navegador: TestClient) -> None:
    css = navegador.get("/static/mcl.css")
    fuente = navegador.get("/static/fuentes/inter.woff2")

    assert css.status_code == 200
    assert "--terracota: #9F6C52" in css.text
    assert fuente.status_code == 200
