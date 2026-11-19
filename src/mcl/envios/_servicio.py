"""Solicitudes de transporte y su ciclo de vida.

Flujo normal::

    pendiente ──► confirmado ──► en_transito ──► entregado
        │
        ├──► rechazado   (lo decide el transportista)
        └──► cancelado   (lo decide el cliente)

El administrador puede corregir el estado de cualquier envío a mano.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from types import MappingProxyType

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from mcl.catalogo import obtener_transportista
from mcl.core import (
    Actor,
    CategoriaServicio,
    Ciudad,
    ConflictoError,
    DatosInvalidosError,
    EstadoEnvio,
    PermisoDenegadoError,
    RecursoNoEncontradoError,
    Rol,
    get_settings,
)
from mcl.envios._cotizacion import cotizar
from mcl.envios._modelos import Envio, EventoEnvio

LONGITUD_MAXIMA_CLIENTE = 60
LONGITUD_MAXIMA_NOTAS = 500
# Hora del día en que se espera la entrega, para estimar el avance del viaje.
HORA_ESTIMADA_ENTREGA = time(18, 0)
# El avance en el mapa nunca toca los extremos mientras el viaje sigue en curso.
AVANCE_MINIMO = 0.08
AVANCE_MAXIMO = 0.92

_Flujo = Mapping[EstadoEnvio, tuple[EstadoEnvio, ...]]

_FLUJO_TRANSPORTISTA: _Flujo = MappingProxyType(
    {
        EstadoEnvio.PENDIENTE: (EstadoEnvio.RECHAZADO, EstadoEnvio.CONFIRMADO),
        EstadoEnvio.CONFIRMADO: (EstadoEnvio.EN_TRANSITO,),
        EstadoEnvio.EN_TRANSITO: (EstadoEnvio.ENTREGADO,),
    }
)
_FLUJO_CLIENTE: _Flujo = MappingProxyType({EstadoEnvio.PENDIENTE: (EstadoEnvio.CANCELADO,)})
_FLUJOS: Mapping[Rol, _Flujo] = MappingProxyType(
    {
        Rol.CLIENTE: _FLUJO_CLIENTE,
        Rol.TRANSPORTISTA: _FLUJO_TRANSPORTISTA,
        # Desde el detalle del envío el administrador opera como el transportista.
        Rol.ADMINISTRADOR: _FLUJO_TRANSPORTISTA,
    }
)


@dataclass(frozen=True, slots=True)
class DatosSolicitud:
    """Lo que captura un cliente para pedir un servicio."""

    transportista_id: int
    origen: Ciudad
    destino: Ciudad
    categoria: CategoriaServicio
    peso_kg: int
    fecha_entrega: date
    notas: str = ""


def crear_solicitud(
    sesion: Session, datos: DatosSolicitud, cliente: str, ahora: datetime | None = None
) -> Envio:
    """Registra una solicitud nueva en estado ``pendiente`` con su precio cotizado.

    Raises:
        RecursoNoEncontradoError: si el transportista no existe.
        DatosInvalidosError: si la cotización tiene advertencias, la fecha no es futura o
            algún texto es demasiado largo.
    """
    ahora = ahora or datetime.now(UTC)
    cliente = cliente.strip()
    if not cliente:
        raise DatosInvalidosError("Indica el nombre de la empresa que solicita el servicio.")
    if len(cliente) > LONGITUD_MAXIMA_CLIENTE:
        msg = f"El nombre de la empresa admite hasta {LONGITUD_MAXIMA_CLIENTE} caracteres."
        raise DatosInvalidosError(msg)
    notas = datos.notas.strip()
    if len(notas) > LONGITUD_MAXIMA_NOTAS:
        msg = f"La descripción de la carga admite hasta {LONGITUD_MAXIMA_NOTAS} caracteres."
        raise DatosInvalidosError(msg)
    if datos.fecha_entrega <= ahora.astimezone(get_settings().tz).date():
        raise DatosInvalidosError("La fecha de entrega debe ser a partir de mañana.")

    transportista = obtener_transportista(sesion, datos.transportista_id)
    cotizacion = cotizar(transportista, datos.origen, datos.destino, datos.peso_kg, datos.categoria)
    if not cotizacion.valida:
        raise DatosInvalidosError(cotizacion.advertencias[0])

    envio = Envio(
        cliente=cliente,
        transportista=transportista,
        origen=datos.origen,
        destino=datos.destino,
        categoria=datos.categoria,
        peso_kg=datos.peso_kg,
        fecha_entrega=datos.fecha_entrega,
        distancia_km=cotizacion.distancia_km,
        precio=cotizacion.precio,
        creado_en=ahora,
        notas=notas,
    )
    envio.historial.append(EventoEnvio(estado=EstadoEnvio.PENDIENTE, ocurrido_en=ahora))
    sesion.add(envio)
    sesion.commit()
    return envio


def acciones_disponibles(envio: Envio, actor: Actor) -> tuple[EstadoEnvio, ...]:
    """Estados a los que ``actor`` puede llevar el envío siguiendo el flujo normal."""
    if not _participa(envio, actor):
        return ()
    return _FLUJOS[actor.rol].get(envio.estado, ())


def cambiar_estado(
    sesion: Session,
    envio_id: int,
    nuevo: EstadoEnvio,
    actor: Actor,
    ahora: datetime | None = None,
) -> Envio:
    """Lleva un envío a ``nuevo`` y lo anota en su historial.

    Raises:
        RecursoNoEncontradoError: si el envío no existe.
        PermisoDenegadoError: si ``actor`` no participa en el envío o su rol no puede
            hacer ese cambio.
        ConflictoError: si el cambio no es posible desde el estado actual.
    """
    envio = obtener_envio(sesion, envio_id)
    if nuevo is envio.estado:
        msg = f"El envío {envio.folio} ya está {nuevo.etiqueta.lower()}."
        raise ConflictoError(msg)
    if actor.rol is not Rol.ADMINISTRADOR:
        _verificar_cambio(envio, nuevo, actor)
    envio.estado = nuevo
    envio.historial.append(EventoEnvio(estado=nuevo, ocurrido_en=ahora or datetime.now(UTC)))
    sesion.commit()
    return envio


def obtener_envio(sesion: Session, envio_id: int) -> Envio:
    """Busca un envío por su identificador.

    Raises:
        RecursoNoEncontradoError: si no existe.
    """
    envio = sesion.get(Envio, envio_id)
    if envio is None:
        raise RecursoNoEncontradoError("Envío", envio_id)
    return envio


def listar_envios(sesion: Session) -> list[Envio]:
    """Todos los envíos, del más reciente al más antiguo."""
    return list(sesion.scalars(select(Envio).order_by(Envio.creado_en.desc(), Envio.id.desc())))


def envios_del_cliente(sesion: Session, cliente: str) -> list[Envio]:
    """Envíos que solicitó ``cliente``, del más reciente al más antiguo."""
    consulta = (
        select(Envio)
        .where(Envio.cliente == cliente)
        .order_by(Envio.creado_en.desc(), Envio.id.desc())
    )
    return list(sesion.scalars(consulta))


def envios_del_transportista(sesion: Session, transportista_id: int) -> list[Envio]:
    """Envíos asignados a un transportista, del más reciente al más antiguo."""
    consulta = (
        select(Envio)
        .where(Envio.transportista_id == transportista_id)
        .order_by(Envio.creado_en.desc(), Envio.id.desc())
    )
    return list(sesion.scalars(consulta))


def contar_entregados(sesion: Session, transportista_id: int) -> int:
    """Cuántos viajes ha entregado un transportista en la plataforma."""
    consulta = select(func.count(Envio.id)).where(
        Envio.transportista_id == transportista_id, Envio.estado == EstadoEnvio.ENTREGADO
    )
    return sesion.scalar(consulta) or 0


def envios_por_transportista(sesion: Session) -> dict[int, int]:
    """Cuántas solicitudes ha recibido cada transportista (en cualquier estado)."""
    consulta = select(Envio.transportista_id, func.count(Envio.id)).group_by(Envio.transportista_id)
    return dict(sesion.execute(consulta).all())


def renombrar_cliente(sesion: Session, anterior: str, nuevo: str) -> str:
    """Cambia el nombre de una empresa cliente en todos sus envíos y devuelve el nuevo.

    Raises:
        DatosInvalidosError: si el nombre nuevo está vacío o es demasiado largo.
    """
    nuevo = " ".join(nuevo.split())
    if not nuevo:
        raise DatosInvalidosError("Escribe el nombre de tu empresa.")
    if len(nuevo) > LONGITUD_MAXIMA_CLIENTE:
        msg = f"El nombre de la empresa admite hasta {LONGITUD_MAXIMA_CLIENTE} caracteres."
        raise DatosInvalidosError(msg)
    if nuevo != anterior:
        sesion.execute(update(Envio).where(Envio.cliente == anterior).values(cliente=nuevo))
        sesion.commit()
    return nuevo


def avance_estimado(envio: Envio, ahora: datetime | None = None) -> float:
    """Fracción del recorrido (0 a 1) que se estima cubierta, para dibujar el mapa.

    Mientras el envío va en tránsito se interpola entre el inicio del viaje y las 18:00 del
    día de entrega, sin tocar los extremos para que se note que sigue en camino.
    """
    if envio.estado is EstadoEnvio.ENTREGADO:
        return 1.0
    if envio.estado is not EstadoEnvio.EN_TRANSITO:
        return 0.0
    inicio = envio.momento_de(EstadoEnvio.EN_TRANSITO)
    if inicio is None:
        return AVANCE_MINIMO
    fin = datetime.combine(envio.fecha_entrega, HORA_ESTIMADA_ENTREGA, tzinfo=get_settings().tz)
    total = max(1.0, (fin - inicio).total_seconds())
    transcurrido = ((ahora or datetime.now(UTC)) - inicio).total_seconds()
    return min(AVANCE_MAXIMO, max(AVANCE_MINIMO, transcurrido / total))


def _participa(envio: Envio, actor: Actor) -> bool:
    if actor.rol is Rol.CLIENTE:
        return envio.cliente == actor.empresa
    if actor.rol is Rol.TRANSPORTISTA:
        return envio.transportista_id == actor.transportista_id
    return True


def _verificar_cambio(envio: Envio, nuevo: EstadoEnvio, actor: Actor) -> None:
    if not _participa(envio, actor):
        raise PermisoDenegadoError(
            "Solo el cliente o el transportista del envío pueden cambiar su estado."
        )
    flujo = _FLUJOS[actor.rol]
    if nuevo in flujo.get(envio.estado, ()):
        return
    if any(nuevo in destinos for destinos in flujo.values()):
        msg = (
            f"El envío {envio.folio} está {envio.estado.etiqueta.lower()}: ya no se puede "
            f"marcar como {nuevo.etiqueta.lower()}."
        )
        raise ConflictoError(msg)
    msg = (
        f"Como {actor.rol.etiqueta.lower()} no puedes marcar un envío como "
        f"{nuevo.etiqueta.lower()}."
    )
    raise PermisoDenegadoError(msg)
