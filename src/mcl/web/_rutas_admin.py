"""Panel administrativo: indicadores, todas las solicitudes y verificación de transportistas.

En esta demo, entrar al panel equivale a actuar como administrador: sus acciones se
registran con el rol de administrador sin importar el modo elegido en la app.
"""

from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from mcl.catalogo import cambiar_destacado, cambiar_verificacion, listar_transportistas
from mcl.core import (
    Actor,
    ConflictoError,
    DatosInvalidosError,
    EstadoEnvio,
    PermisoDenegadoError,
    Rol,
    get_session,
)
from mcl.envios import cambiar_estado, envios_por_transportista, listar_envios
from mcl.reportes import indicadores
from mcl.web._formato import dia_mes
from mcl.web._formularios import FormularioEstado, FormularioMarca, requerir
from mcl.web._graficas import grafica_de_dona, grafica_de_lineas
from mcl.web._plantillas import CLASE_ESTADO, renderizar
from mcl.web._sesion import TipoAviso, avisar

router = APIRouter(prefix="/admin", include_in_schema=False)

SesionBD = Annotated[Session, Depends(get_session)]

ADMINISTRADOR = Actor(rol=Rol.ADMINISTRADOR)
RECIENTES_EN_EL_TABLERO = 6
# Segmentos de la dona: cancelados y rechazados se agrupan.
_PARTES_DE_LA_DONA = (
    (EstadoEnvio.PENDIENTE,),
    (EstadoEnvio.CONFIRMADO,),
    (EstadoEnvio.EN_TRANSITO,),
    (EstadoEnvio.ENTREGADO,),
    (EstadoEnvio.CANCELADO, EstadoEnvio.RECHAZADO),
)


def _redirigir(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=HTTPStatus.SEE_OTHER)


@router.get("", response_class=HTMLResponse)
def tablero(request: Request, sesion: SesionBD) -> HTMLResponse:
    """Indicadores, gráficas, solicitudes recientes y mejores transportistas."""
    datos = indicadores(sesion)
    serie = datos.serie_diaria
    contexto = {
        "seccion": "tablero",
        "datos": datos,
        "lineas": grafica_de_lineas(
            [p.solicitudes for p in serie], [dia_mes(p.fecha) for p in serie]
        ),
        "dona": grafica_de_dona(
            [
                (
                    CLASE_ESTADO[estados[0]],
                    " / ".join(e.etiqueta for e in estados),
                    sum(datos.por_estado[e] for e in estados),
                )
                for estados in _PARTES_DE_LA_DONA
            ]
        ),
        "recientes": listar_envios(sesion)[:RECIENTES_EN_EL_TABLERO],
    }
    return renderizar(request, "admin_tablero.html", contexto)


@router.get("/envios", response_class=HTMLResponse)
def solicitudes(request: Request, sesion: SesionBD) -> HTMLResponse:
    """Todas las solicitudes, con su estado editable."""
    contexto = {"seccion": "envios", "envios": listar_envios(sesion)}
    return renderizar(request, "admin_envios.html", contexto)


@router.post("/envios/{envio_id}/estado")
def corregir_estado(
    sesion: SesionBD, envio_id: int, formulario: Annotated[FormularioEstado, Form()]
) -> RedirectResponse:
    """El administrador corrige el estado de cualquier envío."""
    respuesta = _redirigir("/admin/envios")
    try:
        estado = requerir(EstadoEnvio, formulario.estado, "el nuevo estado")
        envio = cambiar_estado(sesion, envio_id, estado, ADMINISTRADOR)
    except (ConflictoError, DatosInvalidosError, PermisoDenegadoError) as error:
        avisar(respuesta, error.mensaje, TipoAviso.ERROR)
    else:
        avisar(respuesta, f"{envio.folio}: {estado.etiqueta}")
    return respuesta


@router.get("/transportistas", response_class=HTMLResponse)
def transportistas(request: Request, sesion: SesionBD) -> HTMLResponse:
    """Transportistas con interruptores para verificarlos y destacarlos."""
    contexto = {
        "seccion": "transportistas",
        "transportistas": listar_transportistas(sesion),
        "solicitudes": envios_por_transportista(sesion),
    }
    return renderizar(request, "admin_transportistas.html", contexto)


@router.post("/transportistas/{transportista_id}/marcas")
def cambiar_marca(
    sesion: SesionBD, transportista_id: int, formulario: Annotated[FormularioMarca, Form()]
) -> RedirectResponse:
    """Enciende o apaga la verificación o el destacado de un transportista."""
    respuesta = _redirigir("/admin/transportistas")
    activado = formulario.activado
    if formulario.campo == "verificado":
        t = cambiar_verificacion(sesion, transportista_id, activado, ADMINISTRADOR)
        avisar(respuesta, f"{t.nombre}: {'verificado' if activado else 'sin verificar'}")
    elif formulario.campo == "destacado":
        t = cambiar_destacado(sesion, transportista_id, activado, ADMINISTRADOR)
        avisar(respuesta, f"{t.nombre}: {'destacado' if activado else 'ya no destacado'}")
    else:
        avisar(respuesta, "No se reconoce el cambio solicitado.", TipoAviso.ERROR)
    return respuesta
