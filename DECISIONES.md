# Decisiones y opciones — Bot de facturas

> Documento vivo. Recoge lo que vamos pensando, las opciones barajadas y las decisiones
> tomadas sobre la evolución del bot. Se actualiza en cada sesión de trabajo.
>
> Última actualización: 2026-07-02 (rev. 4)

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

## Roadmap de aprendizaje (incremental — cada paso es útil y se termina)

Orden pensado para aprender sin frustrarse: de lo más fundamental/fácil a lo más difícil.

1. **SQLite como fuente de verdad.** El bot escribe en DB local. Primer paso hacia la
   independencia + aprender bases de datos. (Sheets como espejo opcional al principio.)
2. **Web local propia** (FastAPI + SQLite + frontend sencillo) para ver balances. Aprender
   desarrollo web, login, despliegue. Aquí se deja de necesitar Sheets para visibilidad.
3. **IA de audio** (Whisper → parseo → flujo de confirmación existente). Primera victoria de IA.
4. **IA de visión** (OCR/VLM local → extraer campos → confirmar). La más dura, al final.

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

## Decisiones pendientes

- ¿Habrá aparato siempre encendido o todo vive en el Mac? (arranque: todo en el Mac).
- Arrancar el roadmap: **git init** (paso 0) y luego **paso 1 (SQLite como fuente de verdad)**.
- Decidir si Sheets se mantiene como espejo temporal o se retira ya.
- ¿Repo de GitHub privado? (recomendado). El push lo hace el autor cuando quiera.
- Ir colando las mejoras de robustez del tema 1 cuando toque.
