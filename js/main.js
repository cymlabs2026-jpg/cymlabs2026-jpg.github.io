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
    .map(function (enlace) { return document.querySelector(enlace.getAttribute('href')); })
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
     Fondo animado del hero: red de nodos y circuitos
     Refuerza el concepto del isotipo (personas, datos y tecnología conectados).
     --------------------------------------------------------------- */
  const canvas = document.getElementById('hero-canvas');

  if (canvas && !movimientoReducido) {
    const ctx = canvas.getContext('2d');
    let nodos = [];
    let animacion = null;
    let ancho = 0;
    let alto = 0;

    const DISTANCIA_ENLACE = 150;

    function dimensionar() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const rect = canvas.getBoundingClientRect();

      ancho = rect.width;
      alto = rect.height;
      canvas.width = Math.floor(ancho * dpr);
      canvas.height = Math.floor(alto * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      // Densidad proporcional al área, con tope para no castigar equipos modestos.
      const cantidad = Math.min(Math.round((ancho * alto) / 16000), 90);

      nodos = Array.from({ length: cantidad }, function () {
        return {
          x: Math.random() * ancho,
          y: Math.random() * alto,
          vx: (Math.random() - 0.5) * 0.35,
          vy: (Math.random() - 0.5) * 0.35,
          r: Math.random() * 1.6 + 1
        };
      });
    }

    function dibujar() {
      ctx.clearRect(0, 0, ancho, alto);

      nodos.forEach(function (nodo) {
        nodo.x += nodo.vx;
        nodo.y += nodo.vy;

        if (nodo.x < 0 || nodo.x > ancho) nodo.vx *= -1;
        if (nodo.y < 0 || nodo.y > alto) nodo.vy *= -1;
      });

      // Enlaces entre nodos cercanos: la opacidad decae con la distancia.
      for (let i = 0; i < nodos.length; i++) {
        for (let j = i + 1; j < nodos.length; j++) {
          const dx = nodos[i].x - nodos[j].x;
          const dy = nodos[i].y - nodos[j].y;
          const distancia = Math.hypot(dx, dy);

          if (distancia < DISTANCIA_ENLACE) {
            ctx.strokeStyle = 'rgba(37, 99, 235, ' + (1 - distancia / DISTANCIA_ENLACE) * 0.35 + ')';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(nodos[i].x, nodos[i].y);
            ctx.lineTo(nodos[j].x, nodos[j].y);
            ctx.stroke();
          }
        }
      }

      ctx.fillStyle = 'rgba(6, 182, 212, 0.7)';
      nodos.forEach(function (nodo) {
        ctx.beginPath();
        ctx.arc(nodo.x, nodo.y, nodo.r, 0, Math.PI * 2);
        ctx.fill();
      });

      animacion = requestAnimationFrame(dibujar);
    }

    function iniciar() {
      if (animacion === null) dibujar();
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
      temporizadorResize = setTimeout(dimensionar, 200);
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
