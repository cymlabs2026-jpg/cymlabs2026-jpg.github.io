"""Construye grabador.html con las frases de frases.txt incrustadas.

Cada frase guarda dos formas: el texto que se lee en pantalla y el texto «de modelo»
(con la pronunciación de config/glosario.toml: «Claude» → «Clod»), que es el que va al
metadata.csv. Así el entrenamiento y la voz del agente usan la misma pronunciación.

Uso:  python construir_grabador.py
"""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parent
sys.path.insert(0, str(RAIZ / "src"))

from agente_video.config import aplicar_glosario  # noqa: E402


def leer_frases() -> list[str]:
    lineas = (AQUI / "frases.txt").read_text(encoding="utf-8").splitlines()
    return [l.strip() for l in lineas if l.strip() and not l.lstrip().startswith("#")]


def main() -> None:
    with (RAIZ / "config" / "glosario.toml").open("rb") as f:
        pronunciacion = tomllib.load(f).get("pronunciacion", {})
    frases = [
        {"id": f"cm_{i:04d}", "texto": t, "modelo": aplicar_glosario(t, pronunciacion)}
        for i, t in enumerate(leer_frases(), 1)
    ]
    for f in frases:
        if "|" in f["texto"]:
            raise SystemExit(f"La frase {f['id']} contiene «|», que rompe el metadata.csv")
    html = (AQUI / "grabador_plantilla.html").read_text(encoding="utf-8")
    html = html.replace("/*FRASES*/", json.dumps(frases, ensure_ascii=False))
    (AQUI / "grabador.html").write_text(html, encoding="utf-8")
    print(f"grabador.html listo con {len(frases)} frases")


if __name__ == "__main__":
    main()
