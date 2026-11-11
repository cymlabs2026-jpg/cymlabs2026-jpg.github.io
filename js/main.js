/* ==========================================================================
   C&M Labs — Interacciones del sitio
   Sin dependencias. Cargado con defer, así que el DOM ya existe.
   ========================================================================== */

(function () {
  'use strict';

  const movimientoReducido = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------------------------------------------------------------
     Menú móvil
     --------------------------------------------------------------- */
  const hamburguesa = document.getElementById('hamburguesa');
  const menuMovil = document.getElementById('menu-movil');

  function cerrarMenu() {
    hamburguesa.setAttribute('aria-expanded', 'false');
    hamburguesa.setAttribute('aria-label', 'Abrir menú de navegación');
    menuMovil.classList.remove('abierto');
    document.body.classList.remove('menu-abierto');
  }

  if (hamburguesa && menuMovil) {
    hamburguesa.addEventListener('click', function () {
      const abierto = hamburguesa.getAttribute('aria-expanded') === 'true';
      if (abierto) {
        cerrarMenu();
      } else {
        hamburguesa.setAttribute('aria-expanded', 'true');
        hamburguesa.setAttribute('aria-label', 'Cerrar menú de navegación');
        menuMovil.classList.add('abierto');
        document.body.classList.add('menu-abierto');
      }
    });

    menuMovil.querySelectorAll('a').forEach(function (enlace) {
      enlace.addEventListener('click', cerrarMenu);
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && menuMovil.classList.contains('abierto')) {
        cerrarMenu();
        hamburguesa.focus();
      }
    });

    // Al pasar a escritorio el CSS oculta el menú y la hamburguesa. Si quedara abierto,
    // el bloqueo de scroll del body seguiría activo y sin ningún control para quitarlo.
    const anchoEscritorio = window.matchMedia('(min-width: 1024px)');
    anchoEscritorio.addEventListener('change', function (e) {
      if (e.matches) cerrarMenu();
    });
  }

  /* ---------------------------------------------------------------
     Barra de navegación: fondo al hacer scroll y enlace activo
     --------------------------------------------------------------- */
  const nav = document.getElementById('nav');
  const enlacesNav = Array.from(document.querySelectorAll('.nav__enlace'));
  const secciones = enlacesNav
    .map(function (enlace) {
      // Solo las anclas de esta misma página participan en el resaltado por scroll.
      // Los enlaces a otras páginas (p. ej. "/index.html#soluciones" desde una
      // subpágina) no son selectores válidos y romperían querySelector.
      const href = enlace.getAttribute('href');
      return href && href.charAt(0) === '#' ? document.querySelector(href) : null;
    })
    .filter(Boolean);

  let tickPendiente = false;

  function alHacerScroll() {
    nav.classList.toggle('nav--scrolled', window.scrollY > 20);

    // La sección activa es la última cuyo borde superior ya pasó el punto de lectura.
    const puntoLectura = window.scrollY + window.innerHeight * 0.35;
    let activa = null;

    secciones.forEach(function (seccion) {
      if (seccion.offsetTop <= puntoLectura) activa = seccion;
    });

    enlacesNav.forEach(function (enlace) {
      const coincide = activa && enlace.getAttribute('href') === '#' + activa.id;
      enlace.classList.toggle('activo', Boolean(coincide));
    });

    tickPendiente = false;
  }

  window.addEventListener('scroll', function () {
    if (!tickPendiente) {
      tickPendiente = true;
      window.requestAnimationFrame(alHacerScroll);
    }
  }, { passive: true });

  alHacerScroll();

  /* ---------------------------------------------------------------
     Pestañas Empresas / Profesionales
     --------------------------------------------------------------- */
  const pestanas = Array.from(document.querySelectorAll('[role="tab"]'));

  function activarPestana(pestana, moverFoco) {
    pestanas.forEach(function (otra) {
      const esActiva = otra === pestana;
      otra.setAttribute('aria-selected', String(esActiva));
      otra.tabIndex = esActiva ? 0 : -1;
      document.getElementById(otra.getAttribute('aria-controls')).hidden = !esActiva;
    });
    if (moverFoco) pestana.focus();
  }

  pestanas.forEach(function (pestana, indice) {
    pestana.addEventListener('click', function () { activarPestana(pestana, false); });

    pestana.addEventListener('keydown', function (e) {
      let destino = null;
      if (e.key === 'ArrowRight') destino = pestanas[(indice + 1) % pestanas.length];
      if (e.key === 'ArrowLeft') destino = pestanas[(indice - 1 + pestanas.length) % pestanas.length];
      if (e.key === 'Home') destino = pestanas[0];
      if (e.key === 'End') destino = pestanas[pestanas.length - 1];

      if (destino) {
        e.preventDefault();
        activarPestana(destino, true);
      }
    });
  });

  /* ---------------------------------------------------------------
     Tarjetas de soluciones expandibles
     --------------------------------------------------------------- */
  document.querySelectorAll('.solucion__boton').forEach(function (boton) {
    boton.addEventListener('click', function () {
      const abierto = boton.getAttribute('aria-expanded') === 'true';
      const panel = document.getElementById(boton.getAttribute('aria-controls'));
      boton.setAttribute('aria-expanded', String(!abierto));
      panel.classList.toggle('abierto', !abierto);
    });
  });

  /* ---------------------------------------------------------------
     Revelado de secciones al entrar en pantalla
     --------------------------------------------------------------- */
  const aRevelar = document.querySelectorAll('.revelar');

  if (movimientoReducido || !('IntersectionObserver' in window)) {
    aRevelar.forEach(function (el) { el.classList.add('visible'); });
  } else {
    const observador = new IntersectionObserver(function (entradas) {
      entradas.forEach(function (entrada) {
        if (entrada.isIntersecting) {
          entrada.target.classList.add('visible');
          observador.unobserve(entrada.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -60px 0px' });

    aRevelar.forEach(function (el) { observador.observe(el); });
  }

  /* ---------------------------------------------------------------
     Año actual en el pie
     --------------------------------------------------------------- */
  const anio = document.getElementById('anio');
  if (anio) anio.textContent = String(new Date().getFullYear());

  /* ---------------------------------------------------------------
     Validación y envío del formulario
     --------------------------------------------------------------- */
  const formulario = document.getElementById('formulario');
  const estado = document.getElementById('estado-formulario');
  const btnEnviar = document.getElementById('btn-enviar');

  const mensajesError = {
    nombre: 'Escribe tu nombre para saber cómo dirigirnos a ti.',
    email: 'Necesitamos un correo válido para responderte.',
    perfil: 'Indícanos si escribes como empresa o como profesional.',
    necesidad: 'Selecciona el área en la que te podemos ayudar.',
    mensaje: 'Cuéntanos brevemente tu caso.'
  };

  function validarCampo(campo) {
    const contenedorError = formulario.querySelector('[data-error-de="' + campo.name + '"]');
    const valido = campo.checkValidity();

    campo.setAttribute('aria-invalid', String(!valido));
    if (contenedorError) {
      contenedorError.textContent = valido ? '' : (mensajesError[campo.name] || 'Revisa este campo.');
    }
    return valido;
  }

  function mostrarEstado(texto, tipo) {
    estado.textContent = texto;
    estado.className = 'formulario__estado formulario__estado--' + tipo;
    estado.hidden = false;
  }

  if (formulario) {
    const camposRequeridos = Array.from(formulario.querySelectorAll('[required]'));

    // Solo validamos al salir del campo; molestar mientras se escribe es peor experiencia.
    camposRequeridos.forEach(function (campo) {
      campo.addEventListener('blur', function () { validarCampo(campo); });
      campo.addEventListener('input', function () {
        if (campo.getAttribute('aria-invalid') === 'true') validarCampo(campo);
      });
    });

    formulario.addEventListener('submit', function (e) {
      e.preventDefault();

      const invalidos = camposRequeridos.filter(function (campo) { return !validarCampo(campo); });

      if (invalidos.length > 0) {
        invalidos[0].focus();
        mostrarEstado('Revisa los campos marcados antes de enviar.', 'error');
        return;
      }

      // Asunto con perfil y necesidad, para poder triar los correos entrantes de un vistazo.
      const asunto = document.getElementById('asunto');
      if (asunto) {
        asunto.value = 'Web C&M Labs · ' + document.getElementById('perfil').value +
                       ' · ' + document.getElementById('necesidad').value;
      }

      estado.hidden = true;
      btnEnviar.dataset.cargando = 'true';
      btnEnviar.textContent = 'Enviando…';

      fetch(formulario.action, {
        method: 'POST',
        body: new FormData(formulario),
        headers: { Accept: 'application/json' }
      })
        .then(function (respuesta) {
          // Formspree responde con JSON tanto en éxito como en error.
          return respuesta.json()
            .catch(function () { return null; })
            .then(function (datos) { return { ok: respuesta.ok, datos: datos }; });
        })
        .then(function (r) {
          if (r.ok) {
            formulario.reset();
            camposRequeridos.forEach(function (campo) { campo.removeAttribute('aria-invalid'); });
            mostrarEstado('¡Gracias! Recibimos tu mensaje y te responderemos muy pronto.', 'ok');
            return;
          }

          // Ante un rechazo de Formspree (formulario sin confirmar, cuota agotada…) el detalle
          // llega en inglés: va a la consola para diagnóstico, no a la cara del visitante.
          const detalle = r.datos && r.datos.errors
            ? r.datos.errors.map(function (e) { return e.message; }).join(' | ')
            : 'Sin detalle';
          console.error('Formspree rechazó el envío:', detalle);
          throw new Error(detalle);
        })
        .catch(function () {
          mostrarEstado('No pudimos enviar el mensaje. Inténtalo de nuevo o escríbenos por WhatsApp al +57 317 546 9066.', 'error');
        })
        .finally(function () {
          delete btnEnviar.dataset.cargando;
          btnEnviar.textContent = 'Enviar mensaje';
        });
    });
  }

  /* ---------------------------------------------------------------
     Brillo que sigue al cursor en las tarjetas
     Cada tarjeta lee --mx / --my en su CSS; aquí solo se actualizan.
     --------------------------------------------------------------- */
  const SELECTOR_BRILLO = '.solucion, .valor, .publico__item, .contacto__canal, .pmv__item, ' +
                          '.formacion__lista li, .modulo, .fact, .cifra, .faq details, .diag-vista, .caso__despues';

  if (window.matchMedia('(hover: hover)').matches) {
    document.addEventListener('pointermove', function (e) {
      const tarjeta = e.target.closest && e.target.closest(SELECTOR_BRILLO);
      if (!tarjeta) return;
      const r = tarjeta.getBoundingClientRect();
      tarjeta.style.setProperty('--mx', (e.clientX - r.left) + 'px');
      tarjeta.style.setProperty('--my', (e.clientY - r.top) + 'px');
    }, { passive: true });
  }

  /* ---------------------------------------------------------------
     Cifras que cuentan hacia arriba al aparecer en pantalla
     --------------------------------------------------------------- */
  const cifras = document.querySelectorAll('[data-contar]');

  function contar(el) {
    const meta = Number(el.dataset.contar);
    const sufijo = el.dataset.sufijo || '';
    if (movimientoReducido) { el.textContent = meta + sufijo; return; }
    const inicio = performance.now();
    const duracion = 1400;
    (function paso(ahora) {
      const t = Math.min((ahora - inicio) / duracion, 1);
      const suave = 1 - Math.pow(1 - t, 3);
      el.textContent = Math.round(meta * suave) + sufijo;
      if (t < 1) requestAnimationFrame(paso);
    })(inicio);
  }

  if (cifras.length) {
    if (!('IntersectionObserver' in window)) {
      cifras.forEach(contar);
    } else {
      const obsCifras = new IntersectionObserver(function (entradas) {
        entradas.forEach(function (entrada) {
          if (entrada.isIntersecting) {
            contar(entrada.target);
            obsCifras.unobserve(entrada.target);
          }
        });
      }, { threshold: 0.6 });
      cifras.forEach(function (el) { obsCifras.observe(el); });
    }
  }

  /* ---------------------------------------------------------------
     Calculadora de pérdida por trabajo manual
     Todo se calcula en el navegador; no se envía ningún dato.
     --------------------------------------------------------------- */
  const calc = document.getElementById('calc');

  if (calc) {
    const pesos = new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 });
    const numero = new Intl.NumberFormat('es-CO', { maximumFractionDigits: 1 });
    const SEMANAS_MES = 4.33;
    const HORAS_DIA = 8;

    const personas = document.getElementById('calc-personas');
    const horas = document.getElementById('calc-horas');
    const costo = document.getElementById('calc-costo');

    function pintarBarra(rango) {
      const pct = (rango.value - rango.min) / (rango.max - rango.min) * 100;
      rango.style.setProperty('--pct', pct + '%');
    }

    function calcular() {
      const p = Number(personas.value);
      const h = Number(horas.value);
      const c = Number(costo.value);

      const horasMes = Math.round(p * h * SEMANAS_MES);
      const costoMes = horasMes * c;
      const recupera = Math.round(horasMes / 2);

      document.getElementById('calc-personas-v').textContent = p;
      document.getElementById('calc-horas-v').textContent = h + ' h';
      document.getElementById('calc-costo-v').textContent = pesos.format(c);

      document.getElementById('calc-res-horas').textContent = numero.format(horasMes);
      document.getElementById('calc-res-mes').textContent = pesos.format(costoMes);
      document.getElementById('calc-res-anio').textContent = pesos.format(costoMes * 12);
      document.getElementById('calc-res-recupera').textContent = numero.format(recupera);
      document.getElementById('calc-res-dias').textContent = numero.format(recupera / HORAS_DIA);

      [personas, horas, costo].forEach(pintarBarra);
    }

    calc.addEventListener('input', calcular);
    calcular();
  }

  /* ---------------------------------------------------------------
     Hero: red neuronal interactiva
     Capas de nodos conectadas; pulsos de luz viajan de una capa a la
     siguiente como datos que se procesan. Los nodos cerca del cursor
     se encienden y disparan pulsos nuevos.
     --------------------------------------------------------------- */
  const canvas = document.getElementById('hero-canvas');

  if (canvas) {
    const ctx = canvas.getContext('2d');
    const hero = canvas.parentElement;
    // Con "reducir movimiento" activo la red se dibuja quieta y solo responde al cursor.
    const quieto = movimientoReducido;
    let nodos = [];
    let enlaces = [];
    let salientes = [];
    let pulsos = [];
    let animacion = null;
    let ancho = 0;
    let alto = 0;
    const cursor = { x: -9999, y: -9999 };
    const RADIO_CURSOR = 130;
    const MAX_PULSOS = 90;

    function dimensionar() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const rect = canvas.getBoundingClientRect();

      ancho = rect.width;
      alto = rect.height;
      canvas.width = Math.floor(ancho * dpr);
      canvas.height = Math.floor(alto * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      // Escritorio: la red ocupa la mitad derecha. Móvil: todo el ancho, detrás del texto.
      const escritorio = ancho >= 1000;
      const capas = escritorio ? [5, 8, 11, 8, 5] : [4, 6, 7, 6, 4];
      const x0 = escritorio ? ancho * 0.5 : ancho * 0.08;
      const x1 = escritorio ? ancho - Math.max(60, ancho * 0.06) : ancho * 0.92;
      const yArriba = alto * 0.16;
      const yAbajo = alto * 0.86;

      nodos = [];
      capas.forEach(function (cantidad, c) {
        const x = x0 + (x1 - x0) * c / (capas.length - 1);
        for (let j = 0; j < cantidad; j++) {
          nodos.push({
            bx: x,
            by: yArriba + (yAbajo - yArriba) * (j + 0.5) / cantidad,
            x: x, y: 0,
            capa: c,
            fase: Math.random() * Math.PI * 2,
            brillo: 0
          });
        }
      });

      // Cada nodo se conecta con parte de la capa siguiente (no con toda: se vería saturado).
      enlaces = [];
      salientes = nodos.map(function () { return []; });
      nodos.forEach(function (a, i) {
        nodos.forEach(function (b, k) {
          if (b.capa === a.capa + 1 && Math.random() < 0.5) {
            salientes[i].push(enlaces.length);
            enlaces.push([i, k]);
          }
        });
      });
      pulsos = [];
    }

    function lanzarPulso(indiceEnlace, rapido) {
      if (pulsos.length >= MAX_PULSOS || indiceEnlace === undefined) return;
      pulsos.push({ e: indiceEnlace, p: 0, v: rapido ? 0.03 : 0.012 + Math.random() * 0.01 });
    }

    function lanzarDesde(indiceNodo, rapido) {
      const opciones = salientes[indiceNodo];
      if (opciones && opciones.length) {
        lanzarPulso(opciones[Math.floor(Math.random() * opciones.length)], rapido);
      }
    }

    hero.addEventListener('pointermove', function (e) {
      const r = canvas.getBoundingClientRect();
      cursor.x = e.clientX - r.left;
      cursor.y = e.clientY - r.top;
      if (quieto) dibujar(0);
    }, { passive: true });

    hero.addEventListener('pointerleave', function () {
      cursor.x = -9999;
      cursor.y = -9999;
      if (quieto) dibujar(0);
    });

    let ultimo = 0;

    function dibujar(tiempo) {
      ctx.clearRect(0, 0, ancho, alto);
      const t = quieto ? 0 : (tiempo || 0);

      // Flotación suave de cada nodo alrededor de su posición base.
      nodos.forEach(function (n, i) {
        n.x = n.bx + Math.cos(t / 2600 + n.fase) * 4;
        n.y = n.by + Math.sin(t / 2200 + n.fase) * 6;

        const cerca = Math.hypot(n.x - cursor.x, n.y - cursor.y) < RADIO_CURSOR;
        n.brillo = quieto ? (cerca ? 1 : 0) : n.brillo + ((cerca ? 1 : 0) - n.brillo) * 0.12;

        // El cursor "activa" nodos: disparan datos hacia la siguiente capa.
        if (!quieto && cerca && Math.random() < 0.06) lanzarDesde(i, true);
      });

      // Actividad espontánea: siempre hay datos entrando por la primera capa.
      if (!quieto && t - ultimo > 140) {
        ultimo = t;
        const entrada = nodos.filter(function (n) { return n.capa === 0; });
        const elegido = nodos.indexOf(entrada[Math.floor(Math.random() * entrada.length)]);
        lanzarDesde(elegido, false);
      }

      // Conexiones
      enlaces.forEach(function (enl) {
        const a = nodos[enl[0]];
        const b = nodos[enl[1]];
        const luz = Math.max(a.brillo, b.brillo);
        ctx.strokeStyle = 'rgba(212, 175, 55, ' + (0.14 + luz * 0.45) + ')';
        ctx.lineWidth = 0.7 + luz * 0.6;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      });

      // Pulsos de datos
      pulsos = pulsos.filter(function (p) {
        p.p += p.v;
        const enl = enlaces[p.e];
        const a = nodos[enl[0]];
        const b = nodos[enl[1]];
        const x = a.x + (b.x - a.x) * p.p;
        const y = a.y + (b.y - a.y) * p.p;

        ctx.fillStyle = 'rgba(255, 226, 140, 0.18)';
        ctx.beginPath();
        ctx.arc(x, y, 6, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = 'rgba(255, 232, 160, 0.95)';
        ctx.beginPath();
        ctx.arc(x, y, 1.9, 0, Math.PI * 2);
        ctx.fill();

        if (p.p >= 1) {
          b.brillo = Math.min(1, b.brillo + 0.5);
          if (Math.random() < 0.75) lanzarDesde(enl[1], false);
          return false;
        }
        return true;
      });

      // Nodos
      nodos.forEach(function (n) {
        const r = 3 + n.brillo * 2.6;
        if (n.brillo > 0.05) {
          ctx.fillStyle = 'rgba(212, 175, 55, ' + n.brillo * 0.16 + ')';
          ctx.beginPath();
          ctx.arc(n.x, n.y, r + 10, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.fillStyle = n.brillo > 0.3 ? '#FFE28C' : 'rgba(212, 175, 55, 0.8)';
        ctx.beginPath();
        ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
        ctx.fill();
      });

      animacion = quieto ? null : requestAnimationFrame(dibujar);
    }

    function iniciar() {
      if (quieto) dibujar(0);
      else if (animacion === null) animacion = requestAnimationFrame(dibujar);
    }

    function detener() {
      if (animacion !== null) {
        cancelAnimationFrame(animacion);
        animacion = null;
      }
    }

    dimensionar();
    iniciar();

    let temporizadorResize;
    window.addEventListener('resize', function () {
      clearTimeout(temporizadorResize);
      temporizadorResize = setTimeout(function () { dimensionar(); if (quieto) dibujar(0); }, 200);
    });

    // No gastar batería animando algo que nadie está viendo. Hacen falta las dos
    // condiciones a la vez: volver a la pestaña no debe reanudar la animación si
    // el hero quedó fuera de pantalla.
    let heroALaVista = true;
    let pestanaALaVista = !document.hidden;

    function revisarAnimacion() {
      if (heroALaVista && pestanaALaVista) iniciar();
      else detener();
    }

    document.addEventListener('visibilitychange', function () {
      pestanaALaVista = !document.hidden;
      revisarAnimacion();
    });

    const heroObserver = new IntersectionObserver(function (entradas) {
      heroALaVista = entradas[0].isIntersecting;
      revisarAnimacion();
    }, { threshold: 0 });

    heroObserver.observe(canvas);
  }

})();
