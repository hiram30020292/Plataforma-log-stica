# Plataforma-log-stica

Este proyecto está para conectar un pequeño grupo de transportistas independientes con
pequeñas empresas.

**MCL - Corregidora Móvil Logistics:** backend en Python para la gestión de flotilla y la
logística de MCL. La app móvil (Flutter) se construirá aparte y consumirá esta API.

## Requisitos

- Python 3.12 o superior
- Git

## Instalación

```bash
git clone https://github.com/hiram30020292/plataforma-log-stica.git
cd plataforma-log-stica
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

En Windows, crea el entorno con `py -m venv .venv` y actívalo con `.venv\Scripts\activate`.

Configuración local (opcional): copia `.env.example` como `.env` y edita los valores.
El archivo `.env` nunca se sube al repositorio.

## Verificar que todo funciona

```bash
pytest                 # tests
ruff check .           # estilo y errores comunes
ruff format --check .  # formato
mypy                   # tipos
```

## Estructura

```
src/mcl/
├── core/    configuración, excepciones y tipos compartidos
└── utils/   funciones auxiliares puras
tests/       tests (espejo de src/mcl)
```

Las reglas de arquitectura y de refactorización segura están en [CLAUDE.md](CLAUDE.md).
