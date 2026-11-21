"""Rutina automática: convierte un encargo en JSON en un video terminado con la voz clonada del autor.

La dispara Superinteligencia (el asistente local) a través de una tarea programada de Claude Code.
Hace lo mismo que se hizo a mano con el video 01:

1. Voz: Chatterbox multilingüe con la referencia larga del autor (exageración 0,7, cfg 0,3),
   3 tomas por bloque y se queda con la mejor (se entiende, se parece a la voz, tiene energía, suena natural).
2. Imagen: escenas animadas estilo CapCut (palabras que suben, acercamiento lento, barrido de color).
3. Subtítulos quemados con la palabra activa en cian, música original bajo la voz y nivel final de −16 LUFS.
4. Entrega: sube video.mp4, subtitulos.srt y, al final, listo.json al repositorio privado,
   en resultados/<job_id>/ de la rama main. Si algo falla, sube solo listo.json con estado "error".

Uso:
    python rutina.py --encargo encargo.json --repo-privado ../superinteligencia-videos
    python rutina.py --encargo encargo.json --repo-privado ../superinteligencia-videos --no-subir   # prueba local

La voz del autor NUNCA se copia a este repositorio: se lee del repositorio privado y todo el
material de trabajo queda en una carpeta temporal fuera de Git.
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import traceback
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "voz_propia"))

FPS = 30
TOMAS = 3
EXAGERACION, CFG = 0.7, 0.3          # opción A, la que eligió el autor
INTRO_S = 2.5                        # tarjeta de título al inicio
ENTRADA_VOZ, SALIDA_VOZ = 0.5, 0.7   # respiro antes y después de cada bloque
UMBRAL_INTELIGIBILIDAD = 0.95
UMBRAL_PARECIDO = 0.92               # medido contra la referencia (las tomas del video 01 dieron 0,93–0,96)
LUFS_OBJETIVO = -16.0
MAX_LETRAS_TOMA = 280                # bloques más largos se generan por frases y se unen

FORMATOS = {
    # ancho, alto, escala del diseño, franja libre abajo (px), tamaño y margen de subtítulos
    "horizontal": (1920, 1080, 1.0, 230, 64, 58),
    "vertical": (1080, 1920, 0.85, 560, 60, 420),
    "cuadrado": (1080, 1080, 0.72, 210, 52, 46),
}
ALIAS_FORMATO = {"16:9": "horizontal", "youtube": "horizontal", "9:16": "vertical", "reels": "vertical",
                 "shorts": "vertical", "tiktok": "vertical", "1:1": "cuadrado"}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


class ErrorEncargo(ValueError):
    """El JSON del encargo no tiene el formato esperado."""


# ---------------------------------------------------------------- encargo

def validar(encargo: dict) -> dict:
    """Revisa el encargo y devuelve una versión normalizada."""
    if not isinstance(encargo, dict):
        raise ErrorEncargo("el encargo debe ser un objeto JSON")
    faltan = [c for c in ("version", "job_id", "bloques") if c not in encargo]
    if faltan:
        raise ErrorEncargo(f"faltan campos obligatorios: {', '.join(faltan)}")
    job_id = str(encargo["job_id"]).strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}", job_id):
        raise ErrorEncargo("job_id solo puede tener letras, números, punto, guion y guion bajo (máx. 100)")
    bloques = encargo["bloques"]
    if not isinstance(bloques, list) or not bloques:
        raise ErrorEncargo("bloques debe ser una lista con al menos un bloque")
    normales = []
    for i, b in enumerate(bloques, 1):
        if not isinstance(b, dict) or not str(b.get("locucion", "")).strip():
            raise ErrorEncargo(f"el bloque {i} no tiene locucion")
        normales.append({"locucion": " ".join(str(b["locucion"]).split()), "pantalla": b.get("pantalla")})
    formato = str(encargo.get("formato") or "horizontal").strip().lower()
    formato = ALIAS_FORMATO.get(formato, formato)
    if formato not in FORMATOS:
        raise ErrorEncargo(f"formato «{encargo.get('formato')}» no soportado (usa horizontal, vertical o cuadrado)")
    cierre = encargo.get("cierre") or {}
    llamado = " ".join(str(cierre.get("llamado_a_la_accion") or "").split())
    estilo = encargo.get("estilo") or {}
    if isinstance(estilo, str):
        estilo = {"descripcion": estilo}
    return {
        "version": encargo["version"], "job_id": job_id, "tema": str(encargo.get("tema") or ""),
        "duracion_objetivo_seg": float(encargo.get("duracion_objetivo_seg") or 0),
        "formato": formato, "titulo_en_pantalla": str(encargo.get("titulo_en_pantalla") or encargo.get("tema") or ""),
        "bloques": normales, "cierre": {**cierre, "llamado_a_la_accion": llamado}, "estilo": estilo,
    }


def pantalla_de(pantalla, locucion: str) -> dict:
    """Lo que se ve en una escena. Acepta texto o un objeto {etiqueta, titulo, subtitulo, puntos, cifra}."""
    if isinstance(pantalla, dict):
        return {
            "etiqueta": pantalla.get("etiqueta", ""),
            "titulo": pantalla.get("titulo") or pantalla.get("texto") or "",
            "sub": pantalla.get("subtitulo") or pantalla.get("sub") or "",
            "puntos": [str(p) for p in (pantalla.get("puntos") or pantalla.get("lista") or [])][:5],
            "cifra": str(pantalla.get("cifra") or ""),
        }
    texto = str(pantalla or "").strip()
    if not texto:  # sin pantalla: la primera frase de la locución
        texto = re.split(r"(?<=[.!?:])\s", locucion)[0]
    return {"etiqueta": "", "titulo": texto, "sub": "", "puntos": [], "cifra": ""}


# ---------------------------------------------------------------- texto para la voz

def _pronunciacion() -> dict:
    datos = tomllib.loads((RAIZ / "config" / "glosario.toml").read_text(encoding="utf-8"))
    return datos.get("pronunciacion", {})


def texto_para_voz(texto: str) -> str:
    """Cifras en palabras y nombres con su pronunciación (los subtítulos conservan la escritura original)."""
    from num2words import num2words

    def cifra(m: re.Match) -> str:
        entero = int(m.group(1).replace(".", ""))
        dicho = num2words(entero, lang="es")
        decimales = m.group(2)
        if decimales:
            # «1,05» se lee «uno coma cero cinco»; «2,5», «dos coma cinco».
            if decimales.startswith("0"):
                dicho += " coma " + " ".join(num2words(int(d), lang="es") for d in decimales)
            else:
                dicho += " coma " + num2words(int(decimales), lang="es")
        if m.group(3):
            dicho += " por ciento"
        return dicho

    texto = texto.replace("$", "")
    texto = re.sub(r"(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d+))?(\s*%)?", cifra, texto)
    texto = re.sub(r"\s+%", " por ciento", texto)
    for escrito, dicho in _pronunciacion().items():
        texto = re.sub(rf"(?<!\w){re.escape(escrito)}(?!\w)", dicho, texto)
    return texto


def partir_frases(texto: str, maximo: int = MAX_LETRAS_TOMA) -> list[str]:
    frases = re.split(r"(?<=[.!?])\s+", texto)
    partes, actual = [], ""
    for f in frases:
        if actual and len(actual) + len(f) + 1 > maximo:
            partes.append(actual)
            actual = f
        else:
            actual = f"{actual} {f}".strip()
    return partes + ([actual] if actual else [])


# ---------------------------------------------------------------- voz

def generar_tomas(textos: dict[str, str], referencia: Path, carpeta: Path, tomas: int) -> dict[str, list[Path]]:
    import torch
    import torchaudio
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    carpeta.mkdir(parents=True, exist_ok=True)
    modelo = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
    sr = modelo.sr
    salida: dict[str, list[Path]] = {}
    for n, (clave, texto) in enumerate(textos.items()):
        salida[clave] = []
        for t in range(1, tomas + 1):
            torch.manual_seed(1000 * t + n)
            trozos = []
            for frase in partir_frases(texto):
                wav = modelo.generate(frase, language_id="es", audio_prompt_path=str(referencia),
                                      exaggeration=EXAGERACION, cfg_weight=CFG)
                trozos += [wav, torch.zeros(1, int(0.22 * sr))]
            ruta = carpeta / f"{clave}_t{t}.wav"
            torchaudio.save(str(ruta), torch.cat(trozos[:-1], dim=1), sr)
            salida[clave].append(ruta)
            log(f"  voz {clave} toma {t}/{tomas} lista")
    del modelo
    gc.collect()
    return salida


def _energia(ruta: Path) -> tuple[float, float]:
    """Variación de tono (semitonos) y dinámica de volumen (dB), como en voz_propia/clon/energia.py."""
    import librosa
    import numpy as np

    y, sr = librosa.load(str(ruta), sr=16000)
    f0, voz, _ = librosa.pyin(y, fmin=70, fmax=400, sr=sr, frame_length=1024)
    f0 = f0[voz & ~np.isnan(f0)]
    tono = 12 * np.log2(np.percentile(f0, 90) / np.percentile(f0, 10)) if len(f0) > 10 else 0.0
    rms = librosa.feature.rms(y=y)[0]
    activo = rms[rms > np.max(rms) * 0.05]
    dinamica = 20 * np.log10(np.percentile(activo, 95) / np.percentile(activo, 20))
    return round(float(tono), 1), round(float(dinamica), 1)


class Medidor:
    """Mide cada toma: inteligibilidad (Whisper), parecido a la voz (Resemblyzer) y naturalidad (UTMOS)."""

    def __init__(self, referencia: Path):
        from faster_whisper import WhisperModel
        from resemblyzer import VoiceEncoder, preprocess_wav

        self.whisper = WhisperModel("small", device="cpu", compute_type="int8")
        self.encoder = VoiceEncoder("cpu", verbose=False)
        self._prep = preprocess_wav
        self.huella = self.encoder.embed_utterance(preprocess_wav(str(referencia)))
        try:
            from utmos_pytorch import UTMOSScoreTorch
            self.utmos = UTMOSScoreTorch(device="cpu")
        except Exception as e:  # sin UTMOS se elige por energía y parecido
            log(f"  aviso: UTMOS no disponible ({e}); la naturalidad no se medirá")
            self.utmos = None

    def medir(self, ruta: Path, texto_voz: str) -> dict:
        import numpy as np
        from preparar_dataset import similitud

        segmentos, _ = self.whisper.transcribe(str(ruta), language="es", beam_size=5)
        oido = " ".join(s.text.strip() for s in segmentos)
        parecido = float(np.dot(self.encoder.embed_utterance(self._prep(str(ruta))), self.huella))
        naturalidad = None
        if self.utmos is not None:
            import librosa
            import torch
            y, _ = librosa.load(str(ruta), sr=16000)
            with torch.no_grad():
                naturalidad = round(float(self.utmos.score(torch.tensor(y).unsqueeze(0)).item()), 2)
        tono, dinamica = _energia(ruta)
        return {"inteligibilidad": round(similitud(texto_voz, oido), 3), "parecido": round(parecido, 3),
                "naturalidad": naturalidad, "tono": tono, "dinamica": dinamica, "oido": oido}


def elegir(mediciones: dict[Path, dict]) -> tuple[Path, dict, str]:
    """Mismo criterio que voz_propia/clon/elegir_clon.py."""
    nat = lambda m: m["naturalidad"] if m["naturalidad"] is not None else 0
    basicas = {r: m for r, m in mediciones.items()
               if m["inteligibilidad"] >= UMBRAL_INTELIGIBILIDAD and m["parecido"] >= UMBRAL_PARECIDO}
    energicas = {r: m for r, m in basicas.items() if m["tono"] >= 8 and m["dinamica"] >= 10}
    if energicas:
        r, m = max(energicas.items(), key=lambda kv: nat(kv[1]))
        return r, m, "cumple todo"
    if basicas:
        r, m = max(basicas.items(), key=lambda kv: kv[1]["tono"] + kv[1]["dinamica"] / 2)
        return r, m, "energía algo baja"
    r, m = max(mediciones.items(), key=lambda kv: kv[1]["inteligibilidad"] + kv[1]["parecido"])
    return r, m, "no cumple los mínimos"


# ---------------------------------------------------------------- imagen y mezcla

def armar_html(escenas: list[dict], formato: str, tema: str) -> str:
    ancho, alto, k, libre, _, _ = FORMATOS[formato]
    marca = RAIZ / "plantillas" / "marca"
    html = (RAIZ / "rutina" / "escenas.html").read_text(encoding="utf-8")
    html = html.replace("/*CSS_MARCA*/", (marca / "base.css").read_text(encoding="utf-8"))
    html = html.replace("/*LOGO*/", (marca / "logo.svg").read_text(encoding="utf-8"))
    datos = {"escenas": escenas, "ancho": ancho, "alto": alto, "k": k, "libre_abajo": libre, "tema": tema}
    return html.replace("/*DATOS*/", json.dumps(datos, ensure_ascii=False))


def animar(escenas: list[dict], formato: str, tema: str, salida: Path) -> float:
    from playwright.sync_api import sync_playwright

    ancho, alto = FORMATOS[formato][:2]
    with sync_playwright() as p:
        navegador = p.chromium.launch(executable_path=os.environ.get("AGENTE_VIDEO_CHROMIUM") or None)
        pagina = navegador.new_page(viewport={"width": ancho, "height": alto})
        pagina.set_content(armar_html(escenas, formato, tema), wait_until="networkidle")
        pagina.evaluate("document.fonts.ready")
        total = pagina.evaluate("TOTAL")
        cuadros = int(round(total * FPS))
        ffmpeg = subprocess.Popen(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS),
             "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
             "-r", str(FPS), str(salida)], stdin=subprocess.PIPE)
        for i in range(cuadros):
            pagina.evaluate(f"pintar({i / FPS})")
            ffmpeg.stdin.write(pagina.screenshot(type="jpeg", quality=92))
            if i % (FPS * 10) == 0:
                log(f"  imagen {i // FPS} / {int(total)} s")
        ffmpeg.stdin.close()
        if ffmpeg.wait() != 0:
            raise RuntimeError("FFmpeg falló al codificar la animación")
        navegador.close()
    return cuadros / FPS


def medir_lufs(ruta: Path) -> float:
    from agente_video import medios
    salida = medios.ffmpeg("-i", str(ruta), "-af", "ebur128", "-f", "null", "-").stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", salida)[-1])


def mezclar(animacion: Path, clips: dict[str, Path], inicios: dict[str, float], textos_pantalla: dict[str, str],
            intro_s: float, cierre_s: float, musica: bool, formato: str, trabajo: Path, salida: Path,
            whisper) -> list[dict]:
    from agente_video import medios
    from agente_video.subtitulos_animados import generar_ass, tiempos_palabras

    duracion = medios.duracion(animacion)
    entradas, filtros, etiquetas = ["-i", str(animacion)], [], []
    for i, (clave, wav) in enumerate(clips.items(), 1):
        entradas += ["-i", str(wav)]
        filtros.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={int(inicios[clave] * 1000)}:all=1[v{i}];")
        etiquetas.append(f"[v{i}]")
    filtros.append(f"{''.join(etiquetas)}amix=inputs={len(etiquetas)}:normalize=0,apad,atrim=0:{duracion:.3f},"
                   "loudnorm=I=-18:TP=-2:LRA=7[locucion];")
    if musica:
        from agente_video.musica import componer
        pista = componer(duracion, trabajo / "musica.wav", intro_s=intro_s, cierre_s=cierre_s)
        n = len(clips) + 1
        entradas += ["-i", str(pista)]
        filtros += ["[locucion]asplit=2[voz_sola][voz_control];",
                    f"[{n}:a]equalizer=f=1800:t=o:w=1.5:g=-4,volume=0.35[cama];",
                    "[cama][voz_control]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=500[cama_baja];",
                    "[voz_sola][cama_baja]amix=inputs=2:normalize=0:duration=first[mezcla];"]
        etiqueta = "[mezcla]"
    else:
        etiqueta = "[locucion]"
    filtros.append(f"{etiqueta}aresample=48000[audio]")
    guion = trabajo / "filtro_audio.txt"
    guion.write_text("\n".join(filtros), encoding="utf-8")
    audio = trabajo / "audio.wav"
    medios.ffmpeg(*entradas, "-filter_complex_script", str(guion), "-map", "[audio]", "-t", f"{duracion:.3f}", str(audio))
    ganancia = LUFS_OBJETIVO - medir_lufs(audio)

    # Subtítulos animados: tiempo de cada palabra con Whisper, palabra activa en cian.
    ancho, alto, _, _, tamano, margen = FORMATOS[formato]
    bloques = [{"inicio": inicios[c], "palabras": tiempos_palabras(w, textos_pantalla[c], whisper)} for c, w in clips.items()]
    ass = generar_ass(bloques, trabajo / "subtitulos.ass", ancho, alto, tamano=tamano, margen_v=margen)
    medios.ffmpeg("-i", str(animacion), "-i", str(audio), "-map", "0:v", "-map", "1:a",
                  "-vf", f"ass={ass}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                  "-af", f"volume={ganancia:.2f}dB,alimiter=limit=0.84:attack=3:release=60:level=false",
                  "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", f"{duracion:.3f}", str(salida))
    return [{"inicio": inicios[c], "fin": inicios[c] + medios.duracion(w), "texto": textos_pantalla[c]} for c, w in clips.items()]


# ---------------------------------------------------------------- producción completa

def producir(enc: dict, referencia: Path, trabajo: Path, tomas: int, notas: list[str]) -> dict:
    from agente_video import medios
    from agente_video.etapas.subtitulos import generar_srt

    tiempos = {}
    t = time.time()
    claves = [f"b{i}" for i in range(1, len(enc["bloques"]) + 1)]
    pantalla = dict(zip(claves, (b["locucion"] for b in enc["bloques"])))
    if enc["cierre"]["llamado_a_la_accion"]:
        pantalla["cierre"] = enc["cierre"]["llamado_a_la_accion"]
    voz = {c: texto_para_voz(texto) for c, texto in pantalla.items()}

    log(f"1/4 Voz: {len(voz)} bloques × {tomas} tomas con Chatterbox")
    tomas_por_bloque = generar_tomas(voz, referencia, trabajo / "tomas", tomas)
    tiempos["voz"] = time.time() - t

    t = time.time()
    log("2/4 Midiendo y eligiendo la mejor toma de cada bloque")
    medidor = Medidor(referencia)
    elegidas, metricas = {}, {}
    for clave, rutas in tomas_por_bloque.items():
        mediciones = {r: medidor.medir(r, voz[clave]) for r in rutas}
        ruta, m, nota = elegir(mediciones)
        elegidas[clave], metricas[clave] = ruta, m
        log(f"  {clave}: {ruta.stem} · intelig. {m['inteligibilidad']:.0%} · parecido {m['parecido']:.3f} · "
            f"natural {m['naturalidad']} · tono {m['tono']} st · dinámica {m['dinamica']} dB · {nota}")
        if nota != "cumple todo":
            notas.append(f"{clave}: {nota}")
    tiempos["medicion"] = time.time() - t

    # Línea de tiempo: intro, un bloque por idea y cierre.
    duraciones = {c: medios.duracion(r) for c, r in elegidas.items()}
    estilo = enc["estilo"]
    escenas = [{"tipo": "intro", "etiqueta": estilo.get("etiqueta") or "C&M Labs",
                "titulo": enc["titulo_en_pantalla"], "duracion": INTRO_S}]
    inicios, cursor = {}, INTRO_S
    for clave, bloque in zip(claves, enc["bloques"]):
        dur = round(duraciones[clave] + ENTRADA_VOZ + SALIDA_VOZ, 2)
        escenas.append({"tipo": "bloque", **pantalla_de(bloque["pantalla"], bloque["locucion"]), "duracion": dur})
        inicios[clave] = cursor + ENTRADA_VOZ
        cursor += dur
    cierre_s = 4.0
    if "cierre" in elegidas:
        cierre_s = max(4.0, round(duraciones["cierre"] + 2.0, 2))
        inicios["cierre"] = cursor + 0.5
    cierre = enc["cierre"]
    escenas.append({"tipo": "cierre", "titulo": cierre.get("pantalla") or cierre.get("titulo") or "¿Lo llevamos a tu equipo?",
                    "sub": cierre.get("subtitulo") or "", "enlace": cierre.get("enlace") or "cymlabs2026-jpg.github.io",
                    "duracion": cierre_s})

    t = time.time()
    log(f"3/4 Animación ({enc['formato']})")
    animacion = trabajo / "animacion.mp4"
    animar(escenas, enc["formato"], estilo.get("tema", "claro"), animacion)
    tiempos["imagen"] = time.time() - t

    t = time.time()
    log("4/4 Mezcla, música, subtítulos y nivel final")
    video = trabajo / "video.mp4"
    narracion = mezclar(animacion, elegidas, inicios, pantalla, INTRO_S, cierre_s, estilo.get("musica", True) is not False,
                        enc["formato"], trabajo, video, medidor.whisper)
    duracion = medios.duracion(video)
    plan = [{"inicio": 0, "fin": duracion, "tipo": "normal", "velocidad": 1.0}]
    srt = trabajo / "subtitulos.srt"
    srt.write_text(generar_srt(narracion, plan), encoding="utf-8")
    tiempos["mezcla"] = time.time() - t

    lufs = medir_lufs(video)
    verificar(video, srt, lufs, duracion)
    objetivo = enc["duracion_objetivo_seg"]
    if objetivo and abs(duracion - objetivo) / objetivo > 0.25:
        notas.append(f"duración {duracion:.0f} s frente a {objetivo:.0f} s pedidos: ajusta el largo de las locuciones")
    notas.append("tiempos (min): " + ", ".join(f"{k} {v / 60:.1f}" for k, v in tiempos.items()))
    notas.append("voz generada con IA a partir de la voz del autor (con marca de agua de Chatterbox)")
    return {"video": video, "srt": srt, "duracion_seg": round(duracion, 1), "loudness_lufs": round(lufs, 1),
            "bloques": len(enc["bloques"]),
            "parecido_voz_min": round(min(m["parecido"] for m in metricas.values()), 3),
            "inteligibilidad_min": round(min(m["inteligibilidad"] for m in metricas.values()), 3)}


def verificar(video: Path, srt: Path, lufs: float, duracion: float) -> None:
    """Comprobaciones mínimas antes de entregar."""
    from agente_video import medios
    if not video.exists() or video.stat().st_size < 100_000:
        raise RuntimeError("el video no se generó o está vacío")
    if not medios.tiene_audio(video):
        raise RuntimeError("el video no tiene audio")
    if duracion < 5:
        raise RuntimeError(f"el video dura solo {duracion:.1f} s")
    if abs(lufs - LUFS_OBJETIVO) > 1.0:
        raise RuntimeError(f"el nivel quedó en {lufs:.1f} LUFS (se esperaba {LUFS_OBJETIVO})")
    if not srt.read_text(encoding="utf-8").strip():
        raise RuntimeError("los subtítulos .srt quedaron vacíos")


# ---------------------------------------------------------------- entrega en el repo privado

def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    identidad = []
    if not subprocess.run(["git", "-C", str(repo), "config", "user.email"], capture_output=True, text=True).stdout.strip():
        identidad = ["-c", "user.name=Rutina de video C&M Labs", "-c", "user.email=noreply@anthropic.com"]
    return subprocess.run(["git", *identidad, "-C", str(repo), *args], capture_output=True, text=True)


def subir(repo: Path, job_id: str, archivos: dict[str, Path], mensaje: str) -> None:
    """Copia los archivos a resultados/<job_id>/ y los sube a main (con reintentos)."""
    destino = repo / "resultados" / job_id
    destino.mkdir(parents=True, exist_ok=True)
    for nombre, origen in archivos.items():
        shutil.copy(origen, destino / nombre)
    _git(repo, "add", *(str(destino / n) for n in archivos))
    r = _git(repo, "commit", "-m", mensaje)
    if r.returncode != 0 and "nothing to commit" not in r.stdout:
        raise RuntimeError(f"git commit falló: {r.stderr or r.stdout}")
    for intento in range(5):
        r = _git(repo, "-c", "push.negotiate=true", "push", "origin", "HEAD:main")
        if r.returncode == 0:
            return
        log(f"  push rechazado (intento {intento + 1}): {r.stderr.strip()[-300:]}")
        _git(repo, "fetch", "--depth=50", "origin", "main")
        _git(repo, "rebase", "origin/main")
        time.sleep(2 ** (intento + 1))
    raise RuntimeError(f"no se pudo subir al repositorio privado: {r.stderr.strip()[-500:]}")


def preparar_repo(repo: Path) -> None:
    if not (repo / ".git").exists():
        raise RuntimeError(f"{repo} no es un repositorio git (¿se clonó superinteligencia-videos?)")
    _git(repo, "checkout", "main")
    _git(repo, "fetch", "--depth=50", "origin", "main")
    _git(repo, "rebase", "origin/main")


def buscar_referencia(repo: Path, voz: str | None) -> Path:
    candidatos = [Path(voz)] if voz else [repo / "voz" / "ref_larga.wav", repo / "ref_larga.wav"]
    for c in candidatos:
        if c.exists():
            return c
    raise RuntimeError("no se encontró la voz de referencia: " + ", ".join(str(c) for c in candidatos))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--encargo", required=True, help="Archivo JSON del encargo ('-' para leerlo de la entrada estándar)")
    parser.add_argument("--repo-privado", default=os.environ.get("SUPERINTELIGENCIA_REPO", str(RAIZ.parent.parent / "superinteligencia-videos")),
                        help="Clon de cymlabs2026-jpg/superinteligencia-videos")
    parser.add_argument("--voz", help="Otra voz de referencia (por defecto voz/ref_larga.wav del repo privado)")
    parser.add_argument("--tomas", type=int, default=TOMAS)
    parser.add_argument("--trabajo", help="Carpeta de trabajo (por defecto, una temporal fuera de Git)")
    parser.add_argument("--no-subir", action="store_true", help="No sube nada; deja la entrega en la carpeta de trabajo")
    args = parser.parse_args()

    inicio = time.time()
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    os.environ.setdefault("AGENTE_VIDEO_CHROMIUM", "/opt/pw-browsers/chromium" if Path("/opt/pw-browsers/chromium").exists() else "")
    repo = Path(args.repo_privado).resolve()
    trabajo = Path(args.trabajo or tempfile.mkdtemp(prefix="rutina_video_"))
    trabajo.mkdir(parents=True, exist_ok=True)
    notas: list[str] = []
    job_id = "desconocido"
    listo: dict = {}
    try:
        crudo = sys.stdin.read() if args.encargo == "-" else Path(args.encargo).read_text(encoding="utf-8")
        try:
            datos = json.loads(crudo)
        except json.JSONDecodeError as e:
            raise ErrorEncargo(f"el encargo no es JSON válido: {e}") from e
        job_id = str(datos.get("job_id", job_id)) if isinstance(datos, dict) else job_id
        enc = validar(datos)
        job_id = enc["job_id"]
        log(f"Encargo {job_id}: «{enc['tema']}» · {len(enc['bloques'])} bloques · {enc['formato']}")
        if not args.no_subir:
            preparar_repo(repo)
        referencia = buscar_referencia(repo, args.voz)
        r = producir(enc, referencia, trabajo, args.tomas, notas)
        listo = {"job_id": job_id, "estado": "ok", "duracion_seg": r["duracion_seg"], "loudness_lufs": r["loudness_lufs"],
                 "bloques": r["bloques"], "parecido_voz_min": r["parecido_voz_min"],
                 "inteligibilidad_min": r["inteligibilidad_min"],
                 "minutos_de_trabajo": round((time.time() - inicio) / 60, 1), "notas": notas}
        if not args.no_subir:
            log("Subiendo video y subtítulos al repositorio privado")
            subir(repo, job_id, {"video.mp4": r["video"], "subtitulos.srt": r["srt"]}, f"Resultado {job_id}: video y subtítulos")
        else:
            shutil.copy(r["video"], trabajo / "entrega_video.mp4")
    except Exception as e:  # noqa: BLE001 - cualquier fallo se reporta en listo.json
        traceback.print_exc()
        listo = {"job_id": job_id, "estado": "error", "error": f"{type(e).__name__}: {e}",
                 "minutos_de_trabajo": round((time.time() - inicio) / 60, 1), "notas": notas}
    listo["minutos_de_trabajo"] = round((time.time() - inicio) / 60, 1)
    ruta_listo = trabajo / "listo.json"
    ruta_listo.write_text(json.dumps(listo, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.no_subir and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}", job_id):
        try:
            subir(repo, job_id, {"listo.json": ruta_listo}, f"Resultado {job_id}: {listo['estado']}")
        except Exception as e:  # noqa: BLE001
            log(f"ERROR al subir listo.json: {e}")
            listo["estado"] = "error"
            listo.setdefault("error", f"no se pudo subir listo.json: {e}")
    print(json.dumps(listo, ensure_ascii=False, indent=2))
    log(f"Carpeta de trabajo: {trabajo}")
    return 0 if listo["estado"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
