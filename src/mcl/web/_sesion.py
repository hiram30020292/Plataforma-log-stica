"""Preferencias de la persona que usa la demo y avisos de una sola vez, guardados en cookies.

La demo no tiene inicio de sesión: cada navegador elige con qué rol usar la plataforma, a
nombre de qué empresa solicita servicios y con qué transportista opera. Las cookies solo
guardan esas preferencias; los datos viven en la base de datos.
"""

from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import quote, unquote

from fastapi import Request, Response
from sqlalchemy.orm import Session

from mcl.catalogo import Transportista, listar_transportistas
from mcl.core import Actor, Rol
from mcl.demo import CLIENTE_DE_EJEMPLO

COOKIE_ROL = "mcl_rol"
COOKIE_EMPRESA = "mcl_empresa"
COOKIE_TRANSPORTISTA = "mcl_transportista"
COOKIE_AVISO = "mcl_aviso"
_UN_ANO = 60 * 60 * 24 * 365
_LONGITUD_MAXIMA_EMPRESA = 60
_LONGITUD_MAXIMA_AVISO = 300


class TipoAviso(StrEnum):
    """Cómo se ve un aviso: confirmación o error."""

    EXITO = "exito"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Aviso:
    """Mensaje que se muestra una sola vez, en la página siguiente."""

    mensaje: str
    tipo: TipoAviso = TipoAviso.EXITO


@dataclass(frozen=True, slots=True)
class Preferencias:
    """Rol, empresa y transportista con los que el navegador usa la demo."""

    rol: Rol = Rol.CLIENTE
    empresa: str = CLIENTE_DE_EJEMPLO
    transportista_id: int | None = None


def leer_preferencias(request: Request) -> Preferencias:
    """Lee las preferencias; un valor ausente o alterado toma su valor por defecto."""
    cookies = request.cookies
    try:
        rol = Rol(cookies.get(COOKIE_ROL, Rol.CLIENTE))
    except ValueError:
        rol = Rol.CLIENTE
    empresa = " ".join(unquote(cookies.get(COOKIE_EMPRESA, "")).split())
    if not empresa or len(empresa) > _LONGITUD_MAXIMA_EMPRESA:
        empresa = CLIENTE_DE_EJEMPLO
    texto_id = cookies.get(COOKIE_TRANSPORTISTA, "")
    transportista_id = int(texto_id) if texto_id.isdecimal() else None
    return Preferencias(rol=rol, empresa=empresa, transportista_id=transportista_id)


def guardar_preferencias(
    respuesta: Response,
    *,
    rol: Rol | None = None,
    empresa: str | None = None,
    transportista_id: int | None = None,
) -> None:
    """Guarda en el navegador las preferencias indicadas (las demás no cambian)."""
    if rol is not None:
        _guardar(respuesta, COOKIE_ROL, rol.value)
    if empresa is not None:
        _guardar(respuesta, COOKIE_EMPRESA, empresa)
    if transportista_id is not None:
        _guardar(respuesta, COOKIE_TRANSPORTISTA, str(transportista_id))


def borrar_preferencias(respuesta: Response) -> None:
    """Vuelve a las preferencias por defecto."""
    for nombre in (COOKIE_ROL, COOKIE_EMPRESA, COOKIE_TRANSPORTISTA):
        respuesta.delete_cookie(nombre, path="/")


def transportista_actual(sesion: Session, preferencias: Preferencias) -> Transportista | None:
    """Transportista con el que opera el navegador; si no eligió uno, el primero del catálogo."""
    transportistas = listar_transportistas(sesion)
    elegido = next(
        (t for t in transportistas if t.id == preferencias.transportista_id),
        None,
    )
    return elegido or next(iter(transportistas), None)


def actor_actual(sesion: Session, preferencias: Preferencias) -> Actor:
    """Quién actúa en esta petición, según las preferencias del navegador."""
    transportista = transportista_actual(sesion, preferencias)
    return Actor(
        rol=preferencias.rol,
        empresa=preferencias.empresa,
        transportista_id=transportista.id if transportista else None,
    )


def avisar(respuesta: Response, mensaje: str, tipo: TipoAviso = TipoAviso.EXITO) -> None:
    """Deja un aviso para mostrarlo en la siguiente página."""
    respuesta.set_cookie(
        COOKIE_AVISO,
        quote(f"{tipo.value}|{mensaje[:_LONGITUD_MAXIMA_AVISO]}", safe=""),
        httponly=True,
        samesite="lax",
        path="/",
    )


def leer_aviso(request: Request) -> Aviso | None:
    """El aviso pendiente, si hay uno."""
    crudo = request.cookies.get(COOKIE_AVISO)
    if not crudo:
        return None
    tipo, _, mensaje = unquote(crudo).partition("|")
    if not mensaje:
        return None
    try:
        return Aviso(mensaje=mensaje[:_LONGITUD_MAXIMA_AVISO], tipo=TipoAviso(tipo))
    except ValueError:
        return None


def borrar_aviso(respuesta: Response) -> None:
    """Quita el aviso una vez mostrado."""
    respuesta.delete_cookie(COOKIE_AVISO, path="/")


def _guardar(respuesta: Response, nombre: str, valor: str) -> None:
    respuesta.set_cookie(
        nombre,
        quote(valor, safe=""),
        max_age=_UN_ANO,
        httponly=True,
        samesite="lax",
        path="/",
    )
