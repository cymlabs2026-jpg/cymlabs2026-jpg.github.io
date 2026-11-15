"""Transcribe la grabación con tiempos y corrige los términos de marca."""

from __future__ import annotations

from .. import medios
from ..config import aplicar_glosario
from ..proyecto import Proyecto, escribir_json
from . import ErrorEtapa

NOMBRE = "transcripcion"
DESCRIPCION = "Transcribir lo que se dice"


def ejecutar(proyecto: Proyecto, config: dict, servicios) -> dict:
    if servicios.transcriptor is None:
        raise ErrorEtapa("No hay transcriptor configurado.")
    audio = proyecto.trabajo / "audio.wav"
    medios.extraer_audio(proyecto.trabajo / "fuente.mp4", audio)

    segmentos = servicios.transcriptor(config).transcribir(str(audio))
    glosario = config.get("_glosario", {})
    for s in segmentos:
        s["texto"] = aplicar_glosario(s["texto"], glosario)

    escribir_json(proyecto.ruta("transcripcion.json"), segmentos)
    return {"segmentos": len(segmentos)}
