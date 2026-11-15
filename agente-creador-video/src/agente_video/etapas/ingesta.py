"""Une las grabaciones de crudo/ en un solo video con formato uniforme."""

from __future__ import annotations

from .. import medios
from ..proyecto import Proyecto, escribir_json
from . import ErrorEtapa

NOMBRE = "ingesta"
DESCRIPCION = "Unir y normalizar las grabaciones"


def ejecutar(proyecto: Proyecto, config: dict, servicios) -> dict:
    grabaciones = proyecto.grabaciones()
    if not grabaciones:
        raise ErrorEtapa(
            f"No hay grabaciones en {proyecto.crudo}. Copia ahí tus videos (mp4, mov, mkv o webm); "
            "si son varios, se unen en orden alfabético."
        )
    video = config["video"]
    proyecto.trabajo.mkdir(exist_ok=True)
    partes = []
    for i, grabacion in enumerate(grabaciones):
        parte = proyecto.trabajo / f"parte_{i:02d}.mp4"
        medios.normalizar(grabacion, parte, video["ancho"], video["alto"], video["fps"])
        partes.append(parte)

    fuente = proyecto.trabajo / "fuente.mp4"
    medios.concatenar(partes, fuente)
    for parte in partes:
        if parte != fuente:
            parte.unlink(missing_ok=True)

    datos = {"archivos": [g.name for g in grabaciones], "duracion": round(medios.duracion(fuente), 2)}
    escribir_json(proyecto.trabajo / "fuente.json", datos)
    return datos
