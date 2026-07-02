"""Bot de gastos — punto de entrada (long polling).

Dos formas de registrar un gasto:
- Guiado con BOTONES: /gasto (recomendado, cómodo en el móvil).
- Atajo por TEXTO: un mensaje con cada dato en una línea (o separado por «|»).

Fase 1 (FACTURAS_ACTIVAS=0): solo gastos. Fase 2 (=1): además foto/PDF a Drive (por el atajo de texto).
"""
from __future__ import annotations

import logging
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import drive
import sheets
import validacion
from config import cargar_config, validar_config
from validacion import ErrorValidacion, Factura

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
)
log = logging.getLogger("bot-facturas")

EXTENSIONES = {"image/jpeg": "jpg", "image/png": "png", "application/pdf": "pdf"}

# Estados del flujo con botones
TIPO, UNIDAD, GRUPO, CATEGORIA, CONCEPTO, IMPORTE, CONFIRMAR = range(7)

AYUDA = (
    "Hola 👋 Para registrar un gasto, pulsa /gasto y te guío con botones.\n\n"
    "O mándalo en un mensaje, cada dato en una línea:\n"
    "Sección\nCategoría\nConcepto\nImporte\n\n"
    "Ejemplo:\nCastores\nMaterial de unidad\nCena fin de ronda\n47,30\n\n"
    "Usa /chatid para ver tu identificador."
)


# ====================== Comandos básicos ======================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(AYUDA)


async def cmd_chatid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = context.bot_data["cfg"]
    chat_id = update.effective_chat.id
    nombre = cfg.nombre_de(chat_id)
    if nombre:
        await update.message.reply_text(f"Tu chat_id es {chat_id}.\nEstás autorizado como: {nombre}.")
    else:
        await update.message.reply_text(
            f"Tu chat_id es {chat_id}.\nAún no estás autorizado; pásale este número a quien gestiona el bot."
        )


# ====================== Helpers compartidos ======================

def _escribir_fila(context, cfg, factura, quien, enlace, momento) -> None:
    if cfg.dry_run:
        log.info("[DRY_RUN] Fila que se añadiría: %s", sheets.construir_fila(factura, quien, enlace, momento))
    else:
        fila = sheets.construir_fila(factura, quien, enlace, momento)
        sheets.append_fila(context.bot_data["sheets"], cfg.sheets_id, cfg.sheets_range, fila)


def _resumen(factura, quien) -> str:
    return (
        f"• Sección: {factura.seccion}\n"
        f"• Categoría: {factura.categoria}\n"
        f"• Concepto: {factura.concepto}\n"
        f"• Importe: {factura.importe:.2f} €\n"
        f"• Por: {quien}"
    )


# ====================== Atajo: gasto por texto ======================

async def manejar_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cfg = context.bot_data["cfg"]
    mensaje = update.message
    chat_id = update.effective_chat.id

    if not cfg.esta_autorizado(chat_id):
        log.info("Mensaje ignorado de chat_id no autorizado: %s", chat_id)
        return

    texto = mensaje.text or mensaje.caption
    resultado = validacion.parsear(texto, cfg.catalogos)
    if isinstance(resultado, ErrorValidacion):
        await mensaje.reply_text(resultado.mensaje)
        return
    factura: Factura = resultado

    momento = datetime.now()
    quien = cfg.nombre_de(chat_id)
    enlace = ""

    try:
        if cfg.facturas_activas:
            if not (mensaje.photo or mensaje.document):
                await mensaje.reply_text("Falta la factura (foto o PDF). Adjúntala con el texto en el pie.")
                return
            archivo_tg, mimetype, ext = await _extraer_archivo(mensaje, context)
            contenido = bytes(await archivo_tg.download_as_bytearray())
            nombre_archivo = _nombre_archivo(factura, momento, ext)
            if cfg.dry_run:
                enlace = "https://example.com/DRY_RUN"
            else:
                carpeta = cfg.catalogos.carpeta_drive(factura.seccion)
                enlace = drive.subir_factura(context.bot_data["drive"], carpeta, nombre_archivo, contenido, mimetype)
        _escribir_fila(context, cfg, factura, quien, enlace, momento)
    except Exception:  # noqa: BLE001
        log.exception("Error procesando el gasto de %s", quien)
        await mensaje.reply_text("Ha habido un error al registrar el gasto. Inténtalo más tarde.")
        return

    extra = f"\n• Enlace: {enlace}" if (enlace and not cfg.dry_run) else ""
    await mensaje.reply_text("✅ Gasto registrado.\n" + _resumen(factura, quien) + extra)


async def _extraer_archivo(mensaje, context):
    if mensaje.photo:
        foto = mensaje.photo[-1]
        archivo = await context.bot.get_file(foto.file_id)
        return archivo, "image/jpeg", "jpg"
    doc = mensaje.document
    mimetype = doc.mime_type or "application/octet-stream"
    if mimetype in EXTENSIONES:
        ext = EXTENSIONES[mimetype]
    elif doc.file_name and "." in doc.file_name:
        ext = doc.file_name.rsplit(".", 1)[-1].lower()
    else:
        ext = "bin"
    archivo = await context.bot.get_file(doc.file_id)
    return archivo, mimetype, ext


def _nombre_archivo(factura, momento, ext) -> str:
    seccion = factura.seccion.lower().replace(" ", "-")
    sello = momento.strftime("%Y%m%d_%H%M%S")
    return f"{sello}_{seccion}_{factura.importe:.2f}.{ext}"


# ====================== Flujo guiado con botones ======================

def _teclado(opciones, prefijo, por_fila=2):
    botones = [InlineKeyboardButton(o, callback_data=f"{prefijo}|{i}") for i, o in enumerate(opciones)]
    filas = [botones[i:i + por_fila] for i in range(0, len(botones), por_fila)]
    return InlineKeyboardMarkup(filas)


async def iniciar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = context.bot_data["cfg"]
    if not cfg.esta_autorizado(update.effective_chat.id):
        return ConversationHandler.END
    context.user_data.clear()
    teclado = InlineKeyboardMarkup([[
        InlineKeyboardButton("💸 Gasto", callback_data="tipo|gasto"),
        InlineKeyboardButton("🧾 Factura", callback_data="tipo|factura"),
    ]])
    await update.message.reply_text("¿Qué quieres registrar?", reply_markup=teclado)
    return TIPO


async def elegir_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "tipo|factura":
        await q.edit_message_text("🧾 Las facturas estarán disponibles en la Fase 2. Por ahora usa /gasto.")
        return ConversationHandler.END
    cfg = context.bot_data["cfg"]
    unidades = cfg.catalogos.codigos_secciones
    context.user_data["unidades"] = unidades
    await q.edit_message_text("Elige la unidad:", reply_markup=_teclado(unidades, "uni", 2))
    return UNIDAD


async def elegir_unidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    cfg = context.bot_data["cfg"]
    unidad = context.user_data["unidades"][int(q.data.split("|")[1])]
    context.user_data["unidad"] = unidad
    grupos = cfg.catalogos.grupos_de(unidad)
    if grupos:
        context.user_data["grupos"] = grupos
        await q.edit_message_text(f"{unidad} → elige el grupo:", reply_markup=_teclado(grupos, "grp", 2))
        return GRUPO
    cats = cfg.catalogos.codigos_categorias_de(unidad)
    context.user_data["cats"] = cats
    await q.edit_message_text(f"{unidad} → elige la categoría:", reply_markup=_teclado(cats, "cat", 1))
    return CATEGORIA


async def elegir_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    cfg = context.bot_data["cfg"]
    unidad = context.user_data["unidad"]
    grupo = context.user_data["grupos"][int(q.data.split("|")[1])]
    cats = cfg.catalogos.categorias_de_grupo(unidad, grupo)
    context.user_data["cats"] = cats
    await q.edit_message_text(f"{unidad} · {grupo} → elige la categoría:", reply_markup=_teclado(cats, "cat", 1))
    return CATEGORIA


async def elegir_categoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    categoria = context.user_data["cats"][int(q.data.split("|")[1])]
    context.user_data["categoria"] = categoria
    await q.edit_message_text(f"Categoría: {categoria}\n\n✍️ Escribe el concepto (descripción breve):")
    return CONCEPTO


async def recibir_concepto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["concepto"] = update.message.text.strip()
    await update.message.reply_text("💶 Escribe el importe en euros (p. ej. 47,30):")
    return IMPORTE


async def recibir_importe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    importe = validacion._parsear_importe(update.message.text)
    if importe is None:
        await update.message.reply_text("Importe no válido. Escríbelo otra vez (p. ej. 47,30):")
        return IMPORTE
    context.user_data["importe"] = importe
    d = context.user_data
    teclado = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Confirmar", callback_data="ok"),
        InlineKeyboardButton("❌ Cancelar", callback_data="no"),
    ]])
    resumen = (
        "Revisa el gasto:\n"
        f"• Unidad: {d['unidad']}\n"
        f"• Categoría: {d['categoria']}\n"
        f"• Concepto: {d['concepto']}\n"
        f"• Importe: {importe:.2f} €"
    )
    await update.message.reply_text(resumen, reply_markup=teclado)
    return CONFIRMAR


async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "no":
        await q.edit_message_text("❌ Cancelado.")
        context.user_data.clear()
        return ConversationHandler.END
    cfg = context.bot_data["cfg"]
    d = context.user_data
    quien = cfg.nombre_de(update.effective_chat.id)
    factura = Factura(seccion=d["unidad"], categoria=d["categoria"], concepto=d["concepto"], importe=d["importe"])
    try:
        _escribir_fila(context, cfg, factura, quien, "", datetime.now())
    except Exception:  # noqa: BLE001
        log.exception("Error registrando gasto (botones) de %s", quien)
        await q.edit_message_text("Ha habido un error al registrar el gasto. Inténtalo más tarde.")
        context.user_data.clear()
        return ConversationHandler.END
    await q.edit_message_text("✅ Gasto registrado.\n" + _resumen(factura, quien))
    context.user_data.clear()
    return ConversationHandler.END


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Cancelado.")
    return ConversationHandler.END


# ====================== main ======================

def main() -> None:
    cfg = cargar_config()
    for problema in validar_config(cfg):
        log.warning("Configuración: %s", problema)
    if not cfg.telegram_token:
        raise SystemExit("No se puede arrancar sin TELEGRAM_BOT_TOKEN. Revisa el fichero .env")

    app = Application.builder().token(cfg.telegram_token).build()
    app.bot_data["cfg"] = cfg

    if not cfg.dry_run:
        from autenticacion import credenciales
        creds = credenciales(cfg.auth_mode, cfg.credentials_path)
        app.bot_data["sheets"] = sheets.construir_servicio(creds)
        if cfg.facturas_activas:
            app.bot_data["drive"] = drive.construir_servicio(creds)

    conv = ConversationHandler(
        entry_points=[CommandHandler("gasto", iniciar)],
        states={
            TIPO: [CallbackQueryHandler(elegir_tipo, pattern=r"^tipo\|")],
            UNIDAD: [CallbackQueryHandler(elegir_unidad, pattern=r"^uni\|")],
            GRUPO: [CallbackQueryHandler(elegir_grupo, pattern=r"^grp\|")],
            CATEGORIA: [CallbackQueryHandler(elegir_categoria, pattern=r"^cat\|")],
            CONCEPTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_concepto)],
            IMPORTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_importe)],
            CONFIRMAR: [CallbackQueryHandler(confirmar, pattern=r"^(ok|no)$")],
        },
        fallbacks=[CommandHandler("cancel", cancelar)],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("chatid", cmd_chatid))
    app.add_handler(conv)
    app.add_handler(
        MessageHandler((filters.TEXT | filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND, manejar_gasto)
    )

    log.info("Bot arrancado (facturas=%s, dry_run=%s). Esperando mensajes…", cfg.facturas_activas, cfg.dry_run)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
