"""Tests de cotizaciones, solicitudes y ciclo de vida de los envíos."""

from dataclasses import replace
from datetime import date, datetime, timedelta

import pytest
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
)
from mcl.demo import CLIENTE_DE_EJEMPLO
from mcl.envios import (
    COORDENADAS,
    DatosSolicitud,
    Envio,
    acciones_disponibles,
    avance_estimado,
    cambiar_estado,
    contar_entregados,
    cotizar,
    crear_solicitud,
    distancia_km,
    envios_del_cliente,
    envios_del_transportista,
    envios_por_transportista,
    listar_envios,
    obtener_envio,
    renombrar_cliente,
)

CLIENTE = Actor(rol=Rol.CLIENTE, empresa=CLIENTE_DE_EJEMPLO)
ADMIN = Actor(rol=Rol.ADMINISTRADOR)

SOLICITUD = DatosSolicitud(
    transportista_id=2,
    origen=Ciudad.QUERETARO,
    destino=Ciudad.LEON,
    categoria=CategoriaServicio.PAQUETERIA,
    peso_kg=900,
    fecha_entrega=date(2026, 11, 25),
    notas="  20 cajas  ",
)


def _transportista_de(envio: Envio) -> Actor:
    return Actor(rol=Rol.TRANSPORTISTA, transportista_id=envio.transportista_id)


def _del_cliente(sesion: Session, estado: EstadoEnvio) -> Envio:
    return next(e for e in envios_del_cliente(sesion, CLIENTE_DE_EJEMPLO) if e.estado is estado)


class TestCotizacion:
    def test_cada_ciudad_tiene_coordenadas(self) -> None:
        assert set(COORDENADAS) == set(Ciudad)

    def test_distancia_por_carretera(self) -> None:
        assert distancia_km(Ciudad.QUERETARO, Ciudad.CDMX) == 230
        assert distancia_km(Ciudad.CDMX, Ciudad.QUERETARO) == 230

    def test_dentro_de_la_misma_ciudad(self) -> None:
        assert distancia_km(Ciudad.PUEBLA, Ciudad.PUEBLA) == 25

    def test_formula_del_precio(self, sesion_demo: Session) -> None:
        lopez = obtener_transportista(sesion_demo, 1)

        cotizacion = cotizar(lopez, Ciudad.QUERETARO, Ciudad.CDMX, 2000)

        # 2200 + 230 km x 22 $/km x (0.8 + 0.4 x 2000/30000) = 6382.9 → múltiplo de 50
        assert cotizacion.distancia_km == 230
        assert cotizacion.precio == 6400
        assert cotizacion.valida

    def test_un_vehiculo_lleno_cuesta_mas(self, sesion_demo: Session) -> None:
        lopez = obtener_transportista(sesion_demo, 1)

        vacio = cotizar(lopez, Ciudad.QUERETARO, Ciudad.MONTERREY, 100)
        lleno = cotizar(lopez, Ciudad.QUERETARO, Ciudad.MONTERREY, 30_000)

        assert lleno.precio > vacio.precio

    @pytest.mark.parametrize(
        ("viaje", "mensaje"),
        [
            ((Ciudad.QUERETARO, Ciudad.CDMX, 1600, None), "supera la capacidad"),
            ((Ciudad.QUERETARO, Ciudad.CDMX, 0, None), "mayor a cero"),
            ((Ciudad.CDMX, Ciudad.CDMX, 500, None), "distintos"),
            ((Ciudad.QUERETARO, Ciudad.CDMX, 500, CategoriaServicio.CARGA_PESADA), "no ofrece"),
        ],
    )
    def test_advertencias(
        self,
        sesion_demo: Session,
        viaje: tuple[Ciudad, Ciudad, int, CategoriaServicio | None],
        mensaje: str,
    ) -> None:
        express = obtener_transportista(sesion_demo, 3)

        cotizacion = cotizar(express, *viaje)

        assert not cotizacion.valida
        assert any(mensaje in a for a in cotizacion.advertencias)


class TestSolicitud:
    def test_crea_la_solicitud_pendiente(self, sesion_demo: Session, ahora: datetime) -> None:
        envio = crear_solicitud(sesion_demo, SOLICITUD, " Mi Empresa ", ahora)

        guardado = obtener_envio(sesion_demo, envio.id)
        assert guardado.folio == f"S-{1000 + envio.id}"
        assert guardado.cliente == "Mi Empresa"
        assert guardado.estado is EstadoEnvio.PENDIENTE
        assert guardado.notas == "20 cajas"
        assert guardado.creado_en == ahora
        assert [e.estado for e in guardado.historial] == [EstadoEnvio.PENDIENTE]
        rapidos = obtener_transportista(sesion_demo, 2)
        esperado = cotizar(rapidos, Ciudad.QUERETARO, Ciudad.LEON, 900)
        assert (guardado.precio, guardado.distancia_km) == (
            esperado.precio,
            esperado.distancia_km,
        )

    @pytest.mark.parametrize(
        ("datos", "cliente", "mensaje"),
        [
            (replace(SOLICITUD, fecha_entrega=date(2026, 11, 18)), "Mi Empresa", "mañana"),
            (SOLICITUD, "   ", "nombre de la empresa"),
            (SOLICITUD, "x" * 61, "60 caracteres"),
            (replace(SOLICITUD, notas="x" * 501), "Mi Empresa", "500 caracteres"),
            (replace(SOLICITUD, peso_kg=5001), "Mi Empresa", "capacidad"),
            (replace(SOLICITUD, destino=Ciudad.QUERETARO), "Mi Empresa", "distintos"),
            (replace(SOLICITUD, categoria=CategoriaServicio.MUDANZAS), "Mi Empresa", "no ofrece"),
        ],
    )
    def test_datos_invalidos(
        self,
        sesion_demo: Session,
        ahora: datetime,
        datos: DatosSolicitud,
        cliente: str,
        mensaje: str,
    ) -> None:
        with pytest.raises(DatosInvalidosError, match=mensaje):
            crear_solicitud(sesion_demo, datos, cliente, ahora)

    def test_transportista_inexistente(self, sesion_demo: Session, ahora: datetime) -> None:
        with pytest.raises(RecursoNoEncontradoError):
            crear_solicitud(sesion_demo, replace(SOLICITUD, transportista_id=99), "Yo", ahora)


class TestCicloDeVida:
    def test_el_transportista_lleva_el_envio_hasta_la_entrega(
        self, sesion_demo: Session, ahora: datetime
    ) -> None:
        envio = _del_cliente(sesion_demo, EstadoEnvio.PENDIENTE)
        transportista = _transportista_de(envio)

        for paso, estado in enumerate(
            [EstadoEnvio.CONFIRMADO, EstadoEnvio.EN_TRANSITO, EstadoEnvio.ENTREGADO], start=1
        ):
            cambiar_estado(
                sesion_demo, envio.id, estado, transportista, ahora + timedelta(hours=paso)
            )

        assert envio.estado is EstadoEnvio.ENTREGADO
        assert [e.estado for e in envio.historial] == [
            EstadoEnvio.PENDIENTE,
            EstadoEnvio.CONFIRMADO,
            EstadoEnvio.EN_TRANSITO,
            EstadoEnvio.ENTREGADO,
        ]
        assert envio.momento_de(EstadoEnvio.ENTREGADO) == ahora + timedelta(hours=3)

    def test_el_transportista_puede_rechazar(self, sesion_demo: Session) -> None:
        envio = _del_cliente(sesion_demo, EstadoEnvio.PENDIENTE)

        cambiar_estado(sesion_demo, envio.id, EstadoEnvio.RECHAZADO, _transportista_de(envio))

        assert envio.estado is EstadoEnvio.RECHAZADO

    def test_el_cliente_cancela_mientras_esta_pendiente(self, sesion_demo: Session) -> None:
        envio = _del_cliente(sesion_demo, EstadoEnvio.PENDIENTE)

        cambiar_estado(sesion_demo, envio.id, EstadoEnvio.CANCELADO, CLIENTE)

        assert envio.estado is EstadoEnvio.CANCELADO

    def test_el_cliente_ya_no_cancela_un_envio_confirmado(self, sesion_demo: Session) -> None:
        envio = _del_cliente(sesion_demo, EstadoEnvio.CONFIRMADO)

        with pytest.raises(ConflictoError, match="ya no se puede"):
            cambiar_estado(sesion_demo, envio.id, EstadoEnvio.CANCELADO, CLIENTE)

    def test_el_cliente_no_acepta_viajes(self, sesion_demo: Session) -> None:
        envio = _del_cliente(sesion_demo, EstadoEnvio.PENDIENTE)

        with pytest.raises(PermisoDenegadoError, match="cliente"):
            cambiar_estado(sesion_demo, envio.id, EstadoEnvio.CONFIRMADO, CLIENTE)

    def test_otro_cliente_no_toca_el_envio(self, sesion_demo: Session) -> None:
        envio = _del_cliente(sesion_demo, EstadoEnvio.PENDIENTE)
        ajeno = Actor(rol=Rol.CLIENTE, empresa="Otra Empresa")

        with pytest.raises(PermisoDenegadoError):
            cambiar_estado(sesion_demo, envio.id, EstadoEnvio.CANCELADO, ajeno)

    def test_otro_transportista_no_toca_el_envio(self, sesion_demo: Session) -> None:
        envio = _del_cliente(sesion_demo, EstadoEnvio.PENDIENTE)
        otro = Actor(rol=Rol.TRANSPORTISTA, transportista_id=envio.transportista_id + 1)

        with pytest.raises(PermisoDenegadoError):
            cambiar_estado(sesion_demo, envio.id, EstadoEnvio.CONFIRMADO, otro)

    def test_no_se_salta_etapas(self, sesion_demo: Session) -> None:
        envio = _del_cliente(sesion_demo, EstadoEnvio.PENDIENTE)

        with pytest.raises(ConflictoError):
            cambiar_estado(sesion_demo, envio.id, EstadoEnvio.ENTREGADO, _transportista_de(envio))

    def test_el_mismo_estado_es_un_conflicto(self, sesion_demo: Session) -> None:
        envio = _del_cliente(sesion_demo, EstadoEnvio.PENDIENTE)

        with pytest.raises(ConflictoError, match="ya está pendiente"):
            cambiar_estado(sesion_demo, envio.id, EstadoEnvio.PENDIENTE, ADMIN)

    def test_el_administrador_corrige_cualquier_estado(self, sesion_demo: Session) -> None:
        envio = _del_cliente(sesion_demo, EstadoEnvio.ENTREGADO)

        cambiar_estado(sesion_demo, envio.id, EstadoEnvio.EN_TRANSITO, ADMIN)

        assert envio.estado is EstadoEnvio.EN_TRANSITO

    def test_envio_inexistente(self, sesion_demo: Session) -> None:
        with pytest.raises(RecursoNoEncontradoError):
            cambiar_estado(sesion_demo, 999, EstadoEnvio.CANCELADO, ADMIN)


class TestAccionesDisponibles:
    def test_segun_el_rol_y_la_etapa(self, sesion_demo: Session) -> None:
        pendiente = _del_cliente(sesion_demo, EstadoEnvio.PENDIENTE)
        en_transito = _del_cliente(sesion_demo, EstadoEnvio.EN_TRANSITO)
        entregado = _del_cliente(sesion_demo, EstadoEnvio.ENTREGADO)

        assert acciones_disponibles(pendiente, CLIENTE) == (EstadoEnvio.CANCELADO,)
        assert acciones_disponibles(pendiente, _transportista_de(pendiente)) == (
            EstadoEnvio.RECHAZADO,
            EstadoEnvio.CONFIRMADO,
        )
        assert acciones_disponibles(en_transito, ADMIN) == (EstadoEnvio.ENTREGADO,)
        assert acciones_disponibles(en_transito, CLIENTE) == ()
        assert acciones_disponibles(entregado, _transportista_de(entregado)) == ()

    def test_quien_no_participa_no_tiene_acciones(self, sesion_demo: Session) -> None:
        pendiente = _del_cliente(sesion_demo, EstadoEnvio.PENDIENTE)

        assert acciones_disponibles(pendiente, Actor(rol=Rol.CLIENTE, empresa="Otra")) == ()
        assert acciones_disponibles(pendiente, Actor(rol=Rol.TRANSPORTISTA)) == ()


class TestConsultas:
    def test_del_mas_reciente_al_mas_antiguo(self, sesion_demo: Session) -> None:
        envios = listar_envios(sesion_demo)

        assert len(envios) == 50
        fechas = [e.creado_en for e in envios]
        assert fechas == sorted(fechas, reverse=True)

    def test_envios_del_cliente(self, sesion_demo: Session) -> None:
        mios = envios_del_cliente(sesion_demo, CLIENTE_DE_EJEMPLO)

        assert [e.estado for e in mios] == [
            EstadoEnvio.PENDIENTE,
            EstadoEnvio.CONFIRMADO,
            EstadoEnvio.EN_TRANSITO,
            EstadoEnvio.ENTREGADO,
        ]

    def test_envios_del_transportista_y_conteos(self, sesion_demo: Session) -> None:
        de_lopez = envios_del_transportista(sesion_demo, 1)
        conteo = envios_por_transportista(sesion_demo)

        assert all(e.transportista_id == 1 for e in de_lopez)
        assert conteo[1] == len(de_lopez)
        assert sum(conteo.values()) == 50
        assert contar_entregados(sesion_demo, 1) == sum(
            e.estado is EstadoEnvio.ENTREGADO for e in de_lopez
        )

    def test_renombrar_cliente_en_todos_sus_envios(self, sesion_demo: Session) -> None:
        nuevo = renombrar_cliente(sesion_demo, CLIENTE_DE_EJEMPLO, "  Abarrotes   Pérez ")

        assert nuevo == "Abarrotes Pérez"
        assert envios_del_cliente(sesion_demo, CLIENTE_DE_EJEMPLO) == []
        assert len(envios_del_cliente(sesion_demo, "Abarrotes Pérez")) == 4

    @pytest.mark.parametrize(("nombre", "mensaje"), [("  ", "nombre"), ("x" * 61, "60")])
    def test_renombrar_con_nombre_invalido(
        self, sesion_demo: Session, nombre: str, mensaje: str
    ) -> None:
        with pytest.raises(DatosInvalidosError, match=mensaje):
            renombrar_cliente(sesion_demo, CLIENTE_DE_EJEMPLO, nombre)


class TestAvanceEstimado:
    def test_segun_la_etapa(self, sesion_demo: Session, ahora: datetime) -> None:
        assert avance_estimado(_del_cliente(sesion_demo, EstadoEnvio.PENDIENTE), ahora) == 0
        assert avance_estimado(_del_cliente(sesion_demo, EstadoEnvio.CONFIRMADO), ahora) == 0
        assert avance_estimado(_del_cliente(sesion_demo, EstadoEnvio.ENTREGADO), ahora) == 1

    def test_en_transito_avanza_con_el_tiempo(self, sesion_demo: Session, ahora: datetime) -> None:
        envio = _del_cliente(sesion_demo, EstadoEnvio.EN_TRANSITO)

        ahora_mismo = avance_estimado(envio, ahora)
        manana = avance_estimado(envio, ahora + timedelta(days=1))

        assert 0.08 <= ahora_mismo < manana <= 0.92

    def test_en_transito_nunca_toca_los_extremos(
        self, sesion_demo: Session, ahora: datetime
    ) -> None:
        envio = _del_cliente(sesion_demo, EstadoEnvio.EN_TRANSITO)

        assert avance_estimado(envio, ahora - timedelta(days=30)) == 0.08
        assert avance_estimado(envio, ahora + timedelta(days=30)) == 0.92
