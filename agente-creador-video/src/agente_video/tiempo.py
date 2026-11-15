"""Plan de edición y conversión de tiempos.

El plan de edición divide la grabación original en tramos consecutivos:

- "normal":   se conserva tal cual (alguien habla).
- "acelerar": nadie habla pero la pantalla se mueve (la IA está generando);
              se reproduce a `velocidad` veces.
- "cortar":   nadie habla y la pantalla está quieta; se elimina.

Como el video final es más corto, cualquier tiempo de la grabación original
(una frase, un capítulo) se traduce al tiempo final con `remapear`.
"""

from __future__ import annotations

Intervalo = tuple[float, float]

DURACION_MINIMA_TRAMO = 1.0  # No vale la pena acelerar o cortar tramos más cortos.


def _interseccion(a: Intervalo, b: Intervalo) -> Intervalo | None:
    ini, fin = max(a[0], b[0]), min(a[1], b[1])
    return (ini, fin) if fin > ini else None


def restar(a: Intervalo, quitar: list[Intervalo]) -> list[Intervalo]:
    """Partes de `a` que no cubre ningún intervalo de `quitar`."""
    partes = [a]
    for q in quitar:
        nuevas = []
        for p in partes:
            if q[1] <= p[0] or q[0] >= p[1]:
                nuevas.append(p)
                continue
            if q[0] > p[0]:
                nuevas.append((p[0], q[0]))
            if q[1] < p[1]:
                nuevas.append((q[1], p[1]))
        partes = nuevas
    return partes


def construir_plan(
    duracion: float,
    silencios: list[Intervalo],
    quietos: list[Intervalo],
    *,
    velocidad_espera: float = 4.0,
    cortar_tiempo_muerto: bool = True,
    margen_s: float = 0.3,
) -> list[dict]:
    """Construye el plan de edición a partir de los silencios y la pantalla quieta."""
    especiales: list[tuple[float, float, str]] = []
    for ini, fin in sorted(silencios):
        ini, fin = max(0.0, ini + margen_s), min(duracion, fin - margen_s)
        if fin - ini < DURACION_MINIMA_TRAMO:
            continue
        quietos_aqui = [x for q in quietos if (x := _interseccion((ini, fin), q))]
        tipo_quieto = "cortar" if cortar_tiempo_muerto else "acelerar"
        for q in quietos_aqui:
            especiales.append((q[0], q[1], tipo_quieto))
        for p in restar((ini, fin), quietos_aqui):
            especiales.append((p[0], p[1], "acelerar"))

    especiales = [e for e in sorted(especiales) if e[1] - e[0] >= DURACION_MINIMA_TRAMO]

    plan: list[dict] = []
    cursor = 0.0
    for ini, fin, tipo in especiales:
        if ini > cursor:
            plan.append(_tramo(cursor, ini, "normal", 1.0))
        plan.append(_tramo(ini, fin, tipo, velocidad_espera if tipo == "acelerar" else 1.0))
        cursor = fin
    if cursor < duracion:
        plan.append(_tramo(cursor, duracion, "normal", 1.0))
    return _unir_iguales(plan)


def _tramo(ini: float, fin: float, tipo: str, velocidad: float) -> dict:
    return {"inicio": round(ini, 3), "fin": round(fin, 3), "tipo": tipo, "velocidad": velocidad}


def _unir_iguales(plan: list[dict]) -> list[dict]:
    unido: list[dict] = []
    for t in plan:
        if unido and unido[-1]["tipo"] == t["tipo"] and unido[-1]["velocidad"] == t["velocidad"]:
            unido[-1]["fin"] = t["fin"]
        else:
            unido.append(dict(t))
    return unido


def duracion_tramo_final(tramo: dict) -> float:
    if tramo["tipo"] == "cortar":
        return 0.0
    return (tramo["fin"] - tramo["inicio"]) / tramo["velocidad"]


def duracion_final(plan: list[dict]) -> float:
    return sum(duracion_tramo_final(t) for t in plan)


def remapear(t: float, plan: list[dict]) -> float:
    """Traduce un tiempo de la grabación original al tiempo del video final."""
    acumulado = 0.0
    for tramo in plan:
        if t < tramo["inicio"]:
            break
        if t < tramo["fin"]:
            if tramo["tipo"] == "cortar":
                return acumulado
            return acumulado + (t - tramo["inicio"]) / tramo["velocidad"]
        acumulado += duracion_tramo_final(tramo)
    return acumulado


# --- Formatos ---------------------------------------------------------------

def a_srt(segundos: float) -> str:
    ms = int(round(max(0.0, segundos) * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def a_youtube(segundos: float) -> str:
    """Formato de capítulo de YouTube: 0:00, 4:07, 1:02:03."""
    total = int(max(0.0, segundos))
    h, resto = divmod(total, 3600)
    m, s = divmod(resto, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def a_marca(segundos: float) -> str:
    """Formato legible con décimas, usado en guion.md: 1:02.5."""
    m, s = divmod(max(0.0, segundos), 60)
    return f"{int(m)}:{s:04.1f}"


def de_marca(texto: str) -> float:
    """Convierte '1:02.5', '62.5' o '1:02:03' a segundos."""
    partes = [float(p) for p in texto.strip().split(":")]
    segundos = 0.0
    for p in partes:
        segundos = segundos * 60 + p
    return segundos
