# MCL · Corregidora Móvil Logistics

Plataforma para conectar a un pequeño grupo de transportistas independientes con pequeñas
empresas, **programada en Python**.

- **Aplicación web:** el negocio busca transportistas, cotiza al instante, solicita el
  servicio y le da seguimiento hasta la entrega. El transportista acepta y atiende los
  viajes, y el administrador supervisa todo desde un panel con indicadores.
- **API para la app móvil:** catálogo de transportistas y cotizaciones en JSON, con
  documentación interactiva en `/docs`. La app móvil (Flutter) se construirá aparte.

Está hecha con FastAPI (servidor), Jinja2 (pantallas generadas en Python) y SQLAlchemy con
Alembic (base de datos y migraciones). Usa SQLite en desarrollo y PostgreSQL en producción.

| Inicio | Seguimiento del envío | Panel administrativo |
|---|---|---|
| ![Inicio](docs/capturas/inicio.png) | ![Seguimiento](docs/capturas/envio.png) | ![Panel](docs/capturas/admin.png) |

## Verla funcionando en GitHub, sin instalar nada

GitHub Pages solo publica páginas estáticas y no puede correr un servidor de Python. GitHub
Codespaces sí puede: abre el proyecto en una máquina en la nube, desde el navegador.

[![Abrir en GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/hiram30020292/Plataforma-log-stica?quickstart=1)

1. Haz clic en el botón de arriba, o en el repositorio entra a **Code → Codespaces → Create
   codespace on main**.
2. Espera unos minutos la primera vez: se instalan las dependencias y la app arranca sola.
3. La app se abre en otra pestaña. Si no se abre, ve a la pestaña **Ports** (Puertos) de
   abajo y haz clic en el globo de la fila **8000**.
4. Para que otras personas la vean, en **Ports** haz clic derecho en el puerto 8000 →
   **Port Visibility → Public** y comparte la dirección.

El codespace se detiene solo después de un rato sin uso. Las cuentas personales tienen
horas gratis cada mes; los codespaces se administran en https://github.com/codespaces.

## Qué incluye

**Para los negocios (cliente)**
- Portada con buscador, categorías y transportistas destacados.
- Catálogo con filtros por texto (sin importar acentos), categoría, ciudad, vehículo y orden.
- Perfil de cada transportista: calificación, viajes, cobertura y opiniones.
- Solicitud con **cotización en vivo**: distancia por carretera, precio y avisos (sobrepeso,
  origen igual al destino, servicio no ofrecido).
- "Mis envíos": activos e historial, con mapa de la ruta, avance estimado y línea de
  tiempo. Al recibir el envío, el cliente lo califica.

**Para los transportistas**
- Panel con solicitudes nuevas, viajes en curso, completados e ingresos.
- Aceptar o rechazar, iniciar el viaje y marcarlo como entregado.
- Registro de nuevos transportistas (quedan "en revisión" hasta que se verifican).

**Para el administrador**
- Tablero con indicadores, solicitudes por día, estado de las solicitudes y mejores
  transportistas.
- Tabla de todas las solicitudes con el estado editable.
- Verificación y destacado de transportistas.

Todas las reglas del negocio (precios, permisos por rol, flujo de estados, calificaciones)
viven en Python y tienen tests.

## Requisitos

- Python 3.12 o superior
- Git

## Instalación

```bash
git clone https://github.com/hiram30020292/Plataforma-log-stica.git
```

```bash
cd Plataforma-log-stica
```

```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
pip install -e ".[dev]"
```

En Windows, crea el entorno con `py -m venv .venv` y actívalo con `.venv\Scripts\activate`.

## Ejecutar la plataforma

```bash
uvicorn mcl.api:create_app --factory --reload
```

Abre http://127.0.0.1:8000 en el navegador. La primera vez se crea la base de datos
`mcl.db` con datos de ejemplo: 8 transportistas y 50 solicitudes. Para detener el servidor,
pulsa `Ctrl+C`.

- http://127.0.0.1:8000: la aplicación web.
- http://127.0.0.1:8000/admin: el panel administrativo.
- http://127.0.0.1:8000/docs: la API para la app móvil.

No necesita internet: las fuentes y los estilos van incluidos en el proyecto.

## Guía para presentarla (5 minutos)

1. **Portada** (`/`): busca "Querétaro" o toca una categoría.
2. **Catálogo:** filtra por ciudad o vehículo; los resultados cambian sin recargar.
3. **Perfil** de "Rápidos del Bajío": calificación, cobertura y opiniones. Toca
   *Solicitar servicio*.
4. **Solicitud:** cambia el peso y el destino y mira la cotización recalcularse. Si el
   peso supera la capacidad, la app lo avisa y no deja enviar. Envía la solicitud.
5. **Mis envíos:** abre el envío en tránsito y muestra el mapa con el avance y la línea
   de tiempo.
6. **Menú ☰ → Panel del transportista:** acepta la solicitud nueva, inicia el viaje y
   márcalo como entregado.
7. **Menú ☰ → Panel del cliente:** abre ese envío y califícalo; la opinión aparece en el
   perfil del transportista.
8. **Menú ☰ → Panel administrativo:** indicadores, gráficas, cambio de estado desde la
   tabla y verificación de transportistas.
9. Al terminar, en **Perfil → Restablecer datos de ejemplo** la demo queda como nueva.

La demo no pide inicio de sesión: en **Perfil** se elige el modo (cliente, transportista o
administrador), el nombre de la empresa y con qué transportista operar.

## Configuración

Copia `.env.example` como `.env` y ajusta los valores; el archivo `.env` nunca se sube al
repositorio. Las variables principales:

| Variable | Para qué sirve | Valor por defecto |
|---|---|---|
| `MCL_DATABASE_URL` | Base de datos | `sqlite:///./mcl.db` |
| `MCL_TIMEZONE` | Zona horaria de las fechas | `America/Mexico_City` |
| `MCL_DEMO_DATA` | Cargar y restablecer los datos de ejemplo | `true` |
| `MCL_SMTP_USER`, `MCL_SMTP_PASSWORD` | Avisos por Gmail (contraseña de aplicación) | sin definir |

Para PostgreSQL, instala el controlador con `pip install -e ".[postgres]"` y usa una URL
como `postgresql+psycopg://usuario:clave@servidor:5432/mcl`.

## Base de datos

El esquema se versiona con migraciones de Alembic (`src/mcl/db/migrations/versions`). La
app aplica las migraciones pendientes al arrancar. Para cambiar el esquema, modifica los
modelos y genera la migración:

```bash
alembic revision --autogenerate -m "describe el cambio"
```

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
├── api/             aplicación FastAPI: API JSON v1, errores y arranque
├── web/             pantallas en Python (rutas, plantillas Jinja2, estilos)
├── db/              migraciones de la base de datos (Alembic)
├── catalogo/        transportistas, búsqueda, registro y verificación
├── envios/          cotización, solicitudes, ciclo de vida y seguimiento
├── calificaciones/  opiniones y promedio de cada transportista
├── reportes/        indicadores del panel administrativo
├── demo/            datos de ejemplo
├── core/            configuración, base de datos, excepciones y tipos compartidos
└── utils/           funciones auxiliares puras
tests/               tests (espejo de src/mcl)
```

Las reglas de arquitectura y de refactorización segura están en [CLAUDE.md](CLAUDE.md).
