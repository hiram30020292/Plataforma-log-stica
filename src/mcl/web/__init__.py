"""Interfaz web de MCL, programada en Python: FastAPI arma cada página con plantillas Jinja2.

Incluye la app (catálogo, solicitudes, envíos, panel del transportista y perfil) y el panel
administrativo. Toda la lógica vive en los módulos de tema; esta capa solo traduce entre
el navegador y el dominio.
"""

from mcl.web._app import configurar_web
from mcl.web._errores import acepta_html, pagina_de_error

__all__ = ["acepta_html", "configurar_web", "pagina_de_error"]
