"""Convierte las plantillas HTML de marca en imágenes, con un navegador sin ventana (Playwright).

Se usa HTML porque así la intro, el cierre y la miniatura comparten tipografías,
colores y logo con el sitio web, y se pueden rediseñar sin tocar código.
"""

from __future__ import annotations

import base64
import html
import os
import re
from pathlib import Path

# Valores de la configuración o del propio agente, que pueden llevar HTML a propósito.
CLAVES_SIN_ESCAPAR = {"css", "logo", "foco", "llamado", "imagen_html", "logo_html"}


def disponible() -> bool:
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        return False
    return True


def llenar(carpeta: Path, nombre: str, valores: dict[str, str]) -> str:
    """Rellena una plantilla: {{clave}} se reemplaza por su valor (escapado como HTML)."""
    texto = (carpeta / nombre).read_text(encoding="utf-8")
    valores = {"css": (carpeta / "base.css").read_text(encoding="utf-8"),
               "logo": (carpeta / "logo.svg").read_text(encoding="utf-8"), **valores}

    def reemplazo(m: re.Match) -> str:
        clave = m.group(1)
        valor = str(valores.get(clave, ""))
        if clave in CLAVES_SIN_ESCAPAR:
            return valor
        texto = html.escape(valor)
        # Un número no se separa de su unidad al partir la línea: «28 %», «15 M».
        texto = re.sub(r"(\d) (%|M\b)", "\\1&nbsp;\\2", texto)
        # *palabra* se resalta con el degradado de la marca.
        return re.sub(r"\*([^*]+)\*", r'<span class="acento">\1</span>', texto)

    return re.sub(r"\{\{(\w+)\}\}", reemplazo, texto)


def imagen_como_dato(ruta: Path) -> str:
    """Imagen incrustada en el HTML (la página no puede leer archivos locales)."""
    tipo = {".png": "png", ".webp": "webp", ".svg": "svg+xml"}.get(ruta.suffix.lower(), "jpeg")
    return f"data:image/{tipo};base64,{base64.b64encode(ruta.read_bytes()).decode()}"


def a_png(contenido_html: str, salida: Path, ancho_salida: int = 1920) -> None:
    """Toma una captura del diseño (1920x1080) y la guarda con el ancho pedido."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        # AGENTE_VIDEO_CHROMIUM permite usar un Chromium ya instalado en el equipo.
        navegador = p.chromium.launch(executable_path=os.environ.get("AGENTE_VIDEO_CHROMIUM") or None)
        try:
            pagina = navegador.new_page(
                viewport={"width": 1920, "height": 1080}, device_scale_factor=ancho_salida / 1920
            )
            pagina.set_content(contenido_html, wait_until="networkidle")
            pagina.evaluate("document.fonts.ready")
            pagina.screenshot(path=str(salida))
        finally:
            navegador.close()
