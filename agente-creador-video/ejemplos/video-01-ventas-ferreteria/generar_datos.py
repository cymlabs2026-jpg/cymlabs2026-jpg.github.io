"""Genera las ventas ficticias de una ferretería para el video 01.

Los datos son inventados, pero tienen historias reales que Claude debe encontrar
(estacionalidad, una sede que cae, una categoría que vende mucho y deja poco) y
errores sembrados a propósito para que el primer prompt los detecte.

Uso:  python generar_datos.py
Salida: ventas_ferreteria.xlsx y clave_de_respuestas.md en esta misma carpeta.
Siempre produce los mismos datos (semilla fija).
"""

from __future__ import annotations

import random
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

AQUI = Path(__file__).parent
SEMILLA = 2026

INICIO = date(2025, 11, 1)
FIN = date(2026, 10, 31)
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

SEDES = {
    # nombre: (líneas de venta diarias promedio, vendedores)
    "Palmira Centro": (5.0, ["Andrea Gómez", "Luis Cárdenas", "Marta Ríos"]),
    "Palmira Norte": (3.6, ["Jorge Patiño", "Diana Castro"]),
    "Candelaria": (2.0, ["Felipe Mora", "Sandra Ruiz"]),
}

# categoría: (peso en ventas, margen típico, [(producto, precio de venta COP)])
CATEGORIAS = {
    "Herramientas eléctricas": (0.45, 0.12, [("Taladro percutor 650 W", 289_000), ("Pulidora 4-1/2\" 850 W", 239_000),
                                           ("Sierra circular 7-1/4\"", 459_000), ("Atornillador inalámbrico 12 V", 319_000)]),
    "Herramientas manuales": (1.0, 0.32, [("Martillo de uña 16 oz", 32_000), ("Juego de destornilladores x6", 45_000),
                                          ("Llave expansiva 10\"", 38_000), ("Flexómetro 5 m", 18_500)]),
    "Tornillería y fijaciones": (1.6, 0.45, [("Caja tornillo drywall x100", 14_500), ("Chazos plásticos 1/4\" x100", 9_800),
                                             ("Pernos hexagonales 3/8\" x10", 16_000), ("Puntillas 2\" libra", 6_500)]),
    "Pinturas": (1.0, 0.28, [("Vinilo tipo 1 galón", 78_000), ("Esmalte sintético galón", 92_000),
                             ("Rodillo de felpa 9\"", 21_000), ("Thinner galón", 34_000)]),
    "Plomería": (1.0, 0.30, [("Tubo PVC 1/2\" x 6 m", 19_500), ("Llave de paso 1/2\"", 27_000),
                             ("Sifón flexible", 15_500), ("Soldadura PVC 1/4 galón", 42_000)]),
    "Electricidad": (1.1, 0.33, [("Cable #12 x metro", 4_200), ("Toma doble con polo", 9_500),
                                 ("Interruptor sencillo", 7_800), ("Bombillo LED 12 W", 8_900)]),
    "Construcción": (1.2, 0.15, [("Cemento gris 50 kg", 34_500), ("Arena lavada bulto", 9_000),
                                 ("Varilla corrugada 3/8\"", 21_000), ("Bloque #5", 2_400)]),
    "Impermeabilizantes": (0.6, 0.36, [("Manto asfáltico 3 mm rollo", 189_000), ("Impermeabilizante acrílico galón", 96_000),
                                       ("Sellador de grietas 300 ml", 23_000)]),
}

MEDIOS_PAGO = [("Efectivo", 0.34), ("Tarjeta", 0.27), ("Nequi", 0.2), ("Transferencia", 0.12), ("Crédito", 0.07)]

# Cantidades típicas por línea según la categoría (los bloques y la puntilla se venden por montón).
CANTIDAD = {"Construcción": (2, 40), "Tornillería y fijaciones": (1, 8), "Electricidad": (1, 25),
            "Herramientas eléctricas": (1, 2)}

# Afluencia de clientes por mes: diciembre es temporada alta; enero, la cuesta de enero.
FACTOR_MES = {12: 1.4, 1: 0.85}


def factor_sede(sede: str, d: date) -> float:
    meses_desde_inicio = (d.year - INICIO.year) * 12 + d.month - INICIO.month
    if sede == "Candelaria":
        return 1.0 + 0.07 * meses_desde_inicio  # Sede nueva que crece cada mes.
    if sede == "Palmira Norte" and d >= date(2026, 7, 1):
        return 0.6  # Desde julio abrió un competidor grande al lado.
    return 1.0


def factor_categoria(categoria: str, d: date) -> float:
    m = d.month
    f = 1.0
    if m == 12:
        f *= 1.45 if categoria in ("Pinturas", "Electricidad") else 1.2  # Arreglos de fin de año.
    if categoria == "Impermeabilizantes" and m in (4, 5, 10, 11):
        f *= 2.6  # Temporadas de lluvia.
    if categoria == "Construcción" and m in (1, 2):
        f *= 0.7  # Arranque lento de obras.
    return f


def generar_filas() -> list[dict]:
    # La semilla se fija aquí y no al importar: otras librerías (el navegador del
    # renderizador, por ejemplo) consumen números al azar y cambiarían los datos.
    random.seed(SEMILLA)
    filas = []
    factura = 10_000
    d = INICIO
    while d <= FIN:
        if d.weekday() == 6 and random.random() < 0.6:  # Domingo: la mayoría de días cierran.
            d += timedelta(days=1)
            continue
        for sede, (lineas_dia, vendedores) in SEDES.items():
            esperado = lineas_dia * factor_sede(sede, d) * FACTOR_MES.get(d.month, 1.0)
            n = max(0, round(random.gauss(esperado, esperado * 0.2)))
            for _ in range(n):
                categorias = list(CATEGORIAS)
                pesos = [CATEGORIAS[c][0] * factor_categoria(c, d) for c in categorias]
                cat = random.choices(categorias, pesos)[0]
                _, margen, productos = CATEGORIAS[cat]
                producto, precio = random.choice(productos)
                lo, hi = CANTIDAD.get(cat, (1, 4))
                cantidad = random.randint(lo, hi)
                costo = round(precio * (1 - random.gauss(margen, 0.02)), -1)
                factura += 1
                filas.append({
                    "Fecha": d,
                    "Factura": f"FV-{factura}",
                    "Sede": sede,
                    "Categoría": cat,
                    "Producto": producto,
                    "Cantidad": cantidad,
                    "Precio unitario": precio,
                    "Costo unitario": costo,
                    "Total venta": cantidad * precio,
                    "Vendedor": random.choice(vendedores),
                    "Medio de pago": random.choices([m for m, _ in MEDIOS_PAGO], [p for _, p in MEDIOS_PAGO])[0],
                })
        d += timedelta(days=1)
    return filas


def sembrar_errores(filas: list[dict]) -> list[str]:
    """Introduce errores típicos de un Excel real y devuelve su descripción."""
    errores = []
    elegibles = list(range(len(filas)))
    random.shuffle(elegibles)
    tomar = lambda n: [elegibles.pop() for _ in range(n)]

    for i in tomar(12):
        filas[i]["Sede"] = random.choice(["palmira centro", "Palmira Centro ", "Centro", "P. Centro"])
    errores.append("12 filas con la sede escrita de otra forma: «palmira centro», «Palmira Centro » (con espacio al final), «Centro» y «P. Centro».")

    for i in tomar(8):
        filas[i]["Costo unitario"] = None
    errores.append("8 filas sin costo unitario (celda vacía).")

    for i in tomar(10):
        filas[i]["Fecha"] = filas[i]["Fecha"].strftime("%d/%m/%Y")
    errores.append("10 fechas guardadas como texto (dd/mm/aaaa) en lugar de fecha.")

    for i in tomar(4):
        filas[i]["Cantidad"] = -filas[i]["Cantidad"]
        filas[i]["Total venta"] = filas[i]["Cantidad"] * filas[i]["Precio unitario"]
    errores.append("4 devoluciones con cantidad negativa, sin ninguna marca que las identifique.")

    i = tomar(1)[0]
    filas[i]["Cantidad"] = 1000
    filas[i]["Total venta"] = 1000 * filas[i]["Precio unitario"]
    errores.append(f"1 cantidad absurda: 1.000 unidades de «{filas[i]['Producto']}» en la factura {filas[i]['Factura']} (seguramente eran 10).")

    for i in tomar(5):
        filas[i]["Total venta"] = filas[i]["Total venta"] + random.choice([10_000, -5_000, 50_000])
    errores.append("5 filas donde el total no coincide con cantidad × precio.")

    duplicadas = [dict(filas[i]) for i in tomar(6)]
    for dup in duplicadas:
        filas.append(dup)
    errores.append("6 facturas duplicadas (filas idénticas repetidas).")
    filas.sort(key=lambda f: (f["Fecha"] if isinstance(f["Fecha"], date) else _fecha_texto(f["Fecha"]), f["Factura"]))
    return errores


def _fecha_texto(texto: str) -> date:
    dia, mes, anio = (int(x) for x in texto.split("/"))
    return date(anio, mes, dia)


def escribir_excel(filas: list[dict], ruta: Path) -> None:
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Ventas"
    columnas = list(filas[0])
    hoja.append(columnas)
    for f in filas:
        hoja.append([f[c] for c in columnas])
    for celda in hoja[1]:
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor="0F172A")
    anchos = {"Fecha": 12, "Factura": 11, "Sede": 16, "Categoría": 24, "Producto": 34, "Cantidad": 10,
              "Precio unitario": 15, "Costo unitario": 15, "Total venta": 14, "Vendedor": 16, "Medio de pago": 15}
    for i, c in enumerate(columnas, 1):
        hoja.column_dimensions[get_column_letter(i)].width = anchos[c]
    for fila in hoja.iter_rows(min_row=2):
        if isinstance(fila[0].value, date):
            fila[0].number_format = "DD/MM/YYYY"
        for celda in fila[6:9]:
            celda.number_format = "#,##0"
    hoja.freeze_panes = "A2"
    libro.save(ruta)


def cop(valor: float) -> str:
    return f"${valor:,.0f}".replace(",", ".")


def millones(valor: float) -> str:
    return f"${valor / 1e6:,.1f} M".replace(",", "X").replace(".", ",").replace("X", ".")


def clave(filas_limpias: list[dict], errores: list[str], total_filas: int) -> str:
    por_mes_sede = defaultdict(float)
    por_cat = defaultdict(lambda: [0.0, 0.0])
    por_sede = defaultdict(float)
    for f in filas_limpias:
        mes = (f["Fecha"].year, f["Fecha"].month)
        por_mes_sede[(mes, f["Sede"])] += f["Total venta"]
        por_sede[f["Sede"]] += f["Total venta"]
        por_cat[f["Categoría"]][0] += f["Total venta"]
        por_cat[f["Categoría"]][1] += f["Cantidad"] * f["Costo unitario"]
    total = sum(por_sede.values())
    costo = sum(c for _, c in por_cat.values())
    meses = sorted({m for m, _ in por_mes_sede})
    por_mes = {m: sum(por_mes_sede[(m, s)] for s in SEDES) for m in meses}
    mejor, peor = max(por_mes, key=por_mes.get), min(por_mes, key=por_mes.get)
    norte = [(m, por_mes_sede[(m, "Palmira Norte")]) for m in meses]
    norte_antes = sum(v for m, v in norte if m < (2026, 7)) / sum(1 for m, _ in norte if m < (2026, 7))
    norte_despues = sum(v for m, v in norte if m >= (2026, 7)) / sum(1 for m, _ in norte if m >= (2026, 7))
    caida = 100 * (1 - norte_despues / norte_antes)
    bajo = ("Construcción", "Herramientas eléctricas")
    participacion_bajo_margen = 100 * sum(por_cat[c][0] for c in bajo) / total
    margen_bajo_margen = 100 * sum(por_cat[c][0] - por_cat[c][1] for c in bajo) / (total - costo)

    lineas = [
        "# Clave de respuestas · Video 01",
        "",
        "Úsala para **verificar a Claude mientras grabas**. Si una cifra de Claude no se parece a estas, dilo en el video: enseñar a verificar es parte del mensaje.",
        "",
        "Las cifras están calculadas **sobre los datos limpios** (sin errores sembrados). Si Claude analiza sin limpiar, sus totales se desvían un poco, sobre todo por la cantidad absurda de 1.000 unidades.",
        "",
        "## Lo que el prompt 1 debería encontrar",
        "",
        f"El archivo tiene {total_filas:,} filas. Errores sembrados:".replace(",", "."),
        "",
        *[f"- {e}" for e in errores],
        "",
        "## Cifras generales (noviembre 2025 – octubre 2026)",
        "",
        f"- Ventas totales: **{millones(total)}**",
        f"- Margen bruto: **{millones(total - costo)}** ({f"{100 * (total - costo) / total:.1f}".replace(".", ",")} %)",
        "",
        "| Sede | Ventas | Participación |",
        "|---|---|---|",
        *[f"| {s} | {millones(v)} | {100 * v / total:.0f} % |" for s, v in sorted(por_sede.items(), key=lambda x: -x[1])],
        "",
        "## Rentabilidad por categoría",
        "",
        "| Categoría | Ventas | Margen % |",
        "|---|---|---|",
        *[
            f"| {c} | {millones(v)} | {100 * (v - k) / v:.0f} % |"
            for c, (v, k) in sorted(por_cat.items(), key=lambda x: -x[1][0])
        ],
        "",
        "## Ventas por mes y sede (millones de COP)",
        "",
        "| Mes | " + " | ".join(SEDES) + " |",
        "|---|" + "---|" * len(SEDES),
        *[
            f"| {MESES[m - 1]} {a} | "
            + " | ".join(f"{por_mes_sede[((a, m), s)] / 1e6:,.1f}".replace(".", ",") for s in SEDES)
            + " |"
            for a, m in meses
        ],
        "",
        "## Ventas totales por mes",
        "",
        *[f"- {MESES[m - 1]} {a}: {millones(por_mes[(a, m)])}" for a, m in meses],
        "",
        "## Las historias que el panel debería contar",
        "",
        f"1. **Palmira Norte cae desde julio de 2026:** pasó de {millones(norte_antes)} a {millones(norte_despues)} al mes en promedio "
        f"({caida:.0f} % menos). En los datos no hay una causa; en el guion, la explicación es que abrió un competidor grande al lado. Es la alerta principal.",
        f"2. **Candelaria crece:** de {millones(por_mes_sede[(meses[0], 'Candelaria')])} en {MESES[meses[0][1] - 1]} a "
        f"{millones(por_mes_sede[(meses[-1], 'Candelaria')])} en {MESES[meses[-1][1] - 1]}. Es la sede más pequeña, pero la de mejor tendencia.",
        f"3. **Construcción y herramientas eléctricas son el {participacion_bajo_margen:.0f} % de las ventas pero solo el {margen_bajo_margen:.0f} % del margen.** "
        "Tornillería y fijaciones es lo contrario: tickets pequeños y margen cercano al 45 %.",
        f"4. **Estacionalidad:** {MESES[mejor[1] - 1]} es el mejor mes y {MESES[peor[1] - 1]} el peor (la cuesta de enero). "
        "Impermeabilizantes se dispara en las temporadas de lluvia (abril–mayo y octubre–noviembre).",
        "",
        "Si la proyección de Claude para noviembre y diciembre no sube, pregúntale por la estacionalidad: es un buen momento para el video.",
    ]
    return "\n".join(lineas) + "\n"


def main() -> None:
    filas = generar_filas()
    limpias = [dict(f) for f in filas]
    errores = sembrar_errores(filas)
    escribir_excel(filas, AQUI / "ventas_ferreteria.xlsx")
    (AQUI / "clave_de_respuestas.md").write_text(clave(limpias, errores, len(filas)), encoding="utf-8")
    print(f"{len(filas)} filas escritas en ventas_ferreteria.xlsx")


if __name__ == "__main__":
    main()
