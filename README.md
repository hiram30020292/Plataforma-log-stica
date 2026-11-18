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
git clone https://github.com/hiram30020292/Plataforma-log-stica.git
cd Plataforma-log-stica
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

En Windows, crea el entorno con `py -m venv .venv` y actívalo con `.venv\Scripts\activate`.

Configuración local (opcional): copia `.env.example` como `.env` y edita los valores.
El archivo `.env` nunca se sube al repositorio.

## Ejecutar la API

```bash
uvicorn mcl.api:create_app --factory --reload
```

Con el servidor encendido, abre en el navegador:

- http://127.0.0.1:8000/health: estado del servicio.
- http://127.0.0.1:8000/docs: documentación interactiva para probar la API.

Para detenerlo, pulsa `Ctrl+C`.

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
├── api/     API con FastAPI (rutas y respuestas de error)
├── core/    configuración, excepciones y tipos compartidos
└── utils/   funciones auxiliares puras
tests/       tests (espejo de src/mcl)
```

Las reglas de arquitectura y de refactorización segura están en [CLAUDE.md](CLAUDE.md).
