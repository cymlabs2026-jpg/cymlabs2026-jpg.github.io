"""Prepara el kit de publicación: capítulos, descripción, títulos y reporte."""

from __future__ import annotations

from .. import medios, tiempo
from ..proyecto import Proyecto, leer_json
from . import guion as guion_etapa

NOMBRE = "entrega"
DESCRIPCION = "Capítulos, descripción y reporte"

# Reglas de YouTube para que los capítulos aparezcan en la barra del video.
CAPITULOS_MINIMOS = 3
SEPARACION_MINIMA_S = 10


def capitulos_finales(capitulos: list[dict], plan: list[dict], duracion: float) -> tuple[list[dict], list[str]]:
    """Traduce los capítulos al tiempo final y aplica las reglas de YouTube."""
    avisos = []
    finales: list[dict] = []
    for c in sorted(capitulos, key=lambda c: c["inicio"]):
        t = 0.0 if not finales else tiempo.remapear(c["inicio"], plan)
        if finales and t - finales[-1]["inicio"] < SEPARACION_MINIMA_S:
            avisos.append(f"Capítulo «{c['titulo']}» omitido: queda a menos de {SEPARACION_MINIMA_S} s del anterior.")
            continue
        if duracion - t < SEPARACION_MINIMA_S and finales:
            avisos.append(f"Capítulo «{c['titulo']}» omitido: dura menos de {SEPARACION_MINIMA_S} s.")
            continue
        finales.append({"inicio": t, "titulo": c["titulo"]})
    if finales and len(finales) < CAPITULOS_MINIMOS:
        avisos.append(f"YouTube pide al menos {CAPITULOS_MINIMOS} capítulos; con {len(finales)} no se mostrarán.")
    return finales, avisos


def ejecutar(proyecto: Proyecto, config: dict, servicios) -> dict:
    plan_info = leer_json(proyecto.ruta("edicion.json"))
    plan = plan_info["tramos"]
    guion = guion_etapa.cargar(proyecto)
    duracion = medios.duracion(proyecto.entrega / "video_final.mp4")

    capitulos, avisos = capitulos_finales(guion["capitulos"], plan, duracion)
    texto_capitulos = "\n".join(f"{tiempo.a_youtube(c['inicio'])} {c['titulo']}" for c in capitulos)
    (proyecto.entrega / "capitulos.txt").write_text(texto_capitulos + "\n", encoding="utf-8")

    descripcion = [guion["descripcion"]] if guion["descripcion"] else []
    if guion["prompts"]:
        descripcion.append("PROMPTS DEL VIDEO")
        descripcion += [f"{i}. {p}" for i, p in enumerate(guion["prompts"], 1)]
    if capitulos:
        descripcion += ["CAPÍTULOS", texto_capitulos]
    (proyecto.entrega / "descripcion.txt").write_text("\n\n".join(descripcion) + "\n", encoding="utf-8")

    if guion["titulos"]:
        titulos = [f"{t}  (recomendado)" if i == 0 else t for i, t in enumerate(guion["titulos"])]
        (proyecto.entrega / "titulos.txt").write_text("\n".join(titulos) + "\n", encoding="utf-8")

    original = plan_info["duracion_original"]
    ahorro = 100 * (1 - duracion / original) if original else 0
    reporte = [
        "# Reporte del video\n",
        f"- Grabación original: {tiempo.a_youtube(original)}",
        f"- Video final: {tiempo.a_youtube(duracion)} ({ahorro:.0f}% más corto)",
        f"- Esperas aceleradas: {plan_info['tramos_acelerados']}",
        f"- Tiempos muertos cortados: {plan_info['tramos_cortados']}",
        f"- Capítulos: {len(capitulos)}",
        f"- Voz: {config['voz']['modo']}",
    ]
    if avisos:
        reporte += ["\n## Avisos\n"] + [f"- {a}" for a in avisos]
    (proyecto.entrega / "reporte.md").write_text("\n".join(reporte) + "\n", encoding="utf-8")
    return {"duracion_final": round(duracion, 2), "capitulos": len(capitulos), "avisos": avisos}
