# Bot de facturas — Grupo Scout Buen Consejo

Bot de Telegram para que cualquier scouter autorizado registre una factura (foto o PDF) con una
descripción. El bot **sube la factura a Google Drive** (carpeta según la sección) y **añade una fila a
Google Sheets**, y confirma al scouter. No clasifica ni interpreta nada: solo valida, reparte y confirma.

> **Versión 1.** La clasificación asistida (fuzzy/IA), el despliegue 24/7 en Raspberry Pi y las copias de
> seguridad son fases futuras. El código está organizado para añadirlas sin reescribir lo existente.

---

## Formato del mensaje

Envía la factura como **foto o documento**, con este texto en el pie (caption):

```
SECCIÓN | CATEGORÍA | CONCEPTO | IMPORTE
```

Ejemplo:

```
Castores | Material de unidad | Pinturas para el local | 47,30
```

- **SECCIÓN**: una de `Castores, Manada, Tropa, Escultas, Clan, Grupo, Campamento`. Determina la carpeta de Drive.
- **CATEGORÍA**: depende de la sección (ver más abajo).
- **CONCEPTO**: descripción libre breve (va a la columna *Comentarios*).
- **IMPORTE**: cantidad en euros (admite coma o punto: `47,30` o `47.30`).

El campo *Quién* no se escribe: lo deduce el bot del `chat_id` de quien envía. La comparación de sección y
categoría **ignora mayúsculas y acentos**.

### Categorías por sección

- **Unidades** (Castores, Manada, Tropa, Escultas, Clan): `Material de unidad`, `Excursión de unidad`.
- **Grupo**: las categorías de la "Tabla de Gastos" (Intendencia, Formación, Pañoletas, …).
- **Campamento**: las 46 partidas del presupuesto de campamento (Autobuses, Makro, Toldos, …).

El catálogo completo está en [`config/categorias.yaml`](config/categorias.yaml).

---

## Qué se guarda en Google Sheets

Por cada factura válida se añade una fila. Orden de columnas (alineado a la "Tabla de Gastos" + 2 columnas nuevas **al final**, para no romper fórmulas existentes):

| A: UNIDAD | B: Trimestre | C: Categoría | D: Importe | E: Factura | F: Fecha | G: Comentarios | H: Enlace factura | I: Quién |
|---|---|---|---|---|---|---|---|---|

- **E "Factura"** (tipo de justificante: TRANSFERENCIA/Sí…) lo deja **en blanco** el bot; lo rellena tesorería si quiere.
- **H "Enlace factura"**: URL del archivo subido a Drive.
- **I "Quién"**: autor, deducido del `chat_id`.
- **Trimestre**: se calcula desde la fecha (Sep–Dic = 1º, Ene–Mar = 2º, Abr–Ago = 3º; ajustable en `src/util.py`).

Fila de cabeceras recomendada para crear la hoja:
`UNIDAD | Trimestre | Categoría | Importe | Factura | Fecha | Comentarios | Enlace factura | Quién`
(el rango por defecto es `Tabla de Gastos!A:I`, configurable en `.env`).

---

## Puesta en marcha

### 0. Requisitos
- Python 3.10 o superior.

### 1. Crear el bot de Telegram
Habla con [@BotFather](https://t.me/BotFather), crea un bot y copia el **token** → `TELEGRAM_BOT_TOKEN`.

### 2. Google Cloud + credenciales
1. Crea (o reutiliza) un proyecto en Google Cloud y **habilita las APIs de Drive y Sheets**.
2. **Recomendado (Google Workspace, p. ej. `@buenconsejo95.com`): cuenta de servicio.**
   - Crea una **cuenta de servicio** y descarga su **clave JSON** → guárdala en `config/` y apunta
     `GOOGLE_CREDENTIALS_PATH` a ella. `GOOGLE_AUTH_MODE=service_account`.
   - Crea una **Unidad compartida (Shared Drive)** para las facturas y, dentro, una carpeta por sección.
     Añade el email de la cuenta de servicio como **Administrador de contenido** de la Unidad compartida.
   - **Comparte la hoja de Google Sheets** con el email de la cuenta de servicio (rol *Editor*).
3. **Alternativa (Gmail gratuito): OAuth.** `GOOGLE_AUTH_MODE=oauth` y `GOOGLE_CREDENTIALS_PATH` apuntando al
   `client_secret*.json` de tipo *App de escritorio*. La primera ejecución abrirá el navegador y generará
   `config/token.json`.

### 3. Carpetas y hoja
- Crea una carpeta de Drive por sección y anota su **ID** (parte final de la URL de la carpeta).
- Crea la hoja de Google Sheets con la fila de cabeceras y anota su **ID**.

### 4. Configuración
```bash
cp .env.example .env
cp config/secciones.example.yaml config/secciones.yaml
cp config/autorizados.example.yaml config/autorizados.yaml
```
- Rellena `.env` (token, `GOOGLE_SHEETS_ID`, ruta de credenciales).
- Rellena `config/secciones.yaml` con el ID de carpeta de cada sección.
- Rellena `config/autorizados.yaml` con los `chat_id` y nombres (ver "Dar de alta usuarios").

### 5. Instalar dependencias
```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
```

### 6. Arrancar
```bash
python src/bot.py
```

---

## Dar de alta usuarios

Cada scouter envía **`/chatid`** al bot; este responde su número. Cópialo a `config/autorizados.yaml`:

```yaml
autorizados:
  - chat_id: 11111111
    nombre: "Nombre Apellido"
```

Quien no esté en la lista es ignorado en silencio.

---

## Pruebas

Pruebas offline (no tocan Telegram ni Google):
```bash
pytest
```

Probar el flujo de Telegram **sin** Google: pon `DRY_RUN=1` en `.env` y arranca el bot; simulará la subida a
Drive y la escritura en Sheets (solo deja traza en el log).

---

## Privacidad (importante)
- Cuentas de Telegram y Google **de la asociación**, nunca personales. Activa 2FA en Google.
- **No** se versionan: `.env`, credenciales JSON, `token.json`, `config/autorizados.yaml`, `config/secciones.yaml`
  ni ningún `*.xlsx` (ver `.gitignore`).
- Las facturas con **datos personales de menores no se envían por Telegram**: se suben directamente a Drive.
  El bot es solo para facturas de proveedores / gastos generales.
- Durante el desarrollo y las pruebas, usa **solo datos ficticios**.

---

## Estructura

```
bot-facturas/
├── config/
│   ├── secciones.example.yaml   # sección -> carpeta de Drive (plantilla)
│   ├── categorias.yaml          # categorías por sección
│   └── autorizados.example.yaml # chat_id -> nombre (plantilla)
├── src/
│   ├── config.py            # carga .env + catálogos + autorizados
│   ├── catalogos.py         # secciones y categorías (desde YAML)
│   ├── autenticacion.py     # credenciales Google (service_account | oauth)
│   ├── validacion.py        # parseo + validación del mensaje
│   ├── drive.py             # subida a Drive
│   ├── sheets.py            # construcción de fila + append
│   ├── util.py              # normalización y trimestre
│   └── bot.py               # punto de entrada (long polling)
└── tests/                   # pruebas offline
```
