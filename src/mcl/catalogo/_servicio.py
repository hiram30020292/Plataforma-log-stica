"""Operaciones del catálogo: consultar, registrar y verificar transportistas."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from mcl.catalogo._busqueda import FiltroCatalogo, filtrar_transportistas
from mcl.catalogo._modelos import Transportista
from mcl.catalogo._vehiculos import ESPECIFICACIONES_VEHICULO
from mcl.core import (
    Actor,
    CategoriaServicio,
    Ciudad,
    DatosInvalidosError,
    PermisoDenegadoError,
    RecursoNoEncontradoError,
    Rol,
    TipoVehiculo,
)

LONGITUD_MAXIMA_NOMBRE = 40
LONGITUD_MAXIMA_TELEFONO = 20
DIGITOS_MINIMOS_TELEFONO = 8
CAPACIDAD_MINIMA_KG = 100
LONGITUD_MAXIMA_DESCRIPCION = 500
TARIFA_BASE_MINIMA = 100
TARIFA_BASE_MAXIMA = 1_000_000
DESCRIPCION_POR_DEFECTO = "Transportista de nuevo ingreso en la plataforma."
_CARACTERES_TELEFONO = frozenset("0123456789 +-()")


@dataclass(frozen=True, slots=True)
class DatosRegistro:
    """Lo que captura un transportista para publicar su perfil."""

    nombre: str
    ciudad: Ciudad
    telefono: str
    vehiculo: TipoVehiculo
    capacidad_kg: int
    tarifa_base: int
    categorias: tuple[CategoriaServicio, ...]
    zonas: tuple[Ciudad, ...] = ()
    descripcion: str = ""


def listar_transportistas(sesion: Session) -> list[Transportista]:
    """Todos los transportistas, en orden de alta."""
    return list(sesion.scalars(select(Transportista).order_by(Transportista.id)))


def buscar_transportistas(sesion: Session, filtro: FiltroCatalogo) -> list[Transportista]:
    """Transportistas que cumplen ``filtro`` (ver :func:`filtrar_transportistas`)."""
    return filtrar_transportistas(listar_transportistas(sesion), filtro)


def transportistas_destacados(sesion: Session) -> list[Transportista]:
    """Transportistas que el administrador destacó, del mejor al peor calificado."""
    destacados = sesion.scalars(select(Transportista).where(Transportista.destacado))
    return filtrar_transportistas(destacados, FiltroCatalogo())


def obtener_transportista(sesion: Session, transportista_id: int) -> Transportista:
    """Busca un transportista por su identificador.

    Raises:
        RecursoNoEncontradoError: si no existe.
    """
    transportista = sesion.get(Transportista, transportista_id)
    if transportista is None:
        raise RecursoNoEncontradoError("Transportista", transportista_id)
    return transportista


def registrar_transportista(
    sesion: Session, datos: DatosRegistro, ahora: datetime | None = None
) -> Transportista:
    """Publica el perfil de un transportista nuevo.

    El perfil queda sin verificar ni destacar hasta que lo revise un administrador. Su
    ciudad base siempre forma parte de su cobertura.

    Raises:
        DatosInvalidosError: si algún dato no cumple las reglas del registro.
    """
    nombre = datos.nombre.strip()
    if not nombre:
        raise DatosInvalidosError("Escribe el nombre comercial.")
    if len(nombre) > LONGITUD_MAXIMA_NOMBRE:
        msg = f"El nombre comercial admite hasta {LONGITUD_MAXIMA_NOMBRE} caracteres."
        raise DatosInvalidosError(msg)
    telefono = _validar_telefono(datos.telefono)
    capacidad_maxima = ESPECIFICACIONES_VEHICULO[datos.vehiculo].capacidad_kg
    if not CAPACIDAD_MINIMA_KG <= datos.capacidad_kg <= capacidad_maxima:
        msg = (
            f"La capacidad de un vehículo tipo {datos.vehiculo.etiqueta.lower()} debe estar "
            f"entre {CAPACIDAD_MINIMA_KG} y {capacidad_maxima:,} kg."
        )
        raise DatosInvalidosError(msg)
    if not TARIFA_BASE_MINIMA <= datos.tarifa_base <= TARIFA_BASE_MAXIMA:
        msg = f"La tarifa base debe estar entre ${TARIFA_BASE_MINIMA:,} y ${TARIFA_BASE_MAXIMA:,}."
        raise DatosInvalidosError(msg)
    if not datos.categorias:
        raise DatosInvalidosError("Elige al menos un servicio.")
    descripcion = datos.descripcion.strip() or DESCRIPCION_POR_DEFECTO
    if len(descripcion) > LONGITUD_MAXIMA_DESCRIPCION:
        msg = f"La descripción admite hasta {LONGITUD_MAXIMA_DESCRIPCION} caracteres."
        raise DatosInvalidosError(msg)

    transportista = Transportista(
        nombre=nombre,
        ciudad=datos.ciudad,
        zonas=list(dict.fromkeys([datos.ciudad, *datos.zonas])),
        vehiculo=datos.vehiculo,
        capacidad_kg=datos.capacidad_kg,
        categorias=list(dict.fromkeys(datos.categorias)),
        tarifa_base=datos.tarifa_base,
        telefono=telefono,
        descripcion=descripcion,
        creado_en=ahora or datetime.now(UTC),
        tono=200 + sum(map(ord, nombre)) % 40,
    )
    sesion.add(transportista)
    sesion.commit()
    return transportista


def cambiar_verificacion(
    sesion: Session, transportista_id: int, verificado: bool, actor: Actor
) -> Transportista:
    """Marca un perfil como verificado (o le quita la marca). Solo para administradores."""
    _exigir_administrador(actor)
    transportista = obtener_transportista(sesion, transportista_id)
    transportista.verificado = verificado
    sesion.commit()
    return transportista


def cambiar_destacado(
    sesion: Session, transportista_id: int, destacado: bool, actor: Actor
) -> Transportista:
    """Destaca un perfil en la página de inicio (o lo quita). Solo para administradores."""
    _exigir_administrador(actor)
    transportista = obtener_transportista(sesion, transportista_id)
    transportista.destacado = destacado
    sesion.commit()
    return transportista


def _validar_telefono(telefono: str) -> str:
    telefono = " ".join(telefono.split())
    digitos = sum(c.isdigit() for c in telefono)
    if (
        digitos < DIGITOS_MINIMOS_TELEFONO
        or len(telefono) > LONGITUD_MAXIMA_TELEFONO
        or not set(telefono) <= _CARACTERES_TELEFONO
    ):
        msg = f"Escribe un teléfono válido, con al menos {DIGITOS_MINIMOS_TELEFONO} dígitos."
        raise DatosInvalidosError(msg)
    return telefono


def _exigir_administrador(actor: Actor) -> None:
    if actor.rol is not Rol.ADMINISTRADOR:
        raise PermisoDenegadoError("Solo un administrador puede verificar o destacar perfiles.")
