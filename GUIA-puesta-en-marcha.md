# Puesta en marcha del bot de gastos (en tu ordenador)

Guía completa para arrancar el bot **en tu ordenador personal**, paso a paso. No hace falta saber programar:
sigue los pasos en orden.

> El bot (Fase 1) registra gastos: el scouter manda un mensaje de texto
> `SECCIÓN | CATEGORÍA | CONCEPTO | IMPORTE` y el bot lo escribe en la hoja de Google. (Las **facturas a Drive**
> son la Fase 2, más adelante.)

---

## 1. Qué necesitas antes de empezar
- El fichero **`bot-facturas.zip`** (todo el proyecto).
- El fichero **`credenciales.json`** (la clave de la cuenta de servicio que descargaste de Google Cloud).
  ⚠️ **No viene dentro del zip** (es secreto) → tienes que llevarlo aparte.
- **Python 3.10 o superior** instalado.
- Tu **hoja de Google** ya compartida con la cuenta de servicio como *Editor* (ya hecho ✅).
- Una cuenta de **Telegram**.

## 2. Descomprimir el proyecto
1. Copia **`bot-facturas.zip`** a tu PC (p. ej. a `Documentos`) y **descomprímelo** (clic derecho → *Extraer todo*).
   Te quedará una carpeta **`bot-facturas`**.
2. Copia también el **`credenciales.json`** (estaba en *Descargas*). Pásalo de forma **segura** (USB, tu Drive
   personal…), **no** por chat/email público — da acceso de escritura a la hoja.
   - (Si ves carpetas `__pycache__` dentro, son caché de Python: puedes borrarlas, dan igual.)

## 3. Instalar Python (si no lo tienes)
1. Ve a **python.org/downloads** e instala Python 3.x.
2. En el instalador (Windows), **marca la casilla "Add Python to PATH"** (¡importante!).
3. Comprueba: abre una terminal y escribe `python --version` → debe mostrar 3.10 o más.
   (Si dice que no reconoce `python`, prueba con `py --version`; si tampoco, reinstala marcando "Add to PATH".)

## 4. Colocar credenciales y configuración
1. Mete **`credenciales.json`** dentro de la carpeta **`bot-facturas\config\`**.
2. En `bot-facturas\`, **haz una copia de `.env.example` y renómbrala a `.env`**. Ábrela con el Bloc de notas y
   rellénala:
   ```
   TELEGRAM_BOT_TOKEN=          (lo creas en el paso 5)
   GOOGLE_SHEETS_ID=            (el ID de tu hoja: en la URL .../d/ESTE_ID/edit)
   GOOGLE_CREDENTIALS_PATH=config/credenciales.json
   GOOGLE_SHEETS_RANGE=Tabla de Gastos!A:I
   GOOGLE_AUTH_MODE=service_account
   FACTURAS_ACTIVAS=0
   DRY_RUN=0
   ```
   ⚠️ Tu hoja debe tener una pestaña llamada exactamente **`Tabla de Gastos`**. Si tu pestaña de datos se llama
   distinto, pon ese nombre en `GOOGLE_SHEETS_RANGE` (p. ej. `MiPestaña!A:I`).
3. Haz una copia de **`config\autorizados.example.yaml`** y renómbrala a **`config\autorizados.yaml`** (la
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
Tienes dos formas:
- **Con botones (recomendado):** manda **`/gasto`** al bot y ve eligiendo (tipo → unidad → grupo → categoría); luego escribe el concepto y el importe, y pulsa **✅ Confirmar**.
- **Por texto:** un mensaje con cada dato en una línea:
  ```
  Castores
  Material de unidad
  Cena fin de ronda
  47,30
  ```
En ambos casos debe responder **"✅ Gasto registrado"** y aparecer una **fila nueva** en la hoja (y actualizarse los balances). 🎉
Borra esa fila de prueba cuando quieras.

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
- **Dice "error al registrar el gasto" o no aparece la fila** → comprueba: ¿compartiste la hoja con la cuenta de
  servicio (*Editor*)? ¿`GOOGLE_SHEETS_ID` correcto? ¿la pestaña se llama `Tabla de Gastos` (o ajustaste el rango)?
- **"No se encuentra el fichero de credenciales"** → revisa `GOOGLE_CREDENTIALS_PATH` y que el `.json` esté en
  `config\`.
- **`#N/A` en los balances** → hay una celda con error en las columnas A/C/D de `Tabla de Gastos` (Ctrl+F → `#N/A`).
- (Opcional) Probar la lógica sin Telegram: `.venv\Scripts\python -m pytest` dentro de `bot-facturas`.

## 11. Qué falta / siguientes pasos
- **Fase 2 — Facturas a Drive**: poner `FACTURAS_ACTIVAS=1`, habilitar la **Drive API**, crear una carpeta por
  sección y poner sus IDs en `config\secciones.yaml`. El bot pedirá la foto/PDF y la subirá.
- **Producción**: pasar la cuenta de servicio a la **cuenta del grupo** (o que el administrador del Workspace active
  Cloud) y usar un bot/cuenta de Telegram de la asociación. Solo cambian 2-3 valores del `.env`.
- **Presupuestos automáticos**: ver `google-sheets\RELLENAR-PRESUPUESTO-CON-IA.md`.

> Para entender o cambiar cualquier parte del sistema: **`MANUAL.md`**. Para replicarlo otro año/grupo:
> **`REPLICAR-CON-IA.md`**.
