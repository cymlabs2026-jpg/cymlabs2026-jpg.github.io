"""Música de fondo original, compuesta por código: sin licencias ni reclamos de Content ID.

Estilo «corporativo tranquilo»: pads cálidos, arpegio de piano eléctrico, bajo
suave y percusión ligera, sobre una progresión optimista. La pieza se adapta a
la duración del video: entra con los pads durante la intro, suma batería en el
cuerpo y la retira en el cierre, con un desvanecimiento final.

    from agente_video.musica import componer
    componer(duracion=157, salida=Path("musica.wav"), intro_s=3, cierre_s=15)
"""

from __future__ import annotations

import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

SR = 48_000

# Progresión (notas MIDI). Do mayor: Cmaj9 – Am9 – Fmaj7 – Gsus4.
ACORDES = [
    {"bajo": 36, "pad": [55, 59, 62, 64], "arpegio": [60, 64, 67, 71, 74, 71, 67, 64]},
    {"bajo": 33, "pad": [52, 55, 60, 64], "arpegio": [57, 60, 64, 67, 71, 67, 64, 60]},
    {"bajo": 29, "pad": [53, 57, 60, 64], "arpegio": [53, 57, 60, 64, 69, 64, 60, 57]},
    {"bajo": 31, "pad": [55, 60, 62, 67], "arpegio": [55, 60, 62, 67, 72, 67, 62, 60]},
]


def _hz(nota: int) -> float:
    return 440.0 * 2 ** ((nota - 69) / 12)


def _tono_pad(frec: float, n: int, rng: np.random.Generator) -> np.ndarray:
    """Tres osciladores ligeramente desafinados con pocos armónicos: un pad cálido."""
    t = np.arange(n) / SR
    s = np.zeros(n)
    for desafine in (-0.06, 0.0, 0.07):
        f = frec * 2 ** (desafine / 12)
        fase = rng.uniform(0, 2 * np.pi)
        for h in range(1, 6):
            s += np.sin(2 * np.pi * f * h * t + fase * h) / h**1.6
    return s / 3


def _envolvente(n: int, ataque: float, liberacion: float) -> np.ndarray:
    a, r = min(n, int(ataque * SR)), min(n, int(liberacion * SR))
    env = np.ones(n)
    env[:a] = np.linspace(0, 1, a)
    if r:
        env[-r:] *= np.linspace(1, 0, r)
    return env


def _nota_piano(frec: float, dur: float, vel: float) -> np.ndarray:
    """Piano eléctrico sencillo: fundamental + armónicos que se apagan antes."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.sin(2 * np.pi * frec * t) * np.exp(-t * 2.2)
    s += 0.35 * np.sin(2 * np.pi * frec * 2 * t) * np.exp(-t * 5)
    s += 0.12 * np.sin(2 * np.pi * frec * 3 * t) * np.exp(-t * 9)
    s *= _envolvente(n, 0.004, 0.05)
    return s * vel


def _bombo(n_max: int) -> np.ndarray:
    n = min(n_max, int(0.35 * SR))
    t = np.arange(n) / SR
    frec = 48 + 70 * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(frec) / SR) * np.exp(-t * 9)


def _platillo(rng: np.random.Generator) -> np.ndarray:
    n = int(0.05 * SR)
    ruido = rng.standard_normal(n)
    ruido = np.diff(ruido, prepend=0)  # Quita graves: suena más a platillo cerrado.
    return ruido * np.exp(-np.arange(n) / SR * 90)


def _sumar(destino: np.ndarray, sonido: np.ndarray, inicio: int, ganancia: float = 1.0) -> None:
    fin = min(len(destino), inicio + len(sonido))
    if inicio < fin:
        destino[inicio:fin] += sonido[: fin - inicio] * ganancia


def componer(duracion: float, salida: Path, intro_s: float = 3.0, cierre_s: float = 15.0,
             bpm: float = 96.0, semilla: int = 7) -> Path:
    rng = np.random.default_rng(semilla)
    total = int((duracion + 0.5) * SR)
    pulso = 60 / bpm
    compas = 4 * pulso
    pads, piano, bajo, bateria = (np.zeros(total) for _ in range(4))
    inicio_cierre = duracion - cierre_s

    n_compases = int(np.ceil(duracion / compas)) + 1
    for c in range(n_compases):
        t0 = c * compas
        acorde = ACORDES[c % len(ACORDES)]
        i0 = int(t0 * SR)
        n = int((compas + 0.6) * SR)  # Se solapa con el siguiente para unir los acordes.

        # Pads: siempre presentes.
        env = _envolvente(n, 0.8, 0.9)
        for nota in acorde["pad"]:
            _sumar(pads, _tono_pad(_hz(nota), n, rng) * env, i0, 0.16)

        if t0 < intro_s - 0.2:
            continue  # Durante la intro solo suenan los pads.

        # Arpegio en corcheas, con dinámica humana.
        for k, nota in enumerate(acorde["arpegio"]):
            vel = 0.5 + 0.15 * (k % 4 == 0) + rng.uniform(-0.05, 0.05)
            _sumar(piano, _nota_piano(_hz(nota), 1.2, vel), int((t0 + k * pulso / 2) * SR), 0.22)

        # Bajo en blancas.
        for k in (0, 2):
            n_b = int(pulso * 2 * SR)
            tb = np.arange(n_b) / SR
            nota_b = np.sin(2 * np.pi * _hz(acorde["bajo"]) * tb) + 0.25 * np.sin(2 * np.pi * _hz(acorde["bajo"]) * 2 * tb)
            _sumar(bajo, nota_b * _envolvente(n_b, 0.03, 0.25), int((t0 + k * pulso) * SR), 0.32)

        # Batería: entra un compás después de la intro y sale en el cierre.
        if intro_s + compas <= t0 < inicio_cierre - compas / 2:
            for k in (0, 2):
                _sumar(bateria, _bombo(total), int((t0 + k * pulso) * SR), 0.5)
            for k in range(8):
                if k % 2 == 1:
                    _sumar(bateria, _platillo(rng), int((t0 + k * pulso / 2) * SR), 0.03)

    # Mezcla en estéreo: pads y piano abiertos, bajo y batería al centro.
    izq = pads * 0.9 + piano * 0.7 + bajo + bateria
    der = pads * 1.0 + np.roll(piano, int(0.012 * SR)) * 0.8 + bajo + bateria
    mezcla = np.stack([izq, der], axis=1)
    mezcla[-int(4 * SR):] *= np.linspace(1, 0, int(4 * SR))[:, None]  # Desvanecimiento final.
    mezcla /= np.max(np.abs(mezcla)) + 1e-9
    mezcla = mezcla[: int(duracion * SR)]

    with tempfile.TemporaryDirectory() as tmp:
        cruda = Path(tmp) / "cruda.wav"
        with wave.open(str(cruda), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((mezcla * 0.8 * 32767).astype("<i2").tobytes())
        # Acabado: suaviza agudos ásperos, añade sala y nivela.
        acabado = ("lowpass=f=9000,aecho=0.8:0.6:70|130|210:0.25|0.18|0.1,"
                   "acompressor=threshold=-18dB:ratio=2:attack=20:release=300,loudnorm=I=-20:TP=-2:LRA=8,"
                   f"atrim=0:{duracion:.3f}")  # el eco añade cola: se recorta a la duración pedida
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(cruda), "-af", acabado,
                        "-ar", str(SR), str(salida)], check=True)
    return salida
