# Rellenar el presupuesto con ayuda de una IA

**Objetivo:** dado el Excel de presupuestos del año, que una IA produzca los números que van en la columna
**Presupuestado** de los balances (Grupo y Campamento) y en los **parámetros** de Unidades, **ya mapeados** a las
categorías correctas.

**Qué darle a la IA:** el Excel de presupuestos del año (o sus números) + **este documento** + (útil) `MANUAL.md`.

---

## De dónde salen los números (estructura del Excel de presupuestos)
- Hoja **"Presupuesto 25-26"** → desglose de GASTOS por *partida → línea*, con columnas **1º/2º/3º trimestre**. (Para GRUPO.)
- Libro de campamento, hoja **"PRESUPUESTOS"** → partidas por bloque, **importe único**. (Para CAMPAMENTO.)
- Hoja **"Datos grupo ronda"** → nº educandos/scouters por unidad y tarifas. (Para UNIDADES.)

---

## Reglas de mapeo (lo importante)

### GRUPO — por trimestre
Cada **categoría del Balance Grupo** se rellena con la(s) **línea(s) del desglose**. La mayoría es 1:1 por nombre;
ojo con estas:
- **Seguros EdM** = suma de "Cuota seguro EdM" + "Cuota seguro nuevos asociados".
- **Formación** = suma de los cursos (monitor, coordinador, delegado…).
- **PAG 2025** ← la línea "P.A.G. 20XX" del año.
- **NO van a Grupo** (son de otra parte): "Salidas de Secciones" (es el presupuesto de las **Excursión de unidad**
  de las unidades) y "Material Secciones" / dinero a unidades (es el **Dinero entregado** por unidad).
- Si una línea del presupuesto no tiene categoría en el balance → avisar (no inventar).

**Ejemplo resuelto 25/26** (Categoría → 1ºT · 2ºT · 3ºT):

| Categoría | 1ºT | 2ºT | 3ºT |
|---|--:|--:|--:|
| Seguros EdM | 0 | 9.172 | 0 |
| Formación | 2.394 | 0 | 0 |
| Excursiones de grupo | 12.800 | 3.000 | 0 |
| Actividades de grupo | 0 | 1.936 | 1.232 |
| Juegos de grupo | 135 | 65 | 70 |
| Actividades con padres | 80 | 300 | 100 |
| Actividades de voluntariado | 200 | 0 | 0 |
| Actividades de scouters | 540 | 640 | 170 |
| Comidas scouters | 850,50 | 607,50 | 243 |
| Coches de apoyo | 160 | 190 | 0 |
| Fotocopias | 40 | 0 | 50 |
| Fotografía y vídeo | 82 | 0 | 0 |
| Intendencia | 741 | 1.870 | 590 |
| Llaves | 20 | 0 | 0 |
| Botiquín | 80 | 0 | 0 |
| Página web | 0 | 66 | 0 |
| Búsqueda campamento | 500 | 40 | 0 |
| Trovador | 120 | 30 | 0 |
| Pañoletas | 200 | 0 | 0 |
| Coordinación de grupo | 50 | 50 | 50 |
| Recuerdo viento | 0 | 0 | 450 |
| Imprevistos | 200 | 400 | 200 |
| PAG 2025 | 0 | 0 | 1.500 |

### CAMPAMENTO — importe único
1:1 por nombre de partida (los nombres coinciden con las categorías del balance).

**Ejemplo resuelto 25/26** (Categoría → Importe): Autobuses 5.900 · Camión 3.990 · Coche y furgoneta 3.300 ·
Gasolina y peajes 700 · Desplazamientos 0 · Intendente 700 · Cocinero 700 · Pinches 1.175 · Seguros extra 35 ·
Makro 4.200 · Supermercado 2.200 · Carnicería 6.600 · Panadería 1.100 · Frutería 3.000 · Comida misiones 180 ·
Parrillada 495 · Renovación botiquín 80 · Farmacia 500 · Iris 200 · Hidrográficas 70 · Finca campamento 400 ·
Imprevistos colo 200 · Comida colo 418 · Pala excavadora 500 · Impresos colo 15 · Gasolina colo 150 · Imprevistos
200 · Toldos 444 · Pita 537,97 · Plásticos 483 · Material de cocina 350 · Sistema de aguas 18 · Madera 5.723 ·
Renovación material 883,82 · Ferretería (Obramat y campa) 630 · Gastos coordinación 52 · Material limpieza 1.350 ·
Proyecto electricidad + nevera 804,75 · Viento campa 40 · Castores 120 · Manada 324 · Tropa 204 · Escultas 279 ·
Clan 216 · Juegos de grupo 150 · Cena jefes 540.

### UNIDADES — parámetros (no son celdas de presupuesto)
El presupuesto de unidades se calcula en la hoja con 3 parámetros + los conteos:
- **€ por persona — Material**, **€ por persona — Excursión**, **Mínimo de Material por unidad** (van en el bloque
  PARÁMETROS de la pestaña `Balance Unidades`).
- **Conteos** por unidad (editables): Castores 25 educandos / 7 scouters · Manada 39/7 · Tropa 24/8 · Escultas 37/3
  · Clan 24/2.
- ⚠️ **Aviso de cálculo:** el Excel histórico usa € por **educando** (3,50) y mínimo 100 €/unidad·trimestre. El
  modelo nuevo usa € por **persona** (educando+scouter) y es **anual**. La IA (o tú) debe **recalcular la tarifa**
  o decidir las nuevas (no copiar 3,50 sin más).

---

## Qué debe DEVOLVER la IA
1. **Tabla para `Presupuesto Grupo`**: `Categoría | 1ºT | 2ºT | 3ºT` (23 filas), lista para pegar.
2. **Tabla para `Presupuesto Campamento`**: `Categoría | Importe` (46 filas), lista para pegar.
3. **Parámetros de Unidades**: los 3 valores + los conteos.
4. Avisar de cualquier línea del presupuesto que no encaje en ninguna categoría.

> El sitio ideal donde pegar (1) y (2) son unas pestañas `Presupuesto Grupo` / `Presupuesto Campamento` con las que
> los balances se rellenan solos (vía VLOOKUP). Si quieres, pídeme que te las monte en el script.

---

## Prompt para la IA (cópialo)

```
Tengo un sistema de gastos de un grupo scout (Google Sheets). Quiero que rellenes el PRESUPUESTO.
Te adjunto: el Excel de presupuestos del año, este documento (RELLENAR-PRESUPUESTO-CON-IA.md) y MANUAL.md.

Haz lo siguiente, siguiendo las REGLAS DE MAPEO del documento:
1. Para GRUPO: dame una tabla "Categoría | 1ºT | 2ºT | 3ºT" con las 23 categorías y sus importes por
   trimestre, aplicando los casos especiales (Seguros EdM = suma de seguros; Formación = suma de cursos;
   "Salidas de Secciones" y "Material Secciones" NO van a Grupo; etc.).
2. Para CAMPAMENTO: dame una tabla "Categoría | Importe" con las 46 partidas (1:1 por nombre).
3. Para UNIDADES: dame el € por persona (material y excursión) y el mínimo, RECALCULADOS para € por
   persona = educando+scouter y base ANUAL (no copies el 3,50 por educando sin recalcular); y los conteos.
4. Avísame de cualquier línea del presupuesto que no encaje en ninguna categoría.

Devuélvelo en tablas listas para pegar. No inventes números: si algo no está claro, pregúntame.
```
