"""Creación de la aplicación: API JSON, interfaz web y respuestas de error comunes."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from http import HTTPStatus
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from mcl import __version__
from mcl.api._v1 import router as api_v1
from mcl.core import (
    ConflictoError,
    DatosInvalidosError,
    Environment,
    MCLError,
    PermisoDenegadoError,
    RecursoNoEncontradoError,
    Settings,
    dispose_engines,
    get_settings,
    new_session,
)
from mcl.db import upgrade_database
from mcl.demo import sembrar_si_esta_vacia
from mcl.web import acepta_html, configurar_web, pagina_de_error

_logger = logging.getLogger(__name__)

# Código HTTP de cada error del dominio. Cualquier otro MCLError es un error interno (500).
_STATUS_POR_ERROR: dict[type[MCLError], HTTPStatus] = {
    DatosInvalidosError: HTTPStatus.UNPROCESSABLE_ENTITY,
    RecursoNoEncontradoError: HTTPStatus.NOT_FOUND,
    ConflictoError: HTTPStatus.CONFLICT,
    PermisoDenegadoError: HTTPStatus.FORBIDDEN,
}

_MENSAJE_ERROR_INTERNO = "Ocurrió un error interno. Inténtalo de nuevo más tarde."
_MENSAJE_PAGINA_NO_ENCONTRADA = "Puede que el registro se haya eliminado al restablecer los datos."

# Rutas que siempre responden JSON, aunque las abra un navegador.
_RUTAS_DE_API = ("/api/", "/health", "/docs", "/redoc", "/openapi.json")

_DESCRIPCION = """
API de **MCL - Corregidora Móvil Logistics** para la app móvil.

La interfaz web de la plataforma está en la raíz del servidor: [abrir la app](/).
"""


class HealthResponse(BaseModel):
    """Respuesta de ``GET /health``."""

    status: Literal["ok"] = "ok"
    app: str
    version: str
    environment: Environment


class ErrorResponse(BaseModel):
    """Cuerpo de toda respuesta de error del dominio."""

    codigo: str
    mensaje: str


_sistema = APIRouter(tags=["sistema"])


@_sistema.get("/health")
def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    """Indica que el servicio está vivo y qué versión corre."""
    return HealthResponse(
        app=settings.app_name,
        version=__version__,
        environment=settings.environment,
    )


def _quiere_una_pagina(request: Request) -> bool:
    """Las rutas de la interfaz web responden con páginas a los navegadores."""
    return not request.url.path.startswith(_RUTAS_DE_API) and acepta_html(request)


async def _responder_error_mcl(request: Request, error: MCLError) -> Response:
    """Convierte un error del dominio en JSON ``{codigo, mensaje}`` o en una página de error."""
    status = next(
        (s for clase, s in _STATUS_POR_ERROR.items() if isinstance(error, clase)),
        HTTPStatus.INTERNAL_SERVER_ERROR,
    )
    mensaje = error.mensaje
    if status is HTTPStatus.INTERNAL_SERVER_ERROR:
        # El detalle queda en el log del servidor; al cliente nunca se le muestra.
        _logger.error("Error interno: %s", error.mensaje, exc_info=error)
        mensaje = _MENSAJE_ERROR_INTERNO
    if _quiere_una_pagina(request):
        return pagina_de_error(request, status, mensaje)
    cuerpo = ErrorResponse(codigo=error.codigo, mensaje=mensaje)
    return JSONResponse(status_code=status, content=cuerpo.model_dump())


async def _responder_error_http(request: Request, error: StarletteHTTPException) -> Response:
    """Las direcciones que no existen muestran una página amable en el navegador."""
    if _quiere_una_pagina(request) and error.status_code in {
        HTTPStatus.NOT_FOUND,
        HTTPStatus.METHOD_NOT_ALLOWED,
    }:
        status = HTTPStatus(error.status_code)
        return pagina_de_error(request, status, _MENSAJE_PAGINA_NO_ENCONTRADA)
    return await http_exception_handler(request, error)


async def _responder_error_de_validacion(
    request: Request, error: RequestValidationError
) -> Response:
    """Una dirección o formulario malformado muestra una página en lugar de JSON técnico."""
    if not _quiere_una_pagina(request):
        return await request_validation_exception_handler(request, error)
    if request.method == "GET":
        return pagina_de_error(request, HTTPStatus.NOT_FOUND, _MENSAJE_PAGINA_NO_ENCONTRADA)
    return pagina_de_error(
        request,
        HTTPStatus.UNPROCESSABLE_ENTITY,
        "Revisa los datos del formulario e inténtalo de nuevo.",
    )


async def _responder_error_inesperado(request: Request, error: Exception) -> Response:
    """Último recurso ante un error de programación: nunca muestra el detalle al cliente."""
    _logger.error("Error inesperado en %s", request.url.path, exc_info=error)
    if _quiere_una_pagina(request):
        return pagina_de_error(request, HTTPStatus.INTERNAL_SERVER_ERROR, _MENSAJE_ERROR_INTERNO)
    cuerpo = ErrorResponse(codigo=MCLError.codigo, mensaje=_MENSAJE_ERROR_INTERNO)
    return JSONResponse(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, content=cuerpo.model_dump())


def _preparar_base_de_datos(settings: Settings) -> None:
    """Aplica las migraciones pendientes y, en la demo, carga los datos de ejemplo."""
    upgrade_database()
    if settings.demo_data:
        with new_session() as sesion:
            if sembrar_si_esta_vacia(sesion):
                _logger.info("Se cargaron los datos de ejemplo.")


@asynccontextmanager
async def _ciclo_de_vida(_app: FastAPI) -> AsyncIterator[None]:
    yield
    dispose_engines()


def create_app() -> FastAPI:
    """Crea la aplicación. Uvicorn la llama con ``--factory``."""
    settings = get_settings()
    _preparar_base_de_datos(settings)
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=_DESCRIPCION,
        debug=settings.debug,
        lifespan=_ciclo_de_vida,
    )
    app.include_router(_sistema)
    app.include_router(api_v1)
    configurar_web(app)
    app.exception_handler(MCLError)(_responder_error_mcl)
    app.exception_handler(StarletteHTTPException)(_responder_error_http)
    app.exception_handler(RequestValidationError)(_responder_error_de_validacion)
    app.exception_handler(Exception)(_responder_error_inesperado)
    return app
