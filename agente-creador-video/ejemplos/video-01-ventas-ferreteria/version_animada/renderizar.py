"""Renderiza la versión animada del video 01 a partir de los datos de la ferretería.

Cada cuadro se dibuja en un navegador sin ventana (escenas.html), con el estado de
la animación calculado solo a partir del tiempo; así el resultado es exacto y
repetible. Luego se une con la intro y la pantalla final de la marca.

Uso (con el agente instalado con los extras [marca] y [voz]):
    python renderizar.py                                  # video sin voz
    python renderizar.py --voz ruta/es_MX-claude-high.onnx  # con voz sintética y subtítulos
    python renderizar.py --locucion carpeta/              # con tu voz grabada (e1.wav … e9.wav, cierre.wav)
    python renderizar.py --previa                         # cuadros fijos para revisar el diseño

Salida en esta carpeta: el video (por defecto video_01_version_animada.mp4) y, si hay voz,
sus subtítulos con el mismo nombre y extensión .srt.
"""

from __future__ import annotations

import argparse
import json
import re
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
from agente_video.etapas.marca import tarjeta_a_clip, valores_cierre  # noqa: E402
from agente_video.etapas.subtitulos import generar_srt  # noqa: E402

FPS = 30
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
TITULO = "Analiza las ventas de tu negocio con Claude en 15 minutos"

# Duración mínima de cada escena (s). Si la locución es más larga, la escena se alarga.
ESCENAS_BASE = [["e1", 8], ["e2", 11], ["e3", 7], ["e4", 10], ["e5", 8], ["e6", 10], ["e7", 9], ["e8", 11], ["e9", 7]]
ENTRADA_VOZ = 0.6   # La voz empieza un poco después de que aparece la escena.
SALIDA_VOZ = 0.9    # Y deja un respiro antes de la siguiente.

# Locución, escrita como se lee (las cifras en palabras). La pronunciación de
# «Claude» y «C&M» la corrige el diccionario de config/glosario.toml.
LOCUCION = {
    "e1": "Este es un año completo de ventas de una ferretería con tres sedes: más de tres mil seiscientas filas. Y nadie lo había mirado.",
    "e2": "Antes de analizar, hay que entender los datos. Y aquí había siete errores escondidos: sedes mal escritas, "
          "costos vacíos, fechas guardadas como texto, devoluciones sin marcar, una venta de mil galones de thinner, "
          "totales que no cuadran y facturas duplicadas.",
    "e3": "Con los datos limpios, el año se resume en dos cifras: quinientos setenta millones de pesos en ventas, "
          "y un margen bruto del veinticinco por ciento.",
    "e4": "Primera alerta: Palmira Norte se está cayendo. Desde julio vende un veintiocho por ciento menos cada mes. "
          "Algo cambió, y hay que averiguar qué.",
    "e5": "La buena noticia: Candelaria, la sede más pequeña, pasó de nueve a diecisiete millones al mes. Casi duplica sus ventas.",
    "e6": "Segunda alerta: vender mucho no es ganar mucho. Construcción y herramientas eléctricas son el cuarenta y cuatro "
          "por ciento de las ventas, pero solo el veinticuatro por ciento del margen. La tornillería, en cambio, deja un "
          "cuarenta y cinco por ciento.",
    "e7": "Y el calendario manda: diciembre es el mejor mes del año. Enero, el peor.",
    "e8": "Con esto, hay tres decisiones claras para el próximo mes. Uno: ir a Palmira Norte y entender la caída. "
          "Dos: empujar los productos que dejan margen. Y tres: preparar el inventario para diciembre y para la temporada de lluvias.",
    "e9": "Todo este análisis se hizo con Claude, en una tarde, sin fórmulas. Los prompts están en la descripción, "
          "y el paso a paso, en el próximo video.",
    "cierre": "Si quieres que tu equipo trabaje así, conoce la formación Claude Empresarial de C&M Labs. Nos vemos en el próximo video.",
}

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


def armar_html(escenas: list | None = None) -> str:
    plantillas = RAIZ / "plantillas" / "marca"
    html = (AQUI / "escenas.html").read_text(encoding="utf-8")
    html = html.replace("/*CSS_MARCA*/", (plantillas / "base.css").read_text(encoding="utf-8"))
    html = html.replace("/*LOGO*/", (plantillas / "logo.svg").read_text(encoding="utf-8"))
    datos = {**calcular_datos(), "escenas": escenas or ESCENAS_BASE}
    return html.replace("/*DATOS*/", json.dumps(datos, ensure_ascii=False))


def abrir_pagina(p, escenas: list | None = None):
    navegador = p.chromium.launch(executable_path=os.environ.get("AGENTE_VIDEO_CHROMIUM") or None)
    pagina = navegador.new_page(viewport={"width": 1920, "height": 1080})
    pagina.set_content(armar_html(escenas), wait_until="networkidle")
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


def sintetizar_locucion(modelo: str, config: dict, carpeta: Path) -> dict[str, tuple[Path, float]]:
    from agente_video.proveedores.tts import VozPiper

    voz = VozPiper(modelo, velocidad=config["voz"].get("velocidad", 1.0), pronunciacion=config["_pronunciacion"])
    carpeta.mkdir(parents=True, exist_ok=True)
    clips = {}
    for clave, texto in LOCUCION.items():
        wav = carpeta / f"{clave}.wav"
        voz.sintetizar(texto, str(wav))
        clips[clave] = (wav, medios.duracion(wav))
    return clips


def cargar_locucion(carpeta: Path) -> dict[str, tuple[Path, float]]:
    """Locución grabada: un archivo por bloque y, si existe, textos.json con lo que se dijo (para los subtítulos)."""
    clips = {}
    for clave in LOCUCION:
        archivo = next((carpeta / f"{clave}{ext}" for ext in (".wav", ".mp3", ".m4a") if (carpeta / f"{clave}{ext}").exists()), None)
        if archivo is None:
            raise SystemExit(f"Falta el bloque {clave} en {carpeta}")
        clips[clave] = (archivo, medios.duracion(archivo))
    textos = carpeta / "textos.json"
    if textos.exists():
        LOCUCION.update(json.loads(textos.read_text(encoding="utf-8")))
    return clips


def video(modelo_voz: str | None, locucion: str | None = None, nombre_salida: str = "video_01_version_animada.mp4",
          musica: bool = False) -> None:
    from playwright.sync_api import sync_playwright

    config = cargar_config()
    config["video"].update(ancho=1920, alto=1080, fps=FPS)
    trabajo = AQUI / "trabajo"
    trabajo.mkdir(exist_ok=True)
    marca = config["marca"]
    # Pantalla final de este video: foto del equipo en el recuadro y logo en el círculo.
    if (AQUI / "cierre_foto.webp").exists():
        marca["cierre_imagen"] = str(AQUI / "cierre_foto.webp")
    marca["cierre_logo_en_circulo"] = True

    # 0. Locución: cada escena dura al menos lo que su voz más los respiros.
    if locucion:
        clips = cargar_locucion(Path(locucion))
    elif modelo_voz:
        clips = sintetizar_locucion(modelo_voz, config, trabajo / "voz")
    else:
        clips = {}
    escenas = [[e, max(d, round(clips[e][1] + ENTRADA_VOZ + SALIDA_VOZ, 2)) if e in clips else d] for e, d in ESCENAS_BASE]
    cierre_s = max(marca["cierre_s"], round(clips["cierre"][1] + 2.5, 2)) if clips else marca["cierre_s"]

    # 1. La animación, cuadro por cuadro.
    animacion = trabajo / "animacion.mp4"
    with sync_playwright() as p:
        navegador, pagina = abrir_pagina(p, escenas)
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
    plantillas = RAIZ / "plantillas" / "marca"
    render.a_png(render.llenar(plantillas, "intro.html", {
        "etiqueta": marca["etiqueta"], "titulo": TITULO, "lema": marca["lema"]}), trabajo / "intro.png")
    render.a_png(render.llenar(plantillas, "cierre.html", valores_cierre(config, plantillas)), trabajo / "cierre.png")
    tarjeta_a_clip(trabajo / "intro.png", trabajo / "intro.mp4", marca["intro_s"], config["video"])
    tarjeta_a_clip(trabajo / "cierre.png", trabajo / "cierre.mp4", cierre_s, config["video"])

    # 3. Todo junto.
    salida = AQUI / nombre_salida
    imagen = trabajo / "imagen.mp4" if clips else salida
    medios.concatenar([trabajo / "intro.mp4", animacion, trabajo / "cierre.mp4"], imagen)
    if clips:
        mezclar_locucion(imagen, salida, clips, escenas, marca["intro_s"], trabajo, musica, cierre_s)
    print(f"Listo: {salida} ({medios.duracion(salida):.0f} s)")


def mezclar_locucion(imagen: Path, salida: Path, clips: dict, escenas: list, intro_s: float, trabajo: Path,
                     musica: bool = False, cierre_s: float = 15.0) -> None:
    """Pone cada frase en el momento de su escena, añade la música (si se pide), nivela y escribe los subtítulos."""
    inicios, t = {}, intro_s
    for e, d in escenas:
        inicios[e] = t + ENTRADA_VOZ
        t += d
    inicios["cierre"] = t + 0.8
    duracion = medios.duracion(imagen)

    entradas, filtros, etiquetas, bloques = ["-i", str(imagen)], [], [], []
    for i, (clave, (wav, dur)) in enumerate(clips.items(), 1):
        entradas += ["-i", str(wav)]
        filtros.append(f"[{i}:a]aresample=48000,adelay={int(inicios[clave] * 1000)}:all=1[v{i}];")
        etiquetas.append(f"[v{i}]")
        bloques.append({"inicio": inicios[clave], "fin": inicios[clave] + dur, "texto": LOCUCION[clave]})
    filtros.append(f"{''.join(etiquetas)}amix=inputs={len(etiquetas)}:normalize=0,apad,atrim=0:{duracion:.3f}[locucion];")
    if musica:
        from agente_video.musica import componer

        pista = componer(duracion, trabajo / "musica.wav", intro_s=intro_s, cierre_s=cierre_s)
        indice = len(clips) + 1
        entradas += ["-i", str(pista)]
        filtros += [
            "[locucion]asplit=2[voz_sola][voz_control];",
            # La música deja hueco a la voz (−4 dB entre 1 y 3 kHz), va 9 dB por debajo y baja más cuando se habla.
            f"[{indice}:a]equalizer=f=1800:t=o:w=1.5:g=-4,volume=0.35[cama];",
            "[cama][voz_control]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=500[cama_baja];",
            "[voz_sola][cama_baja]amix=inputs=2:normalize=0:duration=first[mezcla];",
        ]
        etiqueta = "[mezcla]"
    else:
        etiqueta = "[locucion]"
    filtros.append(f"{etiqueta}aresample=48000[voz]")
    guion = trabajo / "locucion_filtro.txt"
    guion.write_text("\n".join(filtros), encoding="utf-8")
    audio = trabajo / "audio_mezcla.wav"
    medios.ffmpeg(*entradas, "-filter_complex_script", str(guion), "-map", "[voz]", "-t", f"{duracion:.3f}", str(audio))

    # Nivel final con UNA ganancia fija para todo el video (−16 LUFS). La normalización
    # dinámica subiría los tramos de solo música hasta el nivel de la voz.
    medicion = medios.ffmpeg("-i", str(audio), "-af", "ebur128", "-f", "null", "-").stderr
    integrado = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", medicion)[-1])
    ganancia = -16.0 - integrado
    medios.ffmpeg("-i", str(imagen), "-i", str(audio), "-map", "0:v", "-map", "1:a",
                  "-af", f"volume={ganancia:.2f}dB,alimiter=limit=0.84:attack=3:release=60:level=false",
                  "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{duracion:.3f}", str(salida))

    plan = [{"inicio": 0, "fin": duracion, "tipo": "normal", "velocidad": 1.0}]
    salida.with_suffix(".srt").write_text(generar_srt(bloques, plan), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--previa", action="store_true")
    parser.add_argument("--voz", help="Modelo .onnx de Piper para la locución sintética")
    parser.add_argument("--locucion", help="Carpeta con la locución grabada por bloques")
    parser.add_argument("--salida", default="video_01_version_animada.mp4", help="Nombre del video final")
    parser.add_argument("--musica", action="store_true", help="Añade música de fondo original (compuesta por código)")
    args = parser.parse_args()
    previa() if args.previa else video(args.voz, args.locucion, args.salida, args.musica)
