"""Genera los subtítulos en el tiempo del video final, y los graba en la imagen si se pide."""

from __future__ import annotations

from .. import medios, tiempo
from ..proyecto import Proyecto, leer_json
from . import guion as guion_etapa

NOMBRE = "subtitulos"
DESCRIPCION = "Subtítulos sincronizados"

CARACTERES_POR_LINEA = 42
LINEAS_POR_SUBTITULO = 2


def partir_texto(texto: str, maximo: int = CARACTERES_POR_LINEA * LINEAS_POR_SUBTITULO) -> list[str]:
    """Divide un texto largo en trozos legibles, sin cortar palabras."""
    trozos, actual = [], ""
    for palabra in texto.split():
        if actual and len(actual) + 1 + len(palabra) > maximo:
            trozos.append(actual)
            actual = palabra
        else:
            actual = f"{actual} {palabra}".strip()
    if actual:
        trozos.append(actual)
    return trozos


def _en_lineas(trozo: str) -> str:
    if len(trozo) <= CARACTERES_POR_LINEA:
        return trozo
    # Corta en el espacio más cercano al centro para dos líneas equilibradas.
    centro = len(trozo) // 2
    espacios = [i for i, c in enumerate(trozo) if c == " "]
    corte = min(espacios, key=lambda i: abs(i - centro)) if espacios else centro
    return trozo[:corte].strip() + "\n" + trozo[corte:].strip()


def generar_srt(narracion: list[dict], plan: list[dict]) -> str:
    entradas = []
    for bloque in narracion:
        texto = bloque["texto"].strip()
        if not texto:
            continue
        ini, fin = tiempo.remapear(bloque["inicio"], plan), tiempo.remapear(bloque["fin"], plan)
        if fin - ini < 0.3:
            continue
        trozos = partir_texto(texto)
        total = sum(len(t) for t in trozos)
        cursor = ini
        for trozo in trozos:
            dur = (fin - ini) * len(trozo) / total
            entradas.append((cursor, cursor + dur, _en_lineas(trozo)))
            cursor += dur
    return "\n".join(
        f"{i}\n{tiempo.a_srt(a)} --> {tiempo.a_srt(b)}\n{t}\n" for i, (a, b, t) in enumerate(entradas, 1)
    )


def ejecutar(proyecto: Proyecto, config: dict, servicios) -> dict:
    plan = leer_json(proyecto.ruta("edicion.json"))["tramos"]
    narracion = guion_etapa.cargar(proyecto)["narracion"]
    srt = proyecto.entrega / "subtitulos.srt"
    contenido = generar_srt(narracion, plan)
    srt.write_text(contenido, encoding="utf-8")

    if config["subtitulos"]["quemar"]:
        final = proyecto.entrega / "video_final.mp4"
        temporal = proyecto.entrega / "video_final_sin_subtitulos.mp4"
        final.replace(temporal)
        estilo = "FontName=Arial,FontSize=20,Outline=2,Shadow=0,MarginV=40"
        # Se ejecuta dentro de entrega/ para no lidiar con rutas en el filtro (en Windows llevan ':').
        medios.ffmpeg(
            "-i", temporal.name,
            "-vf", f"subtitles={srt.name}:force_style='{estilo}'",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "copy",
            final.name,
            cwd=proyecto.entrega,
        )
        temporal.unlink()

    return {"subtitulos": contenido.count("-->"), "quemados": config["subtitulos"]["quemar"]}
