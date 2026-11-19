"""Tests del catálogo de transportistas."""

from dataclasses import replace
from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from mcl.catalogo import (
    ESPECIFICACIONES_VEHICULO,
    DatosRegistro,
    FiltroCatalogo,
    OrdenCatalogo,
    Transportista,
    buscar_transportistas,
    cambiar_destacado,
    cambiar_verificacion,
    filtrar_transportistas,
    listar_transportistas,
    obtener_transportista,
    registrar_transportista,
    transportistas_destacados,
)
from mcl.core import (
    Actor,
    CategoriaServicio,
    Ciudad,
    DatosInvalidosError,
    PermisoDenegadoError,
    RecursoNoEncontradoError,
    Rol,
    TipoVehiculo,
)

ADMIN = Actor(rol=Rol.ADMINISTRADOR)

REGISTRO = DatosRegistro(
    nombre="  Fletes Corregidora ",
    ciudad=Ciudad.QUERETARO,
    telefono="442  111 2233",
    vehiculo=TipoVehiculo.CAMION,
    capacidad_kg=8_000,
    tarifa_base=1900,
    categorias=(CategoriaServicio.CARGA_GENERAL, CategoriaServicio.MUDANZAS),
    zonas=(Ciudad.CDMX, Ciudad.QUERETARO, Ciudad.CDMX),
)


def _nombres(transportistas: list[Transportista]) -> list[str]:
    return [t.nombre for t in transportistas]


class TestTransportista:
    def test_calificacion_es_el_promedio_exacto(self, sesion_demo: Session) -> None:
        lopez = obtener_transportista(sesion_demo, 1)

        assert lopez.calificacion == pytest.approx(4.8)
        lopez.registrar_estrellas(1)
        assert lopez.num_opiniones == 121
        assert lopez.calificacion == pytest.approx(577 / 121)

    def test_sin_opiniones_la_calificacion_es_cero(self, sesion: Session) -> None:
        nuevo = registrar_transportista(sesion, REGISTRO)

        assert nuevo.num_opiniones == 0
        assert nuevo.calificacion == 0

    @pytest.mark.parametrize(
        ("kilos", "texto"), [(30_000, "30 t"), (1_500, "1.5 t"), (1_000, "1 t"), (800, "800 kg")]
    )
    def test_capacidad_para_mostrar(self, sesion: Session, kilos: int, texto: str) -> None:
        datos = replace(REGISTRO, vehiculo=TipoVehiculo.TRAILER, capacidad_kg=kilos)

        nuevo = registrar_transportista(sesion, datos)

        assert nuevo.capacidad == texto

    def test_especificacion_de_su_vehiculo(self, sesion_demo: Session) -> None:
        lopez = obtener_transportista(sesion_demo, 1)

        assert lopez.especificacion == ESPECIFICACIONES_VEHICULO[TipoVehiculo.TRAILER]
        assert lopez.especificacion.capacidad_kg == 30_000

    def test_cada_vehiculo_tiene_especificacion(self) -> None:
        assert set(ESPECIFICACIONES_VEHICULO) == set(TipoVehiculo)


class TestBusqueda:
    def test_sin_filtros_ordena_por_calificacion(self, sesion_demo: Session) -> None:
        resultado = buscar_transportistas(sesion_demo, FiltroCatalogo())

        assert len(resultado) == 8
        assert resultado[0].nombre == "Rápidos del Bajío"
        calificaciones = [t.calificacion for t in resultado]
        assert calificaciones == sorted(calificaciones, reverse=True)

    def test_ordenar_por_menor_precio(self, sesion_demo: Session) -> None:
        resultado = buscar_transportistas(
            sesion_demo, FiltroCatalogo(orden=OrdenCatalogo.MENOR_PRECIO)
        )

        assert resultado[0].nombre == "Paquetería Ágil"
        precios = [t.tarifa_base for t in resultado]
        assert precios == sorted(precios)

    def test_el_texto_ignora_mayusculas_y_acentos(self, sesion_demo: Session) -> None:
        resultado = buscar_transportistas(sesion_demo, FiltroCatalogo(texto="TAPATIOS"))

        assert _nombres(resultado) == ["Fletes Tapatíos"]

    def test_cada_palabra_debe_aparecer(self, sesion_demo: Session) -> None:
        resultado = buscar_transportistas(sesion_demo, FiltroCatalogo(texto="mudanzas puebla"))

        assert _nombres(resultado) == ["Mudanzas Capital"]

    def test_el_texto_busca_en_servicios_y_cobertura(self, sesion_demo: Session) -> None:
        por_servicio = buscar_transportistas(sesion_demo, FiltroCatalogo(texto="paquetería"))
        por_cobertura = buscar_transportistas(sesion_demo, FiltroCatalogo(texto="león"))

        assert "Paquetería Ágil" in _nombres(por_servicio)
        assert set(_nombres(por_cobertura)) == {"Rápidos del Bajío", "Fletes Tapatíos"}

    def test_la_ciudad_incluye_la_cobertura(self, sesion_demo: Session) -> None:
        resultado = buscar_transportistas(sesion_demo, FiltroCatalogo(ciudad=Ciudad.MONTERREY))

        assert set(_nombres(resultado)) == {"Transporte López", "Norte Cargo"}

    def test_filtra_por_categoria_y_vehiculo(self, sesion_demo: Session) -> None:
        filtro = FiltroCatalogo(
            categoria=CategoriaServicio.CARGA_PESADA, vehiculo=TipoVehiculo.TRAILER
        )

        resultado = buscar_transportistas(sesion_demo, filtro)

        assert set(_nombres(resultado)) == {"Transporte López", "Norte Cargo"}

    def test_sin_coincidencias_devuelve_lista_vacia(self, sesion_demo: Session) -> None:
        assert buscar_transportistas(sesion_demo, FiltroCatalogo(texto="helicóptero")) == []

    def test_filtrar_no_necesita_base_de_datos(self, sesion_demo: Session) -> None:
        transportistas = listar_transportistas(sesion_demo)

        resultado = filtrar_transportistas(
            reversed(transportistas), FiltroCatalogo(vehiculo=TipoVehiculo.VAN)
        )

        assert _nombres(resultado) == ["Logística Express", "Paquetería Ágil"]

    def test_destacados_del_mejor_al_peor(self, sesion_demo: Session) -> None:
        destacados = transportistas_destacados(sesion_demo)

        assert _nombres(destacados) == [
            "Rápidos del Bajío",
            "Transporte López",
            "Logística Express",
            "Norte Cargo",
        ]


class TestConsulta:
    def test_obtener_por_identificador(self, sesion_demo: Session) -> None:
        assert obtener_transportista(sesion_demo, 2).nombre == "Rápidos del Bajío"

    def test_transportista_inexistente(self, sesion_demo: Session) -> None:
        with pytest.raises(RecursoNoEncontradoError, match="999"):
            obtener_transportista(sesion_demo, 999)

    def test_listar_en_orden_de_alta(self, sesion_demo: Session) -> None:
        assert [t.id for t in listar_transportistas(sesion_demo)] == list(range(1, 9))


class TestRegistro:
    def test_publica_el_perfil_sin_verificar(self, sesion: Session, ahora: datetime) -> None:
        nuevo = registrar_transportista(sesion, REGISTRO, ahora)

        guardado = obtener_transportista(sesion, nuevo.id)
        assert guardado.nombre == "Fletes Corregidora"
        assert guardado.telefono == "442 111 2233"
        assert guardado.verificado is False
        assert guardado.destacado is False
        assert guardado.creado_en == ahora
        assert 200 <= guardado.tono < 240

    def test_la_ciudad_base_va_primero_en_la_cobertura(self, sesion: Session) -> None:
        nuevo = registrar_transportista(sesion, REGISTRO)

        assert nuevo.zonas == [Ciudad.QUERETARO, Ciudad.CDMX]

    def test_descripcion_por_defecto(self, sesion: Session) -> None:
        nuevo = registrar_transportista(sesion, REGISTRO)

        assert nuevo.descripcion == "Transportista de nuevo ingreso en la plataforma."

    @pytest.mark.parametrize(
        ("datos", "mensaje"),
        [
            (replace(REGISTRO, nombre="   "), "nombre comercial"),
            (replace(REGISTRO, nombre="x" * 41), "40 caracteres"),
            (replace(REGISTRO, telefono="442"), "teléfono"),
            (replace(REGISTRO, telefono="442-abc-12345"), "teléfono"),
            (replace(REGISTRO, capacidad_kg=50), "entre 100 y 10,000 kg"),
            (replace(REGISTRO, capacidad_kg=12_000), "camión debe estar"),
            (replace(REGISTRO, tarifa_base=50), "tarifa base"),
            (replace(REGISTRO, categorias=()), "al menos un servicio"),
            (replace(REGISTRO, descripcion="x" * 501), "descripción"),
        ],
    )
    def test_datos_invalidos(self, sesion: Session, datos: DatosRegistro, mensaje: str) -> None:
        with pytest.raises(DatosInvalidosError, match=mensaje):
            registrar_transportista(sesion, datos)


class TestVerificacion:
    def test_el_administrador_verifica_y_destaca(self, sesion_demo: Session) -> None:
        cambiar_verificacion(sesion_demo, 5, True, ADMIN)
        cambiar_destacado(sesion_demo, 5, True, ADMIN)

        tapatios = obtener_transportista(sesion_demo, 5)
        assert tapatios.verificado is True
        assert tapatios.destacado is True

    def test_tambien_puede_quitar_las_marcas(self, sesion_demo: Session) -> None:
        cambiar_destacado(sesion_demo, 1, False, ADMIN)

        assert "Transporte López" not in _nombres(transportistas_destacados(sesion_demo))

    @pytest.mark.parametrize("rol", [Rol.CLIENTE, Rol.TRANSPORTISTA])
    def test_solo_el_administrador(self, sesion_demo: Session, rol: Rol) -> None:
        with pytest.raises(PermisoDenegadoError):
            cambiar_verificacion(sesion_demo, 5, True, Actor(rol=rol, transportista_id=5))
        with pytest.raises(PermisoDenegadoError):
            cambiar_destacado(sesion_demo, 5, True, Actor(rol=rol, transportista_id=5))
