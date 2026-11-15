"""La carpeta de un video y su estado.

Cada etapa lee y escribe archivos dentro de la carpeta del proyecto. El archivo
`estado.json` recuerda qué etapas terminaron, para retomar sin repetir trabajo.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path

EXTENSIONES_VIDEO = {".mp4", ".mov", ".mkv", ".webm", ".avi"}


def slug(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = re.sub(r"[^a-zA-Z0-9]+", "-", texto).strip("-").lower()
    return texto or "video"


class Proyecto:
    def __init__(self, carpeta: Path | str):
        self.carpeta = Path(carpeta).resolve()

    # --- Rutas -------------------------------------------------------------
    @property
    def crudo(self) -> Path:
        """Grabaciones originales, sin editar. Se procesan en orden alfabético."""
        return self.carpeta / "crudo"

    @property
    def trabajo(self) -> Path:
        """Archivos intermedios. Se pueden borrar para liberar espacio."""
        return self.carpeta / "trabajo"

    @property
    def entrega(self) -> Path:
        """Lo que se publica: video, subtítulos, capítulos y descripción."""
        return self.carpeta / "entrega"

    def ruta(self, nombre: str) -> Path:
        return self.carpeta / nombre

    # --- Creación ----------------------------------------------------------
    @classmethod
    def crear(cls, base: Path, nombre: str, fecha: date | None = None) -> "Proyecto":
        fecha = fecha or date.today()
        carpeta = Path(base) / f"{fecha.isoformat()}-{slug(nombre)}"
        if carpeta.exists():
            raise FileExistsError(f"Ya existe el proyecto {carpeta}")
        proyecto = cls(carpeta)
        for sub in (proyecto.crudo, proyecto.trabajo, proyecto.entrega):
            sub.mkdir(parents=True)
        proyecto.guardar_estado({"nombre": nombre, "creado": _ahora(), "etapas": {}, "aprobaciones": {}})
        return proyecto

    def grabaciones(self) -> list[Path]:
        if not self.crudo.exists():
            return []
        return sorted(p for p in self.crudo.iterdir() if p.suffix.lower() in EXTENSIONES_VIDEO)

    # --- Estado ------------------------------------------------------------
    @property
    def _archivo_estado(self) -> Path:
        return self.carpeta / "estado.json"

    def estado(self) -> dict:
        if not self._archivo_estado.exists():
            return {"etapas": {}, "aprobaciones": {}}
        return json.loads(self._archivo_estado.read_text(encoding="utf-8"))

    def guardar_estado(self, estado: dict) -> None:
        self.carpeta.mkdir(parents=True, exist_ok=True)
        escribir_json(self._archivo_estado, estado)

    def etapa_completada(self, nombre: str) -> bool:
        return bool(self.estado()["etapas"].get(nombre, {}).get("completada"))

    def marcar_etapa(self, nombre: str, completada: bool = True, **datos) -> None:
        estado = self.estado()
        estado["etapas"][nombre] = {"completada": completada, "fecha": _ahora(), **datos}
        self.guardar_estado(estado)

    def invalidar_desde(self, nombres: list[str]) -> None:
        estado = self.estado()
        for nombre in nombres:
            estado["etapas"].pop(nombre, None)
        self.guardar_estado(estado)

    def aprobado(self, que: str) -> bool:
        return bool(self.estado().get("aprobaciones", {}).get(que))

    def aprobar(self, que: str, valor: bool = True) -> None:
        estado = self.estado()
        estado.setdefault("aprobaciones", {})[que] = valor
        self.guardar_estado(estado)


def escribir_json(ruta: Path, datos) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def leer_json(ruta: Path):
    return json.loads(Path(ruta).read_text(encoding="utf-8"))


def _ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")
