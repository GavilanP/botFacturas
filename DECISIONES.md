# Decisiones y opciones — Bot de facturas

> Documento vivo. Recoge lo que vamos pensando, las opciones barajadas y las decisiones
> tomadas sobre la evolución del bot. Se actualiza en cada sesión de trabajo.
>
> Última actualización: 2026-07-03 (rev. 17)

---

## Objetivo y prioridades del autor (¡clave!)

Declaradas el 2026-07-02. **Reorientan todo el proyecto:**

1. **Aprender** a construir estas cosas (el coste operativo es una ventaja, no una pega).
2. **Privacidad** — preferencia por mantener los datos fuera de terceros (Google, APIs cloud).
3. **No depender de nadie** — autohospedaje, autonomía.
4. **IA local** — poder mandar **fotos o audios** y que un modelo local los reconozca y añada
   el gasto automáticamente.

**Consecuencia:** la recomendación por defecto cambia. La opción D (servidor propio) deja de
ser "sobreingeniería" y pasa a ser **el norte**, porque sus supuestas pegas (esfuerzo, mantener
infra) son justo lo que el autor quiere. Y se sale de Google (Sheets/Drive) y de la API de
Claude, sustituyéndola por IA **local** (esto último ya estaba anticipado como "Fase 2" en
`MANUAL.md`, solo que con API de Claude → ahora modelo local).

---

## Estado actual del proyecto (punto de partida)

Bot de Telegram (Python, `python-telegram-bot`) para registrar gastos del Grupo Scout
Buen Consejo. Dos formas de registrar: flujo guiado con botones (`/gasto`) y atajo por texto.
Valida el mensaje, sube la factura a **Google Drive** (Fase 2, `FACTURAS_ACTIVAS=1`) y añade
una fila a **Google Sheets** (`Tabla de Gastos!A:I`). Sheets también es la interfaz de
tesorería: balances con `SUMIFS`, desplegables dependientes y formato condicional.

Arquitectura actual:

```
Bot Telegram ──> Google Drive (facturas, Fase 2)
            └──> Google Sheets (registro + interfaz de tesorería)
```

---

## Temas discutidos

### 1. Mejoras de robustez y usabilidad del bot (pendientes de decidir)

Detectadas al revisar el código. En orden de valor/esfuerzo:

**Robustez**
1. **Llamadas a Google bloquean el bot** — `sheets.append_fila` y `drive.subir_factura`
   son síncronas dentro de handlers `async`. Con varios usuarios a la vez, el bot se
   congela. Solución barata: `await asyncio.to_thread(...)`.
2. **Fallo a medias = archivo huérfano / duplicado** — si Drive sube pero Sheets falla,
   el usuario reintenta y se duplica. Solución: diario local + reintento (ver punto 4 de
   arquitectura, SQLite).
3. **Avisar al admin de errores** — hoy solo van al log (nadie lo lee en una Raspberry).
   Añadir `ADMIN_CHAT_ID` en `.env` y mandarle el error.
4. **Importe ambiguo** — `_parsear_importe("1.234")` da 1,23 € en vez de 1.234 €.

**Usabilidad**
5. **Alta de usuarios sin reiniciar** — comando `/alta` para admin o recarga del YAML.
6. **Foto descartada en silencio** con `FACTURAS_ACTIVAS=0` — avisar en la confirmación.
7. **Botones caducados** — `KeyError` si se toca un botón de conversación vieja.

**Higiene de código (menor)**
- `validacion._parsear_importe` se llama desde fuera → hacerla pública.
- Falta test del flujo de botones → extraer lógica pura de `confirmar`.

*Prioridad propuesta:* empezar por 1, 2 y 3 (más valor por esfuerzo).

---

### 2. ¿Base de datos propia en vez de Google Sheets?

**Decisión: NO sustituir Sheets por una DB propia.** Razones:

- Sheets no es solo almacenamiento, es la **interfaz de tesorería** (balances, desplegables,
  formato condicional, edición manual de la columna "Factura"). Sustituirla obligaría a
  construir una interfaz web de edición = mucho más código que todo el bot actual.
- Añade infraestructura que mantener (backups, administración) en un entorno de voluntarios.
- Al volumen de un grupo scout (decenas/cientos de filas/año), los problemas de Sheets-como-BD
  no aplican.

**Cuándo sí tendría sentido una DB:** consultas complejas/históricos multi-año, multi-grupo
(multi-tenant), o si la hoja se corrompe por ediciones manuales.

**Opción intermedia recomendada: SQLite como diario local + Sheets como vista.**
El bot escribe primero en SQLite (un fichero, cero admin, incluido en Python) y luego replica
a Sheets. Ventajas:
1. Resuelve la fiabilidad (punto 2 de robustez): si Google falla, el gasto ya está guardado y
   se reintenta después. Nunca se pierde un registro.
2. Fuente de verdad auditable (si alguien rompe una fila en Sheets, tienes el original).
3. Consultas futuras (históricos, informes, Fase 2 de IA) sin depender de la API de Google.
4. Tesorería sigue trabajando en su hoja igual que hasta ahora.

Coste estimado: ~60-80 líneas. Sustituiría al `pendientes.jsonl` propuesto en el punto 2.

**¿Qué motor de base de datos? (decidido 2026-07-02)**

| Motor | Qué es | Veredicto |
|---|---|---|
| **SQLite** ⭐ | Un fichero, sin servidor, incluida en Python. La DB más desplegada del mundo. Open source (dominio público). SQL estándar + ACID. | **EMPEZAR AQUÍ.** Cero admin, perfecta para aprender y para el volumen scout. No es un "juguete": es un destino legítimo. |
| **PostgreSQL** | La DB open source cliente-servidor más potente/moderna. | **Graduación futura.** Cuando exista el servidor/web (pasos 2-4) y haga falta concurrencia robusta o funciones avanzadas. |
| MariaDB/MySQL | Cliente-servidor clásica. | Válida, pero Postgres es mejor inversión de aprendizaje. |
| DuckDB | Muy moderna, pero **analítica** (OLAP). | No encaja: es para analizar millones de filas, no para registrar gastos uno a uno. |

- **Regla:** no elegir Postgres "por si acaso" ahora — administrar un servidor cuando basta un
  fichero es complejidad prematura. Escribir **SQL estándar** en SQLite hace fácil la migración
  a Postgres el día que el proyecto lo pida de verdad.
- El SQL aprendido con SQLite transfiere casi 1:1 a Postgres.

---

### 3. ¿Web con GitHub para dar visibilidad?

**Idea: web de solo lectura para que el grupo vea los presupuestos**, sin dar acceso a la hoja.
No sustituye a Sheets ni a la DB; es una capa de visualización.

**Cómo encajaría (GitHub Pages, hosting estático gratis):**
1. El bot (o tarea nocturna) genera un `datos.json` con **agregados** (gastado por
   sección/categoría/trimestre, presupuestado vs gastado).
2. Se sube al repositorio (commit automático o API de GitHub).
3. Página estática (HTML + JS con gráficas) lee el JSON y pinta los balances.

**Punto delicado — privacidad:** GitHub Pages es **público** (las Pages privadas requieren
Enterprise). Por tanto:
- **Publicable:** totales agregados por sección/categoría, % de presupuesto consumido.
- **NO publicar:** columna "Quién" (nombres), conceptos individuales, enlaces a facturas.
- Si el JSON lleva solo agregados, el problema de privacidad desaparece de raíz.
- Filas detalladas exigirían autenticación → fuera de GitHub Pages (necesitaría servidor).

**Arquitectura completa propuesta:**

```
Bot Telegram ──> SQLite (fuente de verdad, local)
                   ├──> Google Sheets (interfaz de tesorería, edición)
                   └──> datos.json agregado ──> GitHub Pages (visibilidad, solo lectura)
```

**Pregunta abierta (para decidir el alcance de la web):**
¿Para quién es la visibilidad?
- Solo los ~20 scouters → quizá un comando `/balance` en el propio bot basta (usa la lista de
  autorizados como control de acceso, sin repo/web/privacidad que gestionar).
- Público más amplio (familias, transparencia) o gráficas ricas → tiene sentido la web.

---

### 4. ¿Mini-servidor propio con DB + web como interfaz de gestión?

Opción "completa": la web deja de ser un escaparate y pasa a ser **la interfaz de gestión**,
sustituyendo a Google Sheets. Stack sencillo: FastAPI/Flask + SQLite/Postgres + frontend con
login. El balance se llevaría desde ahí.

**Veredicto: técnicamente viable, pero el coste está en la operación, no en el código.**

Escribir la app es lo barato (un prototipo en un fin de semana). Lo que pesa a años vista es
lo que Google da **gratis** hoy y habría que asumir:

- **Estar online 24/7** — el servidor tiene que vivir en algún sitio. Raspberry en casa =
  frágil (luz, internet doméstico, IP dinámica, sysadmin = tú). VPS (~5 €/mes) = fiable pero
  hay que administrarlo (actualizaciones, HTTPS, seguridad).
- **Seguridad** — web pública con login + DB con datos económicos = superficie de ataque real.
  Pasas a ser responsable de login, HTTPS, backups, parcheo de dependencias. Sheets lo resuelve.
- **Backups** — con Sheets son implícitos; con DB propia, si no los montas y los pruebas, un día
  pierdes las cuentas.
- **Bus factor (lo más importante)** — al dejar el grupo, alguien hereda servidor + DB +
  despliegue + web. Con Sheets, la siguiente persona solo abre la hoja. En una asociación de
  voluntarios esto pesa mucho.
- **Pérdida concreta** — tesorería ya sabe usar una hoja de cálculo; habría que reconstruir todo
  lo que Sheets regala (editar, ordenar, filtrar, exportar, fórmulas ad-hoc).

**Cuándo SÍ lo haría:**
- Si es también un proyecto que quieres construir y mantener (hobby/aprendizaje), asumiendo
  operarlo.
- Si hay sucesor o "responsable técnico" estable en el grupo.
- En ese caso: **hosting gestionado (PaaS + Postgres gestionado), NO Raspberry en casa**, y
  backups desde el día uno.

**Recomendación honesta:**
- Objetivo = fiabilidad + transparencia con mínimo riesgo → gana la combinación del tema 3
  (SQLite diario + Sheets interfaz + web solo-lectura con agregados). ~80% del valor, ~20% del
  riesgo operativo. Nadie mantiene un servidor vivo.
- Objetivo = app propia unificada y dispuesto a operarla → adelante, pero con hosting gestionado
  y backups desde el principio.

**Preguntas que deciden el rumbo:**
1. ¿Esto es "infraestructura que debe sobrevivirte" o "proyecto que quieres construir y cuidar"?
2. ¿Quién mantendría el servidor dentro de tres años?

---

### 5. IA local para reconocer fotos y audios (objetivo principal del autor)

Dos tareas muy distintas, una bastante más fácil que la otra:

**Audio → gasto: MUY factible (empezar por aquí).**
- Whisper local (whisper.cpp / faster-whisper / mlx-whisper) transcribe español muy bien,
  incluso modelos pequeños. En Mac con Apple Silicon corre rápido.
- Nota de voz → transcripción → modelo pequeño local (Llama 3.2, Qwen2.5 vía Ollama) extrae
  los campos (sección/categoría/concepto/importe) con prompt de salida JSON.

**Modelos concretos para AUDIO en Mac M1 16 GB (prioridad del autor).**

El pipeline de audio tiene DOS componentes:

*1) Voz → texto (Speech-to-Text): Whisper.*
| Herramienta | Notas |
|---|---|
| **mlx-whisper** | Optimizado para Apple Silicon (framework MLX). El más rápido en tu M1. `pip install`. Recomendado. |
| **whisper.cpp** | Port en C++ con Metal. Muy eficiente, sin Python. Buena alternativa. |
| **faster-whisper** | Multiplataforma; en Mac tira sobre todo de CPU pero va bien. |

Modelo Whisper a usar: **`large-v3-turbo`** (excelente y rápido, ~1,5 GB) o **`medium`**. Para
español, de `small` hacia arriba va bien; `large-v3`/turbo es el mejor. Footprint trivial en 16 GB.

*2) Texto → campos (parseo a JSON): LLM pequeño local vía Ollama.*
| Modelo | Tamaño (Q4) | Notas |
|---|---|---|
| **Qwen2.5 7B** | ~4,7 GB | Sweet spot. Muy bueno en JSON/instrucciones y español. Recomendado. |
| **Qwen2.5 3B** / **Llama 3.2 3B** | ~2 GB | Más ágil; suficiente para esta tarea acotada. |
| **Llama 3.1 8B** | ~5 GB | Buen generalista, español sólido. |

**Ollama** = forma más fácil de correr el LLM (`ollama pull qwen2.5:7b`). Whisper (~1,5 GB) + LLM
7B (~5 GB) a la vez ≈ 8-9 GB → **caben de sobra en 16 GB**. Si va justo, usar LLM 3B.

**Modelos Ollama YA INSTALADOS (verificado 2026-07-02, Ollama v0.17.7):**
`deepseek-coder:6.7b`, `llama3:8b`, `phi3:latest`, **`qwen2.5:14b`**, `qwen2.5-coder:7b`.
- **DECISIÓN: usar `qwen2.5:14b` para el parseo texto→campos.** Ya instalado y superior a la 7B
  recomendada. En 16 GB ocupa ~9 GB al cargar; como Whisper y el LLM corren **en secuencia** (no
  a la vez), no compiten por memoria. No hay que descargar nada para el LLM.
- Suplentes: `llama3:8b` (generalista), `phi3` (ligero, español más flojo). Los `*-coder` son
  para programar, no para esta tarea.
- **Falta instalar Whisper** (no es de Ollama; Ollama solo hace texto): `mlx-whisper` vía pip o
  `whisper.cpp`, + `ffmpeg` (`brew install ffmpeg`). Se hará en el paso 3, no ahora.
- Nota: el servidor de Ollama no estaba arrancado; se arranca con la app o `ollama serve` cuando
  toque.

*Alternativa sin LLM (arranque más simple):* Whisper + `rapidfuzz` (mapear categoría) + regex
para el importe. Menos flexible con frases libres, pero cero dependencia de un LLM. El LLM maneja
mucho mejor "me gasté 47 y pico en...".

**Gotchas del audio:**
- Las notas de voz de Telegram vienen en OGG/Opus → hace falta **ffmpeg** para convertir
  (Whisper lo usa por debajo).
- Los **números** son lo delicado: Whisper suele transcribir "cuarenta y siete con treinta" en
  palabras; el LLM las convierte a 47,30 pero puede fallar → el **paso de confirmación** lo
  cubre.

**Sub-plan del paso 3 (audio):** (a) Whisper transcribiendo notas de voz en español; (b) parseo
del texto → campos (empezar simple o directo con LLM); (c) enchufar al flujo de confirmación
existente.

**Stack de arranque recomendado:** mlx-whisper (`large-v3-turbo`) + Ollama (Qwen2.5 7B) +
rapidfuzz para el mapeo de categorías.

**Ubicación de los modelos (verificado 2026-07-02):**
- Ollama usa `OLLAMA_MODELS=/Volumes/HDD/ollama-models` → los modelos están en un **disco
  externo** (`~/.ollama/models` vacío). Disco interno: solo ~25 GB libres.
- **Regla:** los modelos NUNCA van en la carpeta del proyecto. El código habla con Ollama por
  `localhost:11434` y pide el modelo por NOMBRE (`qwen2.5:14b`); no le importa la ruta física.
- Tenerlos en el disco externo es razonable (poco espacio interno), PERO ⚠️ **el disco debe
  estar montado o la IA falla**. Para el futuro 24/7, el modelo debe estar en almacenamiento
  siempre disponible del aparato que ejecute el bot.
- Whisper (mlx-whisper) descarga a `~/.cache/huggingface` (disco INTERNO, ~1,5 GB). Reubicable
  con `HF_HOME` si hace falta espacio.

**Dónde se implementa el audio en el código (plan):**
- `src/transcribir.py` (NUEVO): audio bytes → texto (Whisper).
- `src/interpretar.py` (NUEVO): texto → campos del gasto (Ollama qwen2.5:14b + rapidfuzz).
  Separar "llamar al modelo" (no testeable) de "validar/mapear campos" (puro → testeable).
- `src/bot.py`: handler nuevo `filters.VOICE` → transcribir → interpretar → botones ✅/❌ (ya
  existen) → `_escribir_fila` → SQLite.
- Config: `AUDIO_ACTIVO=1`, `WHISPER_MODEL`, `OLLAMA_MODEL`, `OLLAMA_HOST` en `.env`.
- Dependencias nuevas: `mlx-whisper`, cliente `ollama` (pip) → requirements.txt.
- Primer sub-paso: instalar mlx-whisper y crear transcribir.py; validar transcripción ES antes
  de seguir.

**Gastos incompletos por audio — DISEÑO PEDIDO POR EL AUTOR (2026-07-02, AÚN NO implementado):**

Comportamiento deseado: si el audio no trae toda la información, **guardar lo que sí hay** y
responder con un mensaje que liste **exactamente qué falta**; lo que falte se completará después
por otra vía (edición). Ejemplo del autor: "si falta la fecha, que se guarde todo menos la fecha
y que el mensaje diga lo que falta".

Cómo implementarlo cuando toque:
1. **`interpretar.py` ya lo prepara:** la dataclass `Propuesta` lleva `faltan: list[str]` con los
   campos que el modelo no pudo extraer (devuelve `null`). Esa lista alimenta el mensaje.
2. **Esquema:** añadir a la tabla `gastos` una columna `estado TEXT NOT NULL DEFAULT 'completo'`
   (`'incompleto'` si falta algo) y permitir NULL en los campos no obligatorios; migración con
   `ALTER TABLE`. El importe seguiría siendo obligatorio de facto (sin importe apenas hay gasto),
   pero guardable como incompleto si el autor lo prefiere.
3. **Mensaje de vuelta:** tras guardar, el bot responde "✅ Guardado (incompleto). Falta: fecha,
   categoría…" usando `Propuesta.faltan`.
4. **Completar después:** un comando `/pendientes` que liste los gastos con `estado='incompleto'`
   y un flujo de edición con botones (o la futura web local) para rellenar lo que falte.
5. **Nota sobre la fecha:** hoy la fecha NO se dicta: se pone sola (fecha de envío). Si se quiere
   poder dictar "ayer" o "el sábado", sería una extensión de `interpretar.py` (extraer fecha
   relativa) — decisión aparte.

Estado: SOLO documentado. Prioridad actual = pipeline de audio (transcribir + interpretar).

**Paso 3 (audio) — AVANCE 2026-07-02:**
- Instalado: `mlx-whisper 0.4.3`, `ollama 0.6.2` (cliente Python), `rapidfuzz 3.14.5` → en
  requirements.txt.
- Creados `src/transcribir.py` (voz→texto) y `src/interpretar.py` (texto→campos, con
  `Propuesta.faltan` preparando los gastos incompletos). 11 tests nuevos de la parte pura
  (29 en total, todos pasan).
- ✅ **Whisper VERIFICADO en el M1**: audio de prueba en español ("cuarenta y siete euros con
  treinta céntimos en pinturas...") → transcrito como «47,30 euros en pinturas para el local de
  Castores, categoría material de unidad». Los números en palabras los convierte la propia
  transcripción. Modelo large-v3-turbo descargado (~1,6 GB, disco interno).
- ⚠️ **Hallazgo:** `OLLAMA_MODELS` en `~/.zshrc` apunta a `/Volumes/HDD/ollama-models`, que YA NO
  EXISTE (el disco hoy se llama "Disco"). Los modelos reales están en
  `/Volumes/Disco/ollama-models/models`, enlazados desde `~/.ollama/models` (symlink). **Arreglo
  pendiente (lo hace el autor):** editar la línea 1 de `~/.zshrc` →
  `export OLLAMA_MODELS=/Volumes/Disco/ollama-models/models` (o borrarla: el symlink ya cubre).
- Pendiente: probar `interpretar.py` end-to-end con qwen2.5:14b (necesita `ollama serve`
  corriendo y el disco "Disco" montado) y cablear el handler de voz en bot.py.

**Paso 3 (audio) — HANDLER CABLEADO Y VERIFICADO END-TO-END (2026-07-03):**
- `src/bot.py`: nuevo `manejar_audio` (handler `filters.VOICE`) → descarga la nota de voz →
  `transcribir_bytes` (Whisper) → `interpretar` (Ollama qwen2.5:14b) → muestra la propuesta con
  botones ✅/❌ → `confirmar_audio` guarda en SQLite vía `_escribir_fila`. Las llamadas a Whisper
  y Ollama van con `asyncio.to_thread` para no bloquear el bot. Si la propuesta está incompleta,
  hoy responde con lo entendido + qué falta y remite a `/gasto` (guardado incompleto: aún NO).
- `/start` ahora incluye una guía de qué decir en el audio (sección, categoría, concepto,
  importe) con ejemplos, solo si `AUDIO_ACTIVO=1`.
- `src/config.py`: nuevos `audio_activo` (env `AUDIO_ACTIVO`), `whisper_model`, `ollama_model`,
  `ollama_host`. `.env.example` documenta las cuatro.
- ✅ **VERIFICADO en Telegram real**: nota de voz «Castores, material de unidad, pinturas para el
  local, cuarenta y siete con treinta» → propuesta correcta → confirmada → `Gasto #2` guardado en
  la DB (Castores / Material de unidad / pinturas para el local / 47,30 €). 29 tests siguen
  pasando.
- ⚠️ **Observación de rendimiento**: la PRIMERA transcripción tardó ~3 min (carga inicial de
  `large-v3-turbo` en memoria + transcribir). Pendiente medir el 2º audio con el modelo ya
  cargado; si sigue lento, valorar modelo Whisper más pequeño (`medium`/`small`) o mejorar el
  mensaje "🎙️ Escuchando…". Durante la espera el único feedback es ese aviso.
- Pendiente aún: gastos incompletos (guardar lo que hay + listar lo que falta), tests del flujo
  de audio de bot.py, y el arreglo de `OLLAMA_MODELS` en `~/.zshrc` (lo hace el autor).

**Paso 3 (audio) — PULIDO 2026-07-03:**
- **Feedback de progreso:** `manejar_audio` edita el mensaje por fases («Transcribiendo…» →
  «Interpretando…») en vez de un único «Escuchando…».
- **Gastos incompletos IMPLEMENTADO** (lo pedido por el autor): si el audio no trae todo pero
  SÍ el importe (obligatorio, es el dato mínimo de un gasto), se guarda como `incompleto` con los
  campos que faltan a `""`, tras confirmar con botón «✅ Guardar (incompleto)». Mensaje lista qué
  falta. Si falta el importe, no se guarda y se pide repetir. Nuevo comando **`/pendientes`** que
  lista los incompletos. Edición para completarlos: aún NO (futuro).
  - DB: nueva columna `estado TEXT NOT NULL DEFAULT 'completo'` con migración idempotente
    (`_migrar` + `ALTER TABLE ADD COLUMN`, se probó sobre la DB real sin perder filas). NO hizo
    falta reconstruir la tabla ni columnas NULL: como el importe es obligatorio, los campos que
    faltan se guardan como `""` (cumplen el `NOT NULL` de texto).
  - `db.py`: `guardar_gasto`/`registro_de` con parámetro `estado`; nueva `listar_pendientes`.
  - Tests: 7 nuevos (estado por defecto, guardar incompleto, listar pendientes, migración de DB
    antigua, `_resumen_parcial`). **36 tests pasan.**
- **Rendimiento — CAUSA Y ARREGLO:** medido en Telegram, la lentitud (~3 min) del primer audio
  NO era Whisper (que ya cargado tarda ~5 s), sino la **carga en frío del LLM `qwen2.5:14b`**
  (~9,7 GB) en Ollama. **DECISIÓN: bajar a `qwen2.5:7b`** (~4,7 GB). Interpretación con carga en
  frío: **8,5 s** (vs 3 min 13 s del 14b), extracción correcta. Cambiado el modelo por defecto en
  `interpretar.py` y `.env`.
- **Almacén de Ollama movido al disco INTERNO** (a petición del autor, para no depender del disco
  externo): `~/.ollama/models` era un symlink a `/Volumes/Disco/ollama-models/models`; se
  reemplazó por carpeta interna real y se hizo `ollama pull qwen2.5:7b` (4,4 GB; ~16 GB internos
  libres). Los 23 GB de modelos viejos siguen en el disco externo (recuperables remontando +
  rehaciendo el symlink). La app de Ollama ignora `~/.zshrc`; se comentó allí la línea muerta
  `OLLAMA_MODELS=/Volumes/HDD/...`. **Regla mantenida:** los modelos NO van en el repo; Ollama los
  sirve por nombre vía localhost.
- **Doc nueva `MODELOS-IA.md`:** guía reproducible (requisitos, instalar Whisper/LLM, cómo cambiar
  la ruta del almacén interno/externo, config `.env`, verificación, rendimiento).

**Paso 3 (audio) — CATÁLOGO EN EL PROMPT DEL LLM 2026-07-03:**
- **Problema detectado:** el mapeo de categorías dependía del fuzzy (`rapidfuzz`) sobre el texto
  libre del modelo, y daba coincidencias CONFIADAMENTE ERRÓNEAS con variaciones semánticas:
  «comida de los monitores» → «Juegos de grupo», «seguro de la federación» → «Juegos de grupo»
  (ambas mal), mostradas como aviso difuso como si estuvieran bien.
- **Arreglo (idea del autor):** darle al modelo el **catálogo oficial de categorías por sección**
  como contexto en el prompt (`construir_prompt` + `_catalogo_texto`), pidiéndole que COPIE
  EXACTAMENTE la categoría de la lista que mejor encaje semánticamente (aunque se diga en plural,
  sin tildes u otras palabras) o `null` si ninguna encaja. El LLM entiende la semántica; el fuzzy
  solo comparaba letras.
- **Verificado:** «comida de los monitores» → «Comidas scouters», «seguro de la federación» →
  «Seguros EdM», «excursiones de unidad» → «Excursión de unidad», «material» → «Material de
  unidad». Y categorías inexistentes («gasolina») → `null` → flujo incompleto (no se inventa).
  Ya no salen avisos difusos porque devuelve el nombre canónico (casa exacto). Tiempos ~5-6 s.
- Test nuevo de `construir_prompt` (incluye el catálogo). 37 tests pasan. El fuzzy de
  `casar_con_catalogos` se mantiene como red de seguridad para erratas menores.

**Foto de ticket → gasto: se puede, pero es lo difícil.**
- Los modelos de visión pequeños fallan sobre todo en el dato crítico: el importe.
- Dos caminos: (a) OCR en el dispositivo (macOS tiene OCR nativo muy bueno vía Vision) +
  parseo del texto; (b) modelo de visión local (Qwen2-VL, MiniCPM-V, moondream).
- No esperar perfección.

**Patrón que lo hace fiable: la IA PROPONE, el usuario CONFIRMA.**
- No hace falta 100% de acierto si hay confirmación de un toque.
- El bot **ya tiene ese flujo** (`recibir_importe` → resumen → ✅/❌ en `bot.py`). La IA solo
  rellena los campos antes de mostrar el resumen. Encaja directamente.
- Mapear texto libre → taxonomía propia: `rapidfuzz` (ya previsto en el MANUAL) + opcional LLM.

**Tensión de hardware a tener presente:**
- IA local quiere máquina con potencia (Mac Apple Silicon ideal).
- Bot 24/7 quiere aparato de bajo consumo siempre encendido (Raspberry) → pero la Raspberry
  no mueve modelos de visión.
- Decisión inicial: **arrancar todo en el Mac**; separar "siempre encendido" de "cerebro de
  IA" más adelante si hace falta.

**Hardware confirmado (2026-07-02): Mac M1, 16 GB RAM.** Máquina sólida para esto:
- **Whisper** (audio): perfecto. `mlx-whisper` (optimizado Apple) o `faster-whisper`; modelos
  base/small instantáneos, medium/large-v3 asumibles. Español muy bueno.
- **LLM de parseo** (texto → campos JSON): Qwen2.5 7B o Llama 3.1 8B cuantizados van cómodos en
  16 GB; 3B aún más ágil. Vía **Ollama** (fácil) o MLX.
- **Visión** (tickets): Qwen2-VL 7B cuantizado es viable (algo justo pero va), o 2B holgado;
  MiniCPM-V, moondream. Además, **OCR nativo de macOS (Vision framework)**: on-device, gratis,
  sin modelo, muy buena calidad de texto → buena opción para tickets.
- Pendiente aún: ¿algún aparato siempre encendido (Raspberry/mini-PC) o de momento solo el Mac?
  → Decisión inicial: **todo en el Mac** y ya se separará si hace falta.

---

## Próximos pasos inmediatos (resumen)

**Ahora mismo → Paso 1: SQLite como fuente de verdad.** El bot escribe cada gasto en una DB
local (`sqlite3`, ya viene con Python).
- Punto de enganche ideal: la función **`_escribir_fila`** en `bot.py` es el ÚNICO sitio donde
  ambos flujos (texto y botones) persisten el gasto. Añadir ahí la escritura en DB cubre los dos.
- Subtareas: crear `src/db.py` (conexión + tabla `gastos` + función `guardar_gasto`); llamarla
  desde `_escribir_fila`; respetar `DRY_RUN`.
- Decisión a tomar: ¿DB **como único** destino, o **DB + Sheets como espejo** durante la
  transición? (recomendado: DB + espejo al principio, para no perder la interfaz de tesorería
  de golpe).
- Opcional: migrar las filas que ya existan en Sheets a la DB.

**En paralelo / cuando apetezca (tareas sueltas):**
- Crear repo **privado en GitHub** + `push` (backup online + control de tareas).
- Mejoras de robustez rápidas del tema 1: `asyncio.to_thread` en las llamadas a Google,
  aviso de errores al admin.

**Después:** Paso 2 (web local) → Paso 3 (IA audio). ~~Paso 4 (IA visión)~~ DESCARTADO por el
autor (2026-07-02): la IA de visión (que un modelo *lea* la foto) queda para futuras versiones,
fuera de los planes actuales.

**Guardar fotos de facturas (sin IA que las lea):** la distinción importa — descartar la IA de
visión NO impide adjuntar la foto como archivo. **SQLite ya admite fotos** (columna `BLOB`); no
hace falta otro motor. Dos enfoques:
- **A. BLOB en la DB:** los bytes dentro de la tabla. Todo en un fichero (un solo backup, portable).
  Contra: el `.db` crece con fotos grandes.
- **B. Foto en disco + ruta en la DB** (⭐ recomendado por sencillez): imagen en `data/facturas/`,
  en la DB solo la ruta. DB pequeña y rápida; contra: respaldar dos cosas.
- Decisión pendiente si/cuando se reactive el adjuntar facturas (hoy `FACTURAS_ACTIVAS=0`).

---

## Roadmap de aprendizaje (incremental — cada paso es útil y se termina)

Orden pensado para aprender sin frustrarse: de lo más fundamental/fácil a lo más difícil.

1. ✅ **SQLite como fuente de verdad.** HECHO (2026-07-02). El bot escribe en DB local. Primer
   paso hacia la independencia + aprender bases de datos.
2. **Web local propia** (FastAPI + SQLite + frontend sencillo) para ver balances. Aprender
   desarrollo web, login, despliegue. Aquí se deja de necesitar Sheets para visibilidad.
   ← **SIGUIENTE PASO MAYOR.**
3. ✅ **IA de audio** (Whisper → parseo → flujo de confirmación existente). HECHO y verificado
   end-to-end (2026-07-03). Primera victoria de IA. Pulido pendiente: rendimiento y gastos
   incompletos.
4. ~~**IA de visión**~~ — DESCARTADA por el autor (2026-07-02), a futuras versiones. Nota:
   *guardar* la foto como adjunto (sin IA) sigue siendo opción; ver tema 5.

Nota: las mejoras de robustez del tema 1 (asyncio.to_thread, aviso al admin) se pueden ir
colando en cualquier momento; el paso 1 (SQLite) ya resuelve la fiabilidad del tema 1.2.

---

### 6. GitHub: control de versiones y hosting (aclaración importante)

Malentendido común a deshacer: **GitHub NO puede alojar la app dinámica** (FastAPI + base de
datos + IA). Eso corre en TU máquina. GitHub sirve para dos cosas distintas:

**a) Guardar el código y su historial (SÍ, y muy recomendable).**
- **Git** = control de versiones en tu ordenador (historial de cambios, volver atrás).
- **GitHub** = copia de ese historial online (backup + compartir) + **Issues/Projects** para
  llevar el control de avances y tareas. Encaja perfecto con "control de avances, versiones".
- Repo **privado** recomendado (por privacidad). Público también valdría si no hay secretos.
- **NUNCA subir secretos:** `.env`, credenciales JSON, `token.json`, `autorizados.yaml`,
  `secciones.yaml`, datos reales. El `.gitignore` del proyecto **ya los excluye**. `DECISIONES.md`
  sí se puede subir (no tiene secretos).

**b) Alojar una web (GitHub Pages): SOLO webs ESTÁTICAS.**
- Pages sirve HTML/CSS/JS fijos; **no** ejecuta Python ni tiene base de datos.
- Podría alojar SOLO la web de solo-lectura si esta lee un `datos.json` de agregados (tema 3).
- Pero Pages es **público** → choca con la prioridad de privacidad salvo que publiques solo
  agregados anónimos.

**Conclusión coherente con las prioridades (privacidad + independencia):**
- Usar GitHub **solo para código + historial + backup** (repo privado) y para llevar tareas.
- Servir la web **desde tu propia app** (FastAPI puede servir las páginas del balance él mismo).
  Así todo queda autohospedado y privado; **no hace falta GitHub Pages**.
- GitHub Pages queda como opción futura *solo si* algún día quieres una página pública de
  transparencia con datos agregados.

**Estado actual:** la carpeta **todavía NO es un repositorio git** (`git init` pendiente). Primer
paso natural: `git init` local + verificar `.gitignore` + primer commit. El remoto en GitHub
(cuenta/push) lo haría el autor cuando quiera.

---

## Comparativa rápida de arquitecturas

| Opción | Fuente de verdad | Interfaz de gestión | Visibilidad | Riesgo operativo | Esfuerzo |
|---|---|---|---|---|---|
| **A. Actual** | Sheets | Sheets | — | Muy bajo | — |
| **B. Diario + web solo-lectura** (temas 2+3) | SQLite | Sheets | Web agregada (GitHub Pages) | Bajo | Medio |
| **C. Solo `/balance` en el bot** | SQLite/Sheets | Sheets | Comando en Telegram | Muy bajo | Bajo |
| **D. Mini-servidor completo** (tema 4) | DB propia | Web propia | Web propia | Alto | Alto |

*Recomendada dadas las prioridades del autor (aprender + privacidad + independencia + IA local):
**D como objetivo**, alcanzada de forma incremental pasando por B (ver roadmap). El único cuidado
que mantengo de la opción D: hacerlo por pasos para terminar y aprender, y tener export/backup
para que un mal día no se lleve las cuentas.*

---

## Decisiones tomadas

- (2026-07-02) La decisión previa de "no sustituir Sheets por DB propia" queda **matizada**: era
  válida para el objetivo "que solo funcione". Con las prioridades reales del autor (aprender,
  privacidad, independencia, IA local), el objetivo pasa a ser la **opción D** (stack propio con
  DB + web + IA local), alcanzada de forma incremental por el roadmap.
- (2026-07-02) La IA será **local** (Whisper + modelo pequeño vía Ollama / OCR nativo), no la API
  de Claude, por la prioridad de privacidad.
- (2026-07-02) Patrón de IA: **propone y el usuario confirma**, reutilizando el flujo de botones
  existente.
- (2026-07-02) **DB-only:** el bot guardará SOLO en SQLite, sin espejo a Sheets. El autor
  quiere centrarse exclusivamente en la base de datos en esta fase. Consecuencia: el bot ya no
  necesita credenciales de Google ni `GOOGLE_SHEETS_ID` para funcionar (Drive solo si
  `FACTURAS_ACTIVAS=1`).
- (2026-07-02) Motor: **SQLite** ahora, PostgreSQL como graduación futura. Escribir SQL estándar.
- (2026-07-02) **Paso 0 HECHO: repositorio git inicializado** (rama `main`, primer commit
  `512a889`). Verificado que los secretos (`.env`, clave JSON de cuenta de servicio,
  `autorizados.yaml`) quedan fuera. Añadido `.claude/` al `.gitignore`. Falta crear el repo
  remoto en GitHub y hacer `push` (lo hará el autor con su cuenta).

## Paso 1 (SQLite) — IMPLEMENTADO (2026-07-02)

- `src/db.py` (nuevo): `init_db`, `guardar_gasto`, `registro_de`. Conexión por operación con
  `contextlib.closing` (cierre garantizado) + `with con` (commit transaccional).
- `src/bot.py`: `_escribir_fila` guarda en SQLite; `init_db` al arrancar (salvo DRY_RUN);
  se quitó el servicio de Sheets; ya no importa `sheets`.
- `src/config.py`: nuevo `db_path` (env `DB_PATH`, def. `data/gastos.db`); `validar_config` ya no
  exige Google en modo solo-DB.
- Tests: `tests/test_db.py` (guardar/recuperar, ids, idempotencia) y `tests/test_config.py`
  (solo-DB no exige Google). **18 tests pasan.**
- `.gitignore`: ignora `data/`, `*.db`, `*.sqlite*`. `.env.example`: documenta `DB_PATH`, marca
  Sheets como legacy.
- **Revisión ultracode (workflow adversarial, 14 agentes):** 5 hallazgos reales corregidos
  (cierre de conexión SQLite, doble llamada en config, init_db en DRY_RUN, falta de test solo-DB,
  `.env.example` desactualizado). 3 descartados como falsos positivos.

## Decisiones pendientes

- ¿Habrá aparato siempre encendido o todo vive en el Mac? (arranque: todo en el Mac).
- ~~git init (paso 0)~~ ✅ hecho. Siguiente: crear repo remoto en GitHub + `push`, y luego
  **paso 1 (SQLite como fuente de verdad)**.
- Decidir si Sheets se mantiene como espejo temporal o se retira ya.
- ¿Repo de GitHub privado? (recomendado). El push lo hace el autor cuando quiera.
- Ir colando las mejoras de robustez del tema 1 cuando toque.
