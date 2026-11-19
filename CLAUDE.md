# CLAUDE.md

Guía del proyecto para Claude y para cualquier persona que trabaje en el código.
Léela antes de hacer cambios y respétala siempre.

## Proyecto

**MCL - Corregidora Móvil Logistics.** Plataforma para conectar a un pequeño grupo de
transportistas independientes con pequeñas empresas. Este repositorio es la plataforma en
Python (aplicación web y API) para:

- **Gestión de flotilla:** vehículos, empleados y licencias, contratos (alquiler, servicios,
  seguros) con avisos de vencimiento, costos y gastos, aprobaciones, firma electrónica,
  encuestas, agenda y reportes de rentabilidad.
- **Marketplace de transporte:** catálogo de transportistas, solicitudes, seguimiento de
  envíos y calificaciones.

Decisiones tomadas:

| Tema | Decisión |
|---|---|
| Interfaz | Aplicación web en Python (FastAPI + Jinja2, `src/mcl/web/`) y API JSON (`src/mcl/api/`) que consumirá la app móvil en Flutter |
| Base de datos | SQLAlchemy + Alembic. SQLite en desarrollo, PostgreSQL en producción (solo cambia `MCL_DATABASE_URL`) |
| Correo | Avisos con Gmail por SMTP, usando una contraseña de aplicación de Google |
| Demo | Sin inicio de sesión todavía: el rol (cliente, transportista, administrador) se elige en la app y se guarda en cookies. La API v1 solo expone lectura y cotizaciones hasta que exista autenticación |

## Comandos

Todo se ejecuta desde la raíz del proyecto:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn mcl.api:create_app --factory --reload  # app en http://127.0.0.1:8000 (API en /docs)
pytest                 # tests
ruff check .           # lint
ruff format --check .  # formato (ruff format . para aplicarlo)
mypy                   # tipos, en modo estricto
```

Un cambio solo está terminado cuando los cuatro checks pasan.

## Arquitectura modular

### Estructura

```
src/mcl/
├── api/       aplicación FastAPI: create_app, API JSON (/api/v1) y respuestas de error
├── web/       interfaz web: rutas, plantillas Jinja2 (templates/) y estáticos (static/)
├── db/        migraciones de Alembic (migrations/versions) y upgrade_database()
├── core/      config.py, database.py (Base, motor, sesiones), exceptions.py, types.py
├── utils/     funciones auxiliares puras
└── <tema>/    un paquete por tema del negocio: catalogo, envios, calificaciones, reportes,
               demo y, más adelante, flotilla, contratos, agenda...
tests/         espejo de src/mcl
```

### Dirección de dependencias

```
api     ──►  web, db, <tema>, core, utils
web     ──►  <tema>, core, utils
db      ──►  <tema>, core
<tema>  ──►  otros <tema>, core, utils
core    ──►  solo core
utils   ──►  nada de mcl (solo la biblioteca estándar)
```

- `api` es la capa más externa: nadie importa de ella. `web` y `db` solo los importa `api`.
  Estas capas solo traducen HTTP ↔ dominio; las reglas de negocio viven en los temas.
- `core` y `utils` nunca importan de un módulo de tema.
- Un tema usa a otro solo a través de su interfaz pública: `from mcl.contratos import Contrato`,
  nunca `from mcl.contratos.servicio import ...`.
- Prohibidas las importaciones circulares. Si dos temas se necesitan mutuamente, lo compartido
  se mueve a `core/types.py` (o se comunican con eventos internos, que se diseñarán en `core`
  cuando hagan falta).
- `tests/test_arquitectura.py` verifica estas reglas automáticamente (capas, interfaz
  pública y ausencia de ciclos).

### Encapsulamiento

- Cada `__init__.py` define `__all__` con su interfaz pública y solo re-exporta: no contiene lógica.
- Lo interno lleva prefijo `_` y no se importa desde fuera de su paquete.
- Imports siempre absolutos (`from mcl.core import get_settings`). Los relativos están
  prohibidos (ruff `TID252`).

### Reglas transversales

- **Configuración:** solo con `mcl.core.get_settings()`. Prohibido `os.environ` y `os.getenv`
  (ruff `TID251`). Las variables llevan prefijo `MCL_`. Los secretos van en `.env`, que nunca
  se sube; `.env.example` documenta las variables sin valores reales.
- **Errores:** toda excepción propia hereda de `MCLError` (`core/exceptions.py`), termina en
  `Error` y tiene un `codigo` estable para la app móvil. `api/app.py` las convierte en JSON
  `{codigo, mensaje}` con su código HTTP, o en una página de error si quien pregunta es un
  navegador en una ruta web; un error interno (500) nunca muestra el detalle al cliente. No se
  lanza `Exception` genérica ni se silencian errores.
- **Base de datos:** los modelos heredan de `mcl.core.Base` (dataclasses de SQLAlchemy). Las
  fechas usan `UTCDateTime` y los enums `EnumText`/`EnumList`. Cada operación de escritura de
  un tema termina con `commit()`. Las rutas obtienen la sesión con `Depends(get_session)`.
- **Tipos:** todo el código lleva anotaciones y pasa `mypy --strict`. Un `# type: ignore`
  necesita código de error y una razón.
- **Fechas:** siempre con zona horaria (ruff `DTZ`).
- **Contrato con la app móvil:** los valores de los enums de `core/types.py` y las respuestas
  de la API no cambian sin versionar.

### Nombres e idioma

- Dominio del negocio en español: `flotilla`, `Contrato`, `EstadoEnvio`.
- Infraestructura técnica en inglés: `core`, `utils`, `config`, `Settings`, `database_url`.
- Identificadores solo en ASCII (sin tildes ni ñ). Docstrings, comentarios y mensajes, en español.

### Tests

- Espejo: `src/mcl/<tema>/` se prueba en `tests/test_<tema>.py`; cuando crezca, en
  `tests/<tema>/test_<archivo>.py`.
- Toda función pública tiene tests.
- Los tests no dependen del `.env` ni de variables reales: `tests/conftest.py` los aísla y
  cada test usa su propia base SQLite en una carpeta temporal (fixtures `sesion`,
  `sesion_demo` y `navegador`).
- La interfaz web se prueba solo con peticiones HTTP (`tests/web/`), nunca importando sus
  módulos internos.

## Refactorización segura

1. **Partir de verde.** Antes de tocar nada, los cuatro checks pasan. Si el comportamiento que
   vas a mover no tiene tests, escríbelos primero.
2. **Pasos pequeños.** Cada paso es *o* un refactor (mismo comportamiento) *o* un cambio de
   funcionalidad, nunca las dos cosas a la vez.
3. **Buscar todos los usos** (`grep -rn "Nombre" src tests`) antes de renombrar, mover o borrar.
4. **Mover sin romper:** crear lo nuevo, migrar los usos y solo entonces borrar lo viejo. Si
   cambia la interfaz pública de un paquete, su `__all__` se actualiza en el mismo paso.
5. **Checks después de cada paso.** Si algo falla, se corrige o se revierte antes de continuar.
6. **Sin trampas:** no se borran ni debilitan tests, ni se añaden `# type: ignore` o `noqa`,
   para que algo pase.
7. **Base de datos:** los cambios de esquema van siempre en migraciones versionadas
   (`alembic revision --autogenerate -m "..."`); `tests/test_db.py` falla si un modelo cambia
   sin su migración. Las migraciones usan tipos estándar de SQLAlchemy, no los de la app.

## Marca (app web y app móvil)

La app web ya la usa (`src/mcl/web/static/mcl.css`). Paleta: `#9F6C52` terracota (botones principales), `#CEB298` arena (etiquetas y chips),
`#EEE7DD` crema (fondo), `#A7B9C6` azul grisáceo claro (bordes y tarjetas), `#82ABBB` azul
grisáceo (encabezados y menú activo). Sobre `#82ABBB` va texto oscuro.

## Hoja de ruta

1. ✅ Base del proyecto: `core`, `utils`, API mínima (`GET /health`), tests y herramientas.
2. ✅ Marketplace (del prototipo LogiConecta): `catalogo`, `envios` (solicitud → envío con
   seguimiento), `calificaciones`, `reportes` (tablero), `demo`, interfaz web y API v1.
3. Usuarios e inicio de sesión; después, API v1 de envíos para la app móvil.
4. Núcleo de flotilla: `flotilla`, `empleados`, `contratos`, `costos`, `agenda`.
5. Flujos internos: `gastos`, `aprobaciones`, `firmas`, `encuestas`.
6. Reportes de rentabilidad y app móvil en Flutter.
