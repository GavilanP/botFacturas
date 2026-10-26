# Puesta en marcha del bot de gastos (en tu ordenador)

Guía completa para arrancar el bot **en tu ordenador personal**, paso a paso. No hace falta saber programar:
sigue los pasos en orden.

> **Modo solo-DB (por defecto).** El bot registra gastos —con **botones**, por **texto** o por **nota de voz**— y
> los guarda en una base de datos **SQLite** en tu ordenador. **No hace falta Google** para esto. Subir la
> foto/PDF a Google Drive es opcional (Fase 2, paso 11), y la **IA de audio** también es opcional (paso 12).

---

## 1. Qué necesitas antes de empezar
- El fichero **`bot-facturas.zip`** (todo el proyecto) — o el repositorio clonado.
- **Python 3.10 o superior** instalado.
- Una cuenta de **Telegram**.
- (Solo si quieres la Fase 2 de facturas a Drive) el **`credenciales.json`** de Google. Para el modo solo-DB
  **no hace falta**.

## 2. Descomprimir el proyecto
1. Copia **`bot-facturas.zip`** a tu PC (p. ej. a `Documentos`) y **descomprímelo** (clic derecho → *Extraer todo*).
   Te quedará una carpeta **`bot-facturas`**.
   - (Si ves carpetas `__pycache__` dentro, son caché de Python: puedes borrarlas, dan igual.)

## 3. Instalar Python (si no lo tienes)
1. Ve a **python.org/downloads** e instala Python 3.x.
2. En el instalador (Windows), **marca la casilla "Add Python to PATH"** (¡importante!).
3. Comprueba: abre una terminal y escribe `python --version` → debe mostrar 3.10 o más.
   (Si dice que no reconoce `python`, prueba con `py --version`; si tampoco, reinstala marcando "Add to PATH".)

## 4. Configuración
1. En `bot-facturas\`, **haz una copia de `.env.example` y renómbrala a `.env`**. Ábrela con el Bloc de notas.
   Para el modo solo-DB basta con esto (el token lo creas en el paso 5):
   ```
   TELEGRAM_BOT_TOKEN=          (lo creas en el paso 5)
   DB_PATH=data/gastos.db
   FACTURAS_ACTIVAS=0
   DRY_RUN=0
   ```
   El bot creará solo el fichero `data/gastos.db` la primera vez. (Los valores de Google que veas en el
   `.env.example` solo hacen falta para la Fase 2 del paso 11; puedes dejarlos en blanco.)
2. Haz una copia de **`config\autorizados.example.yaml`** y renómbrala a **`config\autorizados.yaml`** (la
   rellenarás en el paso 7).

## 5. Crear el bot de Telegram
1. En Telegram, abre **@BotFather** → escribe **`/newbot`**.
2. Te pedirá un **nombre** y un **usuario** (debe acabar en `bot`).
3. Te dará un **token** (algo como `123456:ABC-...`). Cópialo en `TELEGRAM_BOT_TOKEN` del `.env`.

## 6. Instalar dependencias y arrancar
**Abre una terminal dentro de la carpeta `bot-facturas`:**
- Windows 11: clic derecho dentro de la carpeta → **"Abrir en Terminal"**.
- Windows 10: en el Explorador, en la **barra de direcciones** escribe `powershell` y pulsa Enter.

Ejecuta estos comandos (uno a uno):
```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python src\bot.py
```
*(En Mac/Linux: `python3 -m venv .venv` → `.venv/bin/python -m pip install -r requirements.txt` →
`.venv/bin/python src/bot.py`.)*

Si todo va bien, verás: `Bot arrancado (facturas=False, dry_run=False). Esperando mensajes…`

> 💡 Uso estos comandos con `.venv\Scripts\python` directamente para evitar un fallo típico de Windows al
> "activar" el entorno (ver Problemas comunes).

## 7. Darte de alta (tu chat_id)
1. Con el bot arrancado, abre tu bot en Telegram y mándale **`/chatid`** → te responde tu número.
2. Abre `config\autorizados.yaml` (con el Bloc de notas) y pon tu número y nombre:
   ```yaml
   autorizados:
     - chat_id: 11111111
       nombre: "Tu Nombre"
   ```
3. **Para el bot** (en la terminal, pulsa **Ctrl+C**) y **vuelve a arrancarlo**
   (`.venv\Scripts\python src\bot.py`) para que lea el cambio.

## 8. Probar
Tienes tres formas:
- **Con botones (recomendado):** manda **`/gasto`** al bot y ve eligiendo (tipo → unidad → grupo → categoría); luego escribe el concepto y el importe, y pulsa **✅ Confirmar**.
- **Por texto:** un mensaje con cada dato en una línea:
  ```
  Castores
  Material de unidad
  Cena fin de ronda
  47,30
  ```
- **Por voz** (si activaste el audio en el paso 12): manda una nota de voz diciendo sección, categoría, concepto e importe; el bot te enseña una propuesta y la confirmas con ✅.

En los tres casos debe responder **"✅ Gasto registrado"**. El gasto queda en la base de datos `data/gastos.db`. 🎉
Para verlo, puedes usar cualquier visor de SQLite, o el comando `/pendientes` (que lista los gastos guardados como incompletos).

## 9. Uso del día a día
- **Arrancar**: abre la terminal en `bot-facturas` y ejecuta `.venv\Scripts\python src\bot.py`. Mientras la terminal
  esté abierta, el bot funciona.
- **Parar**: **Ctrl+C** en la terminal (o cierra la ventana).
- El bot corre **en tu ordenador**: necesita que el PC esté encendido y el bot arrancado. (Para 24/7 sin el PC, en
  el futuro se migra a una Raspberry Pi.)

## 10. Si algo no va (problemas comunes)
- **`python` no se reconoce** → no marcaste "Add to PATH" al instalar; reinstala marcándolo, o usa `py` en vez de
  `python`.
- **Al activar el entorno sale "la ejecución de scripts está deshabilitada"** → no uses `activate`; usa los
  comandos con `.venv\Scripts\python` (como en el paso 6). *(O ejecuta antes
  `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.)*
- **`pip install` falla o tarda** → necesita internet; reinténtalo.
- **"Falta TELEGRAM_BOT_TOKEN"** → revisa el `.env`.
- **El bot no responde / te ignora** → tu `chat_id` no está en `autorizados.yaml` (manda `/chatid` y añádelo, y
  reinicia el bot).
- **`Conflict: terminated by other getUpdates`** → tienes **dos instancias** del bot corriendo a la vez. Cierra
  todas (Ctrl+C en cada terminal) y arranca solo una.
- **Mandas una nota de voz y no pasa nada** → el audio no está activado (`AUDIO_ACTIVO=0`) o falta algo de la IA;
  revisa el paso 12 y [`MODELOS-IA.md`](MODELOS-IA.md).
- (Opcional) Probar la lógica sin Telegram: `.venv\Scripts\python -m pytest` dentro de `bot-facturas`.

## 11. La web de tesorería (ver balances y editar gastos)
Además del bot, hay una **web** para ver los totales y **gestionar** los gastos (crear, editar,
completar los incompletos y borrar). Usa la **misma** base de datos que el bot.

1. Arráncala en una terminal dentro de `bot-facturas`:
   `.venv\Scripts\python src\run_web.py`
   *(En Mac/Linux: `.venv/bin/python src/run_web.py`.)*
2. Abre en el navegador: **http://127.0.0.1:8000**
3. Para pararla: **Ctrl+C** en esa terminal.

La web escucha **solo en tu ordenador** (`127.0.0.1`): nadie más de la red puede entrar y **no
tiene contraseña**. El bot y la web pueden estar arrancados a la vez (cada uno en su terminal).

## 12. Opcional — Facturas a Google Drive (Fase 2)
Si además de registrar el gasto quieres **subir la foto/PDF** de la factura a Drive:
1. Consigue un **`credenciales.json`** de Google (cuenta de servicio recomendada) y mételo en `config\`.
2. En `.env`: `FACTURAS_ACTIVAS=1`, `GOOGLE_AUTH_MODE=service_account`,
   `GOOGLE_CREDENTIALS_PATH=config/credenciales.json`.
3. Habilita la **Drive API**, crea una carpeta por sección y pon sus IDs en `config\secciones.yaml`.

El bot pedirá la foto/PDF junto al texto y la subirá a la carpeta de la sección. (Sin esto, en modo solo-DB, el
gasto se guarda igual en la base de datos.)

## 13. Opcional — Registrar gastos por voz (IA local)
El bot puede transcribir e interpretar **notas de voz** con IA que corre **en tu ordenador** (el audio no sale de
la máquina). Necesita `ffmpeg`, `mlx-whisper` y **Ollama** con un modelo instalado, y activar `AUDIO_ACTIVO=1`.

👉 **Instalación y configuración paso a paso: [`MODELOS-IA.md`](MODELOS-IA.md).**

> Para entender o cambiar cualquier parte del sistema: **`MANUAL.md`**. Para replicarlo otro año/grupo:
> **`REPLICAR-CON-IA.md`**.
