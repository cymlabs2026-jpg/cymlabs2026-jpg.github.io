"""Genera la miniatura y las tarjetas de marca del video 01, con las cifras reales del Excel.

Uso (con el agente instalado con el extra [marca]):  python generar_miniatura.py
Salida en esta carpeta: foco.png, miniatura.png, intro.png y cierre.png.

Copia foco.png a la carpeta del proyecto del video para que el agente lo use como
foco visual de la miniatura en lugar de un cuadro del video.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook

from agente_video import render
from agente_video.config import RAIZ, cargar_config

AQUI = Path(__file__).parent
PLANTILLAS = RAIZ / "plantillas" / "marca"
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

TITULO = "Analiza las ventas de tu negocio con Claude en 15 minutos"
TEXTO_MINIATURA = "¿Por qué *cayó 28 %*?"


def ventas_palmira_norte() -> list[tuple[str, float]]:
    """Ventas mensuales de Palmira Norte (millones), tal como están en el Excel."""
    por_mes = defaultdict(float)
    for fila in load_workbook(AQUI / "ventas_ferreteria.xlsx", read_only=True).active.iter_rows(min_row=2, values_only=True):
        fecha, _, sede, *_, total, _, _ = fila
        if sede != "Palmira Norte":
            continue
        if isinstance(fecha, str):
            fecha = datetime.strptime(fecha, "%d/%m/%Y")
        por_mes[(fecha.year, fecha.month)] += total
    return [(MESES[m - 1], v / 1e6) for (a, m), v in sorted(por_mes.items())]


def html_foco(datos: list[tuple[str, float]]) -> str:
    maximo = max(v for _, v in datos)
    barras = "".join(
        f'<div class="col"><div class="barra {"baja" if i >= 8 else ""}" style="height:{v / maximo * 100:.1f}%"></div>'
        f'<span>{mes}</span></div>'
        for i, (mes, v) in enumerate(datos)
    )
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
{(PLANTILLAS / "base.css").read_text(encoding="utf-8")}
body {{ background: #fff; }}
body::before {{ display: none; }}
.panel {{ position: absolute; inset: 0; padding: 90px 110px 80px; display: flex; flex-direction: column; }}
.cabecera {{ display: flex; justify-content: space-between; align-items: baseline; }}
h1 {{ font-family: 'Sora', sans-serif; font-size: 64px; font-weight: 700; }}
h1 small {{ display: block; font-size: 36px; font-weight: 600; color: #667085; margin-top: 10px; }}
.alerta {{ font-family: 'Sora', sans-serif; font-weight: 800; font-size: 120px; color: #E11D48; }}
.grafico {{ flex: 1; display: flex; align-items: flex-end; gap: 26px; margin-top: 40px; border-bottom: 4px solid #E5E7EB; }}
.col {{ flex: 1; height: 100%; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; }}
.barra {{ width: 100%; border-radius: 14px 14px 0 0; background: var(--degradado); }}
.barra.baja {{ background: linear-gradient(180deg, #FB7185, #E11D48); }}
.col span {{ position: absolute; bottom: 30px; }}
.meses {{ display: flex; gap: 26px; margin-top: 18px; font-size: 32px; font-weight: 600; color: #667085; }}
.meses span {{ flex: 1; text-align: center; }}
</style></head><body><div class="panel">
<div class="cabecera"><h1>Ventas · Palmira Norte<small>Millones de COP por mes</small></h1><div class="alerta">−28 %</div></div>
<div class="grafico">{barras.replace('<span>', '<span hidden>')}</div>
<div class="meses">{"".join(f"<span>{m}</span>" for m, _ in datos)}</div>
</div></body></html>"""


def main() -> None:
    config = cargar_config()
    marca = config["marca"]
    foco = AQUI / "foco.png"
    render.a_png(html_foco(ventas_palmira_norte()), foco)
    render.a_png(
        render.llenar(PLANTILLAS, "miniatura.html", {"texto": TEXTO_MINIATURA, "foco": render.imagen_como_dato(foco)}),
        AQUI / "miniatura.png",
        ancho_salida=1280,
    )
    render.a_png(render.llenar(PLANTILLAS, "intro.html", {
        "etiqueta": marca["etiqueta"], "titulo": TITULO, "lema": marca["lema"],
    }), AQUI / "intro.png")
    render.a_png(render.llenar(PLANTILLAS, "cierre.html", {
        "etiqueta": "Gracias por ver", "titulo": marca["cierre_titulo"],
        "llamado": marca["cierre_llamado"], "enlace": marca["cierre_enlace"],
    }), AQUI / "cierre.png")
    print("Listo: foco.png, miniatura.png, intro.png y cierre.png")


if __name__ == "__main__":
    main()
