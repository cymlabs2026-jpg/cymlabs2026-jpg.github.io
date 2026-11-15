"""Aplica el plan de edición: corta el tiempo muerto y acelera las esperas."""

from __future__ import annotations

from .. import medios, tiempo
from ..proyecto import Proyecto, leer_json

NOMBRE = "montaje"
DESCRIPCION = "Cortar y acelerar según el plan"


def filtro_montaje(plan: list[dict]) -> str:
    """Grafo de filtros de FFmpeg que recorta cada tramo, lo acelera si toca y los une."""
    lineas, etiquetas = [], []
    n = 0
    for tramo in plan:
        if tramo["tipo"] == "cortar":
            continue
        ini, fin, vel = tramo["inicio"], tramo["fin"], tramo["velocidad"]
        lineas.append(f"[0:v]trim=start={ini}:end={fin},setpts=(PTS-STARTPTS)/{vel}[v{n}];")
        if tramo["tipo"] == "acelerar":
            # En las esperas nadie habla: silencio exacto de la duración acelerada.
            dur = tiempo.duracion_tramo_final(tramo)
            lineas.append(f"aevalsrc=0|0:s=48000:d={dur:.3f}[a{n}];")
        else:
            lineas.append(f"[0:a]atrim=start={ini}:end={fin},asetpts=PTS-STARTPTS[a{n}];")
        etiquetas.append(f"[v{n}][a{n}]")
        n += 1
    lineas.append(f"{''.join(etiquetas)}concat=n={n}:v=1:a=1[v][a]")
    return "\n".join(lineas)


def ejecutar(proyecto: Proyecto, config: dict, servicios) -> dict:
    plan = leer_json(proyecto.ruta("edicion.json"))["tramos"]
    script = proyecto.trabajo / "montaje_filtro.txt"
    script.write_text(filtro_montaje(plan), encoding="utf-8")
    salida = proyecto.trabajo / "montaje.mp4"
    medios.ffmpeg(
        "-i", str(proyecto.trabajo / "fuente.mp4"),
        "-filter_complex_script", str(script),
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
        str(salida),
    )
    return {"duracion": round(medios.duracion(salida), 2)}
