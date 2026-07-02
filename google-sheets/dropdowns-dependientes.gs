/**
 * Bot facturas — utilidades para la hoja de gastos (Google Sheets).
 *
 * 1) Inicializar hoja: crea (si no existen) "Tabla de Gastos", "Catálogo" y las 3 hojas de balance.
 * 2) Desplegables dependientes: al elegir UNIDAD (col A), CATEGORÍA (col C) muestra solo las de esa unidad.
 * 3) Hojas de balance con el GASTADO sumado automáticamente de "Tabla de Gastos".
 *
 * Instalación: Extensiones > Apps Script, pega TODO este código, guarda y recarga la hoja.
 * Usa el menú "Bot facturas".
 *
 * Nota: las fórmulas se insertan con setFormula(s) usando el separador que detecta la hoja
 * (',' o ';'); Google las muestra en tu idioma. No las cambies a mano.
 */

// ===== Configuración =====
const HOJA_DATOS = 'Tabla de Gastos';
const HOJA_CATALOGO = 'Catálogo';
const COL_UNIDAD = 1;     // A
const COL_CATEGORIA = 3;  // C
const FILA_INICIO = 2;
const MONEDA = '#,##0.00" €"';
const FECHA_FMT = 'dd/mm/yyyy';

const CABECERAS_DATOS = ['UNIDAD', 'Trimestre', 'Categoría', 'Importe', 'Factura', 'Fecha', 'Comentarios', 'Enlace factura', 'Quién'];
const CAT_UNIDAD = ['Material de unidad', 'Excursión de unidad', 'Dinero entregado'];

// Colores
const C_CABECERA = '#434343';
const C_CABECERA_TXT = '#ffffff';
const C_PARTIDA = '#d9d9d9';
const C_TITULO = '#fff2cc';
const C_ROJO = '#f4cccc';
const C_VERDE = '#d9ead3';

const UNIDADES = ['Castores', 'Manada', 'Tropa', 'Escultas', 'Clan'];
const FILAS_POR_UNIDAD = 17;

// Separador de argumentos de las fórmulas. Se autodetecta según el idioma de la hoja. No lo toques.
let SEP = ',';

// Categorías de Grupo agrupadas por partida (siguiendo el desglose del presupuesto).
const GRUPO_PARTIDAS = [
  { partida: 'EdM y ASDE', cats: ['Seguros EdM'] },
  { partida: 'Formación', cats: ['Formación'] },
  { partida: 'Actividades', cats: ['Excursiones de grupo', 'Actividades de grupo', 'Juegos de grupo', 'Actividades con padres', 'Actividades de voluntariado', 'Actividades de scouters', 'Comidas scouters', 'Coches de apoyo'] },
  { partida: 'Material', cats: ['Fotocopias', 'Fotografía y vídeo', 'Intendencia', 'Llaves'] },
  { partida: 'Cargos y comisiones', cats: ['Botiquín', 'Página web', 'Búsqueda campamento', 'Trovador', 'Pañoletas', 'Coordinación de grupo', 'Recuerdo viento'] },
  { partida: 'Varios', cats: ['Imprevistos', 'PAG 2025'] }
];

const CAMPAMENTO = [
  { bloque: 'TRANSPORTE', cats: ['Autobuses', 'Camión', 'Coche y furgoneta', 'Gasolina y peajes', 'Desplazamientos'] },
  { bloque: 'CARGOS', cats: ['Intendente', 'Cocinero', 'Pinches', 'Seguros extra'] },
  { bloque: 'ALIMENTACIÓN', cats: ['Makro', 'Supermercado', 'Carnicería', 'Panadería', 'Frutería', 'Comida misiones', 'Parrillada'] },
  { bloque: 'BOTIQUÍN', cats: ['Renovación botiquín', 'Farmacia'] },
  { bloque: 'SITIO CAMPAMENTO', cats: ['Iris', 'Hidrográficas', 'Finca campamento'] },
  { bloque: 'COLONIZACIÓN', cats: ['Imprevistos colo', 'Comida colo', 'Pala excavadora', 'Impresos colo', 'Gasolina colo'] },
  { bloque: 'MATERIAL', cats: ['Imprevistos', 'Toldos', 'Pita', 'Plásticos', 'Material de cocina', 'Sistema de aguas', 'Madera', 'Renovación material', 'Ferretería (Obramat y campa)', 'Gastos coordinación', 'Material limpieza', 'Proyecto electricidad + nevera', 'Viento campa'] },
  { bloque: 'ACTIVIDADES', cats: ['Castores', 'Manada', 'Tropa', 'Escultas', 'Clan', 'Juegos de grupo', 'Cena jefes'] }
];

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Bot facturas')
    .addItem('Inicializar hoja (crear todo)', 'inicializarTodo')
    .addSeparator()
    .addItem('Configurar desplegable de Unidad', 'configurarUnidad')
    .addItem('Aplicar categorías a filas existentes', 'configurarFilasExistentes')
    .addItem('Crear hojas de balance', 'crearHojasBalance')
    .addToUi();
}

// ============================================================
//  INICIALIZACIÓN COMPLETA
// ============================================================

function inicializarTodo() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  SEP = detectarSeparador();
  const msgs = [];
  msgs.push(crearCatalogo(ss));
  msgs.push(crearHojaDatos(ss));
  [['Balance Unidades', crearBalanceUnidades], ['Balance Grupo', crearBalanceGrupo], ['Balance Campamento', crearBalanceCampamento]].forEach(function (par) {
    if (ss.getSheetByName(par[0])) { msgs.push(par[0] + ': ya existía'); return; }
    par[1](ss.insertSheet(par[0]));
    msgs.push(par[0] + ': creada');
  });
  try { configurarUnidad(); } catch (e) { /* la hoja de datos puede no existir aún */ }
  SpreadsheetApp.getUi().alert('Inicialización:\n\n' + msgs.join('\n'));
}

function crearHojaDatos(ss) {
  if (ss.getSheetByName(HOJA_DATOS)) return HOJA_DATOS + ': ya existía (no se toca)';
  const h = ss.insertSheet(HOJA_DATOS);
  h.getRange(1, 1, 1, CABECERAS_DATOS.length).setValues([CABECERAS_DATOS]);
  estiloCabecera(h.getRange(1, 1, 1, CABECERAS_DATOS.length));
  h.setFrozenRows(1);
  const filas = h.getMaxRows() - 1;
  h.getRange(2, 4, filas, 1).setNumberFormat(MONEDA);    // Importe (D)
  h.getRange(2, 6, filas, 1).setNumberFormat(FECHA_FMT); // Fecha (F)
  [90, 80, 200, 90, 110, 95, 260, 260, 140].forEach(function (w, i) { h.setColumnWidth(i + 1, w); });
  return HOJA_DATOS + ': creada';
}

function crearCatalogo(ss) {
  if (ss.getSheetByName(HOJA_CATALOGO)) return HOJA_CATALOGO + ': ya existía (no se toca)';
  const h = ss.insertSheet(HOJA_CATALOGO);
  const filas = [['Unidad', 'Categoría']];
  UNIDADES.forEach(function (u) { CAT_UNIDAD.forEach(function (c) { filas.push([u, c]); }); });
  GRUPO_PARTIDAS.forEach(function (p) { p.cats.forEach(function (c) { filas.push(['Grupo', c]); }); });
  CAMPAMENTO.forEach(function (b) { b.cats.forEach(function (c) { filas.push(['Campamento', c]); }); });
  h.getRange(1, 1, filas.length, 2).setValues(filas);
  estiloCabecera(h.getRange(1, 1, 1, 2));
  h.setFrozenRows(1);
  h.setColumnWidth(1, 140);
  h.setColumnWidth(2, 260);
  return HOJA_CATALOGO + ': creado';
}

// ============================================================
//  1) DESPLEGABLES DEPENDIENTES
// ============================================================

function onEdit(e) {
  const rango = e.range;
  const hoja = rango.getSheet();
  if (hoja.getName() !== HOJA_DATOS) return;
  if (rango.getColumn() !== COL_UNIDAD || rango.getRow() < FILA_INICIO) return;
  const unidad = hoja.getRange(rango.getRow(), COL_UNIDAD).getValue();
  aplicarCategoria(hoja, rango.getRow(), unidad, true);
}

function aplicarCategoria(hoja, fila, unidad, limpiarSiNoEncaja) {
  const celda = hoja.getRange(fila, COL_CATEGORIA);
  const categorias = categoriasDe(unidad);
  if (!categorias.length) {
    celda.clearDataValidations();
    return;
  }
  const regla = SpreadsheetApp.newDataValidation()
    .requireValueInList(categorias, true)
    .setAllowInvalid(false)
    .build();
  celda.setDataValidation(regla);
  if (limpiarSiNoEncaja) {
    const actual = celda.getValue();
    if (actual && categorias.indexOf(actual) === -1) celda.clearContent();
  }
}

function configurarUnidad() {
  const datos = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(HOJA_DATOS);
  const regla = SpreadsheetApp.newDataValidation()
    .requireValueInList(unidadesUnicas(), true)
    .setAllowInvalid(false)
    .build();
  const filas = datos.getMaxRows() - FILA_INICIO + 1;
  datos.getRange(FILA_INICIO, COL_UNIDAD, filas, 1).setDataValidation(regla);
  SpreadsheetApp.getActive().toast('Desplegable de Unidad configurado.');
}

function configurarFilasExistentes() {
  const datos = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(HOJA_DATOS);
  const ultima = datos.getLastRow();
  for (let fila = FILA_INICIO; fila <= ultima; fila++) {
    const unidad = datos.getRange(fila, COL_UNIDAD).getValue();
    if (unidad) aplicarCategoria(datos, fila, unidad, false);
  }
  SpreadsheetApp.getActive().toast('Categorías aplicadas a las filas existentes.');
}

function categoriasDe(unidad) {
  const cat = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(HOJA_CATALOGO);
  if (!cat || cat.getLastRow() < 2) return [];
  const valores = cat.getRange(2, 1, cat.getLastRow() - 1, 2).getValues();
  const lista = [];
  for (const fila of valores) {
    if (fila[0] === unidad && fila[1] !== '' && fila[1] !== null) lista.push(fila[1]);
  }
  return lista;
}

function unidadesUnicas() {
  const cat = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(HOJA_CATALOGO);
  if (!cat || cat.getLastRow() < 2) return [];
  const valores = cat.getRange(2, 1, cat.getLastRow() - 1, 1).getValues();
  const vistas = [];
  for (const fila of valores) {
    if (fila[0] !== '' && vistas.indexOf(fila[0]) === -1) vistas.push(fila[0]);
  }
  return vistas;
}

// ============================================================
//  2) HOJAS DE BALANCE
// ============================================================

function crearHojasBalance() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  SEP = detectarSeparador();
  const creadas = [], existentes = [];
  [['Balance Unidades', crearBalanceUnidades], ['Balance Grupo', crearBalanceGrupo], ['Balance Campamento', crearBalanceCampamento]].forEach(function (par) {
    if (ss.getSheetByName(par[0])) { existentes.push(par[0]); return; }
    par[1](ss.insertSheet(par[0]));
    creadas.push(par[0]);
  });
  let msg = creadas.length ? 'Creadas: ' + creadas.join(', ') + '.' : 'No se creó ninguna hoja nueva.';
  if (existentes.length) {
    msg += '\n\nYa existían (no se han tocado): ' + existentes.join(', ') +
           '.\nBórralas a mano si quieres regenerarlas (ojo: perderías el presupuesto metido a mano).';
  }
  SpreadsheetApp.getUi().alert(msg);
}

// Detecta el separador de argumentos que usa la hoja (',' o ';') de forma empírica.
function detectarSeparador() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const tmp = ss.insertSheet('__sep__' + new Date().getTime());
  tmp.getRange('A1').setFormula('=SUM(1,1)');
  SpreadsheetApp.flush();
  const v = tmp.getRange('A1').getValue();
  ss.deleteSheet(tmp);
  return (v === 2) ? ',' : ';';
}

// --- Helpers de formato ---
function estiloCabecera(rango) {
  rango.setBackground(C_CABECERA).setFontColor(C_CABECERA_TXT).setFontWeight('bold');
}
function pintarBalance(hoja, rangos, soloRojo) {
  const reglas = [];
  rangos.forEach(function (r) {
    reglas.push(SpreadsheetApp.newConditionalFormatRule().whenNumberLessThan(0).setBackground(C_ROJO).setRanges([r]).build());
    if (!soloRojo) reglas.push(SpreadsheetApp.newConditionalFormatRule().whenNumberGreaterThan(0).setBackground(C_VERDE).setRanges([r]).build());
  });
  hoja.setConditionalFormatRules(reglas);
}

// --- Helpers de fórmulas (usan SEP) ---
function sumifGrupo(catCell, tri) {
  return "=SUMIFS('" + HOJA_DATOS + "'!$D:$D" + SEP + "'" + HOJA_DATOS + "'!$A:$A" + SEP + "\"Grupo\"" + SEP +
         "'" + HOJA_DATOS + "'!$C:$C" + SEP + catCell + SEP + "'" + HOJA_DATOS + "'!$B:$B" + SEP + "\"" + tri + "\")";
}
function sumifCamp(catCell) {
  return "=SUMIFS('" + HOJA_DATOS + "'!$D:$D" + SEP + "'" + HOJA_DATOS + "'!$A:$A" + SEP + "\"Campamento\"" + SEP +
         "'" + HOJA_DATOS + "'!$C:$C" + SEP + catCell + ")";
}
function sumifUnidad(unidad, cat, tri) {
  return "=SUMIFS('" + HOJA_DATOS + "'!$D:$D" + SEP + "'" + HOJA_DATOS + "'!$A:$A" + SEP + "\"" + unidad + "\"" + SEP +
         "'" + HOJA_DATOS + "'!$C:$C" + SEP + "\"" + cat + "\"" + SEP + "'" + HOJA_DATOS + "'!$B:$B" + SEP + "\"" + tri + "\")";
}
function sumifUnidadTotal(unidad, cat) {
  return "=SUMIFS('" + HOJA_DATOS + "'!$D:$D" + SEP + "'" + HOJA_DATOS + "'!$A:$A" + SEP + "\"" + unidad + "\"" + SEP +
         "'" + HOJA_DATOS + "'!$C:$C" + SEP + "\"" + cat + "\")";
}
function totalBCD(r) { return "=B" + r + "+C" + r + "+D" + r; }
function resta(p, g) { return ["=B" + p + "-B" + g, "=C" + p + "-C" + g, "=D" + p + "-D" + g, "=E" + p + "-E" + g]; }
function suma2(a, b) { return ["=B" + a + "+B" + b, "=C" + a + "+C" + b, "=D" + a + "+D" + b, "=E" + a + "+E" + b]; }

// --- Balance Grupo: agrupado por partida (como el desglose del presupuesto) ---
function crearBalanceGrupo(hoja) {
  const texto = [[
    'PRESUPUESTADO', '1º Trimestre', '2º Trimestre', '3º Trimestre', 'TOTAL', '',
    'GASTADO', '1º Trimestre', '2º Trimestre', '3º Trimestre', 'TOTAL', '',
    'BALANCE', '1º Trimestre', '2º Trimestre', '3º Trimestre', 'TOTAL'
  ]];
  const partidaRows = [], catRows = [];
  GRUPO_PARTIDAS.forEach(function (p) {
    texto.push([p.partida, '', '', '', '', '', p.partida, '', '', '', '', '', p.partida, '', '', '', '']);
    const cab = texto.length, primera = cab + 1;
    p.cats.forEach(function (cat) {
      texto.push([cat, '', '', '', '', '', cat, '', '', '', '', '', cat, '', '', '', '']);
      catRows.push(texto.length);
    });
    partidaRows.push({ row: cab, primera: primera, ultima: texto.length });
  });
  hoja.getRange(1, 1, texto.length, 17).setValues(texto);

  catRows.forEach(function (r) {
    hoja.getRange(r, 5).setFormula('=B' + r + '+C' + r + '+D' + r);
    hoja.getRange(r, 8, 1, 4).setFormulas([[sumifGrupo('$G' + r, '1º'), sumifGrupo('$G' + r, '2º'), sumifGrupo('$G' + r, '3º'), '=H' + r + '+I' + r + '+J' + r]]);
    hoja.getRange(r, 14, 1, 4).setFormulas([['=B' + r + '-H' + r, '=C' + r + '-I' + r, '=D' + r + '-J' + r, '=E' + r + '-K' + r]]);
  });

  partidaRows.forEach(function (p) {
    if (p.ultima < p.primera) return;
    [2, 3, 4, 5, 8, 9, 10, 11, 14, 15, 16, 17].forEach(function (c) {
      const L = String.fromCharCode(64 + c);
      hoja.getRange(p.row, c).setFormula('=SUM(' + L + p.primera + ':' + L + p.ultima + ')');
    });
  });

  estiloCabecera(hoja.getRange(1, 1, 1, 17));
  hoja.setFrozenRows(1);
  partidaRows.forEach(function (p) { hoja.getRange(p.row, 1, 1, 17).setFontWeight('bold').setBackground(C_PARTIDA); });
  const total = texto.length - 1;
  [2, 8, 14].forEach(function (c) { hoja.getRange(2, c, total, 4).setNumberFormat(MONEDA); });
  pintarBalance(hoja, [hoja.getRange(2, 14, total, 4)], false);
  for (let c = 1; c <= 17; c++) { hoja.setColumnWidth(c, (c === 1 || c === 7 || c === 13) ? 160 : ((c === 6 || c === 12) ? 20 : 85)); }
}

// --- Balance Campamento: una tabla por categoría (agrupada por bloque), sin trimestres ---
function crearBalanceCampamento(hoja) {
  const filas = [['Categoría (campamento)', 'Presupuestado', 'Gastado', 'Balance']];
  const catRows = [], bloqueRows = [];
  CAMPAMENTO.forEach(function (b) {
    filas.push([b.bloque, '', '', '']); bloqueRows.push(filas.length);
    b.cats.forEach(function (c) { filas.push([c, '', '', '']); catRows.push(filas.length); });
  });
  hoja.getRange(1, 1, filas.length, 4).setValues(filas);
  catRows.forEach(function (r) {
    hoja.getRange(r, 3).setFormula(sumifCamp('$A' + r));
    hoja.getRange(r, 4).setFormula('=B' + r + '-C' + r);
  });
  estiloCabecera(hoja.getRange(1, 1, 1, 4));
  bloqueRows.forEach(function (r) { hoja.getRange(r, 1, 1, 4).setFontWeight('bold').setBackground(C_PARTIDA); });
  hoja.getRange(2, 2, filas.length - 1, 3).setNumberFormat(MONEDA);
  hoja.setFrozenRows(1);
  [230, 120, 120, 120].forEach(function (w, i) { hoja.setColumnWidth(i + 1, w); });
  pintarBalance(hoja, [hoja.getRange(2, 4, filas.length - 1, 1)], false);
}

// --- Balance Unidades: parámetros editables + mini-tabla ANUAL por unidad ---
function crearBalanceUnidades(hoja) {
  // Nº educandos/scouters conocidos 25/26 (editables a mano)
  const conteos = { 'Castores': [25, 7], 'Manada': [39, 7], 'Tropa': [24, 8], 'Escultas': [37, 3], 'Clan': [24, 2] };
  const filas = [
    ['PARÁMETROS (UNIDADES)', '', '', ''],
    ['€ por persona — Material', '', '', ''],
    ['€ por persona — Excursión', '', '', ''],
    ['Mínimo de Material por unidad', '', '', ''],
    ['', '', '', '']
  ];
  // Parámetros editables en: B2 (€ material), B3 (€ excursión), B4 (mínimo)
  const bloques = [];
  UNIDADES.forEach(function (u) {
    const base = filas.length + 1;
    const c = conteos[u] || ['', ''];
    filas.push([u, '', '', '']);
    filas.push(['Educandos', c[0], '', '']);
    filas.push(['Scouters', c[1], '', '']);
    filas.push(['Personas', '', '', '']);
    filas.push(['', 'Presupuesto', 'Gastado', 'Balance']);
    filas.push(['Material de unidad', '', '', '']);
    filas.push(['Excursión de unidad', '', '', '']);
    filas.push(['Dinero entregado', '', '', '']);
    filas.push(['Gasto apuntado', '', '', '']);
    filas.push(['Dinero sin justificar', '', '', '']);
    filas.push(['', '', '', '']);
    bloques.push({ u: u, base: base });
  });
  hoja.getRange(1, 1, filas.length, 4).setValues(filas);

  bloques.forEach(function (it) {
    const b = it.base, u = it.u;
    hoja.getRange(b + 3, 2).setFormula('=B' + (b + 1) + '+B' + (b + 2));                  // Personas
    hoja.getRange(b + 5, 2).setFormula('=MAX(B' + (b + 3) + '*$B$2' + SEP + '$B$4)');      // Presup. Material
    hoja.getRange(b + 5, 3).setFormula(sumifUnidadTotal(u, 'Material de unidad'));         // Gastado Material
    hoja.getRange(b + 5, 4).setFormula('=B' + (b + 5) + '-C' + (b + 5));                   // Balance Material
    hoja.getRange(b + 6, 2).setFormula('=B' + (b + 3) + '*$B$3');                          // Presup. Excursión
    hoja.getRange(b + 6, 3).setFormula(sumifUnidadTotal(u, 'Excursión de unidad'));        // Gastado Excursión
    hoja.getRange(b + 6, 4).setFormula('=B' + (b + 6) + '-C' + (b + 6));                   // Balance Excursión
    hoja.getRange(b + 7, 3).setFormula(sumifUnidadTotal(u, 'Dinero entregado'));           // Dinero entregado
    hoja.getRange(b + 8, 3).setFormula('=C' + (b + 5) + '+C' + (b + 6));                   // Gasto apuntado
    hoja.getRange(b + 9, 4).setFormula('=C' + (b + 7) + '-C' + (b + 8));                   // Dinero sin justificar
  });

  estiloCabecera(hoja.getRange(1, 1, 1, 4));
  hoja.getRange(1, 1, 4, 1).setFontWeight('bold');
  hoja.getRange(2, 2, 3, 1).setNumberFormat(MONEDA);   // valores de parámetros
  bloques.forEach(function (it) {
    const b = it.base;
    hoja.getRange(b, 1, 1, 4).setFontWeight('bold').setBackground(C_TITULO);
    hoja.getRange(b + 4, 1, 1, 4).setFontWeight('bold').setBackground(C_PARTIDA);
    hoja.getRange(b + 5, 2, 5, 3).setNumberFormat(MONEDA);
  });
  pintarBalance(hoja, [hoja.getRange(1, 4, filas.length, 1)], false);
  [220, 110, 110, 110].forEach(function (w, i) { hoja.setColumnWidth(i + 1, w); });
  hoja.setFrozenRows(1);
}
