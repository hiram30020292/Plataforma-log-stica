"""Pantallas de la app: inicio, catálogo, solicitudes, envíos, panel del transportista y perfil."""

from datetime import UTC, date, datetime, timedelta
from http import HTTPStatus
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from mcl.calificaciones import DatosCalificacion, calificar_envio, opiniones_de
from mcl.catalogo import (
    DatosRegistro,
    FiltroCatalogo,
    OrdenCatalogo,
    Transportista,
    buscar_transportistas,
    listar_transportistas,
    obtener_transportista,
    registrar_transportista,
    transportistas_destacados,
)
from mcl.core import (
    CategoriaServicio,
    Ciudad,
    ConflictoError,
    DatosInvalidosError,
    EstadoEnvio,
    PermisoDenegadoError,
    RecursoNoEncontradoError,
    Rol,
    TipoVehiculo,
    get_session,
    get_settings,
)
from mcl.demo import restablecer_datos_de_ejemplo
from mcl.envios import (
    DatosSolicitud,
    Envio,
    acciones_disponibles,
    avance_estimado,
    cambiar_estado,
    contar_entregados,
    cotizar,
    crear_solicitud,
    envios_del_cliente,
    envios_del_transportista,
    obtener_envio,
    renombrar_cliente,
)
from mcl.web._acciones import ACCIONES, linea_de_tiempo
from mcl.web._formularios import (
    ConsultaCatalogo,
    FormularioCalificacion,
    FormularioEstado,
    FormularioPerfil,
    FormularioRegistro,
    FormularioSolicitud,
    entero,
    entero_o_none,
    fecha_iso,
    opcion,
    requerir,
    ruta_local,
)
from mcl.web._graficas import mapa_de_ruta
from mcl.web._plantillas import renderizar
from mcl.web._sesion import (
    TipoAviso,
    actor_actual,
    avisar,
    borrar_preferencias,
    guardar_preferencias,
    leer_preferencias,
    transportista_actual,
)

router = APIRouter(include_in_schema=False)

SesionBD = Annotated[Session, Depends(get_session)]

PESO_SUGERIDO_KG = 800
DIAS_SUGERIDOS_PARA_ENTREGA = 4
COMPLETADOS_VISIBLES = 6
# Pantalla con la que empieza cada rol.
INICIO_DEL_ROL = {Rol.CLIENTE: "/envios", Rol.TRANSPORTISTA: "/panel", Rol.ADMINISTRADOR: "/admin"}


def _redirigir(url: str) -> RedirectResponse:
    """Después de un formulario se redirige con 303: recargar no lo envía de nuevo."""
    return RedirectResponse(url, status_code=HTTPStatus.SEE_OTHER)


def _hoy() -> date:
    return datetime.now(UTC).astimezone(get_settings().tz).date()


# --------------------------------------------------------------------------- inicio y catálogo


@router.get("/", response_class=HTMLResponse)
def inicio(request: Request, sesion: SesionBD) -> HTMLResponse:
    """Portada: buscador, categorías, transportistas destacados y cómo funciona."""
    contexto = {
        "pestana": "inicio",
        "categorias": list(CategoriaServicio),
        "destacados": transportistas_destacados(sesion),
    }
    return renderizar(request, "inicio.html", contexto)


def _filtro(consulta: ConsultaCatalogo) -> FiltroCatalogo:
    return FiltroCatalogo(
        texto=consulta.texto,
        categoria=opcion(CategoriaServicio, consulta.categoria),
        ciudad=opcion(Ciudad, consulta.ciudad),
        vehiculo=opcion(TipoVehiculo, consulta.vehiculo),
        orden=opcion(OrdenCatalogo, consulta.orden) or OrdenCatalogo.MEJOR_CALIFICADOS,
    )


@router.get("/buscar", response_class=HTMLResponse)
def catalogo(
    request: Request, sesion: SesionBD, consulta: Annotated[ConsultaCatalogo, Query()]
) -> HTMLResponse:
    """Catálogo de transportistas con filtros."""
    filtro = _filtro(consulta)
    contexto = {
        "pestana": "buscar",
        "filtro": filtro,
        "resultados": buscar_transportistas(sesion, filtro),
    }
    return renderizar(request, "catalogo.html", contexto)


@router.get("/buscar/resultados", response_class=HTMLResponse)
def resultados_del_catalogo(
    request: Request, sesion: SesionBD, consulta: Annotated[ConsultaCatalogo, Query()]
) -> HTMLResponse:
    """Solo la lista de resultados, para filtrar sin recargar la página."""
    resultados = buscar_transportistas(sesion, _filtro(consulta))
    return renderizar(request, "_resultados.html", {"resultados": resultados}, fragmento=True)


@router.get("/transportistas/{transportista_id}", response_class=HTMLResponse)
def perfil_del_transportista(
    request: Request, sesion: SesionBD, transportista_id: int
) -> HTMLResponse:
    """Perfil público de un transportista con sus opiniones."""
    transportista = obtener_transportista(sesion, transportista_id)
    contexto = {
        "pestana": "buscar",
        "t": transportista,
        "opiniones": opiniones_de(sesion, transportista.id),
        "viajes": contar_entregados(sesion, transportista.id),
    }
    return renderizar(request, "transportista.html", contexto)


# --------------------------------------------------------------------------- solicitudes


def _contexto_solicitud(
    sesion: Session, formulario: FormularioSolicitud, error: str | None = None
) -> dict[str, Any]:
    """Valores del formulario de solicitud (los sugeridos si faltan) y su cotización."""
    transportistas = listar_transportistas(sesion)
    if not transportistas:
        raise ConflictoError("Todavía no hay transportistas registrados en la plataforma.")
    elegido_id = entero_o_none(formulario.transportista)
    elegido = next((t for t in transportistas if t.id == elegido_id), transportistas[0])
    origen = opcion(Ciudad, formulario.origen) or elegido.ciudad
    destino = opcion(Ciudad, formulario.destino) or next(
        (zona for zona in elegido.zonas if zona is not elegido.ciudad), Ciudad.CDMX
    )
    categoria = opcion(CategoriaServicio, formulario.categoria) or elegido.categorias[0]
    peso = PESO_SUGERIDO_KG if not formulario.peso else entero_o_none(formulario.peso) or 0
    hoy = _hoy()
    try:
        fecha = fecha_iso(formulario.fecha, "la fecha")
    except DatosInvalidosError:
        fecha = hoy + timedelta(days=DIAS_SUGERIDOS_PARA_ENTREGA)
    return {
        "transportistas": transportistas,
        "elegido": elegido,
        "origen": origen,
        "destino": destino,
        "categoria": categoria,
        "peso": peso,
        "fecha": fecha,
        "fecha_minima": hoy + timedelta(days=1),
        "notas": formulario.notas,
        "cotizacion": cotizar(elegido, origen, destino, peso, categoria),
        "error": error,
    }


@router.get("/solicitar", response_class=HTMLResponse)
def formulario_de_solicitud(
    request: Request, sesion: SesionBD, formulario: Annotated[FormularioSolicitud, Query()]
) -> HTMLResponse:
    """Formulario para pedir un servicio, con la cotización calculada al momento."""
    contexto = _contexto_solicitud(sesion, formulario)
    volver = f"/transportistas/{contexto['elegido'].id}" if formulario.transportista else "/envios"
    contexto.update(pestana="envios" if volver == "/envios" else "buscar", volver=volver)
    return renderizar(request, "solicitud.html", contexto)


@router.get("/solicitar/cotizacion", response_class=HTMLResponse)
def cotizacion_en_vivo(
    request: Request, sesion: SesionBD, formulario: Annotated[FormularioSolicitud, Query()]
) -> HTMLResponse:
    """Solo el recuadro de la cotización, para recalcularla mientras se llena el formulario."""
    contexto = _contexto_solicitud(sesion, formulario)
    return renderizar(request, "_cotizacion.html", contexto, fragmento=True)


@router.post("/solicitar", response_model=None)
def enviar_solicitud(
    request: Request, sesion: SesionBD, formulario: Annotated[FormularioSolicitud, Form()]
) -> HTMLResponse | RedirectResponse:
    """Registra la solicitud a nombre de la empresa del navegador."""
    preferencias = leer_preferencias(request)
    try:
        datos = DatosSolicitud(
            transportista_id=entero(formulario.transportista, "El transportista"),
            origen=requerir(Ciudad, formulario.origen, "la ciudad de origen"),
            destino=requerir(Ciudad, formulario.destino, "la ciudad de destino"),
            categoria=requerir(CategoriaServicio, formulario.categoria, "el tipo de carga"),
            peso_kg=entero(formulario.peso, "El peso"),
            fecha_entrega=fecha_iso(formulario.fecha, "la fecha de entrega"),
            notas=formulario.notas,
        )
        envio = crear_solicitud(sesion, datos, preferencias.empresa)
    except DatosInvalidosError as error:
        contexto = _contexto_solicitud(sesion, formulario, error.mensaje)
        contexto.update(pestana="envios", volver="/envios")
        return renderizar(
            request, "solicitud.html", contexto, status_code=HTTPStatus.UNPROCESSABLE_ENTITY
        )
    respuesta = _redirigir(f"/envios/{envio.id}")
    guardar_preferencias(respuesta, rol=Rol.CLIENTE)
    avisar(respuesta, f"Solicitud {envio.folio} enviada")
    return respuesta


# --------------------------------------------------------------------------- envíos


@router.get("/envios", response_class=HTMLResponse)
def mis_envios(request: Request, sesion: SesionBD, vista: str = "activas") -> HTMLResponse:
    """Panel del cliente: envíos activos e historial de su empresa."""
    preferencias = leer_preferencias(request)
    mios = envios_del_cliente(sesion, preferencias.empresa)
    activos = [envio for envio in mios if envio.estado.activo]
    historial = [envio for envio in mios if not envio.estado.activo]
    vista = "historial" if vista == "historial" else "activas"
    contexto = {
        "pestana": "envios",
        "vista": vista,
        "activos": activos,
        "historial": historial,
        "lista": historial if vista == "historial" else activos,
        "novedades": sum(envio.estado is not EstadoEnvio.PENDIENTE for envio in activos),
    }
    return renderizar(request, "envios.html", contexto)


def _volver_del_envio(rol: Rol) -> str:
    return {Rol.TRANSPORTISTA: "/panel", Rol.ADMINISTRADOR: "/admin/envios"}.get(rol, "/envios")


@router.get("/envios/{envio_id}", response_class=HTMLResponse)
def detalle_del_envio(request: Request, sesion: SesionBD, envio_id: int) -> HTMLResponse:
    """Seguimiento de un envío: mapa, datos, línea de tiempo y acciones según el rol."""
    envio = obtener_envio(sesion, envio_id)
    preferencias = leer_preferencias(request)
    actor = actor_actual(sesion, preferencias)
    cerrado = envio.estado in {EstadoEnvio.CANCELADO, EstadoEnvio.RECHAZADO}
    contexto = {
        "pestana": "panel" if actor.rol is Rol.TRANSPORTISTA else "envios",
        "envio": envio,
        "volver": _volver_del_envio(actor.rol),
        "acciones": [(estado, ACCIONES[estado]) for estado in acciones_disponibles(envio, actor)],
        "seguimiento": linea_de_tiempo(envio),
        "mapa": None if cerrado else mapa_de_ruta(avance_estimado(envio)),
        "puede_calificar": (
            actor.rol is Rol.CLIENTE
            and envio.cliente == actor.empresa
            and envio.estado is EstadoEnvio.ENTREGADO
            and envio.calificacion is None
        ),
    }
    return renderizar(request, "envio.html", contexto)


@router.post("/envios/{envio_id}/estado")
def cambiar_estado_del_envio(
    request: Request,
    sesion: SesionBD,
    envio_id: int,
    formulario: Annotated[FormularioEstado, Form()],
) -> RedirectResponse:
    """Aceptar, rechazar, iniciar, entregar o cancelar, según quién lo pida."""
    actor = actor_actual(sesion, leer_preferencias(request))
    respuesta = _redirigir(ruta_local(formulario.volver, f"/envios/{envio_id}"))
    try:
        estado = requerir(EstadoEnvio, formulario.estado, "el nuevo estado")
        cambiar_estado(sesion, envio_id, estado, actor)
    except (ConflictoError, DatosInvalidosError, PermisoDenegadoError) as error:
        avisar(respuesta, error.mensaje, TipoAviso.ERROR)
    else:
        avisar(respuesta, ACCIONES[estado].aviso)
    return respuesta


@router.post("/envios/{envio_id}/calificacion")
def calificar(
    request: Request,
    sesion: SesionBD,
    envio_id: int,
    formulario: Annotated[FormularioCalificacion, Form()],
) -> RedirectResponse:
    """El cliente califica un envío entregado."""
    actor = actor_actual(sesion, leer_preferencias(request))
    respuesta = _redirigir(f"/envios/{envio_id}")
    try:
        datos = DatosCalificacion(
            estrellas=entero(formulario.estrellas, "La calificación"), texto=formulario.texto
        )
        calificar_envio(sesion, envio_id, datos, actor)
    except (ConflictoError, DatosInvalidosError, PermisoDenegadoError) as error:
        avisar(respuesta, error.mensaje, TipoAviso.ERROR)
    else:
        avisar(respuesta, "Gracias por tu calificación")
    return respuesta


# --------------------------------------------------------------------------- transportista


@router.get("/panel", response_class=HTMLResponse)
def panel_del_transportista(request: Request, sesion: SesionBD) -> HTMLResponse:
    """Solicitudes nuevas, viajes en curso y completados del transportista elegido."""
    transportista = transportista_actual(sesion, leer_preferencias(request))
    mios: list[Envio] = []
    if transportista is not None:
        mios = envios_del_transportista(sesion, transportista.id)
    completados = [e for e in mios if e.estado is EstadoEnvio.ENTREGADO]
    contexto = {
        "pestana": "panel",
        "t": transportista,
        "nuevas": [e for e in mios if e.estado is EstadoEnvio.PENDIENTE],
        "en_curso": [
            e for e in mios if e.estado in {EstadoEnvio.CONFIRMADO, EstadoEnvio.EN_TRANSITO}
        ],
        "completados": completados[:COMPLETADOS_VISIBLES],
        "ingresos": sum(e.precio for e in completados),
        "ACCIONES": ACCIONES,
    }
    return renderizar(request, "panel.html", contexto)


@router.get("/registro", response_class=HTMLResponse)
def formulario_de_registro(request: Request) -> HTMLResponse:
    """Formulario para que un transportista publique su perfil."""
    formulario = FormularioRegistro(
        ciudad=Ciudad.QUERETARO,
        vehiculo=TipoVehiculo.CAMIONETA,
        capacidad="1000",
        tarifa="1500",
        categorias=[CategoriaServicio.CARGA_GENERAL],
    )
    return renderizar(request, "registro.html", {"pestana": "perfil", "form": formulario})


@router.post("/registro", response_model=None)
def registrar(
    request: Request, sesion: SesionBD, formulario: Annotated[FormularioRegistro, Form()]
) -> HTMLResponse | RedirectResponse:
    """Publica el perfil y pasa a operar como ese transportista."""
    try:
        datos = DatosRegistro(
            nombre=formulario.nombre,
            ciudad=requerir(Ciudad, formulario.ciudad, "la ciudad base"),
            telefono=formulario.telefono,
            vehiculo=requerir(TipoVehiculo, formulario.vehiculo, "el tipo de vehículo"),
            capacidad_kg=entero(formulario.capacidad, "La capacidad"),
            tarifa_base=entero(formulario.tarifa, "La tarifa base"),
            categorias=tuple(
                c for v in formulario.categorias if (c := opcion(CategoriaServicio, v))
            ),
            zonas=tuple(z for v in formulario.zonas if (z := opcion(Ciudad, v))),
            descripcion=formulario.descripcion,
        )
        transportista = registrar_transportista(sesion, datos)
    except DatosInvalidosError as error:
        contexto = {"pestana": "perfil", "form": formulario, "error": error.mensaje}
        return renderizar(
            request, "registro.html", contexto, status_code=HTTPStatus.UNPROCESSABLE_ENTITY
        )
    respuesta = _redirigir(f"/transportistas/{transportista.id}")
    guardar_preferencias(respuesta, rol=Rol.TRANSPORTISTA, transportista_id=transportista.id)
    avisar(
        respuesta, "Perfil publicado. Queda en revisión hasta que lo verifique un administrador."
    )
    return respuesta


# --------------------------------------------------------------------------- perfil y modos


@router.get("/perfil", response_class=HTMLResponse)
def perfil(request: Request, sesion: SesionBD) -> HTMLResponse:
    """Modo de uso (rol) y datos de la demo."""
    transportista = transportista_actual(sesion, leer_preferencias(request))
    contexto: dict[str, Any] = {
        "pestana": "perfil",
        "transportistas": listar_transportistas(sesion),
        "transportista": transportista,
    }
    return renderizar(request, "perfil.html", contexto)


@router.post("/perfil")
def guardar_perfil(
    request: Request, sesion: SesionBD, formulario: Annotated[FormularioPerfil, Form()]
) -> RedirectResponse:
    """Cambia el nombre de la empresa (en todos sus envíos) y el transportista elegido."""
    preferencias = leer_preferencias(request)
    respuesta = _redirigir("/perfil")
    try:
        transportista: Transportista = obtener_transportista(
            sesion, entero(formulario.transportista, "El transportista")
        )
        empresa = renombrar_cliente(sesion, preferencias.empresa, formulario.empresa)
    except (DatosInvalidosError, RecursoNoEncontradoError) as error:
        avisar(respuesta, error.mensaje, TipoAviso.ERROR)
        return respuesta
    guardar_preferencias(respuesta, empresa=empresa, transportista_id=transportista.id)
    avisar(respuesta, "Cambios guardados")
    return respuesta


@router.post("/perfil/restablecer")
def restablecer(sesion: SesionBD) -> RedirectResponse:
    """Vuelve a cargar los datos de ejemplo (solo si la demo está activada)."""
    if not get_settings().demo_data:
        raise PermisoDenegadoError("Los datos de ejemplo están desactivados en este servidor.")
    restablecer_datos_de_ejemplo(sesion)
    respuesta = _redirigir("/")
    borrar_preferencias(respuesta)
    avisar(respuesta, "Datos de ejemplo restablecidos")
    return respuesta


@router.get("/modo/{rol}")
def cambiar_modo(rol: str, siguiente: str = "") -> RedirectResponse:
    """Usa la plataforma como cliente, transportista o administrador."""
    nuevo = opcion(Rol, rol)
    if nuevo is None:
        raise RecursoNoEncontradoError("Modo", rol)
    respuesta = _redirigir(ruta_local(siguiente, INICIO_DEL_ROL[nuevo]))
    guardar_preferencias(respuesta, rol=nuevo)
    avisar(respuesta, f"Modo {nuevo.etiqueta.lower()} activado")
    return respuesta
