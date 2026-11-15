# Video 01 · Analiza las ventas de tu negocio con Claude

**Título recomendado:** Analiza las ventas de tu negocio con Claude en 15 minutos (sin fórmulas)

**Alternativas:**
- Del Excel al tablero: Claude hace el análisis que nadie tiene tiempo de hacer
- Claude Sheets y Data: el caso de una ferretería, paso a paso

**Duración final esperada:** de 7 a 8 minutos (la grabación cruda puede durar 20; el agente corta y acelera).

**Miniatura:** `miniatura.png` de esta carpeta (texto «¿Por qué cayó 28 %?» con el gráfico de Palmira Norte). Para regenerarla: `python generar_miniatura.py`.

**Llamado a la acción:** formación Claude Empresarial → https://cymlabs2026-jpg.github.io/formacion/claude-empresarial.html

---

## Antes de grabar

- [ ] Confirma que tu cuenta de Claude tiene **hojas de cálculo** y **paneles de datos** en Artefactos (según el video de referencia, plan Pro; algunas en beta).
- [ ] Ten abierto `ventas_ferreteria.xlsx` (Ferretería El Roble, ficticia: 3 sedes, noviembre 2025 – octubre 2026).
- [ ] Ten a mano `clave_de_respuestas.md` en otra pantalla o impresa: no se ve en el video.
- [ ] Pantalla en 1080p, zoom del navegador al 125 %, notificaciones apagadas, pestañas personales cerradas.
- [ ] Micrófono a un palmo de la boca; graba 10 segundos de prueba y escúchalos.
- [ ] Graba **una toma por bloque** con el nombre indicado (`01_gancho.mp4`, `02_contexto.mp4`, …). El agente las une en orden alfabético.

**Mientras grabas:**
- Lee cada prompt **en voz alta** mientras lo pegas: así queda en los subtítulos y el agente lo recupera completo para la descripción.
- **No cortes las esperas** mientras Claude trabaja; puedes quedarte callado. El agente las acelera solo.
- Si te equivocas, haz una pausa de 3 segundos y repite la frase. Luego borras la versión mala en `guion.md`.

---

## Tomas

### 01_gancho (20 s) — grábala al final, con el panel terminado

**Pantalla:** el panel de datos terminado; haz scroll despacio hasta la alerta de Palmira Norte.

**Idea a transmitir:**
> Este Excel tiene un año de ventas de una ferretería y nadie lo había mirado. En quince minutos, Claude lo convirtió en esto: qué producto deja plata, qué sede se está cayendo, y qué hacer el mes que viene. Te enseño a hacerlo con tus propios datos.

### 02_contexto (40 s)

**Pantalla:** el Excel crudo; baja unas cuantas filas.

**Idea a transmitir:**
- El caso: Ferretería El Roble, tres sedes (Palmira Centro, Palmira Norte y Candelaria), doce meses, más de 3.600 ventas.
- Es el Excel típico: todo está ahí, pero nadie tiene tiempo de analizarlo.
- Qué necesitas: Claude con plan Pro. Los tres prompts están en la descripción, listos para copiar.
- Los datos son ficticios. Con datos reales de tu empresa, cuidado con la información sensible (lo retomamos al final).

### 03_paso1_entender (1,5 min)

**Pantalla:** nuevo chat en Claude → adjuntas el Excel → pegas el prompt.

**Prompt 1:**
```
Te adjunto las ventas de los últimos 12 meses de una ferretería con tres sedes. Antes de analizar nada, dime qué columnas hay, qué problemas de calidad encuentras (vacíos, duplicados, formatos raros) y qué cinco preguntas de negocio podemos responder con estos datos.
```

**Idea a transmitir:**
- Por qué empezar así: si los datos están sucios, el análisis miente.
- Comenta los errores que encuentre. Hay 7 sembrados (ver la clave): sedes mal escritas, costos vacíos, fechas como texto, devoluciones negativas, una venta de 1.000 galones de thinner, totales que no cuadran y facturas duplicadas.
- Si se le escapa alguno, pregúntale por él en vivo: «¿revisaste si hay cantidades fuera de lo normal?». Mostrar que hay que verificar es parte del mensaje.
- Pídele que limpie: «Corrige esos problemas y explícame qué hiciste con cada uno».

### 04_paso2_hoja (2 min)

**Pantalla:** en el mismo chat → prompt 2 → la hoja creándose en el panel lateral.

**Prompt 2:**
```
Con los datos ya limpios crea una hoja de cálculo con tres pestañas: "Resumen" con ventas por mes y por sede; "Rentabilidad" con ventas, costo y margen por categoría; y "Proyección" con los próximos tres meses. Pon los supuestos de crecimiento en celdas que yo pueda cambiar.
```

**Idea a transmitir:**
- Si Claude hace preguntas antes de crear la hoja, contéstalas en voz alta: es bueno que pregunte.
- Recorre las tres pestañas. Compara una cifra con la clave (por ejemplo, el margen de herramientas eléctricas, cercano al 12 %).
- **Momento clave:** cambia un supuesto de crecimiento en vivo y muestra cómo se recalcula la proyección.
- Si la proyección de noviembre y diciembre no sube, pregúntale por la estacionalidad (diciembre es el mejor mes del año).
- Menciona que se puede exportar a Excel o Google Sheets.

### 05_llamado (20 s)

**Pantalla:** la hoja terminada.

**Idea a transmitir:**
> Esto que acabas de ver es lo que enseñamos en Claude Empresarial: que tu equipo deje de copiar y pegar, y use la IA para analizar y decidir. El enlace está en la descripción.

### 06_paso3_panel (2 min)

**Pantalla:** prompt 3 → el panel de datos.

**Prompt 3:**
```
Con la hoja anterior arma un panel para el gerente: ventas por mes, margen por categoría, comparación entre sedes y tres alertas sobre lo que requiere atención. Que se lea bien en el celular.
```

**Idea a transmitir:** recorre el panel y busca las historias de la clave.
1. Palmira Norte cae cerca de un 28 % desde julio. Inventa la razón en voz alta como gerente: «abrió un competidor al lado, ¿qué hago?».
2. Candelaria casi duplica sus ventas en el año.
3. Construcción y herramientas eléctricas son el 44 % de las ventas pero solo el 24 % del margen.
4. Diciembre es el mejor mes y enero el peor.

Si el panel no muestra alguna, pídesela: «agrega una alerta sobre la tendencia de cada sede».

### 07_cuidados (40 s)

**Pantalla:** el panel.

**Idea a transmitir:**
- El panel **no se actualiza solo**: si conectas Google Sheets, se refresca cuando lo abres o le das actualizar.
- Con datos reales: no subas cédulas, datos de clientes ni información confidencial sin revisar la política de tu empresa y el plan de Claude que usas.
- Claude puede equivocarse: verifica dos o tres cifras clave antes de tomar decisiones.

### 08_cierre (30 s)

**Pantalla:** el panel visto en el celular (o la vista móvil en el navegador).

**Idea a transmitir:**
- Resumen: de un Excel que nadie miraba a tres decisiones concretas, en una tarde.
- Pregunta para comentarios: «¿qué harías tú con Palmira Norte?».
- Siguiente video: «Tu primer Proyecto en Claude: un asistente que conoce tu empresa».

---

## Después de grabar

Crea el proyecto y copia las tomas en su carpeta `crudo/`. Copia también `foco.png` (el gráfico de la caída de Palmira Norte) en la carpeta del proyecto: el agente lo usa como foco de la miniatura.

```bash
agente-video nuevo "Analiza las ventas con Claude"
```

Procésalo (el agente se detiene cuando el guion está listo para revisar):

```bash
agente-video procesar proyectos/2026-11-15-analiza-las-ventas-con-claude
```

Revisa `guion.md`: confirma que los tres prompts quedaron completos y que los capítulos coinciden con las tomas. En la sección «Miniatura» deja `¿Por qué *cayó 28 %*?`. Luego aprueba:

```bash
agente-video aprobar proyectos/2026-11-15-analiza-las-ventas-con-claude
```

La fecha del nombre de la carpeta será la del día en que la crees.
