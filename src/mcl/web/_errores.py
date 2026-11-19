"""Páginas de error para quien navega con el navegador."""

from http import HTTPStatus

from fastapi import Request
from fastapi.responses import HTMLResponse

from mcl.web._plantillas import renderizar

_TITULOS = {
    HTTPStatus.NOT_FOUND: "No encontramos esta página",
    HTTPStatus.METHOD_NOT_ALLOWED: "No encontramos esta página",
    HTTPStatus.FORBIDDEN: "No tienes permiso",
    HTTPStatus.CONFLICT: "No se pudo completar",
    HTTPStatus.UNPROCESSABLE_ENTITY: "Revisa los datos",
}
_TITULO_GENERICO = "Algo salió mal"


def acepta_html(request: Request) -> bool:
    """Indica si quien hace la petición es un navegador que espera una página."""
    return "text/html" in request.headers.get("accept", "")


def pagina_de_error(request: Request, status: HTTPStatus, mensaje: str) -> HTMLResponse:
    """Página con el mensaje del error y un botón para volver al inicio."""
    contexto = {
        "pestana": "",
        "titulo": _TITULOS.get(status, _TITULO_GENERICO),
        "mensaje": mensaje,
    }
    return renderizar(request, "error.html", contexto, status_code=status)
