"""Web local de tesorería (Paso 2): ver balances y gestionar gastos (CRUD).

Reutiliza la lógica compartida de `core/` (misma base de datos que el bot). Pensada para
correr SOLO en localhost (sin login); ver run_web.py. Plantillas server-side con Jinja2.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core import db
from core.config import cargar_config
from core.util import trimestre_de
from core.validacion import Factura, parsear_importe

BASE = Path(__file__).resolve().parent

# Configuración compartida con el bot (misma DB y catálogos). No usamos validar_config:
# la web no necesita el token de Telegram, solo db_path y catálogos.
cfg = cargar_config()
DB = cfg.db_path
db.init_db(DB)

app = FastAPI(title="Tesorería scout")
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")


COOKIE_SECCION = "seccion"


def _seccion_activa(request) -> str | None:
    """La sección fijada como contexto (cookie), o None = «Todo el grupo».

    Se valida contra el catálogo para ignorar cookies obsoletas o manipuladas.
    """
    sec = request.cookies.get(COOKIE_SECCION, "")
    return sec if sec in cfg.catalogos.codigos_secciones else None


def _ctx_comun(request):
    """Datos presentes en todas las páginas: el selector de sección y el contador de
    incompletos del contexto activo (para el menú lateral)."""
    sec = _seccion_activa(request)
    return {
        "seccion_activa": sec,
        "secciones": cfg.catalogos.codigos_secciones,
        "pendientes": len(db.listar_gastos(DB, seccion=sec, estado="incompleto")),
    }


templates = Jinja2Templates(directory=str(BASE / "templates"), context_processors=[_ctx_comun])

# Cada sección scout tiene su color propio: aquí codifica de un vistazo a quién pertenece
# cada gasto (pestañas en la lista, barras en el panel). Las desconocidas caen a un neutro.
COLORES_SECCION = {
    "Castores": "#DC6B2F",
    "Manada": "#D79A22",
    "Tropa": "#2E7D4F",
    "Escultas": "#C0392B",
    "Clan": "#8E44AD",
    "Grupo": "#1E3A2F",
    "Campamento": "#2F6E8F",
}
COLOR_NEUTRO = "#8A8577"


def _euros(valor) -> str:
    """Formatea un número como euros en es-ES: 1.234,50 (miles con punto, sin símbolo)."""
    try:
        entero, dec = f"{abs(float(valor)):.2f}".split(".")
    except (TypeError, ValueError):
        return "0,00"
    signo = "-" if _es_negativo(valor) else ""
    grupos = []
    while len(entero) > 3:
        grupos.insert(0, entero[-3:])
        entero = entero[:-3]
    grupos.insert(0, entero)
    return f"{signo}{'.'.join(grupos)},{dec}"


def _es_negativo(valor) -> bool:
    try:
        return float(valor) < 0
    except (TypeError, ValueError):
        return False


templates.env.filters["euros"] = _euros
templates.env.globals["colores"] = COLORES_SECCION
templates.env.globals["color_neutro"] = COLOR_NEUTRO


# --- Helpers -----------------------------------------------------------------

def _catalogo() -> dict[str, list[str]]:
    """{sección: [categorías]} para poblar los desplegables del formulario."""
    return {s: cfg.catalogos.codigos_categorias_de(s) for s in cfg.catalogos.codigos_secciones}


def _a_input_date(fecha_db: str) -> str:
    """'dd/mm/aaaa' (formato de la DB) -> 'aaaa-mm-dd' (formato de <input type=date>)."""
    try:
        return datetime.strptime(fecha_db, "%d/%m/%Y").strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return ""


def _leer_form(seccion, categoria, concepto, importe_txt, fecha_txt, quien):
    """Valida los campos del formulario. Devuelve (errores, datos) donde datos trae los
    valores ya normalizados listos para guardar (importe float, fecha date)."""
    errores: list[str] = []

    seccion = (seccion or "").strip()
    categoria = (categoria or "").strip()
    concepto = (concepto or "").strip()
    quien = (quien or "").strip()

    if seccion not in cfg.catalogos.codigos_secciones:
        errores.append("La sección no es válida.")
    elif categoria and categoria not in cfg.catalogos.codigos_categorias_de(seccion):
        errores.append("La categoría no pertenece a la sección elegida.")

    importe = parsear_importe(importe_txt or "")
    if importe is None:
        errores.append("El importe no es válido (p. ej. 47,30).")

    try:
        fecha = datetime.strptime((fecha_txt or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        errores.append("La fecha no es válida.")
        fecha = None

    datos = {
        "seccion": seccion, "categoria": categoria, "concepto": concepto,
        "quien": quien, "importe": importe, "fecha": fecha,
    }
    return errores, datos


def _estado_de(datos: dict) -> str:
    """Un gasto está completo cuando tiene sección, categoría y concepto."""
    return "completo" if datos["seccion"] and datos["categoria"] and datos["concepto"] else "incompleto"


# --- Rutas -------------------------------------------------------------------

def _destino_seguro(next: str) -> str:
    """Solo permite redirigir a rutas internas del propio sitio (evita open redirect).

    Rechaza URLs absolutas y protocol-relative («//host», «/\\host»): exige una ruta que
    empiece por «/» y sin esquema ni host.
    """
    partes = urlparse(next or "")
    if partes.scheme or partes.netloc or not next.startswith("/") or next.startswith(("//", "/\\")):
        return "/"
    return next


@app.get("/contexto")
def contexto(sec: str = "", next: str = "/"):
    """Fija (o quita) la sección activa que filtra toda la app. Guardada en cookie."""
    resp = RedirectResponse(_destino_seguro(next), status_code=303)
    if sec in cfg.catalogos.codigos_secciones:
        resp.set_cookie(COOKIE_SECCION, sec, max_age=60 * 60 * 24 * 365, samesite="lax")
    else:
        resp.delete_cookie(COOKIE_SECCION)
    return resp


def _overview_secciones() -> list[dict]:
    """Total y nº de apuntes de TODAS las secciones (en orden de catálogo, incluidas las
    que están a 0 €), más cualquier sección fuera de catálogo (p. ej. incompletos sin sección)."""
    datos = {f["seccion"]: f for f in db.resumen_balances(DB)["por_seccion"]}
    filas = []
    for s in cfg.catalogos.codigos_secciones:
        f = datos.pop(s, None)
        filas.append({"seccion": s, "total": f["total"] if f else 0, "n": f["n"] if f else 0})
    # Lo que quede son secciones no catalogadas (típicamente '' de gastos incompletos).
    for s, f in datos.items():
        filas.append({"seccion": s or "", "total": f["total"], "n": f["n"], "fuera": True})
    return filas


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    sec = _seccion_activa(request)
    if sec:
        ctx = {"nav": "balance", "seccion": sec, "resumen": db.resumen_seccion(DB, sec)}
    else:
        overview = _overview_secciones()
        ctx = {
            "nav": "balance",
            "overview": overview,
            "total_grupo": sum(f["total"] for f in overview),
            "n_grupo": sum(f["n"] for f in overview),
        }
    return templates.TemplateResponse(request, "dashboard.html", ctx)


@app.get("/gastos", response_class=HTMLResponse)
def lista(request: Request, trimestre: str = "", estado: str = ""):
    sec = _seccion_activa(request)
    gastos = db.listar_gastos(
        DB, seccion=sec, trimestre=trimestre or None, estado=estado or None
    )
    return templates.TemplateResponse(
        request, "lista.html",
        {
            "nav": "gastos",
            "gastos": gastos,
            "filtros": {"trimestre": trimestre, "estado": estado},
        },
    )


@app.get("/incompletos", response_class=HTMLResponse)
def incompletos(request: Request):
    sec = _seccion_activa(request)
    gastos = db.listar_gastos(DB, seccion=sec, estado="incompleto")
    return templates.TemplateResponse(
        request, "incompletos.html", {"nav": "incompletos", "gastos": gastos}
    )


@app.get("/estadisticas", response_class=HTMLResponse)
def estadisticas(request: Request):
    sec = _seccion_activa(request)
    resumen = db.resumen_seccion(DB, sec) if sec else db.resumen_balances(DB)
    media = (resumen["total"] / resumen["n"]) if resumen["n"] else 0
    return templates.TemplateResponse(
        request, "estadisticas.html",
        {"nav": "estadisticas", "resumen": resumen, "seccion": sec, "media": media},
    )


# Parámetros de cálculo del presupuesto de unidades (claves en la tabla `parametros`).
PARAM_MATERIAL = "eur_persona_material"
PARAM_EXCURSION = "eur_persona_excursion"
PARAM_MINIMO = "minimo_material"

# Censo conocido de la ronda 25/26 (de RELLENAR-PRESUPUESTO-CON-IA.md). Es solo el valor por
# defecto que se muestra hasta que se edite y guarde en la web.
CENSO_DEFECTO = {
    "Castores": (25, 7), "Manada": (39, 7), "Tropa": (24, 8),
    "Escultas": (37, 3), "Clan": (24, 2),
}

# Categorías de unidad que llevan presupuesto calculado (Dinero entregado no lleva).
CAT_MATERIAL = "Material de unidad"
CAT_EXCURSION = "Excursión de unidad"
CAT_DINERO = "Dinero entregado"


def _num(txt) -> float | None:
    """Importe >= 0 desde texto es-ES; None si no es un número válido."""
    v = parsear_importe(txt)
    if v is None and (txt or "").strip() in ("", "0", "0,00", "0.00"):
        return 0.0
    return v


def _entero(txt) -> int:
    try:
        return max(0, int(float((txt or "0").replace(",", ".").strip() or 0)))
    except ValueError:
        return 0


def _es_unidad(seccion: str) -> bool:
    return cfg.catalogos.seccion_a_lista.get(seccion) == "unidad"


def _parametros() -> dict:
    p = db.obtener_parametros(DB)
    return {
        "material": p.get(PARAM_MATERIAL, 0) or 0,
        "excursion": p.get(PARAM_EXCURSION, 0) or 0,
        "minimo": p.get(PARAM_MINIMO, 0) or 0,
    }


def _semaforo(presupuesto: float, gastado: float) -> dict:
    """Estado presupuestario: restante, % usado y color de semáforo."""
    if presupuesto > 0:
        pct = gastado / presupuesto * 100
        estado = "over" if pct > 100 else ("warn" if pct >= 80 else "ok")
    else:
        pct, estado = 0, "sin"
    return {"presupuesto": presupuesto, "gastado": gastado,
            "restante": presupuesto - gastado, "pct": pct, "estado": estado}


def _presupuesto_unidad(seccion: str, params: dict, censo_db: dict) -> dict:
    """Calcula el presupuesto de una unidad: Material = MAX(personas×€, mínimo),
    Excursión = personas×€. Devuelve censo + líneas por categoría + total."""
    fila = censo_db.get(seccion)
    educandos, scouters = ((fila["educandos"], fila["scouters"]) if fila
                           else CENSO_DEFECTO.get(seccion, (0, 0)))
    personas = educandos + scouters

    pres_material = max(personas * params["material"], params["minimo"])
    pres_excursion = personas * params["excursion"]

    gcat = {f["categoria"]: f["total"] for f in db.resumen_seccion(DB, seccion)["por_categoria"]}
    material = _semaforo(pres_material, gcat.get(CAT_MATERIAL, 0))
    excursion = _semaforo(pres_excursion, gcat.get(CAT_EXCURSION, 0))
    presupuesto = pres_material + pres_excursion
    gastado = material["gastado"] + excursion["gastado"]
    return {
        "seccion": seccion, "educandos": educandos, "scouters": scouters, "personas": personas,
        "material": material, "excursion": excursion,
        "dinero_entregado": gcat.get(CAT_DINERO, 0),
        **_semaforo(presupuesto, gastado),
    }


TRIMESTRES = ["1º", "2º", "3º"]


def _presupuesto_categorias(seccion: str) -> dict:
    """Presupuesto de Grupo/Campamento: categorías agrupadas por partida/bloque, con celdas
    por trimestre (presupuestado y gastado) + totales de fila, columna y sección."""
    pres = db.obtener_presupuesto_categorias(DB, seccion)
    gast = db.gastado_categoria_trimestre(DB, seccion)
    cats = cfg.catalogos.codigos_categorias_de(seccion)
    idx = {c: i for i, c in enumerate(cats)}

    grupos = []
    for partida in cfg.catalogos.grupos_de(seccion):
        filas = []
        for cat in cfg.catalogos.categorias_de_grupo(seccion, partida):
            celdas, tp, tg = [], 0, 0
            for tri in TRIMESTRES:
                p = pres.get((cat, tri), 0) or 0
                g = gast.get((cat, tri), 0) or 0
                tp += p
                tg += g
                celdas.append({"tri": tri, "pres": p, "gast": g})
            filas.append({"categoria": cat, "idx": idx.get(cat, -1), "celdas": celdas,
                          **_semaforo(tp, tg)})
        grupos.append({"partida": partida, "filas": filas})

    tri_tot = {tri: {"pres": sum(pres.get((c, tri), 0) or 0 for c in cats),
                     "gast": sum(gast.get((c, tri), 0) or 0 for c in cats)} for tri in TRIMESTRES}
    total_pres = sum(v["pres"] for v in tri_tot.values())
    total_gast = sum(v["gast"] for v in tri_tot.values())
    return {"grupos": grupos, "trimestres": TRIMESTRES, "tri_tot": tri_tot,
            **_semaforo(total_pres, total_gast)}


@app.get("/presupuestos", response_class=HTMLResponse)
def presupuestos(request: Request):
    sec = _seccion_activa(request)
    params = _parametros()
    censo_db = db.obtener_censo(DB)

    if sec and _es_unidad(sec):
        ctx = {"nav": "presupuestos", "modo": "unidad", "seccion": sec, "params": params,
               "u": _presupuesto_unidad(sec, params, censo_db)}
    elif sec:  # Grupo o Campamento: por categoría y trimestre
        ctx = {"nav": "presupuestos", "modo": "categorias", "seccion": sec,
               "datos": _presupuesto_categorias(sec)}
    else:  # Todo el grupo
        unidades = [s for s in cfg.catalogos.codigos_secciones if _es_unidad(s)]
        otras = [s for s in cfg.catalogos.codigos_secciones if not _es_unidad(s)]
        filas_o = []
        for s in otras:
            d = _presupuesto_categorias(s)
            filas_o.append({"seccion": s, "presupuesto": d["presupuesto"], "gastado": d["gastado"],
                            "restante": d["restante"], "pct": d["pct"], "estado": d["estado"]})
        ctx = {
            "nav": "presupuestos", "modo": "grupo", "params": params,
            "filas_u": [_presupuesto_unidad(s, params, censo_db) for s in unidades],
            "filas_o": filas_o,
        }
    return templates.TemplateResponse(request, "presupuestos.html", ctx)


@app.post("/presupuestos/categorias")
async def guardar_presupuesto_categorias(request: Request):
    """Guarda de una vez toda la tabla de presupuesto por categoría y trimestre de una sección."""
    form = await request.form()
    seccion = form.get("seccion", "")
    if seccion in cfg.catalogos.codigos_secciones and not _es_unidad(seccion):
        for i, cat in enumerate(cfg.catalogos.codigos_categorias_de(seccion)):
            for tri in TRIMESTRES:
                valor = _num(form.get(f"imp:{i}:{tri}", ""))
                if valor is not None:
                    db.fijar_presupuesto_categoria(DB, seccion, cat, tri, valor)
    return RedirectResponse("/presupuestos", status_code=303)


@app.post("/presupuestos/parametros")
def guardar_parametros(material: str = Form(""), excursion: str = Form(""), minimo: str = Form("")):
    for clave, txt in ((PARAM_MATERIAL, material), (PARAM_EXCURSION, excursion), (PARAM_MINIMO, minimo)):
        valor = _num(txt)
        if valor is not None:
            db.fijar_parametro(DB, clave, valor)
    return RedirectResponse("/presupuestos", status_code=303)


@app.post("/presupuestos/censo")
def guardar_censo(seccion: str = Form(""), educandos: str = Form("0"), scouters: str = Form("0")):
    if _es_unidad(seccion):
        db.fijar_censo(DB, seccion, _entero(educandos), _entero(scouters))
    return RedirectResponse("/presupuestos", status_code=303)


@app.get("/asistente", response_class=HTMLResponse)
def asistente(request: Request):
    return templates.TemplateResponse(
        request, "en_construccion.html",
        {
            "nav": "asistente",
            "titulo": "Asistente de IA",
            "eyebrow": "Consultas en lenguaje natural",
            "descripcion": "Un chat para preguntar por tus cuentas («¿cuánto llevamos gastado en "
                           "Campamento este trimestre?») y anotar gastos por texto o voz desde el "
                           "navegador, con la IA local que ya usa el bot.",
            "requisito": "Necesita conectar el navegador con el modelo local (Ollama) que ya "
                         "corre para las notas de voz del bot.",
        },
    )


@app.get("/gastos/nuevo", response_class=HTMLResponse)
def nuevo_form(request: Request):
    hoy = date.today().strftime("%Y-%m-%d")
    gasto = {"fecha_input": hoy, "seccion": _seccion_activa(request) or "", "categoria": "",
             "concepto": "", "importe": "", "quien": ""}
    return templates.TemplateResponse(
        request, "form.html",
        {"nav": "gastos", "gasto": gasto, "catalogo": _catalogo(), "accion": "/gastos",
         "titulo": "Anotar gasto", "errores": []},
    )


@app.post("/gastos")
def crear(
    request: Request,
    seccion: str = Form(""), categoria: str = Form(""), concepto: str = Form(""),
    importe: str = Form(""), fecha: str = Form(""), quien: str = Form(""),
):
    errores, datos = _leer_form(seccion, categoria, concepto, importe, fecha, quien)
    if errores:
        gasto = {"fecha_input": fecha, "seccion": seccion, "categoria": categoria,
                 "concepto": concepto, "importe": importe, "quien": quien}
        return templates.TemplateResponse(
            request, "form.html",
            {"nav": "gastos", "gasto": gasto, "catalogo": _catalogo(), "accion": "/gastos",
             "titulo": "Anotar gasto", "errores": errores},
            status_code=400,
        )

    factura = Factura(datos["seccion"], datos["categoria"], datos["concepto"], datos["importe"])
    # creado_en refleja el momento real del registro; la fecha del gasto la elige el usuario.
    gid = db.guardar_gasto(
        DB, factura, quien=datos["quien"] or "web", enlace="",
        momento=datetime.now(), estado=_estado_de(datos),
    )
    if datos["fecha"] != date.today():
        db.actualizar_gasto(DB, gid, {
            "fecha": datos["fecha"].strftime("%d/%m/%Y"),
            "trimestre": trimestre_de(datos["fecha"]),
        })
    return RedirectResponse("/gastos", status_code=303)


@app.get("/gastos/{gasto_id}/editar", response_class=HTMLResponse)
def editar_form(request: Request, gasto_id: int):
    fila = db.obtener_gasto(DB, gasto_id)
    if fila is None:
        return RedirectResponse("/gastos", status_code=303)
    gasto = {
        "fecha_input": _a_input_date(fila["fecha"]),
        "seccion": fila["seccion"], "categoria": fila["categoria"],
        "concepto": fila["concepto"], "importe": f"{fila['importe']:.2f}".replace(".", ","),
        "quien": fila["quien"],
    }
    return templates.TemplateResponse(
        request, "form.html",
        {"nav": "gastos", "gasto": gasto, "catalogo": _catalogo(), "accion": f"/gastos/{gasto_id}",
         "titulo": f"Editar apunte #{gasto_id}", "errores": []},
    )


@app.post("/gastos/{gasto_id}")
def editar(
    request: Request, gasto_id: int,
    seccion: str = Form(""), categoria: str = Form(""), concepto: str = Form(""),
    importe: str = Form(""), fecha: str = Form(""), quien: str = Form(""),
):
    if db.obtener_gasto(DB, gasto_id) is None:
        return RedirectResponse("/gastos", status_code=303)

    errores, datos = _leer_form(seccion, categoria, concepto, importe, fecha, quien)
    if errores:
        gasto = {"fecha_input": fecha, "seccion": seccion, "categoria": categoria,
                 "concepto": concepto, "importe": importe, "quien": quien}
        return templates.TemplateResponse(
            request, "form.html",
            {"nav": "gastos", "gasto": gasto, "catalogo": _catalogo(), "accion": f"/gastos/{gasto_id}",
             "titulo": f"Editar apunte #{gasto_id}", "errores": errores},
            status_code=400,
        )

    db.actualizar_gasto(DB, gasto_id, {
        "fecha": datos["fecha"].strftime("%d/%m/%Y"),
        "trimestre": trimestre_de(datos["fecha"]),
        "seccion": datos["seccion"], "categoria": datos["categoria"],
        "concepto": datos["concepto"], "importe": datos["importe"],
        "quien": datos["quien"], "estado": _estado_de(datos),
    })
    return RedirectResponse("/gastos", status_code=303)


@app.get("/gastos/{gasto_id}/borrar", response_class=HTMLResponse)
def borrar_form(request: Request, gasto_id: int):
    fila = db.obtener_gasto(DB, gasto_id)
    if fila is None:
        return RedirectResponse("/gastos", status_code=303)
    return templates.TemplateResponse(request, "confirmar_borrado.html", {"nav": "gastos", "gasto": fila})


@app.post("/gastos/{gasto_id}/borrar")
def borrar(gasto_id: int):
    db.borrar_gasto(DB, gasto_id)
    return RedirectResponse("/gastos", status_code=303)
