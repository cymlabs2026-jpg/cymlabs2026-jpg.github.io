"""Subtítulos animados al estilo de las apps de video corto (palabra activa resaltada).

Se queman en la imagen con el formato ASS (lo dibuja FFmpeg con libass), así se ven en cualquier
reproductor o red social sin depender de que activen los subtítulos.

Pasos:
1. Se transcribe cada bloque de voz con faster-whisper pidiendo el tiempo de cada palabra.
2. Las palabras del texto que se muestra (con cifras en dígitos) se reparten sobre esos tiempos
   según su posición en la frase, así el resaltado sigue a la voz aunque digamos "quinientos setenta"
   y en pantalla diga "570".
3. Se agrupan en frases cortas (2 a 4 palabras) y en cada grupo la palabra que se está diciendo
   aparece en el color cian de la marca.
"""
from __future__ import annotations

import re
from pathlib import Path

# Colores en formato ASS: &HAABBGGRR (AA = transparencia, 00 = opaco).
BLANCO = "&H00FFFFFF"
CIAN = "&H00EED322"          # #22D3EE, el cian claro de la marca
CAJA = "&H0020120B"          # #0B1220, el azul noche de la marca (opaco: así no se notan las uniones)
MAX_PALABRAS = 4
MAX_LETRAS = 26


def _peso(palabra: str) -> float:
    """Cuánto 'se tarda' en decir una palabra: las cifras se leen más largas de lo que se escriben."""
    letras = len(re.sub(r"\W", "", palabra)) or 1
    return letras * 3.2 if re.search(r"\d", palabra) else letras


def tiempos_palabras(wav: Path, texto: str, modelo) -> list[tuple[str, float, float]]:
    """Devuelve [(palabra_mostrada, inicio, fin)] en segundos desde el comienzo del audio."""
    segmentos, _ = modelo.transcribe(str(wav), language="es", word_timestamps=True, beam_size=5)
    dichas = [(w.word.strip(), w.start, w.end) for s in segmentos for w in s.words if w.word.strip()]
    palabras = texto.split()
    if not dichas:
        return [(p, 0.0, 0.0) for p in palabras]

    # Línea de tiempo de la voz: posición relativa (0 a 1) → segundo.
    total = sum(_peso(w) for w, _, _ in dichas)
    puntos, acumulado = [(0.0, dichas[0][1])], 0.0
    for w, ini, fin in dichas:
        puntos.append((acumulado / total, ini))
        acumulado += _peso(w)
        puntos.append((acumulado / total, fin))

    def instante(x: float) -> float:
        for (x0, t0), (x1, t1) in zip(puntos, puntos[1:]):
            if x0 <= x <= x1:
                return t0 if x1 == x0 else t0 + (t1 - t0) * (x - x0) / (x1 - x0)
        return puntos[-1][1]

    total_m = sum(_peso(p) for p in palabras)
    salida, acumulado = [], 0.0
    for p in palabras:
        ini = instante(acumulado / total_m)
        acumulado += _peso(p)
        salida.append((p, ini, instante(acumulado / total_m)))
    return salida


def _grupos(palabras: list[tuple[str, float, float]]) -> list[list[tuple[str, float, float]]]:
    """Frases cortas: corta al llegar a 4 palabras, a ~26 letras o después de un signo de puntuación."""
    grupos, actual = [], []
    for p in palabras:
        if actual and (len(actual) >= MAX_PALABRAS or len(" ".join(w for w, _, _ in actual + [p])) > MAX_LETRAS):
            grupos.append(actual)
            actual = []
        actual.append(p)
        if re.search(r"[.,:;?!]$", p[0]) and len(actual) >= 2:
            grupos.append(actual)
            actual = []
    if actual:
        grupos.append(actual)
    return grupos


def _tiempo(s: float) -> str:
    s = max(0.0, s)
    return f"{int(s // 3600)}:{int(s % 3600 // 60):02d}:{s % 60:05.2f}"


def _limpiar(texto: str) -> str:
    return texto.replace("{", "(").replace("}", ")").replace("\\", "/")


def generar_ass(bloques: list[dict], salida: Path, ancho: int = 1920, alto: int = 1080) -> Path:
    """bloques: [{"inicio": s, "palabras": [(palabra, ini, fin), ...]}] con tiempos relativos al bloque."""
    lineas = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {ancho}", f"PlayResY: {alto}",
        "WrapStyle: 2", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding",
        # BorderStyle 3 = caja de fondo detrás del texto, como en CapCut.
        f"Style: Capcut,Inter ExtraBold,64,{BLANCO},{BLANCO},{CAJA},{CAJA},-1,0,0,0,100,100,0,0,3,18,0,2,120,120,58,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for bloque in bloques:
        base = bloque["inicio"]
        grupos = _grupos(bloque["palabras"])
        for g, grupo in enumerate(grupos):
            fin_grupo = grupos[g + 1][0][1] if g + 1 < len(grupos) else grupo[-1][2] + 0.35
            for i, (_, ini, fin) in enumerate(grupo):
                desde = grupo[0][1] if i == 0 else ini
                hasta = grupo[i + 1][1] if i + 1 < len(grupo) else fin_grupo
                if hasta - desde < 0.02:
                    continue
                partes = []
                for j, (w, _, _) in enumerate(grupo):
                    w = _limpiar(w)
                    if j == i:
                        partes.append(r"{\c" + CIAN + "&}" + w + r"{\c" + BLANCO + "&}")
                    else:
                        partes.append(w)
                # Cada grupo nuevo entra con un fundido corto.
                pop = r"{\fad(90,0)}" if i == 0 else ""
                lineas.append(f"Dialogue: 0,{_tiempo(base + desde)},{_tiempo(base + hasta)},Capcut,,0,0,0,,"
                              f"{pop}{' '.join(partes)}")
    salida.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return salida
