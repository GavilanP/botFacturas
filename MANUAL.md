# Manual del sistema — Bot de facturas + hoja de gastos

Grupo Scout Buen Consejo. Documento para **entender el sistema** y, sobre todo, **cómo cambiar cada cosa** en el
futuro. Si retomas esto (tú, otra persona o Claude en otra sesión), **empieza por aquí**.

---

## 1. Qué hace el sistema

Un **bot de Telegram** para registrar gastos. Hay **tres formas** de registrar uno:

1. **Botones** (`/gasto`): el bot guía por tipo → unidad → grupo → categoría → concepto → importe.
2. **Texto**: un mensaje con `SECCIÓN · CATEGORÍA · CONCEPTO · IMPORTE` (una línea por dato o separados por `|`).
3. **Nota de voz**: una **IA local** transcribe (Whisper) e interpreta (Ollama) el audio, propone los campos y el
   usuario confirma con ✅/❌ antes de guardar.

Cada gasto se guarda en una base de datos **SQLite** (`data/gastos.db`), que es la **fuente de verdad** del
sistema. En el modo actual (**solo-DB**) el bot **no necesita Google**.

> **Legacy / opcional.** La versión anterior escribía en **Google Sheets** (con balances por `SUMIFS`), y subir la
> factura a **Google Drive** sigue disponible como Fase 2 (`FACTURAS_ACTIVAS=1`). Ese material se conserva en este
> manual (secciones 4 y las filas marcadas *legacy*), pero **el bot ya no escribe en Sheets**.

---

## 2. Piezas y archivos

```
bot-facturas/
├── src/                       # código (Python)
│   ├── bot.py                 # entrada del BOT (long polling) + handlers
│   ├── run_web.py             # entrada de la WEB (uvicorn, solo localhost)
│   ├── core/                  # lógica COMPARTIDA por bot y web
│   │   ├── validacion.py      #   parseo + validación del mensaje de texto
│   │   ├── catalogos.py       #   carga secciones/categorías desde YAML
│   │   ├── config.py          #   carga .env + catálogos + autorizados
│   │   ├── db.py              #   persistencia y consultas SQLite  ← FUENTE DE VERDAD
│   │   ├── transcribir.py     #   IA: voz -> texto (Whisper local)
│   │   ├── interpretar.py     #   IA: texto -> campos del gasto (Ollama local)
│   │   ├── util.py            #   normalización y cálculo de Trimestre
│   │   ├── autenticacion.py   #   credenciales Google (solo Fase 2)
│   │   └── drive.py/sheets.py #   Drive / Sheets (legacy · solo Fase 2)
│   └── web/                   # web de tesorería (FastAPI + Jinja2)
│       ├── app.py             #   rutas CRUD + balances
│       ├── templates/         #   HTML
│       └── static/            #   estilos
├── config/
│   ├── secciones.yaml         # sección -> carpeta de Drive (real; solo Fase 2)
│   ├── categorias.yaml        # categorías por sección  ← CATÁLOGO, fuente de verdad
│   └── autorizados.yaml       # chat_id -> nombre  (real, no se versiona)
├── data/                      # base de datos SQLite (real, no se versiona)
├── google-sheets/             # LEGACY: Apps Script de la hoja (arquitectura anterior)
├── .env                       # secretos (token, rutas)  ← no se versiona
├── MODELOS-IA.md              # instalar/configurar la IA de audio
└── MANUAL.md                  # este documento
```

> **El catálogo `config/categorias.yaml` es la fuente de verdad** de secciones y categorías: alimenta la
> validación de texto, los menús de botones **y** el contexto que se le da a la IA para mapear lo dictado. Si
> reactivas la hoja de Google (legacy), hay que mantener también sincronizadas las listas del Apps Script
> (`CAT_UNIDAD`, `GRUPO_PARTIDAS`, `CAMPAMENTO`, `UNIDADES`).

---

## 3. Modelo de datos

**Secciones (7):** Castores, Manada, Tropa, Escultas, Clan, **Grupo**, **Campamento**.

**Categorías por sección:**
- **Unidades** (Castores, Manada, Tropa, Escultas, Clan): `Material de unidad`, `Excursión de unidad`,
  `Dinero entregado`.
- **Grupo (23)**, agrupadas en 6 partidas (siguiendo el presupuesto): EdM y ASDE · Formación · Actividades ·
  Material · Cargos y comisiones · Varios.
- **Campamento (46)**, en 8 bloques: TRANSPORTE · CARGOS · ALIMENTACIÓN · BOTIQUÍN · SITIO CAMPAMENTO ·
  COLONIZACIÓN · MATERIAL · ACTIVIDADES.

**Mensaje del bot (texto):** `SECCIÓN | CATEGORÍA | CONCEPTO | IMPORTE` (la validación ignora mayúsculas y acentos).

**Tabla `gastos` de SQLite (`data/gastos.db`) — dónde guarda el bot hoy:**
`id · fecha · trimestre · seccion · categoria · concepto · importe · enlace · quien · creado_en · estado`
- `trimestre` y `fecha` se calculan solos; `quien` sale del `chat_id`; `enlace` es la URL de Drive (vacío salvo
  Fase 2); `creado_en` es la marca de tiempo.
- `estado` = `completo` o `incompleto`. Un gasto por **voz** al que le falte sección/categoría/concepto (pero
  **sí** el importe, obligatorio) se guarda como `incompleto` con esos campos en blanco; se listan con
  `/pendientes`. El esquema y la migración (columna `estado`) están en `src/core/db.py`.

**(Legacy) Columnas de `Tabla de Gastos` en Google Sheets (A:I):**
`UNIDAD | Trimestre | Categoría | Importe | Factura | Fecha | Comentarios | Enlace factura | Quién` — solo
aplica si reactivas la versión que escribía en Sheets (ver `src/core/sheets.py`).

---

## 4. La hoja de Google (cómo se genera) — ⚠️ LEGACY

> Esta sección aplica **solo** a la arquitectura anterior (bot → Google Sheets). El bot actual guarda en SQLite y
> **no** usa la hoja. Se conserva por si algún día se quiere recuperar esa vía o los balances por `SUMIFS`.

Menú **Bot facturas** (lo añade el Apps Script al abrir la hoja):
- **Inicializar hoja (crear todo)** → crea, si no existen, `Tabla de Gastos`, `Catálogo` y los 3 balances.
- **Configurar desplegable de Unidad** → pone el desplegable de UNIDAD en la columna A de `Tabla de Gastos`.
- **Aplicar categorías a filas existentes** → pone el desplegable de Categoría en las filas que ya tienen unidad.
- **Crear hojas de balance** → solo las 3 hojas de balance.

Claves de los balances:
- **Gastado** = `SUMIFS` desde `Tabla de Gastos` (por unidad / categoría / [trimestre]). Se actualiza solo.
- **Presupuestado** = lo pones tú (Grupo y Campamento, por categoría) o se calcula por **parámetros** (Unidades).
- **Balance** = Presupuestado − Gastado. Formato condicional: **negativo = rojo**, **positivo = verde**.
- Las fórmulas usan el **separador que detecta la hoja** (`,` o `;`); no las cambies a mano.
- **Balance Unidades** es **anual**: arriba hay un bloque `PARÁMETROS` (€/persona material, €/persona excursión,
  mínimo material) y por unidad los conteos de educandos/scouters. Material = `máx(personas × €mat, mínimo)`,
  Excursión = `personas × €exc`.

---

## 5. CÓMO CAMBIAR CADA COSA  ⭐ (lo importante)

| Quiero… | Dónde tocar | Después |
|---|---|---|
| **Añadir/quitar/renombrar categoría de Grupo** | `config/categorias.yaml` (lista `grupo`) **y** `dropdowns-dependientes.gs` → `GRUPO_PARTIDAS` (dentro de su partida) | Borrar pestañas `Catálogo` y `Balance Grupo` → menú **Inicializar hoja** + **Crear hojas de balance** |
| **Ídem en Campamento** | `categorias.yaml` (lista `campamento`) **y** `.gs` → `CAMPAMENTO` (en su bloque) | Regenerar `Catálogo` y `Balance Campamento` |
| **Ídem en Unidades** | `categorias.yaml` (lista `unidad`) **y** `.gs` → `CAT_UNIDAD` | Regenerar `Catálogo` y `Balance Unidades` |
| **Añadir/quitar una unidad o sección** | `config/secciones.yaml` (+ carpeta Drive), `categorias.yaml` (`seccion_a_lista`) y, si es unidad, `.gs` → `UNIDADES` | Regenerar |
| **Cambiar parámetros de unidad** (€/persona, mínimo, nº educandos/scouters) | Directamente en la pestaña **`Balance Unidades`** (celdas `B2:B4` y los conteos). **No toca código** | — |
| **Rellenar/cambiar el presupuesto** | Grupo/Campamento: columna **Presupuestado** de cada balance. Unidades: los parámetros | — |
| **Cambiar el criterio de Trimestre** | `src/util.py` → función `trimestre_de` | — |
| **Conectar el bot** (modo solo-DB) | `.env` → `TELEGRAM_BOT_TOKEN` (y opcional `DB_PATH`). **No hace falta Google.** | Reiniciar el bot |
| **Activar/configurar la IA de audio** | `.env` → `AUDIO_ACTIVO`, `WHISPER_MODEL`, `OLLAMA_MODEL`, `OLLAMA_HOST` (ver [`MODELOS-IA.md`](MODELOS-IA.md)) | Reiniciar el bot (y tener Ollama arrancado) |
| **Cambiar el modelo de IA** (p. ej. a 7B/3B) | `.env` → `OLLAMA_MODEL` + `ollama pull <modelo>` | Reiniciar el bot |
| **Activar facturas a Drive** (Fase 2) | `.env` → `FACTURAS_ACTIVAS=1`, credenciales Google, IDs de carpeta en `secciones.yaml` | Reiniciar el bot |
| *(Legacy)* **Regenerar una hoja de Sheets** | Bórrala a mano | Menú **Inicializar hoja** / **Crear hojas de balance** |

> **Regla de oro (catálogo):** al cambiar categorías toca `config/categorias.yaml` — con eso se actualizan la
> validación, los botones y el contexto de la IA. Si además usas la hoja de Google (legacy), sincroniza también
> las listas del `.gs` y regenera las pestañas.

---

## 6. El bot (resumen técnico)

- Arranque: `python src/bot.py` (long polling; no necesita abrir puertos). Una **sola** instancia a la vez (dos
  dan `Conflict` de Telegram).
- **Comandos:** `/gasto` (botones), `/pendientes` (incompletos), `/chatid`, `/start`, `/cancel`.
- **Tres flujos de entrada** convergen en guardar en SQLite (`db.guardar_gasto`):
  - *Botones* (`/gasto`): conversación con teclados; el importe se valida al final.
  - *Texto*: `validacion.parsear` (remitente autorizado → 4 campos → sección → categoría de esa sección →
    importe > 0). Si algo falla, responde y **no escribe**.
  - *Voz*: `transcribir` (Whisper) → `interpretar` (Ollama + catálogo) → propuesta con ✅/❌. Las llamadas a la IA
    van en `asyncio.to_thread` para no bloquear el bot.
- El patrón es **"la IA propone, el usuario confirma"**: nunca se guarda sin confirmación.
- `DRY_RUN=1` en `.env` prueba el flujo sin escribir en la base de datos (solo log).
- Pruebas offline: `pytest` (no tocan Telegram ni la IA).

---

## 7. Cosas a tener en cuenta (gotchas)

> Los primeros puntos son de la **hoja de Google (legacy)**; solo aplican si reactivas esa vía.

- **`#N/A` en los balances** = hay una celda con error en las columnas **A/C/D** de `Tabla de Gastos`; como el
  `SUMIFS` usa la columna entera, contagia. Búscala (Ctrl+F → `#N/A`) y bórrala.
- **Separador de fórmulas**: el script lo autodetecta (`,`/`;`) y construye las fórmulas con él. No las edites a mano.
- **No sobrescribe**: "Inicializar hoja" / "Crear hojas de balance" **no tocan** una pestaña que ya exista (para no
  borrar presupuesto). Para regenerarla, bórrala antes.
- **El bot escribe por API** → no dispara el `onEdit`, así que sus filas no llevan "pegado" el desplegable (pero el
  valor ya es correcto). Los desplegables son para la entrada **manual**.
- Cuentas de Telegram/Google **de la asociación**, nunca personales. `.env`, credenciales y datos reales **no** se
  versionan.

---

## 8. Estado y siguientes pasos

**Ya construido:**
- **IA de audio local** (no la API de Claude, por privacidad): Whisper + Ollama (`qwen2.5:7b`), con el catálogo
  dado al modelo como contexto y `rapidfuzz` como red de seguridad. Ver [`MODELOS-IA.md`](MODELOS-IA.md).
- **Gastos incompletos** por voz + comando `/pendientes`.
- **SQLite como fuente de verdad** (Paso 1 del roadmap).
- **Web local de tesorería** (Paso 2): FastAPI + Jinja2 sobre la misma SQLite. Panel de balances
  (por sección, categoría y trimestre) y **CRUD** de gastos (crear, editar, **completar** los
  incompletos y borrar). Solo `127.0.0.1`, sin login (v1). Arranque: `python src/run_web.py`
  → http://127.0.0.1:8000. Código en `src/web/`.

**Pendiente / futuro** (detalle y decisiones en [`DECISIONES.md`](DECISIONES.md)):
- **Login / autenticación** en la web (necesario antes de abrirla más allá de `127.0.0.1`).
- **Completar los incompletos** también desde el chat (la web ya lo permite).
- **Despliegue 24/7** (systemd / `deploy/bot.service`) y **copias de seguridad** de `data/gastos.db`.
- **Aviso de errores al admin** (`ADMIN_CHAT_ID`) y arranque de instancia única.
