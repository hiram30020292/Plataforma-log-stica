"""Tablas de envíos y de su historial de estados."""

from datetime import date, datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mcl.catalogo import Transportista
from mcl.core import Base, CategoriaServicio, Ciudad, EnumText, EstadoEnvio, UTCDateTime

# Los folios se muestran a partir de S-1001 aunque el identificador interno empiece en 1.
_BASE_FOLIO = 1000


class EventoEnvio(Base):
    """Cambio de estado de un envío; juntos forman su línea de tiempo."""

    __tablename__ = "eventos_envio"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    envio_id: Mapped[int] = mapped_column(ForeignKey("envios.id"), index=True, init=False)
    estado: Mapped[EstadoEnvio] = mapped_column(EnumText(EstadoEnvio))
    ocurrido_en: Mapped[datetime] = mapped_column(UTCDateTime())


class Envio(Base):
    """Solicitud de transporte de un cliente con un transportista.

    Nace como solicitud ``pendiente``; cuando el transportista la acepta se convierte en un
    envío al que se le da seguimiento hasta la entrega.
    """

    __tablename__ = "envios"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    cliente: Mapped[str] = mapped_column(String(60), index=True)
    transportista_id: Mapped[int] = mapped_column(
        ForeignKey("transportistas.id"), index=True, init=False
    )
    transportista: Mapped[Transportista] = relationship(lazy="joined", repr=False)
    origen: Mapped[Ciudad] = mapped_column(EnumText(Ciudad))
    destino: Mapped[Ciudad] = mapped_column(EnumText(Ciudad))
    categoria: Mapped[CategoriaServicio] = mapped_column(EnumText(CategoriaServicio))
    peso_kg: Mapped[int]
    fecha_entrega: Mapped[date]
    distancia_km: Mapped[int]
    precio: Mapped[int]
    creado_en: Mapped[datetime] = mapped_column(UTCDateTime())
    notas: Mapped[str] = mapped_column(Text, default="")
    estado: Mapped[EstadoEnvio] = mapped_column(
        EnumText(EstadoEnvio), default=EstadoEnvio.PENDIENTE, index=True
    )
    # Estrellas que dio el cliente al calificar el servicio (None si aún no califica).
    calificacion: Mapped[int | None] = mapped_column(default=None)
    historial: Mapped[list[EventoEnvio]] = relationship(
        default_factory=list,
        order_by=EventoEnvio.id,
        cascade="all, delete-orphan",
        lazy="selectin",
        repr=False,
    )

    @property
    def folio(self) -> str:
        """Identificador para mostrar a las personas, por ejemplo ``S-1042``."""
        return f"S-{_BASE_FOLIO + self.id}"

    def momento_de(self, estado: EstadoEnvio) -> datetime | None:
        """Cuándo llegó el envío a ``estado`` por primera vez (None si no ha llegado)."""
        return next((e.ocurrido_en for e in self.historial if e.estado is estado), None)
