"""Tests de las funciones auxiliares puras."""

import pytest

from mcl.utils import haversine_km, normalize_text, round_half_up, round_to_multiple


class TestHaversine:
    def test_misma_coordenada_es_cero(self) -> None:
        assert haversine_km(20.59, -100.39, 20.59, -100.39) == 0

    def test_queretaro_a_cdmx_en_linea_recta(self) -> None:
        assert haversine_km(20.59, -100.39, 19.43, -99.13) == pytest.approx(184, abs=1)

    def test_es_simetrica(self) -> None:
        ida = haversine_km(25.69, -100.32, 19.04, -98.21)
        vuelta = haversine_km(19.04, -98.21, 25.69, -100.32)

        assert ida == pytest.approx(vuelta)


class TestRedondeos:
    @pytest.mark.parametrize(
        ("valor", "esperado"),
        [(2.5, 3), (3.5, 4), (2.49, 2), (-0.5, 0), (-1.5, -1), (7.0, 7)],
    )
    def test_los_empates_suben(self, valor: float, esperado: int) -> None:
        assert round_half_up(valor) == esperado

    @pytest.mark.parametrize(
        ("valor", "multiplo", "esperado"),
        [(2175, 50, 2200), (2174.9, 50, 2150), (6382.9, 50, 6400), (24, 50, 0), (25, 50, 50)],
    )
    def test_redondea_al_multiplo_mas_cercano(
        self, valor: float, multiplo: int, esperado: int
    ) -> None:
        assert round_to_multiple(valor, multiplo) == esperado

    @pytest.mark.parametrize("multiplo", [0, -50])
    def test_el_multiplo_debe_ser_positivo(self, multiplo: int) -> None:
        with pytest.raises(ValueError, match="positivo"):
            round_to_multiple(100, multiplo)


class TestNormalizarTexto:
    @pytest.mark.parametrize(
        ("texto", "esperado"),
        [
            ("Querétaro", "queretaro"),
            ("  San   Luis\tPotosí ", "san luis potosi"),
            ("CAMIÓN", "camion"),
            ("Peña", "pena"),
            ("", ""),
        ],
    )
    def test_quita_mayusculas_acentos_y_espacios(self, texto: str, esperado: str) -> None:
        assert normalize_text(texto) == esperado
