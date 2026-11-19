"""Montaje de la interfaz web sobre la aplicación FastAPI."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from mcl.web import _rutas, _rutas_admin
from mcl.web._plantillas import DIRECTORIO_ESTATICOS


def configurar_web(app: FastAPI) -> None:
    """Agrega las pantallas de la app y del panel administrativo, y sus archivos estáticos."""
    app.mount("/static", StaticFiles(directory=DIRECTORIO_ESTATICOS), name="static")
    app.include_router(_rutas_admin.router)
    app.include_router(_rutas.router)
