"""Datos que llegan de los formularios y la barra de direcciones, y cómo se interpretan.

Todo llega como texto. Los modelos aceptan cualquier texto (así un dato mal escrito nunca
rompe la página) y estas funciones lo convierten en tipos del dominio, con mensajes que
la persona entiende cuando algo no cuadra.
"""

from datetime import date
from enum import StrEnum
from urllib.parse import urlsplit

from pydantic import BaseModel, Field

from mcl.core import DatosInvalidosError

_LONGITUD_MAXIMA_BUSQUEDA = 80


class ConsultaCatalogo(BaseModel):
    """Filtros del catálogo en la dirección: ``/buscar?q=...&categoria=...``."""

    q: str = ""
    categoria: str = ""
    ciudad: str = ""
    vehiculo: str = ""
    orden: str = ""

    @property
    def texto(self) -> str:
        """Texto de búsqueda sin espacios sobrantes."""
        return self.q.strip()[:_LONGITUD_MAXIMA_BUSQUEDA]


class FormularioSolicitud(BaseModel):
    """Solicitud de servicio (también sirve para cotizar en vivo)."""

    transportista: str = ""
    origen: str = ""
    destino: str = ""
    categoria: str = ""
    peso: str = ""
    fecha: str = ""
    notas: str = ""


class FormularioEstado(BaseModel):
    """Cambio de estado de un envío y a qué página volver después."""

    estado: str = ""
    volver: str = ""


class FormularioCalificacion(BaseModel):
    """Calificación de un envío entregado."""

    estrellas: str = ""
    texto: str = ""


class FormularioPerfil(BaseModel):
    """Datos de la demo: nombre de la empresa cliente y transportista con el que se opera."""

    empresa: str = ""
    transportista: str = ""


class FormularioRegistro(BaseModel):
    """Registro de un transportista nuevo."""

    nombre: str = ""
    ciudad: str = ""
    telefono: str = ""
    vehiculo: str = ""
    capacidad: str = ""
    tarifa: str = ""
    categorias: list[str] = Field(default_factory=list)
    zonas: list[str] = Field(default_factory=list)
    descripcion: str = ""


class FormularioMarca(BaseModel):
    """Interruptor del panel administrativo (verificado o destacado)."""

    campo: str = ""
    valor: str = ""

    @property
    def activado(self) -> bool:
        """El interruptor solo envía ``valor`` cuando queda encendido."""
        return self.valor == "1"


def opcion[E: StrEnum](enum: type[E], valor: str) -> E | None:
    """Convierte ``valor`` en un miembro de ``enum``, o ``None`` si no corresponde a ninguno."""
    try:
        return enum(valor)
    except ValueError:
        return None


def requerir[E: StrEnum](enum: type[E], valor: str, descripcion: str) -> E:
    """Como :func:`opcion`, pero el valor es obligatorio.

    Raises:
        DatosInvalidosError: si ``valor`` no corresponde a ninguna opción.
    """
    elegido = opcion(enum, valor)
    if elegido is None:
        msg = f"Elige {descripcion}."
        raise DatosInvalidosError(msg)
    return elegido


def entero(valor: str, descripcion: str) -> int:
    """Convierte un número escrito por una persona (acepta ``1,500``).

    Raises:
        DatosInvalidosError: si no es un número entero.
    """
    numero = entero_o_none(valor)
    if numero is None:
        msg = f"{descripcion} debe ser un número entero."
        raise DatosInvalidosError(msg)
    return numero


def entero_o_none(valor: str) -> int | None:
    """Número entero escrito por una persona, o ``None`` si no es uno."""
    limpio = valor.strip().replace(",", "")
    signo, digitos = ("-", limpio[1:]) if limpio.startswith("-") else ("", limpio)
    if not digitos.isdecimal():
        return None
    return int(signo + digitos)


def fecha_iso(valor: str, descripcion: str) -> date:
    """Convierte la fecha de un campo ``<input type="date">`` (``AAAA-MM-DD``).

    Raises:
        DatosInvalidosError: si no es una fecha válida.
    """
    try:
        return date.fromisoformat(valor.strip())
    except ValueError as exc:
        msg = f"Escribe {descripcion} con el formato día/mes/año."
        raise DatosInvalidosError(msg) from exc


def ruta_local(valor: str, por_defecto: str) -> str:
    """``valor`` si es una ruta de esta misma app; si no, ``por_defecto``.

    Evita que un enlace manipulado redirija a otro sitio después de una acción.
    """
    partes = urlsplit(valor)
    es_local = (
        not partes.scheme
        and not partes.netloc
        and valor.startswith("/")
        and not valor.startswith("//")
        and "\\" not in valor
    )
    return valor if es_local else por_defecto
