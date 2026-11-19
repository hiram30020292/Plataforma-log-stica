"""Calificar envíos entregados y consultar opiniones."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from mcl.calificaciones._modelos import Opinion
from mcl.core import (
    Actor,
    ConflictoError,
    DatosInvalidosError,
    EstadoEnvio,
    PermisoDenegadoError,
    Rol,
)
from mcl.envios import obtener_envio

ESTRELLAS_MINIMAS = 1
ESTRELLAS_MAXIMAS = 5
LONGITUD_MAXIMA_TEXTO = 500
TEXTO_POR_DEFECTO = "Sin comentarios."


@dataclass(frozen=True, slots=True)
class DatosCalificacion:
    """Estrellas (de 1 a 5) y comentario opcional que deja el cliente."""

    estrellas: int
    texto: str = ""


def calificar_envio(
    sesion: Session,
    envio_id: int,
    datos: DatosCalificacion,
    actor: Actor,
    ahora: datetime | None = None,
) -> Opinion:
    """El cliente califica un envío entregado; la nota se suma al promedio del transportista.

    Raises:
        RecursoNoEncontradoError: si el envío no existe.
        PermisoDenegadoError: si quien califica no es el cliente del envío.
        ConflictoError: si el envío no está entregado o ya se calificó.
        DatosInvalidosError: si las estrellas no van de 1 a 5 o el texto es muy largo.
    """
    envio = obtener_envio(sesion, envio_id)
    if actor.rol is not Rol.CLIENTE or envio.cliente != actor.empresa:
        raise PermisoDenegadoError("Solo el cliente que contrató el servicio puede calificarlo.")
    if envio.estado is not EstadoEnvio.ENTREGADO:
        raise ConflictoError("Solo se pueden calificar envíos entregados.")
    if envio.calificacion is not None:
        raise ConflictoError("Este envío ya fue calificado.")
    estrellas = datos.estrellas
    if not ESTRELLAS_MINIMAS <= estrellas <= ESTRELLAS_MAXIMAS:
        msg = f"La calificación debe ser de {ESTRELLAS_MINIMAS} a {ESTRELLAS_MAXIMAS} estrellas."
        raise DatosInvalidosError(msg)
    texto = datos.texto.strip() or TEXTO_POR_DEFECTO
    if len(texto) > LONGITUD_MAXIMA_TEXTO:
        msg = f"El comentario admite hasta {LONGITUD_MAXIMA_TEXTO} caracteres."
        raise DatosInvalidosError(msg)

    envio.calificacion = estrellas
    envio.transportista.registrar_estrellas(estrellas)
    opinion = Opinion(
        transportista_id=envio.transportista_id,
        envio_id=envio.id,
        autor=envio.cliente,
        estrellas=estrellas,
        texto=texto,
        creado_en=ahora or datetime.now(UTC),
    )
    sesion.add(opinion)
    sesion.commit()
    return opinion


def opiniones_de(sesion: Session, transportista_id: int) -> list[Opinion]:
    """Opiniones escritas sobre un transportista, de la más reciente a la más antigua."""
    consulta = (
        select(Opinion)
        .where(Opinion.transportista_id == transportista_id)
        .order_by(Opinion.creado_en.desc(), Opinion.id.desc())
    )
    return list(sesion.scalars(consulta))
