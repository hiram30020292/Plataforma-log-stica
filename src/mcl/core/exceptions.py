"""Excepciones propias del dominio de MCL.

Todas heredan de :class:`MCLError`. Así la capa de la API puede capturarlas en un solo
lugar y responder a la app móvil con un ``codigo`` estable que no depende del mensaje.
"""

from typing import ClassVar


class MCLError(Exception):
    """Base de todas las excepciones propias de MCL."""

    codigo: ClassVar[str] = "error_interno"

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


class ConfiguracionError(MCLError):
    """La configuración de la aplicación es inválida o está incompleta."""

    codigo = "configuracion_invalida"


class DatosInvalidosError(MCLError):
    """Los datos recibidos no cumplen una regla del negocio."""

    codigo = "datos_invalidos"


class RecursoNoEncontradoError(MCLError):
    """Se buscó un recurso (vehículo, contrato, envío...) que no existe."""

    codigo = "no_encontrado"

    def __init__(self, recurso: str, identificador: object) -> None:
        super().__init__(f"{recurso} con identificador {identificador!r} no existe.")
        self.recurso = recurso
        self.identificador = identificador


class ConflictoError(MCLError):
    """La operación choca con el estado actual (por ejemplo, un vehículo ya asignado)."""

    codigo = "conflicto"


class PermisoDenegadoError(MCLError):
    """El usuario no tiene permiso para realizar la operación."""

    codigo = "permiso_denegado"
