"""Capa HTTP de MCL (FastAPI).

Solo traduce entre HTTP y el dominio: valida la entrada, llama al módulo del tema que
corresponde y convierte sus errores en respuestas JSON. No contiene reglas de negocio.
"""

from mcl.api.app import create_app

__all__ = ["create_app"]
