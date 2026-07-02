# Guía: montar la hoja de gastos en Google Sheets

Esta hoja es el **destino del bot** y también se puede rellenar a mano. Los desplegables hacen que, al elegir la
**Unidad**, en **Categoría** solo aparezcan las categorías de esa unidad.

> Los desplegables dependientes y la generación de hojas necesitan **Apps Script** (propio de Google Sheets), así
> que la hoja se monta **directamente en Google Sheets**: subir un `.xlsx` no conserva esta lógica. El bot añade
> filas por API; los desplegables son sobre todo para la **entrada manual** (el bot ya valida la categoría).

## Archivos de esta carpeta
- `dropdowns-dependientes.gs` — el Apps Script. Crea las hojas, los desplegables y los balances.
- `catalogo.csv` — **opcional**: el catálogo de categorías por unidad. Ya no hace falta importarlo (el script lo
  genera solo); se deja como respaldo o por si prefieres importarlo a mano.

---

## Opción A (recomendada): crear todo con un clic
1. Crea una **Hoja de cálculo de Google** nueva (en el Drive de la asociación).
2. **Extensiones → Apps Script**, borra lo que haya y **pega** `dropdowns-dependientes.gs`. Guarda (💾). Vuelve a la
   hoja y **recárgala** (F5): aparecerá el menú **Bot facturas**.
3. Menú **Bot facturas → Inicializar hoja (crear todo)**. La primera vez Google pedirá **autorizar** el script (es
   tuyo: Configuración avanzada → *Ir al proyecto* → Permitir).
   - Crea, **si no existen**: `Tabla de Gastos` (cabeceras + formato + desplegable de Unidad), `Catálogo`, y
     `Balance Unidades`, `Balance Grupo`, `Balance Campamento`.
   - No toca ninguna pestaña que ya tengas.
4. Listo. Prueba: en `Tabla de Gastos`, elige una **Unidad** en `A2` → en `C2` aparecen solo sus categorías.

---

## Opción B (manual): usar tu libro actual o montarlo a mano
Para cuando ya tienes un libro con datos (p. ej. tu `Gastos Grupo 2024-2025.xlsx`):
1. Súbelo a Drive y ábrelo **como Hoja de Google** (Archivo → Guardar como Hoja de cálculo de Google). Crea una
   **copia**; el `.xlsx` original no se toca.
2. Comprueba las cabeceras de `Tabla de Gastos` (fila 1, A–I): `UNIDAD | Trimestre | Categoría | Importe | Factura |
   Fecha | Comentarios | Enlace factura | Quién`. Añade al final las que falten (**Enlace factura**, **Quién**).
3. Pega el script (Apps Script) y usa **Bot facturas → Inicializar hoja**: creará el `Catálogo` si no existe (sin
   tocar tu `Tabla de Gastos`). Alternativa: importar `catalogo.csv` (Archivo → Importar) y renombrar la pestaña a
   `Catálogo`.
4. **Bot facturas → Configurar desplegable de Unidad**. Para tus filas antiguas: **Aplicar categorías a filas
   existentes**.

> **Histórico a salvo:** «Aplicar categorías a filas existentes» **no borra nada**. Solo añade el desplegable y deja
> marcadas en rojo (aviso) las categorías antiguas que no encajen con el nuevo modelo por unidad.

---

## Hojas de balance
El menú **Crear hojas de balance** (o **Inicializar hoja**) crea tres pestañas con el **Gastado sumado
automáticamente** de `Tabla de Gastos`; el **Presupuestado lo rellenas tú**.

- **Balance Unidades** (Castores, Manada, Tropa, Escultas, Clan): mini-tabla por unidad con Presupuestado /
  Gastado / Balance por trimestre, más control **Dinero entregado vs Gasto apuntado**. Las filas `Educandos` y
  `Scouters` quedan vacías para tus fórmulas por nº de personas.
- **Balance Grupo**: agrupado por **partida** (EdM y ASDE, Formación, Actividades, Material, Cargos y comisiones,
  Varios) con **subtotales**, en bloques Presupuestado / Gastado / Balance por trimestre.
- **Balance Campamento**: una tabla por categoría (agrupada por bloque), con Presupuestado / Gastado / Balance.

**Formato:** cabeceras con color, partidas/bloques sombreados y **formato condicional** en los balances
(negativo → rojo, positivo → verde).

Notas:
- Re-ejecutar **no sobrescribe** una pestaña que ya exista (para no borrar tu presupuesto). Para regenerarla,
  bórrala a mano primero.
- **"Dinero entregado"** es una categoría **por unidad** (sustituye a la antigua "Dinero unidades" de Grupo).
- Las fórmulas suman las filas cuyo Trimestre sea `1º` / `2º` / `3º`.
- El "Gastado" usa la pestaña de datos llamada exactamente `Tabla de Gastos`. Si la tuya tiene otro nombre,
  cámbialo en la constante `HOJA_DATOS` del script.

---

## Conectar el bot
1. **Comparte** la hoja con el email de la **cuenta de servicio** (rol *Editor*).
2. Copia el **ID** de la hoja (de la URL `/d/<ID>/edit`) a `.env` → `GOOGLE_SHEETS_ID`.
3. El rango por defecto es `Tabla de Gastos!A:I` (`.env` → `GOOGLE_SHEETS_RANGE`).

## Mantenimiento
Si cambian las categorías: edita `config/categorias.yaml` (fuente de verdad del **bot**) y, en el script, las listas
`CAT_UNIDAD`, `GRUPO_PARTIDAS`, `CAMPAMENTO` y `UNIDADES`; luego regenera el `Catálogo` y las hojas de balance
(bórralos y vuelve a "Inicializar hoja"). El `catalogo.csv` es opcional; actualízalo solo si lo usas como respaldo.

## Si tu cuenta Workspace bloquea Apps Script
Algunas organizaciones lo restringen. Alternativa **sin script** (solo aviso, sin desplegable): en `Categoría`,
Datos → Validación de datos → *Fórmula personalizada* `=NO(ESERROR(COINCIDIR(C2; INDIRECTO($A2); 0)))`, creando un
**rango con nombre** por unidad (Castores, Manada, …) con sus categorías. Dímelo y te detallo esa variante.
