# Bot de gastos — Grupo Scout Buen Consejo

Bot de Telegram para que cualquier scouter autorizado registre un **gasto** en segundos. Hay
**tres formas** de hacerlo: guiado con **botones**, por **texto**, o dictando una **nota de voz**
que una **IA local** interpreta. Cada gasto se guarda en una base de datos **SQLite** local
(la fuente de verdad del sistema).

> **Modo actual: solo base de datos (solo-DB).** El bot **no necesita Google** para funcionar:
> guarda directamente en SQLite. Subir la foto/PDF de la factura a Google Drive es opcional
> (Fase 2, `FACTURAS_ACTIVAS=1`). La versión antigua que escribía en Google Sheets se conserva
> como referencia, pero ya no es el camino por defecto (ver [`MANUAL.md`](MANUAL.md)).

---

## Cómo se registra un gasto

**1. Con botones (recomendado en el móvil)** — manda **`/gasto`** y el bot te guía:
tipo → unidad → (grupo) → categoría → concepto → importe → **✅ Confirmar**.

**2. Por texto** — un mensaje con cada dato en una línea (o separado por `|`):

```
Castores
Material de unidad
Pinturas para el local
47,30
```

**3. Por nota de voz** (si el audio está activado) — mándale un audio diciendo la sección, la
categoría, el concepto y el importe. La IA local lo transcribe, extrae los campos y te enseña una
**propuesta** que confirmas con ✅/❌ antes de guardar nada.

```
«Castores, material de unidad, pinturas para el local, cuarenta y siete con treinta euros»
```

En los tres casos la comparación de sección y categoría **ignora mayúsculas y acentos**, y el
campo *Quién* no se escribe: lo deduce el bot del `chat_id` de quien envía.

---

## Comandos

| Comando | Qué hace |
|---|---|
| `/gasto` | Registrar un gasto guiado con botones. |
| `/pendientes` | Listar los gastos **incompletos** (los que se guardaron por voz sin todos los datos). |
| `/chatid` | Ver tu identificador de Telegram (para darte de alta). |
| `/start` | Ayuda y, si el audio está activo, guía de qué decir en la nota de voz. |
| `/cancel` | Cancelar el flujo de botones a medias. |

---

## Dónde se guardan los datos

Todo va a un fichero **SQLite** (`data/gastos.db` por defecto, configurable con `DB_PATH`).
Tabla `gastos`, una fila por gasto:

| Campo | Contenido |
|---|---|
| `fecha` / `trimestre` | Fecha de registro y trimestre scout (calculado). |
| `seccion` / `categoria` / `concepto` / `importe` | Los datos del gasto. |
| `quien` | Autor (deducido del `chat_id`). |
| `enlace` | URL de la factura en Drive (vacío salvo Fase 2). |
| `estado` | `completo` o `incompleto` (voz sin todos los datos). |
| `creado_en` | Marca de tiempo del registro. |

**Gastos incompletos:** si una nota de voz no trae todo pero sí el **importe** (obligatorio), se
guarda como `incompleto` con lo que falte en blanco; luego lo revisas con `/pendientes`. Sin
importe no se guarda.

---

## Puesta en marcha rápida (solo-DB)

Para el arranque detallado paso a paso (Windows incluido), ver
[`GUIA-puesta-en-marcha.md`](GUIA-puesta-en-marcha.md).

### 0. Requisitos
- Python 3.10 o superior. (La IA de audio es aparte — ver más abajo.)

### 1. Crear el bot de Telegram
Habla con [@BotFather](https://t.me/BotFather), crea un bot y copia el **token**.

### 2. Configuración
```bash
cp .env.example .env
cp config/secciones.example.yaml config/secciones.yaml
cp config/autorizados.example.yaml config/autorizados.yaml
```
En `.env` basta con el token para el modo solo-DB:
```dotenv
TELEGRAM_BOT_TOKEN=123456:ABC-...
DB_PATH=data/gastos.db
FACTURAS_ACTIVAS=0
DRY_RUN=0
```

### 3. Instalar y arrancar
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python src/bot.py
```
Si todo va bien: `Bot arrancado (facturas=False, dry_run=False). Esperando mensajes…`

---

## IA de audio (opcional)

El registro por nota de voz usa **Whisper** (voz→texto) y **Ollama** (texto→campos), todo **en
local**: el audio no sale de la máquina. Se activa con `AUDIO_ACTIVO=1` en `.env` y requiere
`ffmpeg`, `mlx-whisper` y el servidor de Ollama con el modelo instalado.

👉 **Guía completa de instalación y configuración: [`MODELOS-IA.md`](MODELOS-IA.md)** (qué
modelos, cómo instalarlos, dónde se guardan y cómo cambiar la ruta).

---

## Web de tesorería (Paso 2)

Además del bot, hay una **web local** para ver los balances y **gestionar** los gastos (crear,
editar, completar los incompletos y borrar). Lee y escribe en la **misma** base de datos SQLite
que el bot. Arranque:

```bash
.venv/bin/python src/run_web.py     # (Windows: .venv\Scripts\python src\run_web.py)
```

Luego abre **http://127.0.0.1:8000** en el navegador. La web escucha **solo en este equipo**
(`127.0.0.1`): nadie más de la red puede entrar y **no tiene login** (v1). Si algún día se quisiera
abrir a otros scouters habría que añadir autenticación.

---

## Facturas a Google Drive (opcional, Fase 2)

Con `FACTURAS_ACTIVAS=1` el bot, además de guardar el gasto, pide la **foto/PDF** y la sube a
Drive (una carpeta por sección). Esto **sí** necesita credenciales de Google:

- `GOOGLE_AUTH_MODE=service_account` (recomendado en Workspace) u `oauth` (Gmail).
- `GOOGLE_CREDENTIALS_PATH` apuntando a la clave, y el ID de carpeta de cada sección en
  `config/secciones.yaml`.

Detalles en [`GUIA-puesta-en-marcha.md`](GUIA-puesta-en-marcha.md) (paso 11).

---

## Dar de alta usuarios

Cada scouter envía **`/chatid`** al bot; este responde su número. Cópialo a
`config/autorizados.yaml`:

```yaml
autorizados:
  - chat_id: 11111111
    nombre: "Nombre Apellido"
```

Quien no esté en la lista es ignorado en silencio. (Tras editar el YAML, reinicia el bot.)

---

## Pruebas

```bash
pytest            # pruebas offline: no tocan Telegram, Google ni la IA
```

Probar el flujo de Telegram **sin** guardar nada real: `DRY_RUN=1` en `.env` (registra en el log
lo que se guardaría).

---

## Privacidad (importante)
- Cuentas de Telegram y Google **de la asociación**, nunca personales.
- La IA de audio es **local** (Whisper + Ollama): las notas de voz no se envían a ningún servicio
  externo.
- **No** se versionan: `.env`, credenciales JSON, `token.json`, `config/autorizados.yaml`,
  `config/secciones.yaml`, la base de datos `data/` ni ningún `*.xlsx` (ver `.gitignore`).
- Durante el desarrollo y las pruebas, usa **solo datos ficticios**.

---

## Estructura

```
bot-facturas/
├── config/
│   ├── secciones.example.yaml   # sección -> carpeta de Drive (plantilla; solo Fase 2)
│   ├── categorias.yaml          # categorías por sección  ← catálogo, fuente de verdad
│   └── autorizados.example.yaml # chat_id -> nombre (plantilla)
├── src/
│   ├── bot.py               # punto de entrada del BOT (long polling) + handlers
│   ├── run_web.py           # punto de entrada de la WEB (uvicorn, solo localhost)
│   ├── core/                # lógica compartida por el bot y la web
│   │   ├── config.py        #   carga .env + catálogos + autorizados
│   │   ├── catalogos.py     #   secciones y categorías (desde YAML)
│   │   ├── validacion.py    #   parseo + validación del mensaje de texto
│   │   ├── db.py            #   persistencia y consultas SQLite  ← fuente de verdad
│   │   ├── transcribir.py   #   IA: voz -> texto (Whisper local)
│   │   ├── interpretar.py   #   IA: texto -> campos del gasto (Ollama local)
│   │   ├── util.py          #   normalización y trimestre
│   │   ├── autenticacion.py #   credenciales Google (solo Fase 2)
│   │   └── drive.py/sheets.py  #  Google Drive / Sheets (legacy / solo Fase 2)
│   └── web/                 # web de tesorería (FastAPI + plantillas Jinja2)
│       ├── app.py           #   rutas y lógica de la web
│       ├── templates/       #   HTML (panel, lista, formulario)
│       └── static/          #   estilos
├── data/                    # base de datos SQLite (no se versiona)
└── tests/                   # pruebas offline
```

---

## Documentación relacionada
- [`GUIA-puesta-en-marcha.md`](GUIA-puesta-en-marcha.md) — arranque paso a paso en tu ordenador.
- [`MODELOS-IA.md`](MODELOS-IA.md) — instalar y configurar la IA de audio (Whisper + Ollama).
- [`MANUAL.md`](MANUAL.md) — entender el sistema y **cómo cambiar cada cosa**.
- [`DECISIONES.md`](DECISIONES.md) — registro de decisiones y evolución del proyecto.
- [`REPLICAR-CON-IA.md`](REPLICAR-CON-IA.md) — replicarlo otro año/grupo.
