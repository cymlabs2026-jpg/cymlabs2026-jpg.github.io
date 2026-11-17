# Voz propia de C&M Labs

Una voz sintética entrenada con **tu propia voz**, para que el agente narre cualquier guion sin que grabes cada video. El modelo es tuyo: sin suscripciones ni licencias de terceros sobre la voz.

Se parte de una voz base en español latino (`es_MX/ald/medium`, de dominio público) y se **afina** con tus grabaciones. Afinar necesita mucho menos audio que entrenar desde cero.

## Resumen del proceso

| Paso | Dónde | Tiempo |
|---|---|---|
| 1. Grabar las frases | Tu computador, en el navegador | 2 o 3 sesiones de 30 a 40 minutos |
| 2. Revisar y preparar | Tu computador o la nube | 10 minutos |
| 3. Entrenar | Una máquina con GPU (alquilada) | Varias horas |
| 4. Exportar y usar | La misma máquina, luego el agente | 10 minutos |

## 1. Grabar las frases

Abre `grabador.html` en **Chrome** o **Edge**. Haz doble clic en el archivo; no necesita internet.

- **Las frases:** son 218, en `frases.txt`, unos 17 minutos de lectura neta. Mezclan vocabulario de C&M Labs, frases cotidianas, preguntas y exclamaciones, y cifras escritas en palabras.
- **El atajo:** <kbd>Espacio</kbd> empieza a grabar y lo vuelves a pulsar para detener. Con <kbd>E</kbd> escuchas la toma. Si una toma sale bien, el grabador pasa solo a la siguiente frase. Si te equivocas, vuelve a grabar y la toma anterior se reemplaza.
- **Avisos:** el grabador te avisa si una toma **saturó**, quedó **muy baja** o fue **muy corta**.
- **Copia de seguridad:** el avance se guarda en el navegador. Al final de cada sesión pulsa **Descargar grabaciones (.zip)**.

**Para que la voz quede bien:**
- Graba siempre en **el mismo lugar**, con **el mismo micrófono** y a **la misma distancia**: un palmo de la boca. El modelo aprende también el sonido de la sala.
- Elige un cuarto pequeño con ropa o cortinas; evita los cuartos vacíos con eco. Funciona mejor un micrófono USB o de solapa que el del portátil.
- Lee con tu tono natural de narrador, el mismo que quieres que tenga la voz final.
- Di **«Claude» como «Clod»** y **«C&M Labs» como «ce y eme labs»**. El texto que va al entrenamiento ya está escrito así (diccionario `[pronunciacion]` de `config/glosario.toml`), y el agente usa el mismo diccionario al narrar.
- El grabador desactiva la cancelación de ruido y el volumen automático del navegador. El modelo debe aprender tu voz real, no el procesamiento del micrófono.

Si cambias `frases.txt`, vuelve a generar el grabador:

```bash
python construir_grabador.py
```

## 2. Revisar y preparar

```bash
python preparar_dataset.py voz_propia_2026-11-20.zip voz_propia_2026-11-22.zip --salida dataset
```

Si grabaste en varias sesiones, pasa todos los `.zip`. Para cada grabación, el script:

- revisa la duración (1 a 15 s), la saturación y el volumen;
- **la transcribe con Whisper y la compara con la frase**: si leíste otra cosa o te comiste palabras, la rechaza;
- normaliza las aprobadas (mono, 22.050 Hz, volumen parejo).

En `dataset/revision.md` queda la lista de frases rechazadas y el motivo, para volver a grabarlas.

**¿Cuánto audio hace falta?**
- **Mínimo para afinar:** unos 20 minutos aprobados.
- **Calidad muy buena:** de 45 a 60 minutos.
- Si te quedas corto, agrega frases a `frases.txt` y graba otro lote.

## 3. Entrenar (en una máquina con GPU)

Entrenar sin GPU tardaría semanas. Alquila una por horas:
- **Google Colab:** con una GPU T4 o mejor.
- **RunPod o Vast.ai:** con una RTX 3090 o 4090.

En ambos casos el costo suele ser de pocos dólares en total. Los comandos de abajo son para Linux con una GPU NVIDIA; en Colab, antepón `!` a cada línea.

> **Importante:** el paquete `piper-tts` publicado en PyPI no trae el código fuente de un componente que necesita el entrenamiento (`monotonic_align/core.pyx`). Por eso hay que entrenar desde el **repositorio oficial**, no solo con `pip install`. Si algún comando falla, consulta `TRAINING.md` en ese repositorio: la herramienta cambia entre versiones.

**3.1. Instala Piper desde el repositorio oficial**

```bash
git clone https://github.com/OHF-Voice/piper1-gpl.git
```

```bash
cd piper1-gpl && python3 -m venv .venv && source .venv/bin/activate
```

```bash
python3 -m pip install -e ".[train]"
```

```bash
./build_monotonic_align.sh
```

**3.2. Descarga la voz base** (español latino, ~850 MB)

```bash
wget -O base.ckpt "https://huggingface.co/datasets/rhasspy/piper-checkpoints/resolve/main/es/es_MX/ald/medium/epoch%3D9999-step%3D1753600.ckpt"
```

**3.3. Sube tu carpeta `dataset/`** (la del paso 2) a la máquina y entrena:

```bash
python3 -m piper.train fit \
  --data.voice_name "cm_labs" \
  --data.csv_path dataset/metadata.csv \
  --data.audio_dir dataset/wavs \
  --model.sample_rate 22050 \
  --data.espeak_voice "es-419" \
  --data.cache_dir cache/ \
  --data.config_path cm_labs.onnx.json \
  --data.batch_size 16 \
  --model.warmstart_ckpt base.ckpt \
  --trainer.max_epochs 1500
```

Lo que conviene saber de este comando:
- **`--model.warmstart_ckpt`** copia los pesos de la voz base sin exigir que el checkpoint sea de la misma versión de Piper. Sirve porque la voz base se entrenó con una versión anterior.
- **`--data.batch_size 16`:** si la GPU se queda sin memoria, bájalo a 8.
- **Cuándo parar:** el entrenamiento guarda checkpoints en `lightning_logs/version_0/checkpoints/`. Escucha el progreso cada 200 a 300 épocas y detenlo (<kbd>Ctrl</kbd>+<kbd>C</kbd>) cuando suene bien. El propio Piper recomienda elegir el checkpoint final **escuchando**, no solo por las métricas.

**3.4. Exporta el modelo**

```bash
python3 -m piper.train.export_onnx --checkpoint "lightning_logs/version_0/checkpoints/ELIGE_UNO.ckpt" --output-file cm_labs.onnx
```

Descarga `cm_labs.onnx` y `cm_labs.onnx.json`, que deben quedar juntos.

## 4. Usarla en el agente

En `config/canal.toml`:

```toml
[voz]
modo = "sintetica"
modelo_piper = "ruta/a/cm_labs.onnx"
velocidad = 1.0
```

Desde ahí, cualquier video del agente se narra con tu voz a partir de `guion.md`.

## Antes de empezar

- **Consentimiento:** entrena solo con la voz de quien dio su permiso. Aquí es la tuya. No uses estas herramientas para imitar la voz de otra persona.
- **Licencia de Piper:** es **GPL-3**. Usarla para producir tus videos no tiene problema. Si C&M Labs **distribuye** el agente a clientes, la GPL aplica a esa distribución. El modelo de voz que entrenes es tuyo.
- **Transparencia:** al publicar videos narrados con la voz sintética, es buena práctica indicarlo en la descripción, aunque suene como tú.

## Qué está probado

**Probado aquí:**
- El grabador, en Chrome con un micrófono simulado: graba, guarda, avisa de saturación y volumen, retoma tras recargar y exporta el ZIP en el formato de Piper.
- La revisión con Whisper: aprueba las tomas buenas y rechaza las mal leídas, las bajas y las saturadas.
- Los nombres de los parámetros de entrenamiento y exportación, leídos del código de `piper-tts` 1.8.

**Sin probar aquí:**
- El **entrenamiento** y la **exportación**: requieren GPU, que este entorno no tiene.
- La compatibilidad del checkpoint base con `warmstart_ckpt`. El primer entrenamiento en la máquina con GPU será la prueba real.
