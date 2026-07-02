# Replicar este sistema con ayuda de una IA

Este sistema (Hoja de Google de gastos + balances, y opcionalmente un bot de Telegram) está pensado para que
**cualquier persona, ayudándose de una IA** (Claude, ChatGPT…), pueda **replicarlo** para su grupo o **cambiar
cosas** cada año, sin tener que reconstruir nada.

La clave: **casi todo lo personalizable está en unas pocas listas**, y el Apps Script crea la hoja entera con un
clic.

---

## 1. Lo único que cambia entre grupos / años

- **Secciones y unidades** (p. ej. Castores, Manada, … Grupo, Campamento).
- **Categorías por sección** (las de unidad, las de Grupo agrupadas por partida, las de Campamento por bloque).
- **Parámetros y presupuestos** → se rellenan **en la propia hoja** (no en código): los € por persona y el mínimo
  de las unidades, y el Presupuestado de Grupo y Campamento.

Dónde viven esas listas:
- Para la **hoja**: al principio de `google-sheets/dropdowns-dependientes.gs` → `UNIDADES`, `CAT_UNIDAD`,
  `GRUPO_PARTIDAS`, `CAMPAMENTO`.
- Para el **bot**: `config/categorias.yaml` y `config/secciones.yaml`.

> Si cambias categorías, cámbialas en **los dos sitios** y regenera las pestañas. (Lo explica `MANUAL.md`.)

---

## 2. Replicar SOLO la hoja (fácil, sin programar)

1. Crea una **Hoja de Google** nueva.
2. **Extensiones → Apps Script**, pega el contenido de `dropdowns-dependientes.gs` y guarda.
3. Recarga la hoja → menú **Bot facturas → Inicializar hoja (crear todo)** (la 1ª vez, autoriza el script).
4. Listo: tienes `Tabla de Gastos`, `Catálogo` y los 3 balances. Rellena los presupuestos.

Para **adaptar** las categorías/secciones: edita las listas del principio del `.gs` (mejor con la IA, ver §4).

---

## 3. Replicar también el BOT (requiere un poco más)

Necesitas: bot de Telegram (de @BotFather), cuenta de Google de la asociación (Workspace recomendado) con una
**cuenta de servicio**, y Python. Sigue `README.md` y el apartado §5/§6 de `MANUAL.md`. Una IA puede guiarte paso a
paso; es la parte más técnica, pero solo se hace una vez.

---

## 4. El "prompt" para tu IA  (cópialo y pégalo)

Adjunta a la IA estos ficheros: **`MANUAL.md`**, **`dropdowns-dependientes.gs`** y (si vas a tocar el bot)
**`README.md`** y **`config/categorias.yaml`**. Luego pega esto:

```
Quiero montar/adaptar un sistema para gestionar los gastos de mi grupo scout:
- Una Hoja de Google con un Apps Script que crea las pestañas (registro de gastos, catálogo de
  categorías y hojas de balance Presupuestado/Gastado/Balance, con desplegables dependientes).
- (Opcional) un bot de Telegram que registra las facturas en esa hoja.

Te he adjuntado: MANUAL.md (cómo funciona y cómo cambiar cada cosa), dropdowns-dependientes.gs
(el Apps Script) y, si toca el bot, README.md y config/categorias.yaml.

Lo que quiero hacer: [ELIGE] (a) replicarlo tal cual para mi grupo; (b) cambiar secciones/categorías;
(c) cambiar parámetros o presupuestos; (d) montar el bot.

Datos de mi grupo:
- Secciones/unidades: ...
- Categorías por sección: ...
- (si aplica) parámetros de unidad y presupuestos: ...

Por favor:
1. Dame el `dropdowns-dependientes.gs` YA MODIFICADO con mis datos (mantén su estructura y su forma de
   insertar fórmulas con el separador autodetectado).
2. Explícame, paso a paso y para alguien NO técnico, cómo pegarlo en Apps Script y ejecutar
   "Inicializar hoja".
3. Respeta las reglas del MANUAL: mantener sincronizadas las listas del .gs con config/categorias.yaml,
   regenerar las pestañas afectadas (borrarlas antes), y no cambiar las comas de las fórmulas a mano.
```

---

## 5. El "kit" completo (qué guardar junto)

Guarda esta carpeta `bot-facturas/` entera, pero lo imprescindible para replicar/cambiar es:
- `MANUAL.md` — cómo funciona y cómo cambiar cada cosa.
- `google-sheets/dropdowns-dependientes.gs` — el Apps Script (crea la hoja entera).
- `google-sheets/GUIA-hoja-google-sheets.md` — pasos para montar la hoja.
- `README.md`, `config/categorias.yaml`, `config/secciones.example.yaml` — para el bot.
- Este `REPLICAR-CON-IA.md`.

Con esos ficheros + el prompt de §4, cualquier IA tiene **todo el contexto** para replicarlo o adaptarlo.
