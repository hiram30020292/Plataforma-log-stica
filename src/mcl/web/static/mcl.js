/* MCL · comodidades del navegador.
   Toda la lógica vive en Python: aquí solo se piden al servidor trozos de página ya
   armados (resultados del catálogo, cotización) y se evitan recargas. Sin este archivo
   la app funciona igual, con botones para enviar los formularios. */
'use strict';

document.documentElement.classList.add('js');

// Los avisos se ocultan solos.
const aviso = document.querySelector('.toast');
if (aviso) setTimeout(() => { aviso.hidden = true; }, 3200);

// Formularios "en vivo": al cambiar un campo se pide al servidor el trozo de página
// actualizado (data-vivo) y se coloca en su destino (data-vivo-destino).
for (const form of document.querySelectorAll('form[data-vivo]')) {
  const destino = document.querySelector(form.dataset.vivoDestino);
  const enviar = form.querySelector('[data-bloqueable]');
  let espera;
  let peticion;
  const actualizar = () => {
    clearTimeout(espera);
    espera = setTimeout(async () => {
      const params = new URLSearchParams();
      for (const [clave, valor] of new FormData(form)) if (valor !== '') params.append(clave, valor);
      peticion?.abort();
      peticion = new AbortController();
      try {
        const r = await fetch(`${form.dataset.vivo}?${params}`, { signal: peticion.signal });
        if (!r.ok) return;
        destino.innerHTML = await r.text();
        if ('vivoHistorial' in form.dataset) history.replaceState(null, '', `${form.action}?${params}`);
        if (enviar) enviar.disabled = destino.querySelector('[data-bloquea]') !== null;
      } catch (error) {
        if (error.name !== 'AbortError') throw error;
      }
    }, 180);
  };
  form.addEventListener('input', actualizar);
  form.addEventListener('change', actualizar);
}

// Selectores e interruptores que envían su formulario al cambiar.
document.addEventListener('change', (e) => {
  if (e.target.matches('[data-autoenvio]')) e.target.form.requestSubmit();
});

// Confirmación antes de acciones delicadas, y posición de la página tras enviar.
document.addEventListener('submit', (e) => {
  const form = e.target;
  if (form.dataset.confirmar && !confirm(form.dataset.confirmar)) {
    e.preventDefault();
    return;
  }
  if ('conservarScroll' in form.dataset) {
    try {
      sessionStorage.setItem('mcl:scroll', JSON.stringify({ ruta: location.pathname, y: scrollY }));
    } catch { /* sin almacenamiento: la página vuelve arriba */ }
  }
});

try {
  const guardado = JSON.parse(sessionStorage.getItem('mcl:scroll') || 'null');
  sessionStorage.removeItem('mcl:scroll');
  if (guardado && guardado.ruta === location.pathname) scrollTo(0, guardado.y);
} catch { /* sin almacenamiento */ }

// Escape cierra el menú lateral.
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && location.hash === '#menu') location.hash = '';
});
