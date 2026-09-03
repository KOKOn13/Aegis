/* Acopio — shared auth + theme + helpers */

// ── Theme ──────────────────────────────────────────────────────────────────
const ROOT = document.documentElement;
(function initTheme() {
  const t = localStorage.getItem('acopio_theme');
  if (t === 'light') ROOT.setAttribute('data-theme', 'light');
})();

const _SUN  = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><line x1="12" y1="2" x2="12" y2="4"/><line x1="12" y1="20" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="6.34" y2="6.34"/><line x1="17.66" y1="17.66" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="4" y2="12"/><line x1="20" y1="12" x2="22" y2="12"/><line x1="4.93" y1="19.07" x2="6.34" y2="17.66"/><line x1="17.66" y1="6.34" x2="19.07" y2="4.93"/></svg>`;
const _MOON = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`;

function toggleTheme() {
  const isLight = ROOT.getAttribute('data-theme') === 'light';
  if (isLight) { ROOT.removeAttribute('data-theme'); localStorage.setItem('acopio_theme','dark'); }
  else { ROOT.setAttribute('data-theme','light'); localStorage.setItem('acopio_theme','light'); }
  syncThemeIcons();
}
function syncThemeIcons() {
  const isLight = ROOT.getAttribute('data-theme') === 'light';
  document.querySelectorAll('.theme-icon').forEach(el => el.innerHTML = isLight ? _MOON : _SUN);
}
syncThemeIcons();

// ── Auth ───────────────────────────────────────────────────────────────────
const API = window.location.origin + '/api';
const ROUTES = {
  coordinador_general: '/dashboard_coordinador.html',
  encargado_centro: '/dashboard_encargado.html',
  voluntario: '/dashboard_voluntario.html',
  institucion_receptora: '/dashboard_institucion.html',
  lider_campana: '/dashboard_lider.html',
};

function getUser() {
  try { return JSON.parse(localStorage.getItem('acopio_user')); } catch { return null; }
}
function logout() {
  localStorage.removeItem('acopio_user');
  window.location.href = '/';
}
function requireRole(...roles) {
  const user = getUser();
  if (!user) return (window.location.href = '/');
  if (roles.length && !roles.includes(user.rol)) return (window.location.href = ROUTES[user.rol] || '/');
  return user;
}

// ── Format helpers ─────────────────────────────────────────────────────────
function fmt(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString('es-MX',{dateStyle:'short',timeStyle:'short'});
}
function fmtNum(n) { return Number(n).toLocaleString('es-MX'); }

// ── Badge helpers ──────────────────────────────────────────────────────────
const TIPO_MAP = {
  recepcion: ['badge-ok','Recepción'],
  entrega: ['badge-info','Entrega'],
  merma: ['badge-err','Merma'],
  transferencia_salida: ['badge-warn','Transf. Salida'],
  transferencia_entrada: ['badge-warn','Transf. Entrada'],
  ajuste: ['badge-neu','Ajuste'],
};
function tipoBadge(tipo) {
  const [cls,label] = TIPO_MAP[tipo] || ['badge-neu', tipo];
  return `<span class="badge ${cls}">${label}</span>`;
}
function tipoSigno(tipo) {
  return ['recepcion','transferencia_entrada','ajuste'].includes(tipo) ? '+' : '-';
}
function tipoColor(tipo) {
  const signo = tipoSigno(tipo);
  return signo === '+' ? 't-ok' : 't-err';
}

// ── Toast ──────────────────────────────────────────────────────────────────
function toast(msg, type = 'ok') {
  const el = document.createElement('div');
  el.style.cssText = `
    position:fixed; bottom:24px; right:24px; z-index:200;
    padding:12px 20px; border-radius:10px; font-size:13px; font-weight:500;
    backdrop-filter:blur(20px); border:1px solid var(--b);
    background:var(--s3); color:var(--t1);
    box-shadow:0 8px 32px rgba(0,0,0,.3);
    animation:slideIn .2s ease;
  `;
  el.textContent = msg;
  if (type === 'err') el.style.color = 'var(--err)';
  if (type === 'ok') el.style.color = 'var(--ok)';
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3200);
}

// Inject keyframe
const _style = document.createElement('style');
_style.textContent = `@keyframes slideIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}`;
document.head.appendChild(_style);

// ── Autocomplete de artículos ───────────────────────────────────────────────
/**
 * Monta un campo de autocompletado que busca artículos en /api/articulos/buscar.
 *
 * @param {string} containerId  ID del elemento donde se insertará el componente
 * @param {function} onChange   Callback llamado con el artículo seleccionado { id, nombre, categoria, unidad }
 *                              o null cuando se limpia la selección
 * @returns {{ getValue, reset }}  Helpers para leer / limpiar externamente
 */
function mountArticuloSearch(containerId, onChange) {
  const wrap = document.getElementById(containerId);
  if (!wrap) return { getValue: () => null, reset: () => {} };

  wrap.innerHTML = `
    <div class="ac-wrap">
      <input
        type="text"
        class="ac-input"
        placeholder="Buscar artículo…"
        autocomplete="off"
      >
      <input type="hidden" class="ac-id-input">
      <div class="ac-dropdown" style="display:none"></div>
      <div class="ac-badge-area"></div>
    </div>`;

  const textInput = wrap.querySelector('.ac-input');
  const idInput   = wrap.querySelector('.ac-id-input');
  const dropdown  = wrap.querySelector('.ac-dropdown');
  const badgeArea = wrap.querySelector('.ac-badge-area');

  let selected = null;
  let debounce = null;
  let focusedIdx = -1;
  let lastResults = [];

  function selectArticulo(art) {
    selected = art;
    idInput.value = art.id;
    textInput.value = '';
    textInput.placeholder = art.nombre;
    hideDropdown();
    badgeArea.innerHTML = `
      <span class="ac-selected-badge">
        ${art.nombre}
        <span class="text-xs t2">${art.categoria} · ${art.unidad}</span>
        <button type="button" class="ac-clear" title="Limpiar">x</button>
      </span>`;
    badgeArea.querySelector('.ac-clear').addEventListener('click', clearSelection);
    if (onChange) onChange(art);
  }

  function clearSelection() {
    selected = null;
    idInput.value = '';
    textInput.placeholder = 'Buscar artículo…';
    textInput.value = '';
    badgeArea.innerHTML = '';
    if (onChange) onChange(null);
    textInput.focus();
  }

  function hideDropdown() {
    dropdown.style.display = 'none';
    focusedIdx = -1;
  }

  function showResults(results) {
    lastResults = results;
    focusedIdx = -1;
    if (!results.length) {
      dropdown.innerHTML = '<div class="ac-empty">Sin resultados</div>';
    } else {
      dropdown.innerHTML = results.map((a, i) => `
        <div class="ac-item" data-i="${i}">
          <span class="ac-item-nombre">${a.nombre}</span>
          <span class="ac-item-meta">${a.categoria} · ${a.unidad}</span>
        </div>`).join('');
      dropdown.querySelectorAll('.ac-item').forEach(el => {
        el.addEventListener('mousedown', e => {
          e.preventDefault();
          selectArticulo(lastResults[+el.dataset.i]);
        });
      });
    }
    dropdown.style.display = 'block';
  }

  function setFocused(idx) {
    const items = dropdown.querySelectorAll('.ac-item');
    items.forEach((el, i) => el.classList.toggle('focused', i === idx));
    focusedIdx = idx;
  }

  textInput.addEventListener('input', () => {
    if (selected) clearSelection();
    clearTimeout(debounce);
    const q = textInput.value.trim();
    if (!q) { hideDropdown(); return; }
    debounce = setTimeout(async () => {
      try {
        const r = await fetch(`${API}/articulos/buscar?q=${encodeURIComponent(q)}`);
        showResults(await r.json());
      } catch { hideDropdown(); }
    }, 200);
  });

  textInput.addEventListener('keydown', e => {
    const items = dropdown.querySelectorAll('.ac-item');
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setFocused(Math.min(focusedIdx + 1, items.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setFocused(Math.max(focusedIdx - 1, 0));
    } else if (e.key === 'Enter' && focusedIdx >= 0) {
      e.preventDefault();
      selectArticulo(lastResults[focusedIdx]);
    } else if (e.key === 'Escape') {
      hideDropdown();
    }
  });

  textInput.addEventListener('focus', () => {
    const q = textInput.value.trim();
    if (q && lastResults.length) dropdown.style.display = 'block';
  });

  document.addEventListener('click', e => {
    if (!wrap.contains(e.target)) hideDropdown();
  });

  return {
    getValue: () => selected,
    reset: clearSelection,
  };
}
