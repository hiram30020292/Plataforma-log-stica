"""API JSON v1 para la app móvil: catálogo de transportistas y cotizaciones.

Las respuestas son parte del contrato con la app: un cambio incompatible va en ``/api/v2``.
"""

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from mcl.calificaciones import Opinion, opiniones_de
from mcl.catalogo import (
    FiltroCatalogo,
    OrdenCatalogo,
    Transportista,
    buscar_transportistas,
    obtener_transportista,
)
from mcl.core import CategoriaServicio, Ciudad, TipoVehiculo, get_session
from mcl.envios import contar_entregados, cotizar

router = APIRouter(prefix="/api/v1", tags=["marketplace"])

SesionBD = Annotated[Session, Depends(get_session)]


class TransportistaSalida(BaseModel):
    """Perfil de un transportista en el catálogo."""

    id: int
    nombre: str
    ciudad: Ciudad
    zonas: list[Ciudad]
    vehiculo: TipoVehiculo
    capacidad_kg: int
    categorias: list[CategoriaServicio]
    tarifa_base: int = Field(description="Tarifa base en pesos mexicanos.")
    calificacion: float = Field(description="Promedio de 1 a 5; 0 si aún no tiene opiniones.")
    num_opiniones: int
    verificado: bool
    telefono: str
    descripcion: str


class FiltroTransportistas(BaseModel):
    """Filtros de búsqueda. ``q`` ignora mayúsculas y acentos; ``ciudad`` incluye cobertura."""

    q: str = ""
    categoria: CategoriaServicio | None = None
    ciudad: Ciudad | None = None
    vehiculo: TipoVehiculo | None = None
    orden: OrdenCatalogo = OrdenCatalogo.MEJOR_CALIFICADOS


class OpinionSalida(BaseModel):
    """Opinión de un cliente."""

    autor: str
    estrellas: int
    texto: str
    creado_en: datetime


class TransportistaDetalleSalida(TransportistaSalida):
    """Perfil completo: incluye viajes entregados y opiniones escritas."""

    viajes_entregados: int
    opiniones: list[OpinionSalida]


class CotizacionEntrada(BaseModel):
    """Datos del viaje a cotizar."""

    transportista_id: int
    origen: Ciudad
    destino: Ciudad
    peso_kg: int = Field(gt=0)
    categoria: CategoriaServicio | None = None


class CotizacionSalida(BaseModel):
    """Precio estimado del viaje y motivos por los que no se podría solicitar."""

    distancia_km: int
    precio: int
    moneda: Literal["MXN"] = "MXN"
    valida: bool
    advertencias: list[str]


def _transportista(t: Transportista) -> TransportistaSalida:
    return TransportistaSalida(
        id=t.id,
        nombre=t.nombre,
        ciudad=t.ciudad,
        zonas=t.zonas,
        vehiculo=t.vehiculo,
        capacidad_kg=t.capacidad_kg,
        categorias=t.categorias,
        tarifa_base=t.tarifa_base,
        calificacion=round(t.calificacion, 1),
        num_opiniones=t.num_opiniones,
        verificado=t.verificado,
        telefono=t.telefono,
        descripcion=t.descripcion,
    )


def _opinion(opinion: Opinion) -> OpinionSalida:
    return OpinionSalida(
        autor=opinion.autor,
        estrellas=opinion.estrellas,
        texto=opinion.texto,
        creado_en=opinion.creado_en,
    )


@router.get("/transportistas")
def listar(
    sesion: SesionBD, filtro: Annotated[FiltroTransportistas, Query()]
) -> list[TransportistaSalida]:
    """Busca transportistas en el catálogo."""
    criterios = FiltroCatalogo(
        texto=filtro.q,
        categoria=filtro.categoria,
        ciudad=filtro.ciudad,
        vehiculo=filtro.vehiculo,
        orden=filtro.orden,
    )
    return [_transportista(t) for t in buscar_transportistas(sesion, criterios)]


@router.get("/transportistas/{transportista_id}")
def detalle(sesion: SesionBD, transportista_id: int) -> TransportistaDetalleSalida:
    """Perfil completo de un transportista."""
    t = obtener_transportista(sesion, transportista_id)
    return TransportistaDetalleSalida(
        **_transportista(t).model_dump(),
        viajes_entregados=contar_entregados(sesion, t.id),
        opiniones=[_opinion(o) for o in opiniones_de(sesion, t.id)],
    )


@router.post("/cotizaciones")
def cotizar_viaje(sesion: SesionBD, entrada: CotizacionEntrada) -> CotizacionSalida:
    """Cotiza un viaje con un transportista sin registrar ninguna solicitud."""
    t = obtener_transportista(sesion, entrada.transportista_id)
    cotizacion = cotizar(t, entrada.origen, entrada.destino, entrada.peso_kg, entrada.categoria)
    return CotizacionSalida(
        distancia_km=cotizacion.distancia_km,
        precio=cotizacion.precio,
        valida=cotizacion.valida,
        advertencias=list(cotizacion.advertencias),
    )
