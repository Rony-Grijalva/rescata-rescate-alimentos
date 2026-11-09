import { icon } from './icons.js';
import { state, can, param } from './state.js';
import { ApiError } from './api.js';

// ------------------------------------------------------------ DOM helper
export function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  if (attrs && (typeof attrs !== 'object' || attrs instanceof Node || Array.isArray(attrs))) { kids.unshift(attrs); attrs = null; }
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'html') el.innerHTML = v;
    else if (k.startsWith('on')) el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
    else el.setAttribute(k, v === true ? '' : v);
  }
  const add = (c) => {
    if (c == null || c === false) return;
    if (Array.isArray(c)) c.forEach(add);
    else el.appendChild(c instanceof Node ? c : document.createTextNode(String(c)));
  };
  kids.forEach(add);
  return el;
}
export const ico = (n, cls) => { const t = document.createElement('span'); t.innerHTML = icon(n, cls); t.style.display = 'contents'; return t; };
export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

// ------------------------------------------------------------ formatos
export const money = (n) => 'S/ ' + Number(n || 0).toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
export const numf = (n, d = 2) => Number(n || 0).toLocaleString('es-PE', { maximumFractionDigits: d });
export const fdate = (s) => {
  if (!s) return '—'; const d = new Date(String(s).replace(' ', 'T')); if (isNaN(d)) return s;
  return d.toLocaleDateString('es-PE', { day: '2-digit', month: 'short' }) + ' ' + d.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' });
};
export const fday = (s) => { if (!s) return '—'; const d = new Date(String(s).replace(' ', 'T')); return isNaN(d) ? s : d.toLocaleDateString('es-PE', { day: '2-digit', month: 'short', year: 'numeric' }); };
export const horas = (hs) => {
  if (hs == null) return '—'; if (hs < 0) return 'vencido';
  if (hs < 48) return `${numf(hs, 1)} h`; const d = hs / 24; return d < 60 ? `${numf(d, 0)} días` : `${numf(d / 30, 0)} meses`;
};

// ------------------------------------------------------------ badges
const ESTADOS = { PUBLICADO: 'b-blue', ASIGNADO: 'b-amber', CERRADO: 'b-gray', PENDIENTE: 'b-amber', ASIGNADA: 'b-blue', ENTREGADA: 'b-green',
  ACTIVO: 'b-green', INACTIVO: 'b-gray', HABILITADA: 'b-green', SUSPENDIDA: 'b-red', CRITICA: 'b-red', ALTA: 'b-amber', MEDIA: 'b-blue', NORMAL: 'b-green',
  OK: 'b-green', ERROR: 'b-red', RECHAZADO: 'b-red', Programado: 'b-gray', 'En punto de recojo': 'b-amber', 'En ruta': 'b-blue', Entregado: 'b-green' };
export const badge = (txt, cls) => h('span', { class: 'badge ' + (cls || ESTADOS[txt] || 'b-gray') }, txt);

// ------------------------------------------------------------ toasts
export function toast(msg, tipo = 'ok', titulo, code) {
  const t = h('div', { class: 'toast ' + (tipo === 'ok' ? '' : tipo), role: 'status' },
    ico(tipo === 'ok' ? 'check' : 'alert'),
    h('div', null, h('b', null, titulo || (tipo === 'ok' ? 'Operación exitosa' : tipo === 'warn' ? 'Atención' : 'No se pudo completar')),
      h('span', null, code ? h('span', { class: 'code' }, code) : null, msg)));
  document.getElementById('toasts').appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; t.style.transition = '.3s'; setTimeout(() => t.remove(), 300); }, tipo === 'ok' ? 3800 : 7000);
}
export const toastErr = (e) => toast(e.message || String(e), 'err', e.code === 'ORA-01031' ? 'Acceso denegado' : e.code === 'VALIDACION' ? 'Revise el formulario' : undefined, e.code && e.code !== 'VALIDACION' ? e.code : null);

// Ejecuta una accion con indicador de carga en el boton y mensajes de exito/error
export async function run(btn, fn, okMsg) {
  if (btn) { btn.disabled = true; btn.classList.add('loading'); }
  try { const r = await fn(); const m = okMsg || (r && r.mensaje); if (m) toast(typeof m === 'function' ? m(r) : m); return r; }
  catch (e) { if (e instanceof ApiError) toastErr(e); else { console.error(e); toast(String(e), 'err'); } throw e; }
  finally { if (btn) { btn.disabled = false; btn.classList.remove('loading'); } }
}
export const safe = (btn, fn, ok) => run(btn, fn, ok).catch(() => null);

// ------------------------------------------------------------ modal
export function modal({ title, sub, body, footer, size = '', onClose }) {
  const root = document.getElementById('modal-root');
  const close = () => { ov.remove(); document.removeEventListener('keydown', esck); onClose && onClose(); };
  const esck = (e) => { if (e.key === 'Escape' && root.lastChild === ov) close(); };
  const ov = h('div', { class: 'overlay', onMousedown: (e) => { if (e.target === ov) close(); } },
    h('div', { class: 'modal ' + size, role: 'dialog', 'aria-modal': 'true' },
      h('div', { class: 'modal-h' }, h('h3', null, title, sub ? h('small', null, sub) : null),
        h('button', { class: 'icon-btn', onClick: close, 'aria-label': 'Cerrar' }, ico('x'))),
      h('div', { class: 'modal-b' }, body),
      footer ? h('div', { class: 'modal-f' }, footer) : null));
  document.addEventListener('keydown', esck);
  root.appendChild(ov);
  const first = ov.querySelector('input:not([type=hidden]),select,textarea'); if (first) setTimeout(() => first.focus(), 50);
  return { close, el: ov };
}

export function confirmar({ titulo, mensaje, ok = 'Eliminar', peligro = true }) {
  return new Promise((res) => {
    let done = false;
    const m = modal({ title: titulo, body: h('p', null, mensaje), onClose: () => { if (!done) res(false); },
      footer: [h('button', { class: 'btn ghost', onClick: () => { done = true; m.close(); res(false); } }, 'Cancelar'),
        h('button', { class: 'btn ' + (peligro ? 'danger' : ''), onClick: () => { done = true; m.close(); res(true); } }, ok)] });
  });
}

// ------------------------------------------------------------ formularios
// campos: {name,label,type:text|number|select|checkbox|date|datetime|textarea|email, options:[{id,nombre}], required, hint, full, step, min, max, placeholder}
export function buildForm(fields, values = {}) {
  const inputs = {}, errs = {};
  const el = h('form', { class: 'form', novalidate: true, onSubmit: (e) => e.preventDefault() });
  for (const f of fields) {
    let inp;
    const v = values[f.name];
    if (f.type === 'select') {
      inp = h('select', { name: f.name }, h('option', { value: '' }, f.placeholder || 'Seleccione…'),
        (f.options || []).map(o => h('option', { value: o.id, selected: String(v) === String(o.id) }, o.nombre)));
    } else if (f.type === 'checkbox') {
      inp = h('input', { type: 'checkbox', name: f.name, checked: !!v });
    } else if (f.type === 'textarea') {
      inp = h('textarea', { name: f.name, rows: f.rows || 3, placeholder: f.placeholder }, v ?? '');
    } else {
      const t = f.type === 'datetime' ? 'datetime-local' : (f.type || 'text');
      let val = v ?? ''; if (t === 'datetime-local' && val) val = String(val).replace(' ', 'T').slice(0, 16); if (t === 'date' && val) val = String(val).slice(0, 10);
      inp = h('input', { type: t, name: f.name, value: val, placeholder: f.placeholder, step: f.step, min: f.min, max: f.max, maxlength: f.maxlength, autocomplete: 'off' });
    }
    inp.addEventListener('input', () => { inp.classList.remove('invalid'); errs[f.name].textContent = ''; });
    inputs[f.name] = inp;
    errs[f.name] = h('div', { class: 'err' });
    el.appendChild(h('div', { class: 'field' + (f.full ? ' full' : '') + (f.type === 'checkbox' ? '' : '') },
      f.type === 'checkbox'
        ? h('label', { class: 'check' }, inp, h('span', null, f.label), f.hint ? h('span', { class: 'hint' }, f.hint) : null)
        : [h('label', null, f.label, f.required ? h('em', null, ' *') : null), inp, f.hint ? h('div', { class: 'hint' }, f.hint) : null],
      errs[f.name]));
  }
  const read = () => {
    const out = {};
    for (const f of fields) {
      const i = inputs[f.name];
      out[f.name] = f.type === 'checkbox' ? (i.checked ? 1 : 0) : i.value;
    }
    return out;
  };
  // validacion en el cliente (obligatorios); el servidor valida de nuevo
  const check = () => {
    let ok = true, first = null;
    for (const f of fields) {
      const i = inputs[f.name]; const val = f.type === 'checkbox' ? 1 : String(i.value).trim();
      if (f.required && !val) { mark(f.name, `${f.label.replace(/ \*$/, '')} es obligatorio`); ok = false; first ||= i; }
    }
    if (first) first.focus(); return ok;
  };
  const mark = (name, msg) => { if (inputs[name]) { inputs[name].classList.add('invalid'); errs[name].textContent = msg; } };
  const setErrors = (fe) => { let first = null; for (const [k, m] of Object.entries(fe || {})) { mark(k, m); first ||= inputs[k]; } if (first) first.focus(); };
  return { el, read, check, setErrors, inputs, mark };
}

export function formModal({ title, sub, fields, values, submitText = 'Guardar', onSubmit, size }) {
  const f = buildForm(fields, values);
  const btn = h('button', { class: 'btn', type: 'submit' }, ico('check'), submitText);
  const go = async () => {
    if (!f.check()) return;
    try { await run(btn, () => onSubmit(f.read())); m.close(); }
    catch (e) { if (e instanceof ApiError && e.fields) f.setErrors(e.fields); }
  };
  btn.addEventListener('click', go);
  f.el.addEventListener('keydown', (e) => { if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') { e.preventDefault(); go(); } });
  const m = modal({ title, sub, size, body: f.el, footer: [h('button', { class: 'btn ghost', onClick: () => m.close() }, 'Cancelar'), btn] });
  return m;
}

// ------------------------------------------------------------ tabla
// cols: {key,label,render(row)->Node|string,num,sort,cls}
export function dataTable({ cols, rows, actions, empty = 'No hay registros para mostrar.', foot }) {
  let sortKey = null, dir = 1;
  const tbody = h('tbody'), thead = h('tr');
  const draw = () => {
    tbody.innerHTML = '';
    let data = rows.slice();
    if (sortKey) data.sort((a, b) => { const x = a[sortKey], y = b[sortKey]; return (x > y ? 1 : x < y ? -1 : 0) * dir; });
    if (!data.length) tbody.appendChild(h('tr', null, h('td', { colspan: cols.length + (actions ? 1 : 0) }, h('div', { class: 'empty' }, h('img', { class: 'ill', src: '/assets/img/empty.svg', alt: '', width: 200, height: 140 }), h('div', null, empty)))));
    for (const r of data) {
      const tr = h('tr');
      for (const c of cols) {
        const v = c.render ? c.render(r) : r[c.key];
        tr.appendChild(h('td', { class: (c.num ? 'num ' : '') + (c.cls || '') }, v == null || v === '' ? h('span', { class: 'muted' }, '—') : v));
      }
      if (actions) { const a = actions(r); tr.appendChild(h('td', { class: 'actions' }, a)); }
      tbody.appendChild(tr);
    }
  };
  for (const c of cols) {
    const th = h('th', { class: (c.num ? 'num ' : '') + ((c.sort !== false && c.key) ? 'sortable' : ''), onClick: () => { if (c.sort === false || !c.key) return; dir = sortKey === c.key ? -dir : 1; sortKey = c.key; draw(); } }, c.label);
    thead.appendChild(th);
  }
  if (actions) thead.appendChild(h('th', null, ''));
  draw();
  return h('div', null, h('div', { class: 'table-wrap' }, h('table', null, h('thead', null, thead), tbody)), foot ? h('div', { class: 'tfoot' }, foot) : null);
}

export const iconBtn = (name, title, onClick, cls = '') => h('button', { class: 'icon-btn sm ' + cls, title, 'aria-label': title, onClick }, ico(name));
export function searchBox(onInput, placeholder = 'Buscar…') {
  let t; const i = h('input', { type: 'search', placeholder, 'aria-label': placeholder });
  i.addEventListener('input', () => { clearTimeout(t); t = setTimeout(() => onInput(i.value.trim()), 220); });
  return h('div', { class: 'search' }, ico('search'), i);
}
export function seg(options, current, onChange) {
  const box = h('div', { class: 'seg' });
  options.forEach(([val, lab]) => box.appendChild(h('button', { class: val === current ? 'on' : '', onClick: (e) => { [...box.children].forEach(b => b.classList.remove('on')); e.currentTarget.classList.add('on'); onChange(val); } }, lab)));
  return box;
}

// ------------------------------------------------------------ SQL resaltado
const KWS = 'SELECT|FROM|WHERE|GROUP BY|ORDER BY|HAVING|INNER JOIN|LEFT JOIN|RIGHT JOIN|FULL OUTER JOIN|CROSS JOIN|JOIN|ON|USING|AS|AND|OR|NOT|IN|IS|NULL|COUNT|SUM|CASE|WHEN|THEN|ELSE|END|DESC|ASC|INSERT INTO|VALUES|UPDATE|SET|DELETE FROM|DELETE|LIMIT|UNION ALL|UNION|DISTINCT|COALESCE|IFNULL|LIKE|BETWEEN|WITH|EXISTS|OUTER|INNER|LEFT|RIGHT|FULL|ROUND|MIN|MAX|AVG';
const TOK = new RegExp(`('[^']*')|(--[^\\n]*)|\\b(${KWS})\\b|\\b(\\d+(?:\\.\\d+)?)\\b`, 'gi');
export function sqlHtml(sql) {
  let out = '', last = 0, m; TOK.lastIndex = 0; const s = String(sql);
  while ((m = TOK.exec(s))) {
    out += esc(s.slice(last, m.index));
    const cls = m[1] ? 'str' : m[2] ? 'cm' : m[3] ? 'kw' : 'numk';
    out += `<span class="${cls}">${esc(m[0])}</span>`; last = m.index + m[0].length;
  }
  return out + esc(s.slice(last));
}
export const sqlBlock = (sql) => h('pre', { class: 'sql', html: sqlHtml(sql) });

// ------------------------------------------------------------ graficos SVG/CSS (sin librerias externas)
const PALETA = ['#2f5bd8', '#f5a524', '#0e9f6e', '#d6334b', '#8b5cf6', '#06b6d4', '#ec4899', '#64748b'];
export function hbars(data, { fmt = numf, color } = {}) {
  const max = Math.max(1, ...data.map(d => d.valor));
  return h('div', null, data.length ? data.map((d, i) => h('div', { class: 'hbar' }, h('span', { class: 'lab', title: d.etiqueta }, d.etiqueta),
    h('div', { class: 'trk' }, h('i', { style: { width: (d.valor / max * 100) + '%', background: color || PALETA[i % PALETA.length] } })), h('span', { class: 'val' }, fmt(d.valor)))) : h('div', { class: 'empty' }, 'Sin datos'));
}
export function vbars(data, { fmt = numf } = {}) {
  const max = Math.max(1, ...data.map(d => d.valor));
  return h('div', null, h('div', { class: 'vbars' }, data.map(d => h('div', { class: 'col', title: `${d.etiqueta}: ${fmt(d.valor)}` }, h('b', null, fmt(d.valor)), h('i', { style: { height: Math.max(1, d.valor / max * 130) + 'px' } })))),
    h('div', { class: 'vbars-lab' }, data.map(d => h('span', { title: d.etiqueta }, d.etiqueta))));
}
export function donut(data, { size = 150 } = {}) {
  const tot = data.reduce((s, d) => s + d.valor, 0), r = 56, c = 2 * Math.PI * r; let off = 0;
  const segs = tot ? data.map((d, i) => { const len = d.valor / tot * c; const s = `<circle cx="75" cy="75" r="${r}" fill="none" stroke="${PALETA[i % PALETA.length]}" stroke-width="22" stroke-dasharray="${len} ${c - len}" stroke-dashoffset="${-off}" transform="rotate(-90 75 75)"/>`; off += len; return s; }).join('') : `<circle cx="75" cy="75" r="${r}" fill="none" stroke="var(--line)" stroke-width="22"/>`;
  const svg = h('div', { html: `<svg width="${size}" height="${size}" viewBox="0 0 150 150">${segs}<text x="75" y="72" text-anchor="middle" font-size="26" font-weight="800" fill="currentColor">${tot}</text><text x="75" y="92" text-anchor="middle" font-size="11" fill="var(--muted)">total</text></svg>` });
  return h('div', { class: 'donut-wrap' }, svg, h('div', { class: 'legend' }, data.map((d, i) => h('div', null, h('i', { style: { background: PALETA[i % PALETA.length] } }), d.etiqueta, h('b', null, d.valor)))));
}

// diagramas de Venn para cada tipo de JOIN
export function venn(tipo) {
  const t = tipo.toUpperCase();
  let mode = 'inner';
  if (t.startsWith('LEFT JOIN COMO')) mode = 'anti'; else if (t.startsWith('LEFT')) mode = 'left'; else if (t.startsWith('RIGHT')) mode = 'right';
  else if (t.startsWith('FULL')) mode = 'full'; else if (t.startsWith('CROSS')) mode = 'cross'; else if (t.startsWith('SELF')) mode = 'self';
  const A = '<circle cx="19" cy="15" r="11"/>', B = '<circle cx="31" cy="15" r="11"/>';
  const clip = '<clipPath id="va"><circle cx="19" cy="15" r="11"/></clipPath><clipPath id="vb"><circle cx="31" cy="15" r="11"/></clipPath>';
  const fill = '#f5a524', base = 'fill="none" stroke="currentColor" stroke-width="1.400"';
  let body = '';
  if (mode === 'inner') body = `<g clip-path="url(#va)"><circle cx="31" cy="15" r="11" fill="${fill}"/></g>`;
  if (mode === 'left') body = `<circle cx="19" cy="15" r="11" fill="${fill}"/>`;
  if (mode === 'right') body = `<circle cx="31" cy="15" r="11" fill="${fill}"/>`;
  if (mode === 'full') body = `<circle cx="19" cy="15" r="11" fill="${fill}"/><circle cx="31" cy="15" r="11" fill="${fill}"/>`;
  if (mode === 'anti') body = `<circle cx="19" cy="15" r="11" fill="${fill}"/><g clip-path="url(#va)"><circle cx="31" cy="15" r="11" fill="var(--surface)"/></g>`;
  if (mode === 'cross') body = '<rect x="9" y="4" width="32" height="22" fill="#f5a52455"/><path d="M9 11h32M9 18h32M20 4v22M30 4v22" stroke="currentColor" stroke-width=".8"/>';
  if (mode === 'self') body = `<circle cx="25" cy="15" r="11" fill="${fill}" opacity=".5"/><path d="M33 8a9 9 0 010 14" stroke="currentColor" fill="none" stroke-width="1.400"/><path d="M32 22l1 1.500 1.500-1.500" stroke="currentColor" fill="none" stroke-width="1.400"/>`;
  const outline = mode === 'cross' ? '' : (mode === 'self' ? `<circle cx="25" cy="15" r="11" ${base}/>` : `<circle cx="19" cy="15" r="11" ${base}/><circle cx="31" cy="15" r="11" ${base}/>`);
  return h('span', { class: 'venn', html: `<svg viewBox="0 0 50 30" width="46" height="30"><defs>${clip}</defs>${body}${outline}</svg>` });
}

export function tabs(items, current, onChange) {
  const box = h('div', { class: 'seg', style: { marginBottom: '14px' } });
  items.forEach(([k, l]) => box.appendChild(h('button', { class: k === current ? 'on' : '', onClick: (e) => { [...box.children].forEach(b => b.classList.remove('on')); e.currentTarget.classList.add('on'); onChange(k); } }, l)));
  return box;
}
export const loading = () => h('div', { class: 'empty' }, h('span', { class: 'btn loading', style: { background: 'transparent', color: 'var(--primary)' } }, 'Cargando…'));
export const options = (list) => (list || []).map(o => ({ id: o.id, nombre: o.nombre }));
export const lk = (k) => state.lookups[k] || [];
export { can, state, param };
