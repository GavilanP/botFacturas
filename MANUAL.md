# Manual del sistema — Bot de facturas + hoja de gastos

Grupo Scout Buen Consejo. Documento para **entender el sistema** y, sobre todo, **cómo cambiar cada cosa** en el
futuro. Si retomas esto (tú, otra persona o Claude en otra sesión), **empieza por aquí**.

---

## 1. Qué hace el sistema

1. Un **bot de Telegram**: un scouter envía una factura (foto/PDF) con el texto
   `SECCIÓN | CATEGORÍA | CONCEPTO | IMPORTE`. El bot valida, sube la foto a **Google Drive** (carpeta de la
   sección) y añade una fila a **Google Sheets** (`Tabla de Gastos`).
2. Una **Hoja de Google** con:
   - `Tabla de Gastos`: el registro de gastos (donde escribe el bot, A:I).
   - `Catálogo`: las categorías por unidad (alimenta los desplegables dependientes).
   - `Balance Unidades`, `Balance Grupo`, `Balance Campamento`: comparan **Presupuestado vs Gastado** (el Gastado
     se suma solo de `Tabla de Gastos`).

El bot **no clasifica** nada (eso es fase 2): solo valida, reparte y confirma.

---

## 2. Piezas y archivos

```
bot-facturas/
├── src/                       # el bot (Python)
│   ├── bot.py                 # punto de entrada (long polling)
│   ├── validacion.py          # parseo + validación del mensaje
│   ├── catalogos.py           # carga secciones/categorías desde YAML
│   ├── config.py              # carga .env + catálogos + autorizados
│   ├── autenticacion.py       # credenciales Google (service_account | oauth)
│   ├── drive.py / sheets.py   # subida a Drive / escritura en Sheets
│   └── util.py                # normalización y cálculo de Trimestre
├── config/
│   ├── secciones.yaml         # sección -> carpeta de Drive  (real, no se versiona)
│   ├── categorias.yaml        # categorías por sección  ← FUENTE DE VERDAD del bot
│   └── autorizados.yaml       # chat_id -> nombre  (real, no se versiona)
├── google-sheets/
│   ├── dropdowns-dependientes.gs   # Apps Script: crea hojas, desplegables y balances
│   ├── catalogo.csv                # opcional (el script genera el Catálogo solo)
│   └── GUIA-hoja-google-sheets.md  # cómo montar la hoja
├── .env                       # secretos (token, IDs, credenciales)  ← no se versiona
└── MANUAL.md                  # este documento
```

> **Dos fuentes de verdad que hay que mantener sincronizadas** cuando cambian las categorías:
> 1. `config/categorias.yaml` → lo que **valida el bot**.
> 2. Las listas del Apps Script (`CAT_UNIDAD`, `GRUPO_PARTIDAS`, `CAMPAMENTO`, `UNIDADES`) → lo que aparece en los
>    **desplegables y balances** de la hoja.

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

**Mensaje del bot:** `SECCIÓN | CATEGORÍA | CONCEPTO | IMPORTE` (la validación ignora mayúsculas y acentos).

**Columnas de `Tabla de Gastos` (A:I):**
`UNIDAD | Trimestre | Categoría | Importe | Factura | Fecha | Comentarios | Enlace factura | Quién`
- El bot rellena UNIDAD, Trimestre (auto), Categoría, Importe, Fecha, Comentarios (=concepto), Enlace factura y
  Quién. **Factura** (tipo de justificante) la deja en blanco.

---

## 4. La hoja de Google (cómo se genera)

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
| **Conectar el bot / cambiar credenciales** | `.env` (`TELEGRAM_BOT_TOKEN`, `GOOGLE_SHEETS_ID`, `GOOGLE_CREDENTIALS_PATH`, `GOOGLE_AUTH_MODE`) + compartir hoja y carpetas con la cuenta de servicio | Reiniciar el bot |
| **Regenerar una hoja desde cero** | Bórrala a mano | Menú **Inicializar hoja** / **Crear hojas de balance** |

> **Regla de oro:** si cambias categorías, hazlo en **los dos sitios** (`categorias.yaml` y las listas del `.gs`) y
> luego **regenera** las pestañas afectadas. El `catalogo.csv` es opcional (respaldo); el script genera el `Catálogo`.

---

## 6. El bot (resumen técnico)

- Arranque: `python src/bot.py` (long polling; no necesita abrir puertos).
- Validaciones (en orden): remitente en lista blanca → hay archivo → caption de 4 campos → sección válida →
  categoría válida **para esa sección** → importe > 0. Si algo falla, responde y **no escribe**.
- Solo confirma "✅ registrada" cuando ha subido el archivo y escrito la fila.
- `DRY_RUN=1` en `.env` prueba el flujo de Telegram sin tocar Google.
- Pruebas offline: `pytest`.

---

## 7. Cosas a tener en cuenta (gotchas)

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

## 8. Fase 2 (futuro, aún no construido)

- **Clasificación asistida (IA)**: cuando la sección/categoría no encaje, primero *fuzzy matching* local
  (`rapidfuzz`) y luego la **API de Claude**. El campo `descripcion` de `config/categorias.yaml` está para
  alimentar esto (cuanto mejor descritas las partidas, mejor clasifica).
- **Despliegue 24/7** en Raspberry Pi (`systemd`) y **copias de seguridad** de la hoja.
- **Automatizar el volcado de presupuestos** desde el Excel (propuesto: pestaña `Presupuesto` + `VLOOKUP`, o un
  script que lo importe).
