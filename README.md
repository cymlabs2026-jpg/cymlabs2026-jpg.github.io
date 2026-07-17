# Sitio web C&M Labs

Landing corporativa de C&M Labs. Sitio estático en HTML, CSS y JavaScript, sin dependencias ni proceso de compilación: los archivos que ves son exactamente los que se publican.

## Ver el sitio en tu computadora

Abre `index.html` haciendo doble clic. Eso basta para revisar todo.

Si quieres servirlo por HTTP (necesario solo si algún navegador bloquea archivos locales), con Python:

```bash
python -m http.server 8000
```

Luego entra a `http://localhost:8000`.

## Estructura

```
index.html          Toda la página: navegación, hero, secciones y pie
css/styles.css      Sistema de diseño y estilos
js/main.js          Menú, pestañas, acordeones, animaciones y formulario
assets/logo.svg     Logotipo completo (isotipo + wordmark)
assets/favicon.svg  Icono de la pestaña del navegador
robots.txt          Indexación para buscadores
sitemap.xml         Mapa del sitio para SEO
.nojekyll           Evita que GitHub Pages procese el sitio con Jekyll
```

## Datos de contacto configurados

| Qué | Valor |
|---|---|
| URL pública | `https://cymlabs2026-jpg.github.io/` |
| WhatsApp | +57 317 546 9066 |
| Correo | c.y.m.labs2026@gmail.com |
| Calendly | `https://calendly.com/c-y-m-labs2026/30min` |
| Formspree | `https://formspree.io/f/xlgqjjpp` |
| Ubicación | Palmira, Valle del Cauca, Colombia |

## Pendiente

| Qué | Dónde | Estado |
|---|---|---|
| Imagen para redes | `assets/og-image.png` | **no existe todavía** |
| Redes sociales | pie de página | quitadas hasta tener perfiles |

### Añadir las redes sociales

Se quitaron del pie porque los perfiles aún no existen y apuntaban a enlaces rotos. El estilo (`.pie__redes`) sigue en `css/styles.css`, así que basta con reponer el marcado.

En `index.html`, dentro de `<div class="pie__marca">`, hay un comentario que señala el lugar exacto. Reemplázalo por esto, con tus URLs reales:

```html
<div class="pie__redes">
  <a href="https://www.linkedin.com/company/TU-PAGINA" target="_blank" rel="noopener" aria-label="C&amp;M Labs en LinkedIn">
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M4.98 3.5A2.5 2.5 0 1 1 0 3.5a2.5 2.5 0 0 1 4.98 0zM.5 8.5h4V24h-4V8.5zm7.5 0h3.8v2.1h.06c.53-1 1.83-2.06 3.77-2.06 4.03 0 4.77 2.65 4.77 6.1V24h-4v-6.9c0-1.65-.03-3.77-2.3-3.77-2.3 0-2.65 1.8-2.65 3.65V24H8V8.5z"/></svg>
  </a>
</div>
```

Añade un `<a>` por cada red. El `aria-label` es obligatorio: el enlace solo contiene un icono, y sin él un lector de pantalla no puede anunciarlo.

### Imagen de vista previa (og-image.png)

Las etiquetas Open Graph de `index.html` apuntan a `assets/og-image.png`, pero ese archivo aún no existe. Hasta que lo crees, al compartir el enlace en WhatsApp o LinkedIn no aparecerá la miniatura.

Debe ser un PNG de **1200 × 630 px** con el logo sobre el fondo azul corporativo y el eslogan. Se puede hacer en Canva o Figma en unos minutos.

### Formulario de contacto (Formspree)

Ya está conectado al endpoint `https://formspree.io/f/xlgqjjpp`. El plan gratuito cubre **50 envíos al mes**.

No se usa la librería `@formspree/ajax`: el envío por AJAX está implementado de forma nativa en `js/main.js` con `fetch`, para no añadir dependencias externas y mantener los mensajes en español. El comportamiento es equivalente.

Campos especiales de Formspree que ya están en uso:

- **`_gotcha`** — campo trampa oculto. Los bots lo rellenan, las personas no; Formspree descarta esos envíos.
- **`_subject`** — asunto del correo. `main.js` lo reescribe antes de enviar con el formato `Web C&M Labs · <perfil> · <necesidad>`, para poder priorizar los mensajes desde la bandeja sin abrirlos.
- **`email`** — al llamarse así, Formspree lo usa como *reply-to*: puedes responder al correo directamente y le llega al cliente.

Si Formspree rechaza un envío (formulario sin confirmar, cuota agotada), el visitante ve un mensaje en español que lo deriva a WhatsApp, y el motivo real queda registrado en la consola del navegador.

### Número de WhatsApp

Ya está configurado: **+57 317 546 9066** (Colombia), presente en el botón flotante, la tarjeta de contacto y el pie.

Si alguna vez cambia, ten en cuenta que los enlaces `wa.me` llevan el número con código de país y **sin** el 0 de marcación, sin signos ni espacios: el `057 3175469066` se escribe `573175469066`.

## Cambiar la identidad visual

Todos los colores, tipografías y espaciados están declarados como variables CSS al inicio de `css/styles.css`, dentro del bloque `:root`. Cambiar un valor ahí se propaga a todo el sitio.

```css
--azul-corporativo: #0F172A;
--azul-tecnologico: #2563EB;
--cian-ia:          #06B6D4;
```

## Editar contenido

Todo el texto está en `index.html`, en español y sin plantillas de por medio: busca la frase que quieres cambiar y edítala directamente.

Para agregar un servicio a una tarjeta de Soluciones, añade un `<li>` dentro de la lista correspondiente (`sol-ia`, `sol-auto`, `sol-bi`, `sol-dev`, `sol-prod`, `sol-form`).

Para agregar un sector, recuerda que la marquesina duplica la lista completa para que el bucle sea continuo: el nuevo sector debe añadirse **en las dos mitades**, en la misma posición.

## Publicar en GitHub Pages

El repositorio debe llamarse exactamente **`cymlabs2026-jpg.github.io`**. Ese nombre es el que hace que GitHub publique el sitio en la raíz del dominio, sin subcarpeta.

### 1. Crear el repositorio (en la web de GitHub)

En [github.com/new](https://github.com/new): nombre `cymlabs2026-jpg.github.io`, visibilidad **Public** (Pages es de pago en repos privados). **No** marques ninguna casilla de inicialización (README, .gitignore, licencia): el proyecto ya tiene su propio contenido y esas casillas crearían un conflicto al subir.

### 2. Subir el código

```bash
git remote add origin https://github.com/cymlabs2026-jpg/cymlabs2026-jpg.github.io.git
git push -u origin main
```

Git pedirá usuario y contraseña. La contraseña **no** es la de tu cuenta: es un *Personal Access Token* que se genera en Settings → Developer settings → Personal access tokens → Tokens (classic), con el permiso `repo` marcado.

### 3. Activar Pages

En el repositorio: **Settings → Pages → Source: Deploy from a branch → Branch: `main` / `(root)` → Save**.

En dos o tres minutos el sitio estará en **https://cymlabs2026-jpg.github.io/**

### Actualizar el sitio más adelante

```bash
git add .
git commit -m "Describe aquí el cambio"
git push
```

Pages se actualiza solo en un par de minutos.

### Usar un dominio propio

Crea un archivo `CNAME` en la raíz con el dominio dentro (por ejemplo `cmlabs.com`), configúralo en Settings → Pages, y reemplaza `cymlabs2026-jpg.github.io` por el dominio nuevo en `index.html` (etiquetas meta y JSON-LD), `robots.txt` y `sitemap.xml`.

## Notas técnicas

- Las tipografías (Space Grotesk, Manrope, Sora) se cargan desde Google Fonts. Es la única dependencia externa.
- La animación del hero se detiene sola cuando la pestaña no está visible o el hero sale de pantalla.
- Todo el movimiento se desactiva si el sistema del visitante pide movimiento reducido.
- El sitio funciona sin JavaScript: se pierden las animaciones y los acordeones, pero el contenido sigue siendo accesible.
