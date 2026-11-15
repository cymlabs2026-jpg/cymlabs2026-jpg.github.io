"""Prueba de punta a punta con FFmpeg real y proveedores de IA falsos.

Se fabrica una "grabación de pantalla" de 30 s:
  0–8 s   habla (tono) y pantalla en movimiento
  8–16 s  silencio y pantalla en movimiento  → se acelera
  16–24 s silencio y pantalla quieta          → se corta
  24–30 s habla y pantalla en movimiento
"""

import shutil
import subprocess
import wave
from pathlib import Path

import pytest

from agente_video.config import cargar_config
from agente_video.medios import duracion
from agente_video.orquestador import EsperandoAprobacion, aprobar_guion, procesar
from agente_video.proveedores import Servicios
from agente_video.proyecto import Proyecto, leer_json

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="requiere FFmpeg")


def _grabacion_falsa(ruta: Path) -> None:
    video = (
        "testsrc2=s=640x360:r=30:d=16[mov1];"
        "color=c=gray:s=640x360:r=30:d=8[quieto];"
        "testsrc2=s=640x360:r=30:d=6[mov2];"
        "[mov1][quieto][mov2]concat=n=3:v=1:a=0[v]"
    )
    audio = (
        "sine=f=440:d=8:sample_rate=48000[t1];"
        "aevalsrc=0:d=16:s=48000[s];"
        "sine=f=440:d=6:sample_rate=48000[t2];"
        "[t1][s][t2]concat=n=3:v=0:a=1[a]"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-filter_complex", f"{video};{audio}",
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-c:a", "aac", str(ruta)],
        check=True,
    )


class TranscriptorFalso:
    def transcribir(self, audio_wav):
        return [
            {"inicio": 0.5, "fin": 7.5, "texto": "Cloud acaba de agregar tres herramientas nuevas a los artefactos."},
            {"inicio": 24.2, "fin": 29.5, "texto": "Y así se cierra el tutorial."},
        ]


class GuionistaFalso:
    def generar(self, segmentos, config):
        return {
            "titulos": ["Título recomendado", "Alternativo"],
            "miniatura": "¿Por qué *cayó*?",
            "descripcion": "Descripción de prueba.",
            "prompts": ["Prompt de prueba"],
            "capitulos": [{"inicio": 0.0, "titulo": "Intro"}, {"inicio": 24.2, "titulo": "Cierre"}],
            "narracion": [{**s, "texto": s["texto"].replace("Cloud", "Claude")} for s in segmentos],
        }


class VozFalsa:
    """Escribe un tono de 2 s en lugar de una voz real."""

    def sintetizar(self, texto, salida_wav):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=f=300:d=2",
                        "-ar", "22050", "-ac", "1", salida_wav], check=True)


@pytest.fixture
def servicios():
    return Servicios(
        transcriptor=lambda c: TranscriptorFalso(),
        guionista=lambda c: GuionistaFalso(),
        voz=lambda c: VozFalsa(),
    )


def _config(proyecto, **cambios):
    config = cargar_config(proyecto.carpeta)
    config["video"].update(ancho=640, alto=360)
    config["marca"].update(intro=False, cierre=False, miniatura=False)
    for seccion, valores in cambios.items():
        config[seccion].update(valores)
    return config


def test_proceso_completo(tmp_path, servicios):
    proyecto = Proyecto.crear(tmp_path, "Prueba")
    _grabacion_falsa(proyecto.crudo / "toma1.mp4")
    config = _config(proyecto)

    with pytest.raises(EsperandoAprobacion):
        procesar(proyecto, servicios=servicios, config=config)
    assert "Claude acaba de agregar" in proyecto.ruta("guion.md").read_text(encoding="utf-8")
    assert not (proyecto.entrega / "video_final.mp4").exists()

    # La persona corrige el guion antes de aprobarlo.
    md = proyecto.ruta("guion.md")
    md.write_text(md.read_text(encoding="utf-8").replace("Y así se cierra", "Así termina"), encoding="utf-8")
    aprobar_guion(proyecto)
    procesar(proyecto, servicios=servicios, config=config)

    edicion = leer_json(proyecto.ruta("edicion.json"))
    assert edicion["tramos_acelerados"] == 1 and edicion["tramos_cortados"] == 1
    final = duracion(proyecto.entrega / "video_final.mp4")
    # 8 normal + ~8/4 acelerado + 0 cortado + 6 normal (± margen) ≈ 16 s, frente a 30 s originales.
    assert 14 < final < 19
    srt = (proyecto.entrega / "subtitulos.srt").read_text(encoding="utf-8")
    assert "Así termina el tutorial." in srt
    capitulos = (proyecto.entrega / "capitulos.txt").read_text(encoding="utf-8")
    assert capitulos.startswith("0:00 Intro")
    assert "Prompt de prueba" in (proyecto.entrega / "descripcion.txt").read_text(encoding="utf-8")

    # Retomar no repite trabajo.
    procesar(proyecto, servicios=servicios, config=config)


def test_voz_sintetica_y_subtitulos_quemados(tmp_path, servicios):
    proyecto = Proyecto.crear(tmp_path, "Prueba voz")
    _grabacion_falsa(proyecto.crudo / "toma1.mp4")
    config = _config(proyecto, voz={"modo": "sintetica"}, subtitulos={"quemar": True}, ia={"aprobar_guion": False})

    procesar(proyecto, servicios=servicios, config=config)
    final = proyecto.entrega / "video_final.mp4"
    assert 14 < duracion(final) < 19
    assert len(list((proyecto.trabajo / "voz").glob("*.wav"))) == 2
    assert not (proyecto.entrega / "video_final_sin_subtitulos.mp4").exists()


def test_musica_de_fondo(tmp_path, servicios):
    proyecto = Proyecto.crear(tmp_path, "Prueba musica")
    _grabacion_falsa(proyecto.crudo / "toma1.mp4")
    musica = tmp_path / "musica.wav"
    with wave.open(str(musica), "wb") as w:  # 1 s de ruido suave; se repite en bucle
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(48000)
        w.writeframes(bytes((i * 37) % 256 for i in range(96000)))
    config = _config(proyecto, musica={"archivo": str(musica)}, ia={"aprobar_guion": False})
    procesar(proyecto, servicios=servicios, config=config)
    assert 14 < duracion(proyecto.entrega / "video_final.mp4") < 19


@pytest.mark.skipif(not __import__("agente_video.render", fromlist=["x"]).disponible(), reason="requiere Playwright")
def test_intro_cierre_y_miniatura(tmp_path, servicios):
    proyecto = Proyecto.crear(tmp_path, "Prueba marca")
    _grabacion_falsa(proyecto.crudo / "toma1.mp4")
    config = _config(proyecto, ia={"aprobar_guion": False})
    config["marca"].update(intro=True, cierre=True, miniatura=True, intro_s=3, cierre_s=5)
    procesar(proyecto, servicios=servicios, config=config)

    # ≈16 s de contenido + 3 s de intro + 5 s de cierre.
    assert 22 < duracion(proyecto.entrega / "video_final.mp4") < 27
    srt = (proyecto.entrega / "subtitulos.srt").read_text(encoding="utf-8")
    assert srt.split("\n")[1].startswith("00:00:03")  # la primera frase entra después de la intro
    miniatura = proyecto.entrega / "miniatura.png"
    medidas = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0",
                              str(miniatura)], capture_output=True, text=True, check=True).stdout.strip()
    assert medidas == "1280,720"
