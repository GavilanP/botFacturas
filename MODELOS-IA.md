# IA local para audio (Whisper + Ollama)

Guía reproducible para dejar funcionando el registro de gastos por **nota de voz**.
Todo corre en la máquina; el audio y los datos **no salen** a ningún servicio externo.

El pipeline tiene dos modelos que corren **en secuencia** (no a la vez):

```
Nota de voz (OGG/Opus) ──▶ Whisper (voz→texto) ──▶ Ollama/LLM (texto→campos) ──▶ propuesta ✅/❌
```

---

## 1. Requisitos del sistema

| Pieza | Para qué | Instalar |
|---|---|---|
| **ffmpeg** | Whisper lo usa para leer el OGG/Opus de Telegram | `brew install ffmpeg` |
| **mlx-whisper** | Voz → texto (optimizado Apple Silicon) | ya en `requirements.txt` |
| **cliente `ollama`** (Python) | Hablar con el servidor de Ollama | ya en `requirements.txt` |
| **Ollama** (servidor) | Corre el LLM que extrae los campos | https://ollama.com (app o `brew install ollama`) |

Las dependencias de Python se instalan con `pip install -r requirements.txt` dentro del `.venv`.

---

## 2. Los dos modelos

### a) Whisper (voz → texto) — se descarga solo
`mlx-whisper` descarga el modelo la primera vez a `~/.cache/huggingface` (disco interno).
No hay que hacer nada manual. Modelo por defecto: `mlx-community/whisper-large-v3-turbo` (~1,6 GB).
Configurable con `WHISPER_MODEL` en `.env` (p. ej. `mlx-community/whisper-medium` si quieres algo más ligero).

### b) LLM (texto → campos) — hay que instalarlo con Ollama
Modelo por defecto del proyecto: **`qwen2.5:7b`** (~4,7 GB, cuantizado). Bueno en español y en
producir JSON; suficiente para extraer 4 campos (sección, categoría, concepto, importe).

```bash
ollama pull qwen2.5:7b
```

Alternativas (cambiar `OLLAMA_MODEL` en `.env`): `qwen2.5:3b` o `llama3.2:3b` (más ligeros y
rápidos), `qwen2.5:14b` (mejor pero ~9,7 GB y carga lenta en 16 GB de RAM).

---

## 3. Dónde se guardan los modelos de Ollama (y cómo cambiar la ruta)

**Importante:** los modelos NO van en la carpeta del proyecto. Ollama tiene **un único almacén
global** y el bot le pide el modelo por NOMBRE (`qwen2.5:7b`) vía `localhost:11434`; no le importa
la ruta física. Así el repo queda limpio (sin GB de blobs) y es portable.

- **Ubicación por defecto:** `~/.ollama/models` (disco **interno**). Es la recomendada: no
  depende de discos externos montados.

- **Cambiar la ruta (p. ej. a un disco externo, si te falta espacio interno):** dos formas.

  1. **Variable de entorno** (para cuando arrancas el servidor desde terminal con `ollama serve`):
     ```bash
     export OLLAMA_MODELS=/ruta/deseada/ollama-models   # ponlo en ~/.zshrc para que persista
     ```
  2. **La app de Ollama (macOS) ignora `~/.zshrc`.** Usa siempre `~/.ollama/models`. Para
     apuntarla a otro disco, sustituye esa carpeta por un enlace simbólico:
     ```bash
     rm -rf ~/.ollama/models                # borra la carpeta/enlace actual (¡ojo con lo que haya!)
     ln -s /Volumes/MiDisco/ollama-models ~/.ollama/models
     ```
     Reinicia la app de Ollama para que tome la nueva ubicación (cerrar y volver a abrir).

- **Verás qué modelos hay** con `ollama list` o `curl -s localhost:11434/api/tags`.

> Nota de este proyecto (2026-07-03): se pasó de un disco externo al interno por defecto.
> Antes `~/.ollama/models` era un symlink a `/Volumes/Disco/ollama-models/models`; se reemplazó
> por una carpeta interna real y se hizo `ollama pull qwen2.5:7b`. Los modelos antiguos siguen en
> el disco externo por si algún día se quieren recuperar (remontar el disco y rehacer el symlink).

---

## 4. Configuración del bot (`.env`)

```dotenv
AUDIO_ACTIVO=1                                      # activa el registro por nota de voz
WHISPER_MODEL=mlx-community/whisper-large-v3-turbo  # modelo de voz→texto
OLLAMA_MODEL=qwen2.5:7b                             # LLM de texto→campos
OLLAMA_HOST=http://localhost:11434                  # servidor de Ollama
```

Con `AUDIO_ACTIVO=0` el bot ignora las notas de voz (y no carga MLX ni Ollama).

---

## 5. Comprobar que funciona

1. Servidor de Ollama arrancado (app abierta o `ollama serve`) y el modelo instalado (`ollama list`).
2. `ffmpeg` disponible (`which ffmpeg`).
3. Arranca el bot (`.venv/bin/python src/bot.py`) con `AUDIO_ACTIVO=1`.
4. En Telegram, manda una nota de voz: «Castores, material de unidad, pinturas para el local,
   cuarenta y siete con treinta euros». El bot responde con la transcripción, la propuesta y los
   botones ✅/❌.

---

## 6. Rendimiento (qué esperar)

- **Primer uso lento:** la primera transcripción y la primera consulta al LLM tras arrancar (o
  tras >5 min de inactividad) tardan más porque cargan el modelo en memoria. En un Mac M1 16 GB:
  Whisper ~pocos segundos ya cargado; el LLM 7B carga en decenas de segundos (el 14B, minutos).
- **Mantener el LLM caliente:** Ollama descarga el modelo de memoria tras ~5 min sin uso
  (`keep_alive` por defecto). Si quieres que el primer audio del día no espere, puedes precargarlo
  o subir el `keep_alive`; a cambio ocupa RAM de forma permanente.
- **Los números** («cuarenta y siete con treinta» → 47,30) los resuelve bien la transcripción y/o
  el LLM, pero el **paso de confirmación ✅/❌** cubre cualquier fallo antes de guardar.
