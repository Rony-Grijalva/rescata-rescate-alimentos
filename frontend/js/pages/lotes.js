import { h, ico, badge, dataTable, iconBtn, searchBox, seg, modal, confirmar, buildForm, formModal, safe, run, toast, toastErr, money, numf, horas, fdate, loading, lk, options, can, state, param } from '../ui.js';
import { get, post, put, del, ApiError } from '../api.js';

const urg = (u) => u ? badge(u) : null;

export async function lotes(root) {
  if (state.rol === 'organizacion') return lotesOrg(root);
  const don = state.rol === 'donante';
  let q = '', estado = '', rows = [];
  const box = h('div', null, loading());
  const reload = async () => {
    const p = new URLSearchParams(); if (q) p.set('q', q); if (estado) p.set('estado', estado);
    rows = await get('/api/lotes?' + p); draw();
  };
  const draw = () => box.replaceChildren(dataTable({
    rows, empty: don ? 'Aún no ha publicado lotes. Use «Publicar lote» para ofrecer sus excedentes.' : 'No hay lotes publicados con ese criterio.',
    cols: [
      { key: 'id_donacion_ofrecida', label: 'Lote', render: r => h('b', null, '#' + r.id_donacion_ofrecida) },
      don ? { key: 'nombre_zona', label: 'Zona de recojo', render: r => h('div', null, r.nombre_zona, h('div', { class: 'muted' }, r.nombre_distrito)) }
          : { key: 'nombre_donante', label: 'Donante', render: r => h('div', null, h('b', null, r.nombre_donante), h('div', { class: 'muted' }, `${r.nombre_zona} · ${r.nombre_distrito}`)) },
      { key: 'estado', label: 'Estado', render: r => badge(r.estado) },
      { key: 'lineas', label: 'Líneas', num: true, render: r => h('span', null, r.lineas, r.requiere_frio ? h('span', { title: 'Contiene alimentos que requieren frío', style: { marginLeft: '6px', color: 'var(--primary)' } }, ico('snow')) : null) },
      { key: 'valor', label: 'Valor', num: true, render: r => money(r.valor) }, { key: 'peso_kg', label: 'Peso', num: true, render: r => numf(r.peso_kg) + ' kg' },
      { key: 'saldo_total', label: 'Disponible', sort: false, render: r => { const pct = r.cantidad_total ? r.saldo_total / r.cantidad_total * 100 : 0; return h('div', { style: { minWidth: '110px' } }, h('div', { class: 'bar' + (pct < 30 ? ' warn' : '') }, h('i', { style: { width: pct + '%' } })), h('small', { class: 'muted' }, `${numf(pct, 0)}% sin repartir`)); } },
      { key: 'horas_vence', label: 'Vence en', render: r => h('div', null, horas(r.horas_vence), ' ', urg(r.urgencia)) },
      { key: 'solicitudes', label: don ? 'Pedidos' : 'Solic.', num: true }],
    actions: (r) => [
      iconBtn('eye', 'Ver detalle y líneas', () => detalle(r.id_donacion_ofrecida, reload), 'info'),
      !don && can('reparto', 'r') ? iconBtn('pin', 'Sugerir receptoras cercanas (sp_sugerir_receptoras)', () => sugerir(r), 'ok') : null,
      !don && can('reparto', 'u') ? iconBtn('scale', 'Repartir equitativamente entre solicitudes pendientes', () => repartir(r, reload), 'ok') : null,
      can('lotes', 'd') ? iconBtn('trash', 'Eliminar lote', async () => { if (await confirmar({ titulo: `Eliminar lote #${r.id_donacion_ofrecida}`, mensaje: 'Se eliminará el lote y sus líneas. Si tiene solicitudes, la base de datos lo impedirá.' })) safe(null, async () => { const x = await del('/api/lotes/' + r.id_donacion_ofrecida); await reload(); return x; }); }, 'danger') : null],
    foot: `${rows.length} lote(s)`,
  }));
  const bar = h('div', { class: 'toolbar' }, searchBox((v) => { q = v; reload(); }, don ? 'Buscar por zona o #' : 'Buscar por donante, zona o #'),
    seg([['', 'Todos'], ['PUBLICADO', 'Publicados'], ['ASIGNADO', 'Asignados'], ['CERRADO', 'Cerrados']], '', (v) => { estado = v; reload(); }), h('span', { class: 'grow' }),
    can('lotes', 'c') ? h('button', { class: 'btn accent', onClick: () => publicar(reload) }, ico('plus'), 'Publicar lote') : null);
  root.append(h('p', { class: 'muted', style: { marginBottom: '14px' } }, don
    ? 'Cada lote es una oferta suya con una o más líneas de alimentos. PUBLICADO: disponible para las organizaciones · ASIGNADO: ya se repartió todo · CERRADO: todas las entregas se completaron.'
    : 'Cada lote es una oferta de un donante con una o más líneas de alimentos. El estado pasa solo a ASIGNADO cuando se reparte todo el saldo y a CERRADO cuando todas las solicitudes se entregan.'), bar, box);
  await reload();
  if (don && param('nuevo')) { history.replaceState(null, '', '#/lotes'); publicar(reload); }
}

// ---------------------------------------------------------------- organizacion: lotes disponibles para pedir
async function lotesOrg(root) {
  let q = '', soloFrio = false, rows = [];
  const box = h('div', null, loading());
  const reload = async () => { rows = await get('/api/lotes' + (q ? '?q=' + encodeURIComponent(q) : '')); draw(); };
  const draw = () => {
    const vis = rows.filter(r => !soloFrio || r.frio_ok);
    box.replaceChildren(dataTable({
      rows: vis, empty: 'No hay lotes disponibles por ahora. Vuelva a revisar más tarde.',
      cols: [
        { key: 'id_donacion_ofrecida', label: 'Lote', render: r => h('b', null, '#' + r.id_donacion_ofrecida) },
        { key: 'nombre_donante', label: 'Ofrece', render: r => h('div', null, h('b', null, r.nombre_donante), h('div', { class: 'muted' }, `${r.nombre_zona} · ${r.nombre_distrito}`)) },
        { key: 'lineas', label: 'Contenido', num: true, render: r => h('span', null, `${r.lineas} alimento(s) · ${numf(r.peso_kg)} kg`) },
        { key: 'valor', label: 'Valor', num: true, render: r => money(r.valor) },
        { key: 'horas_vence', label: 'Vence en', render: r => h('div', null, horas(r.horas_vence), ' ', urg(r.urgencia)) },
        { key: 'frio_ok', label: 'Frío', sort: false, render: r => !r.requiere_frio ? badge('No requiere', 'b-gray') : r.frio_ok ? badge('❄ Compatible', 'b-green') : badge('❄ Requiere frío', 'b-red') },
        { key: 'mi_solicitud', label: 'Su pedido', sort: false, render: r => r.mi_solicitud ? h('a', { href: '#/solicitudes' }, badge(`Solicitado #${r.mi_solicitud} · ${r.mi_estado}`, 'b-blue')) : h('button', { class: 'btn accent xs', onClick: () => solicitar(r, reload) }, ico('hand'), 'Solicitar') }],
      actions: (r) => [iconBtn('eye', 'Ver qué alimentos trae', () => detalleOrg(r.id_donacion_ofrecida, reload), 'info')],
      foot: `${vis.length} lote(s) disponible(s)`,
    }));
  };
  root.append(h('div', { class: 'hint-box' }, ico('info'), h('div', null, 'Pida los lotes que le sirvan con «Solicitar». El coordinador asignará los alimentos y usted podrá programar el recojo desde «Mis solicitudes». Los alimentos con ❄ solo se asignan si su organización tiene refrigeración.')),
    h('div', { class: 'toolbar' }, searchBox((v) => { q = v; reload(); }, 'Buscar por donante, distrito o #'),
      seg([['', 'Todos'], ['1', 'Solo compatibles con mi frío']], '', (v) => { soloFrio = !!v; draw(); }), h('span', { class: 'grow' })), box);
  await reload();
}

async function solicitar(l, done) {
  const aviso = l.frio_ok ? '' : ' Este lote trae alimentos que requieren refrigeración y su organización no la tiene: solo se le podrán asignar las líneas que no necesiten frío.';
  if (!await confirmar({ titulo: `Solicitar lote #${l.id_donacion_ofrecida}`, ok: 'Sí, solicitar', peligro: false, mensaje: `Se registrará su pedido al lote de ${l.nombre_donante}. El coordinador le asignará los alimentos.${aviso}` })) return;
  const r = await safe(null, () => post('/api/solicitudes', { id_donacion_ofrecida: l.id_donacion_ofrecida })); if (r) await done();
}

async function detalleOrg(id, done) {
  const l = await get('/api/lotes/' + id);
  const m = modal({ title: `Lote #${id} · ${l.nombre_donante}`, sub: `${l.nombre_zona} · ${l.nombre_distrito} · recojo: ${l.direccion || 'a coordinar'}`, size: 'xl', onClose: done,
    body: [dataTable({ rows: l.lineas_detalle, cols: [
      { key: 'nombre_alimento', label: 'Alimento', render: r => h('span', null, h('b', null, r.nombre_alimento), r.requiere_refrigeracion ? h('span', { style: { color: 'var(--primary)', marginLeft: '6px' }, title: 'Requiere frío' }, ico('snow')) : null) },
      { key: 'saldo', label: 'Disponible', num: true, render: r => h('b', null, `${numf(r.saldo)} ${r.tipo_medida}`) },
      { key: 'peso_total_kg', label: 'Peso total', num: true, render: r => r.peso_total_kg ? numf(r.peso_total_kg) + ' kg' : null },
      { key: 'horas', label: 'Vence', render: r => h('span', null, horas(r.horas), ' ', badge(r.urgencia)) },
      { key: 'compatible', label: 'Para usted', sort: false, render: r => r.compatible ? badge('Compatible', 'b-green') : badge('Requiere frío', 'b-red') }] }),
      h('div', { style: { marginTop: '14px', textAlign: 'right' } }, l.mi_solicitud ? badge(`Ya lo solicitó (#${l.mi_solicitud})`, 'b-blue')
        : h('button', { class: 'btn accent', onClick: async () => { m.close(); await solicitar({ id_donacion_ofrecida: id, nombre_donante: l.nombre_donante, frio_ok: l.lineas_detalle.every(x => x.compatible) }, done); } }, ico('hand'), 'Solicitar este lote'))] });
}

// ---------------------------------------------------------------- publicar lote con varias lineas
function publicar(done) {
  const donantes = lk('donantes'), alimentos = lk('alimentos');
  const soyDonante = state.rol === 'donante';
  const cab = buildForm([
    ...(soyDonante ? [] : [{ name: 'id_donante', label: 'Donante', type: 'select', options: options(donantes), required: true }]),
    { name: 'id_zona', label: 'Zona de recojo', type: 'select', options: options(lk('zonas')), required: true },
    { name: 'direccion', label: 'Dirección de recojo', full: true, hint: soyDonante ? 'Se propone la dirección de su perfil; puede cambiarla para este lote.' : '' }], {});
  const aplicar = (d) => { if (d) { cab.inputs.id_zona.value = d.id_zona || ''; cab.inputs.direccion.value = d.direccion || ''; } };
  if (soyDonante) aplicar(donantes[0]);
  else cab.inputs.id_donante.addEventListener('change', () => aplicar(donantes.find(x => String(x.id) === cab.inputs.id_donante.value)));
  const wrap = h('div', { class: 'lines' }), totalEl = h('b', null, money(0)); const lineas = [];
  const recalc = () => { let t = 0; lineas.forEach(l => { const v = l.f.read(); t += (parseFloat(v.cantidad) || 0) * (parseFloat(v.costo_unitario) || 0); }); totalEl.textContent = money(t); };
  const addLine = () => {
    const f = buildForm([
      { name: 'id_alimento', label: 'Alimento', type: 'select', options: alimentos.map(a => ({ id: a.id, nombre: a.nombre + (a.frio ? '  ❄' : '') })), required: true },
      { name: 'cantidad', label: 'Cantidad', type: 'number', step: 'any', min: 0, required: true }, { name: 'id_unidad_medida', label: 'Unidad', type: 'select', options: options(lk('unidades')), required: true },
      { name: 'peso_total_kg', label: 'Peso (kg)', type: 'number', step: 'any', min: 0 }, { name: 'costo_unitario', label: 'Costo unit. (S/)', type: 'number', step: '0.01', min: 0, required: true },
      { name: 'fecha_vencimiento', label: 'Vence', type: 'datetime', required: true }], {});
    f.el.className = 'line'; f.el.addEventListener('input', recalc);
    const rm = h('button', { class: 'icon-btn sm danger', type: 'button', title: 'Quitar línea', style: { marginTop: '20px' }, onClick: () => { const i = lineas.findIndex(x => x.f === f); lineas.splice(i, 1); f.el.remove(); recalc(); } }, ico('trash'));
    f.el.appendChild(rm); lineas.push({ f }); wrap.appendChild(f.el);
    const d = new Date(Date.now() + 3 * 864e5); f.inputs.fecha_vencimiento.value = new Date(d - d.getTimezoneOffset() * 6e4).toISOString().slice(0, 16);
  };
  addLine();
  const btn = h('button', { class: 'btn accent' }, ico('check'), 'Publicar lote');
  btn.addEventListener('click', async () => {
    let ok = cab.check(); lineas.forEach(l => { if (!l.f.check()) ok = false; });
    if (!ok) { toast('Complete los campos obligatorios marcados en rojo.', 'warn', 'Faltan datos'); return; }
    const body = { ...cab.read(), lineas: lineas.map(l => l.f.read()) };
    try { await run(btn, () => post('/api/lotes', body)); m.close(); done(); }
    catch (e) { if (e instanceof ApiError) { Object.entries(e.fields || {}).forEach(([k, msg]) => { const mt = k.match(/lineas\[(\d+)\]\.(\w+)/); if (mt && lineas[+mt[1]]) lineas[+mt[1]].f.mark(mt[2], msg); else cab.mark(k, msg); }); } }
  });
  const m = modal({ title: 'Publicar lote de alimentos', sub: 'Se guarda el lote y todas sus líneas en una sola transacción', size: 'xl',
    body: [cab.el, h('div', { style: { display: 'flex', alignItems: 'center', margin: '18px 0 10px' } }, h('h4', { style: { flex: 1 } }, 'Alimentos del lote'), h('button', { class: 'btn ghost sm', type: 'button', onClick: addLine }, ico('plus'), 'Agregar alimento')), wrap,
      h('p', { class: 'muted', style: { marginTop: '10px' } }, '❄ = requiere refrigeración · Valor estimado del lote: ', totalEl)],
    footer: [h('button', { class: 'btn ghost', onClick: () => m.close() }, 'Cancelar'), btn] });
}

// ---------------------------------------------------------------- detalle del lote
async function detalle(id, done) {
  const render = async () => {
    const l = await get('/api/lotes/' + id);
    const body = h('div', null,
      h('div', { class: 'grid g4', style: { marginBottom: '16px' } },
        info('Donante', l.nombre_donante), info('Zona', `${l.nombre_zona} · ${l.nombre_distrito}`), info('Publicado', fdate(l.fecha_publicacion)), info('Estado', badge(l.estado))),
      h('div', { class: 'toolbar' }, h('h4', { style: { flex: 1 } }, 'Líneas del lote'),
        can('lotes', 'c') ? h('button', { class: 'btn ghost sm', onClick: () => agregarLinea(id, async () => { await refresh(); }) }, ico('plus'), 'Agregar línea') : null),
      dataTable({ rows: l.lineas_detalle, cols: [
        { key: 'nombre_alimento', label: 'Alimento', render: r => h('span', null, h('b', null, r.nombre_alimento), r.requiere_refrigeracion ? h('span', { style: { color: 'var(--primary)', marginLeft: '6px' }, title: 'Requiere frío' }, ico('snow')) : null) },
        { key: 'cantidad', label: 'Publicado', num: true, render: r => `${numf(r.cantidad)} ${r.tipo_medida}` }, { key: 'cantidad_repartida', label: 'Repartido', num: true, render: r => numf(r.cantidad_repartida) },
        { key: 'saldo', label: 'Saldo', num: true, render: r => h('b', null, numf(r.saldo)) }, { key: 'costo_unitario', label: 'Costo', num: true, render: r => money(r.costo_unitario) },
        { key: 'peso_total_kg', label: 'Peso', num: true, render: r => r.peso_total_kg ? numf(r.peso_total_kg) + ' kg' : null },
        { key: 'horas', label: 'Vence', render: r => h('span', null, horas(r.horas), ' ', badge(r.urgencia)) }],
        actions: (r) => [can('lotes', 'd') ? iconBtn('trash', 'Quitar línea', async () => { if (await confirmar({ titulo: 'Quitar línea', mensaje: `¿Quitar «${r.nombre_alimento}» del lote?` })) safe(null, async () => { const x = await del('/api/lineas/' + r.id_detalle_donacion_ofrecida); await refresh(); return x; }); }, 'danger') : null] }),
      h('h4', { style: { margin: '20px 0 10px' } }, 'Solicitudes de organizaciones'),
      l.solicitudes_lista.length ? h('div', { style: { display: 'flex', gap: '8px', flexWrap: 'wrap' } }, l.solicitudes_lista.map(s => h('span', { class: 'chip', style: { paddingRight: '10px' } }, `#${s.id_donacion_parcial} ${s.nombre_organizacion}`, badge(s.estado)))) : h('p', { class: 'muted' }, 'Aún ninguna organización solicitó este lote.'));
    return [l, body];
  };
  const bodyBox = h('div', null, loading());
  const m = modal({ title: `Lote #${id}`, sub: 'Detalle de líneas, saldos y vencimientos (v_saldo_linea)', size: 'xl', body: bodyBox, onClose: done });
  const refresh = async () => { const [, b] = await render(); bodyBox.replaceChildren(b); };
  await refresh();
}
const info = (k, v) => h('div', { class: 'card', style: { padding: '12px 14px', boxShadow: 'none' } }, h('small', { class: 'muted' }, k), h('div', { style: { fontWeight: '700', marginTop: '2px' } }, v));

function agregarLinea(lote, done) {
  formModal({ title: 'Agregar línea al lote', sub: `Lote #${lote}`, submitText: 'Agregar',
    fields: [{ name: 'id_alimento', label: 'Alimento', type: 'select', options: lk('alimentos').map(a => ({ id: a.id, nombre: a.nombre + (a.frio ? '  ❄' : '') })), required: true, full: true },
      { name: 'cantidad', label: 'Cantidad', type: 'number', step: 'any', required: true }, { name: 'id_unidad_medida', label: 'Unidad', type: 'select', options: options(lk('unidades')), required: true },
      { name: 'peso_total_kg', label: 'Peso total (kg)', type: 'number', step: 'any' }, { name: 'costo_unitario', label: 'Costo unitario (S/)', type: 'number', step: '0.01', required: true },
      { name: 'fecha_vencimiento', label: 'Fecha y hora de vencimiento', type: 'datetime', required: true, full: true }],
    onSubmit: async (v) => { const r = await post(`/api/lotes/${lote}/lineas`, v); await done(); return r; } });
}

// ---------------------------------------------------------------- matching por cercania
async function sugerir(l) {
  const r = await safe(null, () => post(`/api/lotes/${l.id_donacion_ofrecida}/sugerir`)); if (!r) return;
  const rows = r.data;
  modal({ title: `Receptoras sugeridas · Lote #${l.id_donacion_ofrecida}`, sub: `${l.nombre_donante} · ${l.nombre_zona} — ranking por cercanía y compatibilidad de frío`, size: 'wide',
    body: [dataTable({ rows, cols: [
      { key: 'posicion', label: 'Puesto', render: r => r.posicion ? h('b', { style: { fontSize: '16px' } }, '#' + r.posicion) : badge('Descartada', 'b-red') },
      { key: 'nombre', label: 'Organización', render: r => h('b', null, r.nombre) }, { key: 'tipo', label: 'Tipo' }, { key: 'nombre_zona', label: 'Zona' },
      { key: 'cercania', label: 'Cercanía', render: r => badge(r.cercania, r.nivel === 1 ? 'b-green' : r.nivel === 2 ? 'b-blue' : 'b-gray') },
      { key: 'apta_frio', label: 'Cadena de frío', render: r => r.apta_frio === 'S' ? badge('Compatible', 'b-green') : badge('Sin refrigeración', 'b-red') }] }),
      h('div', { class: 'callout info' }, 'Equivale al procedimiento sp_sugerir_receptoras: solo organizaciones HABILITADAS, ordenadas por misma zona → mismo distrito → otro distrito; se descartan las que no tienen frío si el lote trae perecibles.')] });
}

async function repartir(l, done) {
  if (!await confirmar({ titulo: `Repartir lote #${l.id_donacion_ofrecida}`, ok: 'Repartir', peligro: false,
    mensaje: 'Se dividirá el saldo de cada línea en partes iguales entre las solicitudes PENDIENTES compatibles con el frío, y esas solicitudes pasarán a ASIGNADA.' })) return;
  const r = await safe(null, () => post(`/api/lotes/${l.id_donacion_ofrecida}/repartir`)); if (!r) return;
  await done();
  modal({ title: 'Resultado del reparto equitativo', sub: 'Procedimiento sp_repartir_equitativo', body: h('div', null, r.data.log.length ? r.data.log.map(x => h('div', { class: 'alert-item' }, ico(x.startsWith('Omitida') || x.startsWith('Linea') ? 'alert' : 'check'), h('span', null, x))) : 'Sin movimientos') });
}
