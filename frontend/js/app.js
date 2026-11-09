import { state, store, on, can } from './state.js';
import { get, post, put, ApiError } from './api.js';
import { h, ico, toast, confirmar, safe, loading, sqlHtml, formModal } from './ui.js';
import { icon } from './icons.js';
import { dashboard } from './pages/dashboard.js';
import { lotes } from './pages/lotes.js';
import { solicitudes } from './pages/solicitudes.js';
import { logistica } from './pages/logistica.js';
import { comprobantes } from './pages/comprobantes.js';
import { donantes, organizaciones } from './pages/actores.js';
import { catalogos } from './pages/catalogos.js';
import { consultas } from './pages/consultas.js';
import { pruebas } from './pages/pruebas.js';
import { modelo } from './pages/modelo.js';
import { bitacora } from './pages/bitacora.js';
import { perfil } from './pages/perfil.js';
import { usuarios } from './pages/usuarios.js';

// Cada rol tiene su propio menu: [id, titulo, subtitulo, icono, perm, funcion]. Los separadores son cadenas.
const P = {
  panel: dashboard, lotes, solicitudes, logistica, comprobantes, donantes, organizaciones, catalogos, consultas, pruebas, modelo, bitacora, perfil, usuarios,
};
const MENU = {
  admin: [
    'Operación',
    ['panel', 'Panel del coordinador', 'Qué requiere su atención hoy y cómo va el ciclo del rescate', 'dashboard', 'dashboard'],
    ['lotes', 'Lotes de alimentos', 'Excedentes publicados: ver saldos, sugerir receptoras y repartir', 'package', 'lotes'],
    ['solicitudes', 'Solicitudes y reparto', 'Asigne los alimentos de cada lote a las organizaciones que los pidieron', 'hand', 'solicitudes'],
    ['logistica', 'Logística', 'Supervise despachos, vehículos y personas de recojo', 'truck', 'despachos'],
    ['comprobantes', 'Comprobantes', 'Emita la constancia de cada entrega y consulte las ya emitidas', 'receipt', 'comprobantes'],
    'Registros',
    ['donantes', 'Donantes', 'Comercios y empresas que donan', 'users', 'donantes'],
    ['organizaciones', 'Organizaciones', 'Ollas comunes, comedores y albergues', 'building', 'organizaciones'],
    ['catalogos', 'Catálogos', 'Alimentos, zonas, categorías y unidades', 'book', 'catalogos'],
    'Seguridad',
    ['usuarios', 'Usuarios y accesos', 'Cuentas de ingreso de cada rol: crear, desactivar, restablecer y desbloquear', 'shield', 'usuarios'],
  ],
  donante: [
    ['panel', 'Inicio', 'Resumen de lo que ha donado', 'dashboard', 'dashboard'],
    ['lotes', 'Mis lotes', 'Publique excedentes y vea quién los pidió', 'package', 'lotes'],
    ['comprobantes', 'Mis constancias', 'Constancias de donación de sus entregas', 'receipt', 'comprobantes'],
    ['perfil', 'Mi perfil', 'Datos de contacto de su empresa', 'users', 'perfil'],
  ],
  organizacion: [
    ['panel', 'Inicio', 'Qué puede pedir y qué tiene pendiente', 'dashboard', 'dashboard'],
    ['lotes', 'Lotes disponibles', 'Elija los alimentos que su organización necesita', 'package', 'lotes'],
    ['solicitudes', 'Mis solicitudes', 'Siga el avance de cada pedido y programe su recojo', 'hand', 'solicitudes'],
    ['logistica', 'Mis despachos', 'Recojos programados, su flota y su personal autorizado', 'truck', 'despachos'],
    ['comprobantes', 'Constancias recibidas', 'Comprobantes de lo que ya recibió', 'receipt', 'comprobantes'],
    ['perfil', 'Mi organización', 'Datos de su organización y cadena de frío', 'building', 'perfil'],
  ],
  auditor: [
    ['panel', 'Panel de auditoría', 'Indicadores generales del sistema (solo lectura)', 'dashboard', 'dashboard'],
    ['comprobantes', 'Comprobantes', 'Verifique que el monto emitido coincida con el recalculado', 'receipt', 'comprobantes'],
    'Laboratorio de base de datos',
    ['consultas', 'Consultas JOIN', 'INNER, LEFT, RIGHT, FULL, CROSS, SELF y USING sobre datos reales', 'code', 'consultas'],
    ['pruebas', 'Pruebas de reglas', 'Restricciones, excepciones y reglas de negocio con ROLLBACK', 'flask', 'pruebas'],
    ['modelo', 'Modelo de datos', 'Las 22 tablas, sus claves y su contenido', 'db', 'esquema'],
    ['bitacora', 'Bitácora', 'Auditoría de operaciones', 'list', 'bitacora'],
  ],
};
// El administrador tambien consulta el laboratorio (sin mezclarlo con la operacion)
MENU.admin.push(...MENU.auditor.slice(2));
const ROL_ICON = { admin: 'dashboard', donante: 'package', organizacion: 'building', auditor: 'eye' };
const ROL_DESC = {
  admin: 'Coordina el rescate: reparte los lotes entre las organizaciones, emite constancias y administra los registros.',
  donante: 'Publica los excedentes de su comercio y sigue qué pasó con cada uno.',
  organizacion: 'Pide los alimentos que necesita, programa el recojo y recibe su constancia.',
  auditor: 'Revisa comprobantes, consultas, reglas y bitácora. No modifica nada.',
};

export async function refreshLookups() { state.lookups = await get('/api/lookups'); }
const $ = (id) => document.getElementById(id);
let token = 0;
const items = () => (MENU[state.rol] || []).filter(x => typeof x !== 'string');
const pageDef = (id) => { const x = items().find(i => i[0] === id); return x && { id: x[0], t: x[1], sub: x[2], ic: x[3], perm: x[4], fn: P[x[0]] }; };

async function loadMe() {
  const r = await fetch('/api/me', { credentials: 'same-origin' }).then(r => r.json());
  if (!r.ok) throw Object.assign(new Error(r.error.message), { code: r.error.code });
  state.rol = r.data.rol; state.perm = r.data.permisos; state.me = r.data; state.actor = r.data.actor?.id ? String(r.data.actor.id) : ''; state.actorNombre = r.data.actor?.nombre || '';
  $('dbinfo').textContent = `SQLite ${r.data.sqlite} · base real`;
  const nombre = r.data.usuario?.nombre || r.data.roles[state.rol];
  const u = $('user'); u.replaceChildren(h('span', { class: 'av' }, ico(ROL_ICON[state.rol])), h('span', { class: 'who' }, h('b', null, nombre), h('small', null, r.data.roles[state.rol])), ico('chevron'));
  u.setAttribute('aria-haspopup', 'menu');
  const adm = state.rol === 'admin';
  $('btn-reset').classList.toggle('hide', !can('sistema', 'd')); $('btn-sql').classList.toggle('hide', !adm);
}

function buildNav() {
  const nav = $('nav'); nav.replaceChildren();
  for (const x of MENU[state.rol] || []) {
    if (typeof x === 'string') { nav.appendChild(h('div', { class: 'grp' }, x)); continue; }
    if (!can(x[4], 'r')) continue;
    const a = h('a', { href: '#/' + x[0], 'data-id': x[0] }); a.innerHTML = icon(x[3]) + `<span>${x[1]}</span>`; nav.appendChild(a);
  }
}

async function route() {
  if (!state.rol) return;
  const id = (location.hash.replace('#/', '') || 'panel').split('?')[0];
  let page = pageDef(id);
  if (!page || !can(page.perm, 'r')) { page = pageDef('panel'); if (id !== 'panel') { toast(`Su perfil (${state.me.roles[state.rol]}) no tiene acceso a la sección «${id}». Fue devuelto a su panel.`, 'warn', 'Acceso denegado'); history.replaceState(null, '', '#/panel'); } }
  document.querySelectorAll('#nav a').forEach(a => a.classList.toggle('active', a.dataset.id === page.id));
  $('page-title').textContent = page.t; $('page-sub').textContent = page.sub; document.title = `${page.t} · RESCATA`;
  $('sidebar').classList.remove('open');
  const view = $('view'); const my = ++token;
  view.replaceChildren(loading());
  const box = h('div');
  try { await page.fn(box); }
  catch (e) { console.error(e); if (my === token) view.replaceChildren(h('div', { class: 'card' }, h('div', { class: 'empty' }, ico('alert'), h('div', null, e.message || 'Error al cargar la página'), h('button', { class: 'btn ghost sm', style: { marginTop: '10px' }, onClick: route }, 'Reintentar')))); return; }
  if (my === token) { view.replaceChildren(...box.childNodes); view.scrollTo?.(0, 0); window.scrollTo(0, 0); }
}

// ------------------------------------------------------------ panel SQL en vivo
let sqlCount = 0;
function sqlButton() { $('btn-sql').innerHTML = icon('terminal') + `SQL en vivo${sqlCount ? ` <span class="badge b-navy" style="margin-left:4px">${sqlCount}</span>` : ''}`; }
on('sql', ({ sql, mensaje, ok }) => {
  const body = $('sqlbody'); if (!sqlCount) body.replaceChildren();
  const stamp = new Date().toLocaleTimeString('es-PE');
  const blk = h('div', { class: 'sqlitem' }, h('small', null, `${stamp} · ${mensaje || (ok ? 'operación' : 'operación rechazada (ROLLBACK)')}`), ...sql.map(s => h('pre', { html: sqlHtml(s), style: { marginBottom: '6px' } })));
  body.prepend(blk); sqlCount += sql.length; sqlButton();
});

function setTheme(t) { state.tema = t; document.documentElement.dataset.theme = t; store.set('rescata.tema', t); $('btn-theme').innerHTML = icon(t === 'dark' ? 'sun' : 'moon'); }

// ------------------------------------------------------------ ingreso con credenciales propias
const ROL_NOMBRE = { admin: 'Coordinador', donante: 'Donante', organizacion: 'Organización', auditor: 'Auditor' };
async function pantallaIngreso(mensaje, tipo = 'info') {
  document.body.classList.add('sin-sesion'); document.body.classList.remove('con-sesion'); history.replaceState(null, '', location.pathname);
  $('sqlpanel').classList.remove('open'); $('modal-root').replaceChildren();
  let demo = { activo: false, cuentas: [] };
  try { demo = (await fetch('/api/auth/demo', { credentials: 'same-origin' }).then(r => r.json())).data || demo; } catch { /* servidor caido: se muestra el aviso abajo */ }
  const email = h('input', { id: 'lg-email', type: 'email', name: 'email', autocomplete: 'username', placeholder: 'usuario@organizacion.pe', required: true, maxlength: 120 });
  const pass = h('input', { id: 'lg-pass', type: 'password', name: 'password', autocomplete: 'current-password', placeholder: 'Su contraseña', required: true, maxlength: 128 });
  const eye = h('button', { type: 'button', class: 'eye', 'aria-label': 'Mostrar u ocultar contraseña', onClick: () => { const v = pass.type === 'password'; pass.type = v ? 'text' : 'password'; eye.replaceChildren(ico(v ? 'eyeoff' : 'eye')); } }, ico('eye'));
  const msg = h('div', { class: 'lg-msg ' + (mensaje ? tipo : 'hide'), role: 'alert' }, mensaje || '');
  const btn = h('button', { class: 'btn lg-go', type: 'submit' }, 'Ingresar', ico('arrow'));
  const mostrar = (t, k = 'err') => { msg.className = 'lg-msg ' + k; msg.textContent = t; };
  const form = h('form', { class: 'lg-form', novalidate: true, onSubmit: async (e) => {
    e.preventDefault();
    if (!email.value.trim() || !pass.value) { mostrar('Escriba su correo y su contraseña.'); (email.value.trim() ? pass : email).focus(); return; }
    btn.disabled = true; btn.classList.add('loading');
    try { await post('/api/auth/login', { email: email.value.trim(), password: pass.value }); pass.value = ''; await iniciar(true); }
    catch (er) { mostrar(er instanceof ApiError ? er.message : 'No se pudo conectar con el servidor.'); pass.select(); }
    finally { btn.disabled = false; btn.classList.remove('loading'); }
  } },
    h('div', { class: 'lg-f' }, h('label', { for: 'lg-email' }, 'Correo electrónico'), h('div', { class: 'lg-in' }, ico('user'), email)),
    h('div', { class: 'lg-f' }, h('label', { for: 'lg-pass' }, 'Contraseña'), h('div', { class: 'lg-in' }, ico('lock'), pass, eye)),
    msg, btn);
  const demoBox = demo.activo ? h('details', { class: 'lg-demo', open: true }, h('summary', null, ico('flask'), 'Cuentas de demostración', h('small', null, 'toque una para rellenar el formulario')),
    h('div', { class: 'lg-acc' }, demo.cuentas.map(c => h('button', { type: 'button', class: 'acct', title: c.email, onClick: () => { email.value = c.email; pass.value = demo.password; mostrar('Datos cargados. Pulse «Ingresar».', 'info'); btn.focus(); } },
      h('span', { class: 'r r-' + c.rol }, ROL_NOMBRE[c.rol]), h('b', null, c.nombre), h('small', null, c.email)))),
    h('p', { class: 'muted', style: { fontSize: '11.5px', marginTop: '8px' } }, 'Esta lista solo aparece en modo demostración (RESCATA_DEMO=0 la oculta).')) : null;
  const wrap = h('div', { class: 'lg' },
    h('section', { class: 'lg-hero' }, h('div', { class: 'lg-brand' }, h('span', { class: 'logo' }, ico('hand')), h('div', null, h('b', null, 'RESCATA'), h('small', null, 'Rescate de alimentos · Lima'))),
      h('h1', null, 'Ningún alimento bueno debe perderse.'), h('p', null, 'Conecta a comercios que tienen excedentes con ollas comunes, comedores y albergues, y deja constancia de cada entrega.'),
      h('img', { src: '/assets/img/login-hero.svg', alt: 'Ilustración: una panadería dona alimentos que un camión lleva a un comedor popular', width: 640, height: 560 }),
      h('ul', { class: 'lg-pts' }, h('li', null, ico('shield'), 'Acceso por rol y contraseñas cifradas'), h('li', null, ico('db'), 'Datos reales en base relacional'), h('li', null, ico('receipt'), 'Constancia por cada entrega'))),
    h('section', { class: 'lg-card' }, h('h2', null, 'Iniciar sesión'), h('p', { class: 'muted' }, 'Cada rol entra con su propia cuenta y solo ve lo que le corresponde.'), form, demoBox,
      h('footer', null, 'Base de Datos 2 · UNMSM FISI 2026-II')));
  $('view').replaceChildren(wrap);
  $('page-title').textContent = 'RESCATA'; $('page-sub').textContent = ''; $('nav').replaceChildren(); document.title = 'Iniciar sesión · RESCATA';
  setTimeout(() => email.focus(), 60);
}

// ------------------------------------------------------------ menu de usuario, cierre de sesion y cambio de clave
function menuUsuario() {
  const ya = document.getElementById('umenu'); if (ya) { ya.remove(); return; }
  const m = h('div', { id: 'umenu', class: 'umenu', role: 'menu' },
    h('div', { class: 'who' }, h('b', null, state.me.usuario?.nombre), h('small', null, state.me.usuario?.email), h('span', { class: 'badge b-blue' }, state.me.roles[state.rol])),
    h('button', { role: 'menuitem', onClick: () => { m.remove(); cambiarClave(); } }, ico('lock'), 'Cambiar contraseña'),
    h('button', { role: 'menuitem', class: 'out', onClick: () => { m.remove(); cerrarSesion(); } }, ico('logout'), 'Cerrar sesión'));
  document.body.appendChild(m);
  const r = $('user').getBoundingClientRect(); m.style.top = r.bottom + 8 + 'px'; m.style.right = Math.max(12, innerWidth - r.right) + 'px';
  setTimeout(() => document.addEventListener('click', function f(e) { if (!m.contains(e.target)) { m.remove(); document.removeEventListener('click', f); } }), 0);
}
async function cerrarSesion() {
  try { await post('/api/auth/logout'); } catch { /* aunque falle, se vuelve al ingreso */ }
  state.rol = ''; state.me = null; await pantallaIngreso('Sesión cerrada correctamente. Hasta pronto.', 'ok');
}
function cambiarClave() {
  formModal({ title: 'Cambiar contraseña', sub: 'Se cerrarán sus otras sesiones abiertas',
    fields: [{ name: 'actual', label: 'Contraseña actual', type: 'password', required: true, full: true },
      { name: 'nueva', label: 'Nueva contraseña', type: 'password', required: true, full: true, hint: 'Mínimo 8 caracteres, con letras y números' },
      { name: 'repetir', label: 'Repita la nueva contraseña', type: 'password', required: true, full: true }],
    submitText: 'Actualizar contraseña',
    onSubmit: async (v) => { if (v.nueva !== v.repetir) throw new ApiError({ code: 'VALIDACION', message: 'Las contraseñas nuevas no coinciden.', fields: { repetir: 'No coincide' } }); return post('/api/auth/password', { actual: v.actual, nueva: v.nueva }); } });
}
on('sesion', (m) => { if (state.rol) { state.rol = ''; state.me = null; pantallaIngreso(m || 'Su sesión expiró. Inicie sesión nuevamente.', 'warn'); } });

async function iniciar(nuevo) {
  try { await loadMe(); await refreshLookups(); }
  catch (e) { return pantallaIngreso(e.code === 'SESION' ? undefined : 'No se pudo conectar con el servidor. Ejecute run.bat (Windows) o run.sh y recargue.', 'warn'); }
  document.body.classList.remove('sin-sesion'); document.body.classList.add('con-sesion'); $('user').classList.remove('hide');
  sqlCount = 0; $('sqlbody').replaceChildren(h('p', { class: 'muted' }, 'Aún no se ha ejecutado ninguna operación. Crea, edita o elimina algo y verás aquí el INSERT / UPDATE / DELETE real.')); sqlButton();
  buildNav(); const ya = location.hash; if (nuevo || !ya || ya === '#') history.replaceState(null, '', '#/panel'); route();
  if (nuevo) toast(`Bienvenido, ${state.me.usuario?.nombre}.`, 'ok', 'Sesión iniciada');
}

async function boot() {
  setTheme(state.tema); sqlButton();
  $('burger').innerHTML = icon('menu'); $('sql-clear').innerHTML = icon('trash'); $('sql-close').innerHTML = icon('x');
  $('btn-reset').innerHTML = icon('refresh') + 'Reiniciar demo';
  $('btn-theme').onclick = () => setTheme(state.tema === 'dark' ? 'light' : 'dark');
  $('burger').onclick = () => $('sidebar').classList.toggle('open');
  $('btn-sql').onclick = () => $('sqlpanel').classList.toggle('open'); $('sql-close').onclick = () => $('sqlpanel').classList.remove('open');
  $('sql-clear').onclick = () => { sqlCount = 0; $('sqlbody').replaceChildren(h('p', { class: 'muted' }, 'Sin sentencias.')); sqlButton(); };
  $('user').onclick = (e) => { e.stopPropagation(); menuUsuario(); };
  $('btn-reset').onclick = async (e) => {
    if (!await confirmar({ titulo: 'Reiniciar demostración', ok: 'Restaurar', mensaje: 'Se borrarán todos los cambios y la base volverá a los datos de demostración iniciales.' })) return;
    await safe(e.currentTarget, async () => { const r = await post('/api/sistema/reiniciar'); await refreshLookups(); await route(); return r; });
  };
  window.addEventListener('hashchange', route);
  await iniciar(false);
}
boot();
