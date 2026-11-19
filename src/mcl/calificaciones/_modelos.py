"""Tabla de opiniones sobre transportistas."""

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from mcl.core import Base, UTCDateTime


class Opinion(Base):
    """Opinión escrita de un cliente sobre un transportista.

    Las que nacen de un envío calificado guardan ``envio_id``; cada envío admite una sola.
    """

    __tablename__ = "opiniones"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    transportista_id: Mapped[int] = mapped_column(ForeignKey("transportistas.id"), index=True)
    autor: Mapped[str] = mapped_column(String(60))
    estrellas: Mapped[int]
    texto: Mapped[str] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(UTCDateTime())
    envio_id: Mapped[int | None] = mapped_column(ForeignKey("envios.id"), unique=True, default=None)
