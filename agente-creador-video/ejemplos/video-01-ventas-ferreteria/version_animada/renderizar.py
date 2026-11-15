"""Renderiza la versión animada del video 01 a partir de los datos de la ferretería.

Cada cuadro se dibuja en un navegador sin ventana (escenas.html), con el estado de
la animación calculado solo a partir del tiempo; así el resultado es exacto y
repetible. Luego se une con la intro y la pantalla final de la marca.

Uso (con el agente instalado con el extra [marca]):
    python renderizar.py            # video completo
    python renderizar.py --previa   # solo cuadros fijos de cada escena, para revisar el diseño

Salida: video_01_version_animada.mp4 en esta carpeta.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook

AQUI = Path(__file__).parent
CARPETA_VIDEO = AQUI.parent
sys.path.insert(0, str(CARPETA_VIDEO))

import generar_datos  # noqa: E402  (fija la semilla y regenera los datos limpios)
from agente_video import medios, render  # noqa: E402
from agente_video.config import RAIZ, cargar_config  # noqa: E402
from agente_video.etapas.marca import tarjeta_a_clip  # noqa: E402

FPS = 30
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
TITULO = "Analiza las ventas de tu negocio con Claude en 15 minutos"

DECISIONES = [
    ("Ir a Palmira Norte y entender la caída", "¿Qué cambió en julio: un competidor, los precios, el equipo?"),
    ("Empujar lo que deja margen", "Tornillería, plomería y electricidad a la vista y en combos con lo de alto volumen."),
    ("Preparar diciembre y las lluvias", "Inventario de pinturas, electricidad e impermeabilizantes desde ya."),
]


def calcular_datos() -> dict:
    """Las cifras salen de los datos limpios, las mismas de la clave de respuestas."""
    limpias = generar_datos.generar_filas()
    por_mes_sede = defaultdict(float)
    ventas = costo = 0.0
    bajo_v = bajo_c = 0.0
    for f in limpias:
        mes = (f["Fecha"].year, f["Fecha"].month)
        por_mes_sede[(mes, f["Sede"])] += f["Total venta"]
        c = f["Cantidad"] * f["Costo unitario"]
        ventas += f["Total venta"]
        costo += c
        if f["Categoría"] in ("Construcción", "Herramientas eléctricas"):
            bajo_v += f["Total venta"]
            bajo_c += c
    meses = sorted({m for m, _ in por_mes_sede})
    serie = lambda sede: [[MESES[m - 1], round(por_mes_sede[((a, m), sede)] / 1e6, 1)] for a, m in meses]
    totales = [[MESES[m - 1], round(sum(por_mes_sede[((a, m), s)] for s in generar_datos.SEDES) / 1e6, 1)] for a, m in meses]

    # Las primeras filas del Excel real (con sus errores), para la escena de la hoja de cálculo.
    columnas = ["Fecha", "Sede", "Categoría", "Producto", "Cantidad", "Total venta"]
    hoja = load_workbook(CARPETA_VIDEO / "ventas_ferreteria.xlsx", read_only=True).active
    filas = []
    for fila in hoja.iter_rows(min_row=2, max_row=60, values_only=True):
        fecha, _, sede, cat, prod, cant, _, _, total, _, _ = fila
        fecha = fecha.strftime("%d/%m/%Y") if isinstance(fecha, datetime) else fecha
        filas.append([fecha, sede, cat, prod, cant, f"{total:,.0f}".replace(",", ".")])

    return {
        "columnas": columnas,
        "anchos": [13, 16, 21, 27, 10, 13],
        "numericas": [4, 5],
        "filas": filas,
        "total_filas": hoja.max_row - 1,
        "errores": [
            ["12", "Sedes escritas de otra forma"], ["8", "Costos vacíos"],
            ["10", "Fechas guardadas como texto"], ["4", "Devoluciones sin marcar"],
            ["1", "1.000 galones de thinner"], ["5", "Totales que no cuadran"],
            ["6", "Facturas duplicadas"],
        ],
        "ventas": round(ventas / 1e6, 1),
        "margen": round(100 * (ventas - costo) / ventas, 1),
        "norte": serie("Palmira Norte"),
        "candelaria": serie("Candelaria"),
        "totales": totales,
        "indice_julio": meses.index((2026, 7)),
        "part_ventas": round(100 * bajo_v / ventas),
        "part_margen": round(100 * (bajo_v - bajo_c) / (ventas - costo)),
        "decisiones": DECISIONES,
    }


def armar_html() -> str:
    plantillas = RAIZ / "plantillas" / "marca"
    html = (AQUI / "escenas.html").read_text(encoding="utf-8")
    html = html.replace("/*CSS_MARCA*/", (plantillas / "base.css").read_text(encoding="utf-8"))
    html = html.replace("/*LOGO*/", (plantillas / "logo.svg").read_text(encoding="utf-8"))
    return html.replace("/*DATOS*/", json.dumps(calcular_datos(), ensure_ascii=False))


def abrir_pagina(p):
    navegador = p.chromium.launch(executable_path=os.environ.get("AGENTE_VIDEO_CHROMIUM") or None)
    pagina = navegador.new_page(viewport={"width": 1920, "height": 1080})
    pagina.set_content(armar_html(), wait_until="networkidle")
    pagina.evaluate("document.fonts.ready")
    return navegador, pagina


def previa() -> None:
    """Un cuadro por escena, en el momento en que su animación ya terminó."""
    from playwright.sync_api import sync_playwright

    carpeta = AQUI / "previa"
    carpeta.mkdir(exist_ok=True)
    with sync_playwright() as p:
        navegador, pagina = abrir_pagina(p)
        escenas = pagina.evaluate("ESCENAS")
        inicio = 0
        for id_, dur in escenas:
            pagina.evaluate(f"pintar({inicio + dur * 0.85})")
            pagina.screenshot(path=str(carpeta / f"{id_}.png"))
            inicio += dur
        navegador.close()
    print(f"Cuadros de revisión en {carpeta}")


def video() -> None:
    from playwright.sync_api import sync_playwright

    config = cargar_config()
    config["video"].update(ancho=1920, alto=1080, fps=FPS)
    trabajo = AQUI / "trabajo"
    trabajo.mkdir(exist_ok=True)

    # 1. La animación, cuadro por cuadro.
    animacion = trabajo / "animacion.mp4"
    with sync_playwright() as p:
        navegador, pagina = abrir_pagina(p)
        total = pagina.evaluate("TOTAL")
        cuadros = int(total * FPS)
        ffmpeg = subprocess.Popen(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
             "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest",
             "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS),
             "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", str(animacion)],
            stdin=subprocess.PIPE,
        )
        for i in range(cuadros):
            pagina.evaluate(f"pintar({i / FPS})")
            ffmpeg.stdin.write(pagina.screenshot(type="jpeg", quality=95))
            if i % (FPS * 10) == 0:
                print(f"  {i // FPS:>3} / {int(total)} s", flush=True)
        ffmpeg.stdin.close()
        if ffmpeg.wait() != 0:
            raise RuntimeError("FFmpeg falló al codificar la animación")
        navegador.close()

    # 2. Intro y pantalla final de la marca.
    marca = config["marca"]
    plantillas = RAIZ / "plantillas" / "marca"
    render.a_png(render.llenar(plantillas, "intro.html", {
        "etiqueta": marca["etiqueta"], "titulo": TITULO, "lema": marca["lema"]}), trabajo / "intro.png")
    render.a_png(render.llenar(plantillas, "cierre.html", {
        "etiqueta": "Gracias por ver", "titulo": marca["cierre_titulo"],
        "llamado": marca["cierre_llamado"], "enlace": marca["cierre_enlace"]}), trabajo / "cierre.png")
    tarjeta_a_clip(trabajo / "intro.png", trabajo / "intro.mp4", marca["intro_s"], config["video"])
    tarjeta_a_clip(trabajo / "cierre.png", trabajo / "cierre.mp4", marca["cierre_s"], config["video"])

    # 3. Todo junto.
    salida = AQUI / "video_01_version_animada.mp4"
    medios.concatenar([trabajo / "intro.mp4", animacion, trabajo / "cierre.mp4"], salida)
    print(f"Listo: {salida} ({medios.duracion(salida):.0f} s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--previa", action="store_true")
    previa() if parser.parse_args().previa else video()
