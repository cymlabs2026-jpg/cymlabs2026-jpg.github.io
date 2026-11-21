"""Energía de una voz: variación de tono (semitonos), ritmo (sílabas por segundo) y dinámica de volumen (dB)."""
import sys, re, numpy as np, librosa
def energia(ruta, texto=None):
    y, sr = librosa.load(ruta, sr=16000)
    f0, voz, _ = librosa.pyin(y, fmin=70, fmax=400, sr=sr, frame_length=1024)
    f0 = f0[voz & ~np.isnan(f0)]
    semitonos = 12 * np.log2(np.percentile(f0, 90) / np.percentile(f0, 10)) if len(f0) > 10 else 0
    rms = librosa.feature.rms(y=y)[0]; activo = rms[rms > np.max(rms) * 0.05]
    dinamica = 20 * np.log10(np.percentile(activo, 95) / np.percentile(activo, 20))
    habla = len(activo) * 512 / sr
    silabas = len(re.findall(r"[aeiouáéíóú]+", texto.lower())) if texto else None
    return round(float(semitonos), 1), round(silabas / habla, 1) if silabas else None, round(float(dinamica), 1)
if __name__ == "__main__":
    print(energia(sys.argv[1]))
