"""Operaciones de audio y video con FFmpeg."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path


class ErrorFFmpeg(RuntimeError):
    pass


def verificar_ffmpeg() -> None:
    for programa in ("ffmpeg", "ffprobe"):
        if shutil.which(programa) is None:
            raise ErrorFFmpeg(
                f"No se encontró '{programa}'. Instala FFmpeg: https://ffmpeg.org/download.html "
                "(en Windows: winget install ffmpeg)."
            )


def ejecutar(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    proceso = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd)
    if proceso.returncode != 0:
        cola = "\n".join(proceso.stderr.strip().splitlines()[-15:])
        raise ErrorFFmpeg(f"Falló: {' '.join(args[:6])} …\n{cola}")
    return proceso


def ffmpeg(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return ejecutar(["ffmpeg", "-hide_banner", "-nostdin", "-y", *args], cwd=cwd)


def duracion(ruta: Path) -> float:
    proceso = ejecutar(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(ruta)])
    return float(json.loads(proceso.stdout)["format"]["duration"])


def tiene_audio(ruta: Path) -> bool:
    proceso = ejecutar(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(ruta)]
    )
    return bool(proceso.stdout.strip())


def normalizar(entrada: Path, salida: Path, ancho: int, alto: int, fps: int) -> None:
    """Lleva una grabación a un formato común (resolución, fps, audio) para poder unirla y editarla."""
    filtro = (
        f"scale={ancho}:{alto}:force_original_aspect_ratio=decrease,"
        f"pad={ancho}:{alto}:(ow-iw)/2:(oh-ih)/2:color=black,fps={fps},format=yuv420p"
    )
    con_audio = tiene_audio(entrada)
    args = ["-i", str(entrada)]
    if not con_audio:
        # Pista de silencio para que todas las grabaciones tengan audio.
        args += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest"]
    args += [
        "-map", "0:v:0", "-map", "0:a:0" if con_audio else "1:a:0",
        "-vf", filtro, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", str(salida),
    ]
    ffmpeg(*args)


def concatenar(partes: list[Path], salida: Path) -> None:
    if len(partes) == 1:
        shutil.copyfile(partes[0], salida)
        return
    lista = salida.with_suffix(".txt")
    lista.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in partes), encoding="utf-8")
    ffmpeg("-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(salida))
    lista.unlink()


def extraer_audio(video: Path, salida: Path) -> None:
    """Audio mono a 16 kHz, el formato que espera Whisper."""
    ffmpeg("-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(salida))


def detectar_silencios(video: Path, umbral_db: float, minimo_s: float) -> list[tuple[float, float]]:
    proceso = ffmpeg("-i", str(video), "-vn", "-af", f"silencedetect=noise={umbral_db}dB:d={minimo_s}", "-f", "null", "-")
    return _pares(proceso.stderr, r"silence_start: ([\d.]+)", r"silence_end: ([\d.]+)", duracion(video))


def detectar_pantalla_quieta(video: Path, minimo_s: float) -> list[tuple[float, float]]:
    proceso = ffmpeg("-i", str(video), "-an", "-vf", f"freezedetect=n=0.003:d={minimo_s}", "-f", "null", "-")
    return _pares(proceso.stderr, r"freeze_start: ([\d.]+)", r"freeze_end: ([\d.]+)", duracion(video))


def _pares(texto: str, patron_ini: str, patron_fin: str, total: float) -> list[tuple[float, float]]:
    """Empareja los inicios y finales que reporta FFmpeg (el último puede quedar abierto)."""
    eventos = sorted(
        [(float(m.group(1)), "ini") for m in re.finditer(patron_ini, texto)]
        + [(float(m.group(1)), "fin") for m in re.finditer(patron_fin, texto)]
    )
    pares, abierto = [], None
    for t, tipo in eventos:
        if tipo == "ini":
            abierto = t
        elif abierto is not None:
            pares.append((abierto, t))
            abierto = None
    if abierto is not None:
        pares.append((abierto, total))
    return pares


def cadena_atempo(velocidad: float) -> str:
    """atempo solo admite 0.5–2.0 por filtro; se encadenan para otras velocidades."""
    filtros = []
    while velocidad > 2.0:
        filtros.append("atempo=2.0")
        velocidad /= 2.0
    while velocidad < 0.5:
        filtros.append("atempo=0.5")
        velocidad /= 0.5
    filtros.append(f"atempo={velocidad:.4f}")
    return ",".join(filtros)
