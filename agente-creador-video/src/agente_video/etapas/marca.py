"""Añade la intro y la pantalla final de la marca, y diseña la miniatura."""

from __future__ import annotations

from pathlib import Path

from .. import medios, render
from ..proyecto import Proyecto, escribir_json, leer_json
from . import guion as guion_etapa

NOMBRE = "marca"
DESCRIPCION = "Intro, cierre y miniatura"


def desplazamiento(proyecto: Proyecto) -> float:
    """Segundos que la intro empuja todo el contenido hacia adelante."""
    ruta = proyecto.trabajo / "marca.json"
    return leer_json(ruta)["desplazamiento"] if ruta.exists() else 0.0


def video_base(proyecto: Proyecto) -> Path:
    """El video sobre el que se arma el audio: con intro y cierre si existen."""
    con_marca = proyecto.trabajo / "video_base.mp4"
    return con_marca if con_marca.exists() else proyecto.trabajo / "montaje.mp4"


def tarjeta_a_clip(png: Path, salida: Path, segundos: float, video: dict) -> None:
    """Imagen fija con entrada y salida suaves, y pista de silencio, en el mismo formato del montaje."""
    fundido = min(0.5, segundos / 4)
    filtro = (
        f"scale={video['ancho']}:{video['alto']},format=yuv420p,"
        f"fade=t=in:st=0:d={fundido},fade=t=out:st={segundos - fundido:.2f}:d={fundido}"
    )
    medios.ffmpeg(
        "-loop", "1", "-framerate", str(video["fps"]), "-i", str(png),
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-t", f"{segundos}", "-vf", filtro,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(video["fps"]),
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        str(salida),
    )


def ejecutar(proyecto: Proyecto, config: dict, servicios) -> dict:
    cfg = config["marca"]
    montaje = proyecto.trabajo / "montaje.mp4"
    base = proyecto.trabajo / "video_base.mp4"
    base.unlink(missing_ok=True)
    resumen: dict = {"intro": False, "cierre": False, "miniatura": False}

    if not (cfg["intro"] or cfg["cierre"] or cfg["miniatura"]):
        escribir_json(proyecto.trabajo / "marca.json", {"desplazamiento": 0.0})
        return resumen
    if not render.disponible():
        print('  ⚠ Sin Playwright: se omiten intro, cierre y miniatura. Instálalo con: pip install -e ".[marca]"')
        escribir_json(proyecto.trabajo / "marca.json", {"desplazamiento": 0.0})
        return {**resumen, "aviso": "Playwright no está instalado"}

    plantillas = Path(config["_raiz"]) / "plantillas" / "marca"
    guion = guion_etapa.cargar(proyecto)
    titulo = guion["titulos"][0] if guion["titulos"] else proyecto.estado().get("nombre", "")
    video = config["video"]

    partes, despl = [], 0.0
    if cfg["intro"]:
        png = proyecto.trabajo / "intro.png"
        render.a_png(render.llenar(plantillas, "intro.html", {
            "etiqueta": cfg["etiqueta"], "titulo": titulo, "lema": cfg["lema"],
        }), png)
        clip = proyecto.trabajo / "intro.mp4"
        tarjeta_a_clip(png, clip, cfg["intro_s"], video)
        partes.append(clip)
        despl = medios.duracion(clip)
        resumen["intro"] = True

    partes.append(montaje)

    if cfg["cierre"]:
        png = proyecto.trabajo / "cierre.png"
        render.a_png(render.llenar(plantillas, "cierre.html", {
            "etiqueta": "Gracias por ver", "titulo": cfg["cierre_titulo"],
            "llamado": cfg["cierre_llamado"], "enlace": cfg["cierre_enlace"],
        }), png)
        clip = proyecto.trabajo / "cierre.mp4"
        tarjeta_a_clip(png, clip, cfg["cierre_s"], video)
        partes.append(clip)
        resumen["cierre"] = True

    if len(partes) > 1:
        medios.concatenar(partes, base)

    if cfg["miniatura"]:
        resumen["miniatura"] = _miniatura(proyecto, plantillas, guion, montaje)

    escribir_json(proyecto.trabajo / "marca.json", {"desplazamiento": despl})
    return {**resumen, "desplazamiento": round(despl, 2)}


def _miniatura(proyecto: Proyecto, plantillas: Path, guion: dict, montaje: Path) -> bool:
    texto = guion.get("miniatura", "").strip()
    if not texto:
        print("  ⚠ Sin texto de miniatura en guion.md (sección «Miniatura»): no se generó.")
        return False
    # El foco visual: foco.png/foco.jpg en la carpeta del proyecto, o un cuadro del video.
    foco = next((p for p in (proyecto.ruta("foco.png"), proyecto.ruta("foco.jpg")) if p.exists()), None)
    if foco is None:
        foco = proyecto.trabajo / "foco.png"
        segundo = medios.duracion(montaje) * 0.75  # Hacia el final suele verse el resultado.
        medios.ffmpeg("-ss", f"{segundo:.2f}", "-i", str(montaje), "-frames:v", "1", str(foco))
    proyecto.entrega.mkdir(exist_ok=True)
    render.a_png(
        render.llenar(plantillas, "miniatura.html", {"texto": texto, "foco": render.imagen_como_dato(foco)}),
        proyecto.entrega / "miniatura.png",
        ancho_salida=1280,
    )
    return True
