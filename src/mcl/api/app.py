"""Creación de la aplicación FastAPI y respuestas comunes a toda la API."""

import logging
from http import HTTPStatus
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from mcl import __version__
from mcl.core import (
    ConflictoError,
    DatosInvalidosError,
    Environment,
    MCLError,
    PermisoDenegadoError,
    RecursoNoEncontradoError,
    Settings,
    get_settings,
)

_logger = logging.getLogger(__name__)

# Código HTTP de cada error del dominio. Cualquier otro MCLError es un error interno (500).
_STATUS_POR_ERROR: dict[type[MCLError], HTTPStatus] = {
    DatosInvalidosError: HTTPStatus.UNPROCESSABLE_ENTITY,
    RecursoNoEncontradoError: HTTPStatus.NOT_FOUND,
    ConflictoError: HTTPStatus.CONFLICT,
    PermisoDenegadoError: HTTPStatus.FORBIDDEN,
}

_MENSAJE_ERROR_INTERNO = "Ocurrió un error interno. Inténtalo de nuevo más tarde."


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


async def _responder_error_mcl(_request: Request, error: MCLError) -> JSONResponse:
    """Convierte un error del dominio en JSON ``{codigo, mensaje}`` con su código HTTP."""
    status = next(
        (s for clase, s in _STATUS_POR_ERROR.items() if isinstance(error, clase)),
        HTTPStatus.INTERNAL_SERVER_ERROR,
    )
    mensaje = error.mensaje
    if status is HTTPStatus.INTERNAL_SERVER_ERROR:
        # El detalle queda en el log del servidor; al cliente nunca se le muestra.
        _logger.error("Error interno: %s", error.mensaje, exc_info=error)
        mensaje = _MENSAJE_ERROR_INTERNO
    cuerpo = ErrorResponse(codigo=error.codigo, mensaje=mensaje)
    return JSONResponse(status_code=status, content=cuerpo.model_dump())


def create_app() -> FastAPI:
    """Crea la aplicación. Uvicorn la llama con ``--factory``."""
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=__version__, debug=settings.debug)
    app.include_router(_sistema)
    app.exception_handler(MCLError)(_responder_error_mcl)
    return app
