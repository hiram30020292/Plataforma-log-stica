"""Geometría de las gráficas SVG: la calcula Python y las plantillas solo la dibujan."""

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Punto:
    """Coordenadas dentro del lienzo SVG."""

    x: float
    y: float


@dataclass(frozen=True, slots=True)
class Marca:
    """Texto de un eje con su posición."""

    x: float
    y: float
    texto: str
    ancla: str = "middle"


@dataclass(frozen=True, slots=True)
class GraficaLineas:
    """Serie de valores dibujada como línea con área sombreada."""

    ancho: int
    alto: int
    izquierda: float
    derecha: float
    linea: str
    area: str
    rejilla: tuple[Marca, ...]
    etiquetas: tuple[Marca, ...]
    ultimo: Punto


@dataclass(frozen=True, slots=True)
class Segmento:
    """Porción de la gráfica de dona."""

    clase: str
    etiqueta: str
    valor: int
    trazo: float
    desplazamiento: float


@dataclass(frozen=True, slots=True)
class GraficaDona:
    """Gráfica de dona con su leyenda."""

    radio: float
    circunferencia: float
    total: int
    segmentos: tuple[Segmento, ...]
    leyenda: tuple[Segmento, ...]


@dataclass(frozen=True, slots=True)
class MapaRuta:
    """Ruta curva de origen a destino y la posición estimada del vehículo."""

    trazo: str
    origen: Punto
    destino: Punto
    avance: float
    vehiculo: Punto | None


_ANCHO, _ALTO = 560, 200
_MARGEN_IZQ, _MARGEN_DER, _MARGEN_SUP, _MARGEN_INF = 34, 12, 14, 26
_CADA_CUANTAS_ETIQUETAS = 4
_MINIMO_DE_PUNTOS = 2
_RADIO_DONA = 52
_SEPARACION_DONA = 2
_ORIGEN_MAPA, _DESTINO_MAPA = Punto(30, 70), Punto(290, 30)


def grafica_de_lineas(valores: Sequence[int], etiquetas: Sequence[str]) -> GraficaLineas:
    """Calcula la línea, el área, la rejilla y las etiquetas de una serie."""
    if len(valores) < _MINIMO_DE_PUNTOS or len(valores) != len(etiquetas):
        msg = "Se necesitan al menos dos valores, cada uno con su etiqueta."
        raise ValueError(msg)
    maximo = max(4, math.ceil(max(valores) / 2) * 2)
    alto_util = _ALTO - _MARGEN_SUP - _MARGEN_INF
    paso = (_ANCHO - _MARGEN_IZQ - _MARGEN_DER) / (len(valores) - 1)

    def x(i: int) -> float:
        return round(_MARGEN_IZQ + i * paso, 1)

    def y(valor: float) -> float:
        return round(_ALTO - _MARGEN_INF - valor / maximo * alto_util, 1)

    linea = "".join(f"{'L' if i else 'M'}{x(i)} {y(valor)}" for i, valor in enumerate(valores))
    ultimo = len(valores) - 1
    return GraficaLineas(
        ancho=_ANCHO,
        alto=_ALTO,
        izquierda=_MARGEN_IZQ,
        derecha=_ANCHO - _MARGEN_DER,
        linea=linea,
        area=f"{linea}L{x(ultimo)} {y(0)}L{x(0)} {y(0)}Z",
        rejilla=tuple(
            Marca(x=_MARGEN_IZQ - 8, y=y(t), texto=f"{t:g}", ancla="end")
            for t in (0, maximo / 2, maximo)
        ),
        etiquetas=tuple(
            Marca(x=x(i), y=_ALTO - 6, texto=texto, ancla="end" if i == ultimo else "middle")
            for i, texto in enumerate(etiquetas)
            if i % _CADA_CUANTAS_ETIQUETAS == 0 or i == ultimo
        ),
        ultimo=Punto(x(ultimo), y(valores[ultimo])),
    )


def grafica_de_dona(partes: Sequence[tuple[str, str, int]]) -> GraficaDona:
    """Calcula los segmentos de una dona a partir de ``(clase, etiqueta, valor)``."""
    total = sum(valor for _, _, valor in partes)
    circunferencia = 2 * math.pi * _RADIO_DONA
    leyenda: list[Segmento] = []
    acumulado = 0.0
    for clase, etiqueta, valor in partes:
        largo = valor / total * circunferencia if total else 0.0
        leyenda.append(
            Segmento(
                clase=clase,
                etiqueta=etiqueta,
                valor=valor,
                trazo=round(max(0.0, largo - _SEPARACION_DONA), 2),
                desplazamiento=round(-acumulado, 2),
            )
        )
        acumulado += largo
    return GraficaDona(
        radio=_RADIO_DONA,
        circunferencia=round(circunferencia, 2),
        total=total,
        segmentos=tuple(s for s in leyenda if s.valor),
        leyenda=tuple(leyenda),
    )


def mapa_de_ruta(avance: float) -> MapaRuta:
    """Curva de origen a destino; el vehículo aparece solo mientras va en camino."""
    a, b = _ORIGEN_MAPA, _DESTINO_MAPA
    control = Punto((a.x + b.x) / 2, min(a.y, b.y) - 40)

    def punto(t: float) -> Punto:
        return Punto(
            round((1 - t) ** 2 * a.x + 2 * (1 - t) * t * control.x + t**2 * b.x, 1),
            round((1 - t) ** 2 * a.y + 2 * (1 - t) * t * control.y + t**2 * b.y, 1),
        )

    return MapaRuta(
        trazo=f"M{a.x:g} {a.y:g}Q{control.x:g} {control.y:g} {b.x:g} {b.y:g}",
        origen=a,
        destino=b,
        avance=round(avance, 3),
        vehiculo=punto(avance) if 0 < avance < 1 else None,
    )
