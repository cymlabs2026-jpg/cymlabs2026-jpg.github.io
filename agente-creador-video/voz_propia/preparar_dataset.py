"""Revisa las grabaciones del grabador y arma el conjunto de entrenamiento de Piper.

Para cada grabación:
  1. Comprueba duración, saturación y volumen.
  2. La transcribe con Whisper y la compara con la frase que debía leerse.
  3. Si pasa, la normaliza (mono, 22.050 Hz, volumen parejo) y la incluye.

Uso:
    python preparar_dataset.py voz_propia_2026-11-20.zip [otro.zip ...] --salida dataset

Salida:
    dataset/wavs/*.wav       grabaciones aprobadas y normalizadas
    dataset/metadata.csv     id|texto, solo las aprobadas
    dataset/revision.md      qué se aprobó, qué se rechazó y por qué (para regrabar)

Si grabaste varias sesiones, pasa todos los .zip: si una frase aparece en varios,
se usa la del último archivo.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import re
import subprocess
import sys
import tempfile
import unicodedata
import zipfile
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

SR = 22050
SIMILITUD_MINIMA = 0.85     # Coincidencia mínima entre lo leído y lo que dice Whisper.
DURACION = (1.0, 15.0)      # Piper entrena mejor con frases de 1 a 15 segundos.

NUMEROS = {"0": "cero", "1": "uno", "2": "dos", "3": "tres", "4": "cuatro", "5": "cinco",
           "6": "seis", "7": "siete", "8": "ocho", "9": "nueve"}


def cifras_en_palabras(t: str) -> str:
    """Whisper escribe «3.600» o «28%»; el corpus, «tres mil seiscientas» y «veintiocho por ciento»."""
    from num2words import num2words

    t = t.replace("%", " por ciento ")
    t = re.sub(r"(?<=\d)\.(?=\d{3}\b)", "", t)  # 3.600 → 3600
    return re.sub(r"\d+(?:,\d+)?", lambda m: num2words(float(m.group().replace(",", ".")) if "," in m.group()
                                                       else int(m.group()), lang="es"), t)


def normalizar_texto(t: str) -> list[str]:
    """Minúsculas, cifras en palabras, sin tildes ni signos, para comparar lo leído con lo transcrito."""
    t = cifras_en_palabras(t)
    t = unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z ]+", " ", t).split()


def similitud(esperado: str, oido: str) -> float:
    a, b = normalizar_texto(esperado), normalizar_texto(oido)
    por_palabras = difflib.SequenceMatcher(None, a, b).ratio()
    # Por letras tolera diferencias como «seiscientas»/«seiscientos» o palabras unidas.
    por_letras = difflib.SequenceMatcher(None, "".join(a), "".join(b)).ratio()
    return max(por_palabras, por_letras)


def leer_wav(ruta: Path) -> np.ndarray:
    datos = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(ruta), "-ac", "1", "-ar", str(SR),
                            "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(datos, dtype=np.float32)


def revisar_audio(x: np.ndarray) -> str | None:
    dur = len(x) / SR
    if not DURACION[0] <= dur <= DURACION[1]:
        return f"dura {dur:.1f} s (debe estar entre {DURACION[0]:.0f} y {DURACION[1]:.0f} s)"
    # Saturación: no basta un pico alto, sino muchas muestras pegadas al máximo.
    if np.sum(np.abs(x) >= 0.99) > max(10, 0.0005 * len(x)):
        return "saturada (el sonido se recortó)"
    rms = 20 * np.log10(np.sqrt(np.mean(x**2)) + 1e-12)
    if rms < -40:
        return f"muy baja ({rms:.0f} dB)"
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("zips", nargs="+", type=Path)
    parser.add_argument("--salida", type=Path, default=Path("dataset"))
    parser.add_argument("--modelo-whisper", default="small")
    args = parser.parse_args()

    from agente_video.proveedores.transcriptor import TranscriptorWhisper

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        textos: dict[str, str] = {}
        audios: dict[str, Path] = {}
        for i, z in enumerate(args.zips):
            destino = tmp / f"z{i}"
            with zipfile.ZipFile(z) as archivo:
                archivo.extractall(destino)
            for fila in csv.reader((destino / "metadata.csv").open(encoding="utf-8"), delimiter="|"):
                textos[fila[0]] = fila[1]
                audios[fila[0]] = destino / "wavs" / f"{fila[0]}.wav"

        (args.salida / "wavs").mkdir(parents=True, exist_ok=True)
        transcriptor = TranscriptorWhisper(args.modelo_whisper, "es")
        aprobadas, rechazadas, segundos = [], [], 0.0
        for clave in sorted(textos):
            x = leer_wav(audios[clave])
            problema = revisar_audio(x)
            if problema is None:
                oido = " ".join(s["texto"] for s in transcriptor.transcribir(str(audios[clave])))
                parecido = similitud(textos[clave], oido)
                if parecido < SIMILITUD_MINIMA:
                    problema = f"no coincide con el texto ({parecido:.0%}). Whisper oyó: «{oido}»"
            if problema:
                rechazadas.append((clave, textos[clave], problema))
                print(f"  ✗ {clave}: {problema}")
                continue
            # Normaliza el volumen de cada frase a un nivel parejo (−20 LUFS) sin tocar el timbre.
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(audios[clave]), "-ac", "1", "-ar", str(SR),
                            "-af", "loudnorm=I=-20:TP=-3:LRA=7", "-ar", str(SR), "-sample_fmt", "s16",
                            str(args.salida / "wavs" / f"{clave}.wav")], check=True)
            aprobadas.append((clave, textos[clave]))
            segundos += len(x) / SR
            print(f"  ✓ {clave}")

    with (args.salida / "metadata.csv").open("w", encoding="utf-8", newline="") as f:
        for clave, texto in aprobadas:
            f.write(f"{clave}|{texto}\n")

    informe = [
        "# Revisión del conjunto de entrenamiento\n",
        f"- Aprobadas: **{len(aprobadas)}** ({segundos / 60:.1f} minutos de voz)",
        f"- Rechazadas: **{len(rechazadas)}**",
        "",
        "Recomendado para afinar una voz: al menos 20 minutos aprobados; ideal, 45 a 60.",
    ]
    if rechazadas:
        informe += ["", "## Para volver a grabar", "", "| Frase | Texto | Motivo |", "|---|---|---|"]
        informe += [f"| {c} | {t} | {m} |" for c, t, m in rechazadas]
    (args.salida / "revision.md").write_text("\n".join(informe) + "\n", encoding="utf-8")
    print(f"\n{len(aprobadas)} aprobadas ({segundos / 60:.1f} min), {len(rechazadas)} rechazadas. "
          f"Detalle en {args.salida / 'revision.md'}")


if __name__ == "__main__":
    main()
