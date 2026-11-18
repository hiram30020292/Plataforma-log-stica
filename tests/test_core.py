"""Tests del núcleo: configuración, excepciones y tipos compartidos."""

from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

import mcl
from mcl.core import (
    CategoriaServicio,
    ConfiguracionError,
    ConflictoError,
    DatosInvalidosError,
    Environment,
    EstadoEnvio,
    MCLError,
    PermisoDenegadoError,
    RecursoNoEncontradoError,
    Settings,
    get_settings,
)


def test_el_paquete_expone_su_version() -> None:
    assert mcl.__version__ == "0.1.0"


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

    def test_variable_mcl_desconocida_en_env_es_un_error(self, tmp_path: Path) -> None:
        (tmp_path / ".env").write_text("MCL_DEBUGG=true\n", encoding="utf-8")

        with pytest.raises(ConfiguracionError):
            get_settings()

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
        ]

    def test_se_construyen_desde_el_texto_que_envia_la_app(self) -> None:
        assert CategoriaServicio("paqueteria") is CategoriaServicio.PAQUETERIA
        assert EstadoEnvio("en_transito") is EstadoEnvio.EN_TRANSITO
