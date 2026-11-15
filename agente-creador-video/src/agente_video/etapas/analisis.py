"""Detecta las esperas y el tiempo muerto, y arma el plan de edición."""

from __future__ import annotations

from .. import medios, tiempo
from ..proyecto import Proyecto, escribir_json, leer_json

NOMBRE = "analisis"
DESCRIPCION = "Detectar esperas y tiempo muerto"


def ejecutar(proyecto: Proyecto, config: dict, servicios) -> dict:
    fuente = proyecto.trabajo / "fuente.mp4"
    ed = config["edicion"]
    duracion = medios.duracion(fuente)

    silencios = medios.detectar_silencios(fuente, ed["silencio_db"], ed["silencio_min_s"])
    # Si Whisper escuchó palabras dentro de un "silencio" (alguien habló bajito), se respetan.
    habla = []
    for s in leer_json(proyecto.ruta("transcripcion.json")):
        habla += [tuple(p) for p in s.get("palabras") or [(s["inicio"], s["fin"])]]
    silencios = [p for s in silencios for p in tiempo.restar(s, habla)]
    quietos = medios.detectar_pantalla_quieta(fuente, ed["quieto_min_s"])

    plan = tiempo.construir_plan(
        duracion,
        silencios,
        quietos,
        velocidad_espera=ed["velocidad_espera"],
        cortar_tiempo_muerto=ed["cortar_tiempo_muerto"],
        margen_s=ed["margen_s"],
    )
    final = tiempo.duracion_final(plan)
    resumen = {
        "duracion_original": round(duracion, 2),
        "duracion_final": round(final, 2),
        "tramos_acelerados": sum(t["tipo"] == "acelerar" for t in plan),
        "tramos_cortados": sum(t["tipo"] == "cortar" for t in plan),
    }
    escribir_json(proyecto.ruta("edicion.json"), {**resumen, "tramos": plan})
    return resumen
