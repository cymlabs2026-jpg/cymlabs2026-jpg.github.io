# Agente Creador de Video · C&M Labs

Convierte una grabación de pantalla sin editar en un tutorial listo para YouTube: corta el tiempo muerto, acelera las esperas, limpia la narración, genera subtítulos, capítulos, títulos y descripción.

Tú grabas la demostración; el agente hace la edición. Solo te pide una cosa: revisar el guion antes del montaje final.

> **Versión 0.2: modo tutorial con identidad de marca.** Las siguientes fases (zoom en los clics, avatar, formato vertical, conexión con el Agente de YouTube) están en la [hoja de ruta](#hoja-de-ruta).

## Cómo funciona

```
crudo/*.mp4 ─► 1 ingesta ─► 2 transcripción ─► 3 análisis ─► 4 guion ─► ✋ tu revisión
                                                                             │
  entrega/ ◄─ 9 entrega ◄─ 8 subtítulos ◄─ 7 audio ◄─ 6 marca ◄─ 5 montaje ◄─┘
```

| # | Etapa | Qué hace | Con qué |
|---|---|---|---|
| 1 | Ingesta | Une tus grabaciones (en orden alfabético) y las lleva a un formato común | FFmpeg |
| 2 | Transcripción | Pasa a texto lo que dijiste, con tiempos por palabra, y corrige nombres con el glosario | Whisper, en tu equipo |
| 3 | Análisis | Encuentra las **esperas** (nadie habla y la pantalla se mueve: la IA generando) y el **tiempo muerto** (nadie habla y la pantalla está quieta) | FFmpeg |
| 4 | Guion | Limpia muletillas, propone capítulos, 3 títulos, descripción y recupera los prompts dictados | Claude |
| ✋ | Aprobación | Revisas y corriges `guion.md` | Tú |
| 5 | Montaje | Corta el tiempo muerto y acelera las esperas (×4 por defecto) | FFmpeg |
| 6 | Marca | Intro con el título, pantalla final con huecos para los elementos de YouTube y miniatura de 1280×720 | Playwright, FFmpeg |
| 7 | Audio | Tu voz original o una voz sintética, música de fondo que baja sola cuando hablas, nivel de YouTube (−14 LUFS) | FFmpeg, Piper |
| 8 | Subtítulos | `.srt` sincronizado con el video final, o grabados en la imagen | FFmpeg |
| 9 | Entrega | Capítulos con las reglas de YouTube, descripción con prompts y capítulos, títulos y un reporte | — |

Cada etapa guarda su resultado en la carpeta del proyecto. Si algo falla, al volver a ejecutar se retoma donde quedó, sin repetir lo que ya está hecho.

## Instalación

Necesitas **Python 3.11 o superior** y **FFmpeg**.

En Windows:

```bash
winget install ffmpeg
```

En Mac:

```bash
brew install ffmpeg
```

Luego, dentro de esta carpeta:

```bash
python -m venv .venv
```

```bash
.venv\Scripts\activate
```

(En Mac o Linux: `source .venv/bin/activate`)

```bash
pip install -e ".[transcripcion,ia,marca]"
```

```bash
playwright install chromium
```

(El último comando descarga el navegador que dibuja la intro, el cierre y la miniatura. Sin él, el agente funciona igual pero sin esas piezas.)

Para el guion con Claude, copia `.env.example` como `.env` y pon tu clave de la API. Sin clave el agente funciona igual, pero el guion queda como la transcripción tal cual, sin capítulos, títulos ni descripción.

La primera transcripción descarga el modelo de Whisper (unos 500 MB con el modelo `small`). Las siguientes no.

## Uso

**1. Crea el proyecto**

```bash
agente-video nuevo "Tutorial Claude Sheets"
```

**2. Graba la pantalla** con lo que quieras (OBS, la grabadora de Windows con `Win + Alt + R`, o la de Mac con `Cmd + Shift + 5`) y copia el video en la carpeta `crudo/` del proyecto. No edites nada: los silencios, las esperas y los errores de dicción los resuelve el agente.

**3. Procesa**

```bash
agente-video procesar proyectos/2026-11-15-tutorial-claude-sheets
```

El agente se detiene cuando el guion está listo.

**4. Revisa `guion.md`.** Corrige textos, títulos, el texto de la miniatura (máximo cuatro palabras; lo que va entre `*asteriscos*` se resalta), capítulos o prompts. Si dejas vacío un bloque de la narración, esa frase sale de los subtítulos y de la voz sintética. No cambies las marcas de tiempo entre corchetes.

**5. Aprueba** (y el agente termina solo):

```bash
agente-video aprobar proyectos/2026-11-15-tutorial-claude-sheets
```

**6. Publica.** En `entrega/` encuentras:

| Archivo | Para qué |
|---|---|
| `video_final.mp4` | El video para subir |
| `subtitulos.srt` | Súbelo en YouTube Studio → Subtítulos |
| `titulos.txt` | Tres opciones; la primera es la recomendada |
| `miniatura.png` | Miniatura de 1280×720 lista para subir |
| `descripcion.txt` | Descripción con los prompts y los capítulos, lista para pegar |
| `capitulos.txt` | Solo los capítulos |
| `reporte.md` | Cuánto se recortó y avisos (por ejemplo, capítulos omitidos) |

### Otros comandos

Ver en qué va un proyecto:

```bash
agente-video estado proyectos/2026-11-15-tutorial-claude-sheets
```

Rehacer desde una etapa (por ejemplo, después de cambiar la configuración de edición):

```bash
agente-video procesar proyectos/2026-11-15-tutorial-claude-sheets --desde analisis
```

## Configuración

Todo está en `config/canal.toml`, comentado. Lo más útil:

| Ajuste | Qué cambia |
|---|---|
| `[edicion] velocidad_espera` | Cuánto se aceleran las esperas (4 = cuatro veces más rápido) |
| `[edicion] cortar_tiempo_muerto` | `false` para acelerar el tiempo muerto en vez de cortarlo |
| `[edicion] silencio_min_s` | Cuánto tiene que durar un silencio para tratarlo como espera |
| `[voz] modo` | `original` (tu voz) o `sintetica` (voz generada con Piper desde el guion) |
| `[musica] archivo` | Música de fondo; baja sola cuando hay voz |
| `[marca] intro`, `cierre`, `miniatura` | Activar o quitar cada pieza de marca |
| `[marca] cierre_llamado` | El llamado a la acción de la pantalla final |
| `[subtitulos] quemar` | `true` para grabar los subtítulos en la imagen |
| `[ia] aprobar_guion` | `false` para que no se detenga a pedir revisión |

Un proyecto puede tener su propio `config.toml` con solo los valores que cambian, por ejemplo:

```toml
[voz]
modo = "sintetica"
```

**Glosario** (`config/glosario.toml`): corrige lo que la transcripción escucha mal, como "Cloud" en lugar de "Claude". Añade los nombres de tus productos y cursos.

**Instrucciones del guion** (`prompts/guion_tutorial.md`): la fórmula del tutorial (gancho, contexto, pasos, puente, cierre) y las reglas de limpieza. Se edita sin tocar código.

### Miniatura

El agente pone el texto de la sección «Miniatura» de `guion.md` junto a un **foco visual**: si en la carpeta del proyecto hay un `foco.png` (por ejemplo, una captura del resultado), usa ese; si no, toma un cuadro del video cerca del final, que es donde suele verse el resultado.

El diseño de la intro, el cierre y la miniatura está en `plantillas/marca/` (HTML y CSS, con los colores y tipografías del sitio). Se puede rediseñar sin tocar código.

### Voz sintética

1. `pip install -e ".[voz]"`
2. Descarga una voz de Piper en español desde [rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices/tree/main/es): los dos archivos `.onnx` y `.onnx.json`, juntos en la misma carpeta.
3. Pon la ruta del `.onnx` en `[voz] modelo_piper` y cambia `modo = "sintetica"`.

Recomendada: **`es_MX-claude-high`** (licencia Apache 2.0, permite uso comercial). En las pruebas, Whisper transcribió su audio casi sin errores.

- `[voz] velocidad`: 1.0 es el ritmo natural; 1.08 (por defecto) suena más ágil.
- `[pronunciacion]` en `config/glosario.toml`: cómo debe decir la voz algunas palabras («Claude» → «Clod», «C&M» → «C y M»). Solo afecta al audio; los subtítulos conservan la escritura correcta.

Revisa la licencia de cada voz antes de usarla en un producto comercial.

## Estructura

```
agente-creador-video/
├── config/
│   ├── canal.toml          Ajustes del canal, la edición, la voz y la IA
│   └── glosario.toml       Correcciones de nombres y términos
├── prompts/
│   └── guion_tutorial.md   Instrucciones para Claude
├── plantillas/marca/       Diseño de la intro, el cierre y la miniatura
├── plantillas/musica/      Música de fondo (no se sube a Git)
├── proyectos/              Una carpeta por video (no se sube a Git)
├── src/agente_video/
│   ├── cli.py              Comandos
│   ├── orquestador.py      Orden de etapas, reanudación y aprobación
│   ├── etapas/             Una etapa por archivo
│   ├── proveedores/        Claude, Whisper y Piper; intercambiables
│   ├── render.py           Convierte las plantillas de marca en imágenes
│   ├── tiempo.py           Plan de edición y conversión de tiempos
│   ├── medios.py           Operaciones con FFmpeg
│   ├── proyecto.py         Carpeta y estado de un video
│   └── config.py           Configuración y glosario
├── ejemplos/               Material listo para grabar (video 01: ventas de una ferretería)
└── tests/
```

Cada proyecto queda así:

```
proyectos/2026-11-15-tutorial-claude-sheets/
├── crudo/               Tus grabaciones
├── trabajo/             Intermedios (se pueden borrar al terminar)
├── transcripcion.json   Lo que se dijo, con tiempos
├── edicion.json         Qué se corta y qué se acelera
├── guion.md             El guion que revisas
├── estado.json          Qué etapas están hechas
└── entrega/             Lo que se publica
```

## Pruebas

```bash
pip install -e ".[ia,marca,dev]"
```

```bash
python -m pytest
```

Las pruebas de punta a punta fabrican una grabación falsa con FFmpeg y usan proveedores de IA simulados, así que no gastan créditos ni descargan modelos.

## Hoja de ruta

- [x] **Fase 1 — Modo tutorial:** cortes, aceleración, guion, subtítulos, capítulos, descripción, voz original o sintética, música.
- [x] Intro, pantalla final y miniatura con la identidad de marca.
- [ ] Zoom automático donde se hace clic o se escribe.
- [ ] Avatar de presentador (HeyGen) en intro y cierre.
- [ ] Formato vertical para Shorts y Reels a partir del mismo proyecto.
- [ ] Conexión con el Agente de Contenido para YouTube: miniatura y kit de publicación.
- [ ] Grabación automática de demostraciones de herramientas propias con Playwright.
