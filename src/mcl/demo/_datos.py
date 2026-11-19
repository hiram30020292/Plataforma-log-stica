"""Datos de ejemplo para presentar la plataforma.

Las fechas son relativas al momento en que se cargan, así el panel siempre muestra
actividad reciente. Los envíos de otros clientes se generan con un generador
pseudoaleatorio de semilla fija: los datos son los mismos en cada carga.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from mcl.calificaciones import Opinion
from mcl.catalogo import Transportista
from mcl.core import (
    CategoriaServicio,
    Ciudad,
    ConflictoError,
    EstadoEnvio,
    TipoVehiculo,
    get_settings,
)
from mcl.envios import Envio, EventoEnvio, cotizar
from mcl.utils import round_to_multiple

CLIENTE_DE_EJEMPLO = "Tu Empresa SA"

_OTROS_CLIENTES = (
    "Comercial Ríos",
    "Abarrotes Luna",
    "Muebles Hogar",
    "Farmacias Sol",
    "Aceros del Centro",
    "Distribuidora MX",
    "Industrias Ortega",
)
_ENVIOS_DE_OTROS_CLIENTES = 46
_SEMILLA = 7
_DIAS_DE_HISTORIAL = 28
# Un envío creado hace más de estos días casi siempre ya terminó.
_DIAS_PARA_SER_ANTIGUO = 6
# Los envíos de otros clientes se entregan unos días después de solicitarse.
_DIAS_HASTA_LA_ENTREGA = 3
_PROBABILIDAD_DE_CALIFICAR = 0.6
_PESO_REDONDEADO_A_KG = 50
# Probabilidad acumulada de cada estado, según la antigüedad del envío.
_ESTADOS_ANTIGUOS = (
    (0.88, EstadoEnvio.ENTREGADO),
    (0.95, EstadoEnvio.CANCELADO),
    (1.0, EstadoEnvio.RECHAZADO),
)
_ESTADOS_RECIENTES = (
    (0.3, EstadoEnvio.PENDIENTE),
    (0.55, EstadoEnvio.CONFIRMADO),
    (0.8, EstadoEnvio.EN_TRANSITO),
    (1.0, EstadoEnvio.ENTREGADO),
)
_FLUJO = (
    EstadoEnvio.PENDIENTE,
    EstadoEnvio.CONFIRMADO,
    EstadoEnvio.EN_TRANSITO,
    EstadoEnvio.ENTREGADO,
)
# Tiempo típico entre un cambio de estado y el siguiente.
_PASO_ENTRE_ESTADOS = timedelta(days=0.6)


@dataclass(frozen=True, slots=True, kw_only=True)
class _Transportista:
    nombre: str
    ciudad: Ciudad
    zonas: tuple[Ciudad, ...]
    vehiculo: TipoVehiculo
    capacidad_kg: int
    categorias: tuple[CategoriaServicio, ...]
    tarifa_base: int
    calificacion: float
    opiniones: int
    verificado: bool
    destacado: bool
    tono: int
    telefono: str
    descripcion: str


_TRANSPORTISTAS = (
    _Transportista(
        nombre="Transporte López",
        ciudad=Ciudad.QUERETARO,
        zonas=(Ciudad.QUERETARO, Ciudad.CDMX, Ciudad.MONTERREY, Ciudad.SAN_LUIS_POTOSI),
        vehiculo=TipoVehiculo.TRAILER,
        capacidad_kg=30_000,
        categorias=(CategoriaServicio.CARGA_GENERAL, CategoriaServicio.CARGA_PESADA),
        tarifa_base=2200,
        calificacion=4.8,
        opiniones=120,
        verificado=True,
        destacado=True,
        tono=214,
        telefono="442 123 4567",
        descripcion=(
            "Flota de 12 tractocamiones con caja seca de 53 pies. Rastreo satelital en cada "
            "unidad y seguro de carga incluido."
        ),
    ),
    _Transportista(
        nombre="Rápidos del Bajío",
        ciudad=Ciudad.QUERETARO,
        zonas=(Ciudad.QUERETARO, Ciudad.LEON, Ciudad.CDMX, Ciudad.GUADALAJARA),
        vehiculo=TipoVehiculo.CAMION,
        capacidad_kg=5_000,
        categorias=(CategoriaServicio.CARGA_GENERAL, CategoriaServicio.PAQUETERIA),
        tarifa_base=1800,
        calificacion=4.9,
        opiniones=250,
        verificado=True,
        destacado=True,
        tono=200,
        telefono="442 987 6543",
        descripcion=(
            "Entregas el mismo día dentro del Bajío. Especialistas en distribución para "
            "comercios y centros de distribución."
        ),
    ),
    _Transportista(
        nombre="Logística Express",
        ciudad=Ciudad.QUERETARO,
        zonas=(Ciudad.QUERETARO, Ciudad.CDMX, Ciudad.GUADALAJARA),
        vehiculo=TipoVehiculo.VAN,
        capacidad_kg=1_500,
        categorias=(CategoriaServicio.PAQUETERIA, CategoriaServicio.MUDANZAS),
        tarifa_base=1200,
        calificacion=4.7,
        opiniones=180,
        verificado=True,
        destacado=True,
        tono=228,
        telefono="442 555 0101",
        descripcion=(
            "Vans ligeras para paquetería y mudanzas pequeñas. Maniobras de carga y descarga "
            "incluidas."
        ),
    ),
    _Transportista(
        nombre="Transporte Segura",
        ciudad=Ciudad.QUERETARO,
        zonas=(Ciudad.QUERETARO, Ciudad.PUEBLA, Ciudad.CDMX),
        vehiculo=TipoVehiculo.CAMION,
        capacidad_kg=10_000,
        categorias=(CategoriaServicio.CARGA_GENERAL, CategoriaServicio.CARGA_PESADA),
        tarifa_base=2500,
        calificacion=4.6,
        opiniones=90,
        verificado=True,
        destacado=False,
        tono=190,
        telefono="442 300 2200",
        descripcion="Camiones rabón y tórton con custodia opcional para mercancía de alto valor.",
    ),
    _Transportista(
        nombre="Fletes Tapatíos",
        ciudad=Ciudad.GUADALAJARA,
        zonas=(Ciudad.GUADALAJARA, Ciudad.LEON),
        vehiculo=TipoVehiculo.CAMIONETA,
        capacidad_kg=1_000,
        categorias=(CategoriaServicio.MUDANZAS, CategoriaServicio.PAQUETERIA),
        tarifa_base=900,
        calificacion=4.5,
        opiniones=64,
        verificado=False,
        destacado=False,
        tono=240,
        telefono="33 1234 5678",
        descripcion=(
            "Fletes y mudanzas locales en camioneta de una tonelada. Disponibles fines de semana."
        ),
    ),
    _Transportista(
        nombre="Norte Cargo",
        ciudad=Ciudad.MONTERREY,
        zonas=(Ciudad.MONTERREY, Ciudad.SAN_LUIS_POTOSI, Ciudad.QUERETARO, Ciudad.CDMX),
        vehiculo=TipoVehiculo.TRAILER,
        capacidad_kg=25_000,
        categorias=(CategoriaServicio.CARGA_PESADA, CategoriaServicio.CARGA_GENERAL),
        tarifa_base=3200,
        calificacion=4.7,
        opiniones=142,
        verificado=True,
        destacado=True,
        tono=206,
        telefono="81 8000 1122",
        descripcion=(
            "Rutas troncales norte-centro con plataforma y caja seca. Operadores certificados."
        ),
    ),
    _Transportista(
        nombre="Mudanzas Capital",
        ciudad=Ciudad.CDMX,
        zonas=(Ciudad.CDMX, Ciudad.PUEBLA, Ciudad.QUERETARO),
        vehiculo=TipoVehiculo.CAMION,
        capacidad_kg=3_500,
        categorias=(CategoriaServicio.MUDANZAS,),
        tarifa_base=1500,
        calificacion=4.4,
        opiniones=77,
        verificado=True,
        destacado=False,
        tono=220,
        telefono="55 4000 3344",
        descripcion=(
            "Mudanzas residenciales y de oficina con empaque, embalaje y armado de muebles."
        ),
    ),
    _Transportista(
        nombre="Paquetería Ágil",
        ciudad=Ciudad.PUEBLA,
        zonas=(Ciudad.PUEBLA, Ciudad.CDMX),
        vehiculo=TipoVehiculo.VAN,
        capacidad_kg=1_000,
        categorias=(CategoriaServicio.PAQUETERIA,),
        tarifa_base=800,
        calificacion=4.6,
        opiniones=51,
        verificado=False,
        destacado=False,
        tono=196,
        telefono="222 600 7788",
        descripcion=(
            "Última milla para tiendas en línea. Recolección diaria y evidencia fotográfica "
            "de entrega."
        ),
    ),
)

# (índice del transportista, autor, estrellas, texto, hace cuántos días)
_OPINIONES = (
    (0, "Comercial Ríos", 5, "Llegaron a tiempo y la carga sin un rasguño.", 6),
    (0, "Aceros del Centro", 4, "Buen servicio, la recolección se retrasó una hora.", 20),
    (1, "Abarrotes Luna", 5, "Muy rápidos, ya es nuestro proveedor fijo.", 3),
    (1, "Farmacias Sol", 5, "Excelente comunicación durante el viaje.", 11),
    (2, "Muebles Hogar", 5, "Cuidaron mucho los muebles. Recomendados.", 8),
    (3, "Industrias Ortega", 4, "Precio justo y operador amable.", 15),
    (5, "Distribuidora MX", 5, "Cumplieron la ruta Monterrey-CDMX sin contratiempos.", 9),
)


@dataclass(frozen=True, slots=True, kw_only=True)
class _Envio:
    cliente: str
    transportista: int
    origen: Ciudad
    destino: Ciudad
    categoria: CategoriaServicio
    peso_kg: int
    estado: EstadoEnvio
    creado_hace_dias: float
    entrega_en_dias: int
    notas: str = ""
    calificacion: int | None = None


# Los envíos de la empresa con la que se presenta la demo, uno en cada etapa importante.
_ENVIOS_DEL_CLIENTE = (
    _Envio(
        cliente=CLIENTE_DE_EJEMPLO,
        transportista=1,
        origen=Ciudad.QUERETARO,
        destino=Ciudad.CDMX,
        categoria=CategoriaServicio.CARGA_GENERAL,
        peso_kg=2800,
        estado=EstadoEnvio.EN_TRANSITO,
        creado_hace_dias=2,
        entrega_en_dias=3,
        notas="14 tarimas de producto empacado.",
    ),
    _Envio(
        cliente=CLIENTE_DE_EJEMPLO,
        transportista=2,
        origen=Ciudad.QUERETARO,
        destino=Ciudad.GUADALAJARA,
        categoria=CategoriaServicio.PAQUETERIA,
        peso_kg=600,
        estado=EstadoEnvio.CONFIRMADO,
        creado_hace_dias=1,
        entrega_en_dias=5,
        notas="40 cajas medianas.",
    ),
    _Envio(
        cliente=CLIENTE_DE_EJEMPLO,
        transportista=0,
        origen=Ciudad.QUERETARO,
        destino=Ciudad.MONTERREY,
        categoria=CategoriaServicio.CARGA_PESADA,
        peso_kg=18000,
        estado=EstadoEnvio.PENDIENTE,
        creado_hace_dias=0.2,
        entrega_en_dias=8,
        notas="Maquinaria en 2 piezas, requiere montacargas.",
    ),
    _Envio(
        cliente=CLIENTE_DE_EJEMPLO,
        transportista=1,
        origen=Ciudad.LEON,
        destino=Ciudad.QUERETARO,
        categoria=CategoriaServicio.CARGA_GENERAL,
        peso_kg=1500,
        estado=EstadoEnvio.ENTREGADO,
        creado_hace_dias=12,
        entrega_en_dias=-9,
        calificacion=5,
    ),
)


class _Aleatorio:
    """Generador de Lehmer: pequeño, determinista y suficiente para datos de ejemplo."""

    _MODULO = 2_147_483_647
    _MULTIPLICADOR = 16_807

    def __init__(self, semilla: int) -> None:
        self._estado = semilla

    def siguiente(self) -> float:
        """Número en el intervalo (0, 1)."""
        self._estado = self._estado * self._MULTIPLICADOR % self._MODULO
        return self._estado / self._MODULO

    def indice(self, cantidad: int) -> int:
        """Índice entero entre 0 y ``cantidad - 1``."""
        return int(self.siguiente() * cantidad)


def hay_datos(sesion: Session) -> bool:
    """Indica si la base ya tiene transportistas cargados."""
    return bool(sesion.scalar(select(func.count(Transportista.id))))


def sembrar_si_esta_vacia(sesion: Session, ahora: datetime | None = None) -> bool:
    """Carga los datos de ejemplo solo si la base está vacía. Devuelve si los cargó."""
    if hay_datos(sesion):
        return False
    sembrar_datos_de_ejemplo(sesion, ahora)
    return True


def restablecer_datos_de_ejemplo(sesion: Session, ahora: datetime | None = None) -> None:
    """Borra todos los datos y vuelve a cargar los de ejemplo."""
    for modelo in (Opinion, EventoEnvio, Envio, Transportista):
        sesion.execute(delete(modelo))
    sesion.flush()
    sesion.expunge_all()
    sembrar_datos_de_ejemplo(sesion, ahora)


def sembrar_datos_de_ejemplo(sesion: Session, ahora: datetime | None = None) -> None:
    """Carga transportistas, opiniones y envíos de ejemplo en una base vacía.

    Raises:
        ConflictoError: si la base ya tiene transportistas.
    """
    if hay_datos(sesion):
        raise ConflictoError("La base ya tiene datos; restablécela en lugar de sembrarla.")
    ahora = ahora or datetime.now(UTC)

    transportistas = [_crear_transportista(datos, ahora) for datos in _TRANSPORTISTAS]
    sesion.add_all(transportistas)
    sesion.flush()

    for indice, autor, estrellas, texto, dias in _OPINIONES:
        sesion.add(
            Opinion(
                transportista_id=transportistas[indice].id,
                autor=autor,
                estrellas=estrellas,
                texto=texto,
                creado_en=ahora - timedelta(days=dias),
            )
        )

    planes = [*_ENVIOS_DEL_CLIENTE, *_generar_envios_de_otros_clientes()]
    # Del más antiguo al más reciente, para que los folios crezcan con el tiempo.
    planes.sort(key=lambda plan: -plan.creado_hace_dias)
    sesion.add_all(_crear_envio(plan, transportistas, ahora) for plan in planes)
    sesion.commit()


def _crear_transportista(datos: _Transportista, ahora: datetime) -> Transportista:
    return Transportista(
        nombre=datos.nombre,
        ciudad=datos.ciudad,
        zonas=list(datos.zonas),
        vehiculo=datos.vehiculo,
        capacidad_kg=datos.capacidad_kg,
        categorias=list(datos.categorias),
        tarifa_base=datos.tarifa_base,
        telefono=datos.telefono,
        descripcion=datos.descripcion,
        creado_en=ahora - timedelta(days=90),
        suma_estrellas=round(datos.calificacion * datos.opiniones),
        num_opiniones=datos.opiniones,
        verificado=datos.verificado,
        destacado=datos.destacado,
        tono=datos.tono,
    )


def _generar_envios_de_otros_clientes() -> list[_Envio]:
    """Historial de otros clientes para que el panel administrativo tenga datos."""
    azar = _Aleatorio(_SEMILLA)
    ciudades = list(Ciudad)
    envios: list[_Envio] = []
    for _ in range(_ENVIOS_DE_OTROS_CLIENTES):
        indice = azar.indice(len(_TRANSPORTISTAS))
        transportista = _TRANSPORTISTAS[indice]
        hace_dias = azar.indice(_DIAS_DE_HISTORIAL) + 1
        origen = transportista.zonas[azar.indice(len(transportista.zonas))]
        destino = ciudades[azar.indice(len(ciudades))]
        if destino is origen:
            destino = next(zona for zona in transportista.zonas if zona is not origen)
        tabla = _ESTADOS_ANTIGUOS if hace_dias > _DIAS_PARA_SER_ANTIGUO else _ESTADOS_RECIENTES
        sorteo = azar.siguiente()
        estado = next(estado for limite, estado in tabla if sorteo < limite)
        capacidad = transportista.capacidad_kg
        peso = round_to_multiple(capacidad * (0.2 + azar.siguiente() * 0.7), _PESO_REDONDEADO_A_KG)
        cliente = _OTROS_CLIENTES[azar.indice(len(_OTROS_CLIENTES))]
        categoria = transportista.categorias[azar.indice(len(transportista.categorias))]
        creado_hace_dias = hace_dias + azar.siguiente() * 0.5
        calificacion = None
        if estado is EstadoEnvio.ENTREGADO and azar.siguiente() < _PROBABILIDAD_DE_CALIFICAR:
            calificacion = 4 + round(azar.siguiente())
        envios.append(
            _Envio(
                cliente=cliente,
                transportista=indice,
                origen=origen,
                destino=destino,
                categoria=categoria,
                peso_kg=peso,
                estado=estado,
                creado_hace_dias=creado_hace_dias,
                entrega_en_dias=_DIAS_HASTA_LA_ENTREGA - hace_dias,
                calificacion=calificacion,
            )
        )
    return envios


def _crear_envio(plan: _Envio, transportistas: list[Transportista], ahora: datetime) -> Envio:
    transportista = transportistas[plan.transportista]
    creado_en = ahora - timedelta(days=plan.creado_hace_dias)
    hoy = ahora.astimezone(get_settings().tz).date()
    cotizacion = cotizar(transportista, plan.origen, plan.destino, plan.peso_kg)
    envio = Envio(
        cliente=plan.cliente,
        transportista=transportista,
        origen=plan.origen,
        destino=plan.destino,
        categoria=plan.categoria,
        peso_kg=plan.peso_kg,
        fecha_entrega=hoy + timedelta(days=plan.entrega_en_dias),
        distancia_km=cotizacion.distancia_km,
        precio=cotizacion.precio,
        creado_en=creado_en,
        notas=plan.notas,
        estado=plan.estado,
        calificacion=plan.calificacion,
    )
    pasos = _pasos_hasta(plan.estado)
    # Los cambios van cada 0.6 días, pero ninguno puede quedar en el futuro.
    espacio = min(_PASO_ENTRE_ESTADOS, (ahora - creado_en) / len(pasos))
    envio.historial.extend(
        EventoEnvio(estado=estado, ocurrido_en=creado_en + espacio * i)
        for i, estado in enumerate(pasos)
    )
    return envio


def _pasos_hasta(estado: EstadoEnvio) -> list[EstadoEnvio]:
    """Estados por los que pasó un envío hasta llegar a ``estado``."""
    if estado in _FLUJO:
        return list(_FLUJO[: _FLUJO.index(estado) + 1])
    return [EstadoEnvio.PENDIENTE, estado]
