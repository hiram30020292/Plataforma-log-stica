"""Tabla de transportistas."""

from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from mcl.catalogo._vehiculos import ESPECIFICACIONES_VEHICULO, EspecificacionVehiculo
from mcl.core import Base, CategoriaServicio, Ciudad, EnumList, EnumText, TipoVehiculo, UTCDateTime

KG_POR_TONELADA = 1000


class Transportista(Base):
    """Empresa o persona que ofrece servicios de transporte en el catálogo.

    La calificación se guarda como suma de estrellas y número de opiniones, así el promedio
    es exacto aunque se agreguen miles de opiniones.
    """

    __tablename__ = "transportistas"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    nombre: Mapped[str] = mapped_column(String(60))
    ciudad: Mapped[Ciudad] = mapped_column(EnumText(Ciudad))
    zonas: Mapped[list[Ciudad]] = mapped_column(EnumList(Ciudad))
    vehiculo: Mapped[TipoVehiculo] = mapped_column(EnumText(TipoVehiculo))
    capacidad_kg: Mapped[int]
    categorias: Mapped[list[CategoriaServicio]] = mapped_column(EnumList(CategoriaServicio))
    tarifa_base: Mapped[int]
    telefono: Mapped[str] = mapped_column(String(20))
    descripcion: Mapped[str] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(UTCDateTime())
    suma_estrellas: Mapped[int] = mapped_column(default=0)
    num_opiniones: Mapped[int] = mapped_column(default=0)
    verificado: Mapped[bool] = mapped_column(default=False)
    destacado: Mapped[bool] = mapped_column(default=False)
    # Tono (0-360) con el que se dibuja su vehículo en la app; solo es decorativo.
    tono: Mapped[int] = mapped_column(default=200)

    @property
    def calificacion(self) -> float:
        """Promedio de estrellas, o 0 si todavía no tiene opiniones."""
        if self.num_opiniones == 0:
            return 0.0
        return self.suma_estrellas / self.num_opiniones

    @property
    def capacidad(self) -> str:
        """Capacidad para mostrar: ``"5 t"``, ``"1.5 t"`` u ``"800 kg"``."""
        if self.capacidad_kg >= KG_POR_TONELADA:
            return f"{self.capacidad_kg / KG_POR_TONELADA:g} t"
        return f"{self.capacidad_kg} kg"

    @property
    def especificacion(self) -> EspecificacionVehiculo:
        """Tarifa por kilómetro y carga máxima de su vehículo."""
        return ESPECIFICACIONES_VEHICULO[self.vehiculo]

    def registrar_estrellas(self, estrellas: int) -> None:
        """Suma una opinión nueva al promedio."""
        self.suma_estrellas += estrellas
        self.num_opiniones += 1
