"""Entorno de plantillas Jinja2 y la función que arma cada página."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from mcl import __version__
from mcl.catalogo import OrdenCatalogo
from mcl.core import CategoriaServicio, Ciudad, EstadoEnvio, Rol, TipoVehiculo, get_settings
from mcl.web._formato import dia_mes, dinero, fecha, fecha_hora, numero
from mcl.web._iconos import ICONO_CATEGORIA, ICONOS
from mcl.web._sesion import borrar_aviso, leer_aviso, leer_preferencias

DIRECTORIO_PLANTILLAS = Path(__file__).parent / "templates"
DIRECTORIO_ESTATICOS = Path(__file__).parent / "static"

# Clase CSS que da color a cada estado en insignias, gráficas y línea de tiempo.
CLASE_ESTADO: Mapping[EstadoEnvio, str] = {
    EstadoEnvio.PENDIENTE: "st-pend",
    EstadoEnvio.CONFIRMADO: "st-conf",
    EstadoEnvio.EN_TRANSITO: "st-transit",
    EstadoEnvio.ENTREGADO: "st-done",
    EstadoEnvio.CANCELADO: "st-off",
    EstadoEnvio.RECHAZADO: "st-off",
}

_entorno = Environment(
    loader=FileSystemLoader(DIRECTORIO_PLANTILLAS),
    autoescape=True,
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)
_entorno.filters.update(
    dinero=dinero, numero=numero, fecha=fecha, fecha_hora=fecha_hora, dia_mes=dia_mes
)
_entorno.globals.update(
    ICONOS=ICONOS,
    ICONO_CATEGORIA=ICONO_CATEGORIA,
    CLASE_ESTADO=CLASE_ESTADO,
    CategoriaServicio=CategoriaServicio,
    Ciudad=Ciudad,
    EstadoEnvio=EstadoEnvio,
    OrdenCatalogo=OrdenCatalogo,
    Rol=Rol,
    TipoVehiculo=TipoVehiculo,
    version=__version__,
)
_plantillas = Jinja2Templates(env=_entorno)


def renderizar(
    request: Request,
    plantilla: str,
    contexto: Mapping[str, Any] | None = None,
    *,
    status_code: int = 200,
    fragmento: bool = False,
) -> HTMLResponse:
    """Arma una página con los datos comunes a todas: preferencias, aviso y configuración.

    Un ``fragmento`` es un trozo de página que se pide en segundo plano (resultados del
    catálogo, cotización): no consume el aviso pendiente.
    """
    aviso = None if fragmento else leer_aviso(request)
    datos = {
        "prefs": leer_preferencias(request),
        "aviso": aviso,
        "ruta": request.url.path,
        "demo_data": get_settings().demo_data,
        **(contexto or {}),
    }
    respuesta = _plantillas.TemplateResponse(request, plantilla, datos, status_code=status_code)
    if aviso is not None:
        borrar_aviso(respuesta)
    return respuesta
