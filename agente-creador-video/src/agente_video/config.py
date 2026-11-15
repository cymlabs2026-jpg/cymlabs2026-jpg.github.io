"""Carga de la configuración del canal, del proyecto y del glosario."""

from __future__ import annotations

import copy
import os
import re
import tomllib
from pathlib import Path

# Raíz del agente: la carpeta que contiene config/, prompts/ y proyectos/.
RAIZ = Path(__file__).resolve().parents[2]


def _mezclar(base: dict, extra: dict) -> dict:
    """Mezcla dos diccionarios anidados; los valores de `extra` ganan."""
    resultado = copy.deepcopy(base)
    for clave, valor in extra.items():
        if isinstance(valor, dict) and isinstance(resultado.get(clave), dict):
            resultado[clave] = _mezclar(resultado[clave], valor)
        else:
            resultado[clave] = valor
    return resultado


def _leer_toml(ruta: Path) -> dict:
    if not ruta.exists():
        return {}
    with ruta.open("rb") as f:
        return tomllib.load(f)


def cargar_config(carpeta_proyecto: Path | None = None, raiz: Path = RAIZ) -> dict:
    """Configuración del canal, sobrescrita por el `config.toml` del proyecto si existe."""
    config = _leer_toml(raiz / "config" / "canal.toml")
    if carpeta_proyecto is not None:
        config = _mezclar(config, _leer_toml(carpeta_proyecto / "config.toml"))
    config["_glosario"] = _leer_toml(raiz / "config" / "glosario.toml").get("reemplazos", {})
    config["_raiz"] = str(raiz)
    return config


def aplicar_glosario(texto: str, glosario: dict[str, str]) -> str:
    """Reemplaza términos mal transcritos por su forma correcta (palabra completa)."""
    # Los términos más largos primero, para que "scroll y teller" gane a "scroll".
    for mal in sorted(glosario, key=len, reverse=True):
        patron = r"(?<!\w)" + re.escape(mal) + r"(?!\w)"
        texto = re.sub(patron, glosario[mal], texto)
    return texto


def leer_prompt(nombre: str, raiz: Path = RAIZ) -> str:
    return (raiz / "prompts" / nombre).read_text(encoding="utf-8")


def cargar_env(raiz: Path = RAIZ) -> None:
    """Lee las claves del archivo .env de la raíz, sin pisar las que ya existan en el sistema."""
    ruta = raiz / ".env"
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        valor = valor.strip().strip('"').strip("'")
        if valor:
            os.environ.setdefault(clave.strip(), valor)
