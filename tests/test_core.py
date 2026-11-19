"""Tests del núcleo: configuración, excepciones y tipos compartidos."""

from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy import Column, Integer, MetaData, Table, insert, select, text
from sqlalchemy.exc import IntegrityError, StatementError

import mcl
from mcl.core import (
    Actor,
    CategoriaServicio,
    Ciudad,
    ConfiguracionError,
    ConflictoError,
    DatosInvalidosError,
    EnumList,
    EnumText,
    Environment,
    EstadoEnvio,
    MCLError,
    PermisoDenegadoError,
    RecursoNoEncontradoError,
    Rol,
    Settings,
    TipoVehiculo,
    UTCDateTime,
    dispose_engines,
    get_engine,
    get_settings,
    new_session,
)


def test_el_paquete_expone_su_version() -> None:
    assert mcl.__version__ == "0.2.0"


class TestConfiguracion:
    def test_valores_por_defecto_para_desarrollo(self) -> None:
        settings = Settings()

        assert settings.app_name == "MCL - Corregidora Móvil Logistics"
        assert settings.environment is Environment.DEVELOPMENT
        assert settings.debug is False
        assert settings.database_url == "sqlite:///./mcl.db"
        assert settings.smtp_host == "smtp.gmail.com"
        assert settings.smtp_port == 587
        assert settings.email_enabled is False
        assert settings.timezone == "America/Mexico_City"
        assert settings.demo_data is True

    def test_lee_variables_de_entorno_con_prefijo_mcl(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MCL_ENVIRONMENT", "production")
        monkeypatch.setenv("MCL_DATABASE_URL", "postgresql://mcl@localhost:5432/mcl")

        settings = get_settings()

        assert settings.environment is Environment.PRODUCTION
        assert settings.database_url == "postgresql://mcl@localhost:5432/mcl"

    def test_lee_el_archivo_env(self, tmp_path: Path) -> None:
        (tmp_path / ".env").write_text("MCL_DEBUG=true\n", encoding="utf-8")

        assert get_settings().debug is True

    def test_ignora_variables_ajenas_en_el_archivo_env(self, tmp_path: Path) -> None:
        (tmp_path / ".env").write_text("OTRA_HERRAMIENTA=1\nMCL_DEBUG=true\n", encoding="utf-8")

        assert get_settings().debug is True

    def test_get_settings_reutiliza_la_misma_instancia(self) -> None:
        assert get_settings() is get_settings()

    def test_valor_invalido_lanza_configuracion_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MCL_SMTP_PORT", "no-es-un-numero")

        with pytest.raises(ConfiguracionError, match="smtp_port"):
            get_settings()

    def test_usuario_de_gmail_sin_contrasena_es_invalido(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MCL_SMTP_USER", "avisos@example.com")

        with pytest.raises(ConfiguracionError, match="MCL_SMTP_PASSWORD"):
            get_settings()

    def test_el_error_de_configuracion_no_filtra_la_contrasena(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MCL_SMTP_PASSWORD", "supersecreta")

        with pytest.raises(ConfiguracionError) as error:
            get_settings()

        assert "supersecreta" not in str(error.value)

    def test_correo_habilitado_con_usuario_y_contrasena(self) -> None:
        settings = Settings(
            smtp_user="avisos@example.com",
            smtp_password=SecretStr("clave-de-aplicacion"),
        )

        assert settings.email_enabled is True

    def test_la_contrasena_no_aparece_al_imprimir(self) -> None:
        settings = Settings(
            smtp_user="avisos@example.com",
            smtp_password=SecretStr("supersecreta"),
        )

        assert "supersecreta" not in repr(settings)
        assert "supersecreta" not in str(settings)

    def test_la_zona_horaria_se_convierte_en_zoneinfo(self) -> None:
        settings = Settings(timezone="America/Monterrey")

        assert settings.tz.key == "America/Monterrey"

    def test_zona_horaria_desconocida_es_invalida(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MCL_TIMEZONE", "Marte/Olympus")

        with pytest.raises(ConfiguracionError, match="MCL_TIMEZONE"):
            get_settings()

    def test_los_datos_de_ejemplo_se_pueden_apagar(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MCL_DEMO_DATA", "false")

        assert get_settings().demo_data is False

    def test_la_configuracion_es_inmutable(self) -> None:
        settings = Settings()

        with pytest.raises(ValidationError):
            settings.debug = True  # type: ignore[misc]  # mypy también lo prohíbe: es el punto


class TestExcepciones:
    @pytest.mark.parametrize(
        "excepcion",
        [ConfiguracionError, ConflictoError, DatosInvalidosError, PermisoDenegadoError],
    )
    def test_heredan_de_mcl_error_y_guardan_el_mensaje(self, excepcion: type[MCLError]) -> None:
        error = excepcion("algo salió mal")

        assert isinstance(error, MCLError)
        assert error.mensaje == "algo salió mal"
        assert str(error) == "algo salió mal"

    def test_recurso_no_encontrado_describe_el_recurso(self) -> None:
        error = RecursoNoEncontradoError("Vehículo", 42)

        assert isinstance(error, MCLError)
        assert error.recurso == "Vehículo"
        assert error.identificador == 42
        assert error.mensaje == "Vehículo con identificador 42 no existe."

    def test_cada_excepcion_tiene_un_codigo_unico(self) -> None:
        clases: list[type[MCLError]] = [MCLError, *MCLError.__subclasses__()]
        codigos = [clase.codigo for clase in clases]

        assert len(codigos) == len(set(codigos))


class TestTiposCompartidos:
    """Los valores de texto son el contrato con la app móvil: estos tests evitan cambiarlos
    por accidente."""

    def test_categorias_de_servicio(self) -> None:
        assert [c.value for c in CategoriaServicio] == [
            "carga_general",
            "paqueteria",
            "mudanzas",
            "carga_pesada",
        ]

    def test_estados_de_envio(self) -> None:
        assert [e.value for e in EstadoEnvio] == [
            "pendiente",
            "confirmado",
            "en_transito",
            "entregado",
            "cancelado",
            "rechazado",
        ]

    def test_ciudades(self) -> None:
        assert [c.value for c in Ciudad] == [
            "queretaro",
            "cdmx",
            "guadalajara",
            "monterrey",
            "puebla",
            "leon",
            "san_luis_potosi",
        ]

    def test_tipos_de_vehiculo(self) -> None:
        assert [v.value for v in TipoVehiculo] == ["camioneta", "van", "camion", "trailer"]

    def test_roles(self) -> None:
        assert [r.value for r in Rol] == ["cliente", "transportista", "administrador"]

    def test_se_construyen_desde_el_texto_que_envia_la_app(self) -> None:
        assert CategoriaServicio("paqueteria") is CategoriaServicio.PAQUETERIA
        assert EstadoEnvio("en_transito") is EstadoEnvio.EN_TRANSITO

    @pytest.mark.parametrize(
        "etiquetas",
        [
            [c.etiqueta for c in CategoriaServicio],
            [e.etiqueta for e in EstadoEnvio],
            [c.etiqueta for c in Ciudad],
            [v.etiqueta for v in TipoVehiculo],
            [r.etiqueta for r in Rol],
        ],
    )
    def test_cada_valor_tiene_un_nombre_para_mostrar(self, etiquetas: list[str]) -> None:
        assert all(etiquetas)
        assert len(set(etiquetas)) == len(etiquetas)

    def test_etiquetas_con_acentos(self) -> None:
        assert Ciudad.QUERETARO.etiqueta == "Querétaro"
        assert TipoVehiculo.TRAILER.etiqueta == "Tráiler"
        assert EstadoEnvio.EN_TRANSITO.etiqueta == "En tránsito"

    @pytest.mark.parametrize(
        ("estado", "activo"),
        [
            (EstadoEnvio.PENDIENTE, True),
            (EstadoEnvio.CONFIRMADO, True),
            (EstadoEnvio.EN_TRANSITO, True),
            (EstadoEnvio.ENTREGADO, False),
            (EstadoEnvio.CANCELADO, False),
            (EstadoEnvio.RECHAZADO, False),
        ],
    )
    def test_estados_activos(self, estado: EstadoEnvio, activo: bool) -> None:
        assert estado.activo is activo

    def test_actor_por_defecto_no_representa_a_nadie(self) -> None:
        actor = Actor(rol=Rol.ADMINISTRADOR)

        assert actor.empresa == ""
        assert actor.transportista_id is None


class TestBaseDeDatos:
    def _tabla(self) -> Table:
        return Table(
            "pruebas",
            MetaData(),
            Column("id", Integer, primary_key=True),
            Column("momento", UTCDateTime()),
            Column("ciudad", EnumText(Ciudad)),
            Column("zonas", EnumList(Ciudad)),
        )

    def test_las_fechas_se_guardan_en_utc_y_vuelven_con_zona(self) -> None:
        tabla = self._tabla()
        tabla.metadata.create_all(get_engine())
        en_mexico = datetime(2026, 11, 18, 12, 0, tzinfo=timezone(timedelta(hours=-6)))

        with get_engine().begin() as conexion:
            conexion.execute(insert(tabla).values(id=1, momento=en_mexico))
            guardado = conexion.execute(select(tabla.c.momento)).scalar_one()

        assert guardado == datetime(2026, 11, 18, 18, 0, tzinfo=UTC)
        assert guardado.tzinfo is UTC

    def test_una_fecha_sin_zona_no_se_guarda(self) -> None:
        tabla = self._tabla()
        tabla.metadata.create_all(get_engine())
        ingenua = datetime(2026, 11, 18, 12, 0, tzinfo=UTC).replace(tzinfo=None)

        with get_engine().begin() as conexion, pytest.raises(StatementError, match="zona"):
            conexion.execute(insert(tabla).values(id=1, momento=ingenua))

    def test_los_enums_se_guardan_como_texto(self) -> None:
        tabla = self._tabla()
        tabla.metadata.create_all(get_engine())

        with get_engine().begin() as conexion:
            conexion.execute(
                insert(tabla).values(id=1, ciudad=Ciudad.LEON, zonas=[Ciudad.LEON, Ciudad.CDMX])
            )
            crudo = conexion.execute(text("SELECT ciudad, zonas FROM pruebas")).one()
            fila = conexion.execute(select(tabla.c.ciudad, tabla.c.zonas)).one()

        assert crudo.ciudad == "leon"
        assert fila.ciudad is Ciudad.LEON
        assert fila.zonas == [Ciudad.LEON, Ciudad.CDMX]

    def test_un_motor_por_url_y_se_cierra_entre_tests(self) -> None:
        motor = get_engine()

        assert get_engine() is motor
        dispose_engines()
        assert get_engine() is not motor

    def test_sqlite_respeta_las_claves_foraneas(self) -> None:
        with new_session() as sesion:
            sesion.execute(text("CREATE TABLE padres (id INTEGER PRIMARY KEY)"))
            sesion.execute(
                text("CREATE TABLE hijos (id INTEGER PRIMARY KEY, padre INTEGER REFERENCES padres)")
            )
            with pytest.raises(IntegrityError):
                sesion.execute(text("INSERT INTO hijos (id, padre) VALUES (1, 99)"))
