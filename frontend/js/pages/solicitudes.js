import { h, ico, badge, dataTable, iconBtn, searchBox, seg, modal, confirmar, buildForm, safe, run, toast, money, numf, fdate, loading, lk, options, can, state } from '../ui.js';
import { get, post, del, ApiError } from '../api.js';

const SIGUIENTE = (r) => {
  if (r.estado === 'ENTREGADA') return r.comprobante ? ['Entregada. Constancia ' + r.comprobante, null] : ['Entregada. El coordinador emitirá su constancia.', null];
  if (r.estado === 'PENDIENTE') return ['Esperando que el coordinador le asigne alimentos.', null];
  if (!r.id_despacho) return ['Alimentos asignados: programe el recojo.', 'programar'];
  return ['Recojo programado: siga el avance en «Mis despachos».', 'despachos'];
};

export async function solicitudes(root) {
  const org = state.rol === 'organizacion';
  let q = '', estado = '', rows = [];
  const box = h('div', null, loading());
  const reload = async () => { const p = new URLSearchParams(); if (q) p.set('q', q); if (estado) p.set('estado', estado); rows = await get('/api/solicitudes?' + p); draw(); };
  const draw = () => box.replaceChildren(dataTable({
    rows, empty: org ? 'Aún no ha pedido ningún lote. Vaya a «Lotes disponibles» para solicitar uno.' : 'No hay solicitudes con ese criterio.',
    cols: [{ key: 'id_donacion_parcial', label: 'N.º', render: r => h('b', null, '#' + r.id_donacion_parcial) },
      org ? null : { key: 'nombre_organizacion', label: 'Organización receptora', render: r => h('div', null, h('b', null, r.nombre_organizacion), r.tiene_refrigeracion ? h('span', { style: { color: 'var(--primary)', marginLeft: '6px' }, title: 'Tiene refrigeración' }, ico('snow')) : null) },
      { key: 'id_donacion_ofrecida', label: 'Lote', render: r => h('div', null, '#' + r.id_donacion_ofrecida, h('div', { class: 'muted' }, r.nombre_donante)) },
      { key: 'fecha_solicitud', label: 'Solicitada', render: r => fdate(r.fecha_solicitud) },
      { key: 'estado', label: 'Estado', render: r => badge(r.estado) }, { key: 'lineas', label: 'Líneas', num: true },
      { key: 'peso_kg', label: 'Peso', num: true, render: r => numf(r.peso_kg) + ' kg' }, { key: 'valor', label: 'Valor', num: true, render: r => money(r.valor) },
      org ? { key: 'siguiente', label: 'Siguiente paso', sort: false, render: r => { const [t, a] = SIGUIENTE(r); return h('div', { class: 'next' }, h('span', null, t), a === 'programar' ? h('a', { class: 'btn accent xs', href: '#/logistica?programar=' + r.id_donacion_parcial }, ico('truck'), 'Programar recojo') : a === 'despachos' ? h('a', { class: 'btn ghost xs', href: '#/logistica' }, 'Ver despacho') : null); } }
          : { key: 'comprobante', label: 'Comprobante', render: r => r.comprobante ? badge(r.comprobante, 'b-green') : null }].filter(Boolean),
    actions: (r) => [iconBtn(org ? 'eye' : 'hand', org ? 'Ver detalle de mi solicitud' : 'Gestionar el reparto de esta solicitud', () => gestionar(r.id_donacion_parcial, reload), 'ok'),
      can('solicitudes', 'd') && (!org || (r.estado === 'PENDIENTE' && !r.lineas)) ? iconBtn('trash', org ? 'Cancelar mi solicitud' : 'Eliminar solicitud', async () => { if (await confirmar({ titulo: `${org ? 'Cancelar' : 'Eliminar'} solicitud #${r.id_donacion_parcial}`, ok: org ? 'Cancelar solicitud' : 'Eliminar', mensaje: org ? 'Se cancelará su pedido y el lote quedará libre para otras organizaciones.' : 'Se eliminará la solicitud y su reparto; el saldo vuelve al lote. No se permite si ya tiene despacho.' })) safe(null, async () => { const x = await del('/api/solicitudes/' + r.id_donacion_parcial); await reload(); return x; }); }, 'danger') : null],
    foot: `${rows.length} solicitud(es)`,
  }));
  const bar = h('div', { class: 'toolbar' }, searchBox((v) => { q = v; reload(); }, org ? 'Buscar por donante o #' : 'Buscar por organización, donante o #'),
    seg([['', 'Todas'], ['PENDIENTE', 'Pendientes'], ['ASIGNADA', 'Asignadas'], ['ENTREGADA', 'Entregadas']], '', (v) => { estado = v; reload(); }), h('span', { class: 'grow' }),
    org ? h('a', { class: 'btn accent', href: '#/lotes' }, ico('plus'), 'Pedir un lote') : null);
  root.append(h('p', { class: 'muted', style: { marginBottom: '14px' } }, org
    ? 'PENDIENTE: el coordinador aún no le asigna alimentos · ASIGNADA: ya puede programar el recojo · ENTREGADA: recibió los alimentos y se emite su constancia. El estado cambia solo, según el avance.'
    : 'Las organizaciones piden lotes y aquí usted les asigna líneas concretas. Las reglas de saldo y cadena de frío se validan al repartir; el estado de cada solicitud se actualiza solo (asignada al repartir, entregada al registrar el arribo).'), bar, box);
  await reload();
}

async function gestionar(id, done) {
  const bodyBox = h('div', null, loading());
  const m = modal({ title: `Solicitud #${id}`, sub: state.rol === 'organizacion' ? 'Alimentos que le asignaron y estado de su pedido' : 'Reparto de líneas, estado y despacho', size: 'xl', body: bodyBox, onClose: done });
  const refresh = async () => {
    const s = await get('/api/solicitudes/' + id);
    const edit = can('reparto', 'c') && s.estado !== 'ENTREGADA';
    // formulario de asignacion
    let asignar = null;
    if (edit) {
      const f = buildForm([
        { name: 'linea', label: 'Línea del lote', type: 'select', required: true, options: s.lineas_lote.map(l => ({ id: l.id, nombre: `${l.nombre_alimento}${l.requiere_refrigeracion ? ' ❄' : ''} — saldo ${numf(l.saldo)} ${l.tipo_medida}${l.compatible ? '' : ' (requiere frío)'}` })) },
        { name: 'cantidad', label: 'Cantidad a repartir', type: 'number', step: 'any', required: true }], {});
      f.el.style.gridTemplateColumns = '2fr 1fr auto'; f.el.style.alignItems = 'end';
      f.inputs.linea.addEventListener('change', () => { const l = s.lineas_lote.find(x => String(x.id) === f.inputs.linea.value); if (l) f.inputs.cantidad.value = l.saldo; });
      const b = h('button', { class: 'btn', type: 'button' }, ico('plus'), 'Asignar');
      b.addEventListener('click', async () => { if (!f.check()) return; try { await run(b, () => post(`/api/solicitudes/${id}/asignar`, f.read())); await refresh(); } catch (e) { if (e instanceof ApiError && e.fields) f.setErrors(e.fields); } });
      f.el.appendChild(h('div', { class: 'field' }, b));
      asignar = h('div', { class: 'card', style: { padding: '14px 16px', margin: '14px 0', boxShadow: 'none' } }, h('h4', { style: { marginBottom: '10px' } }, 'Asignar línea (sp_asignar_linea)'), f.el,
        h('p', { class: 'muted', style: { marginTop: '8px', fontSize: '12.5px' } }, 'Se propone el saldo completo de la línea; puede reducirlo. Si pide más que el saldo, o un alimento con ❄ para una organización sin refrigeración, la regla de negocio lo rechaza.'));
    }
    const acciones = [];
    bodyBox.replaceChildren(h('div', null,
      h('div', { class: 'grid g4' }, kv('Organización', s.nombre_organizacion), kv('Lote / Donante', `#${s.id_donacion_ofrecida} · ${s.nombre_donante}`), kv('Estado', badge(s.estado)), kv('Comprobante', s.comprobante ? badge(s.comprobante, 'b-green') : '—')),
      h('div', { class: 'grid g3', style: { marginTop: '12px' } }, kv('Peso asignado', numf(s.peso_kg) + ' kg'), kv('Valor asignado', money(s.valor)), kv('Despacho', s.id_despacho ? '#' + s.id_despacho : 'Sin programar')),
      h('div', { class: 'toolbar', style: { marginTop: '16px' } }, h('h4', { style: { flex: 1 } }, 'Reparto asignado'), ...acciones),
      dataTable({ rows: s.reparto, empty: 'Todavía no se asignó ninguna línea.', cols: [{ key: 'nombre_alimento', label: 'Alimento', render: r => h('b', null, r.nombre_alimento) }, { key: 'cantidad', label: 'Cantidad', num: true, render: r => `${numf(r.cantidad)} ${r.tipo_medida}` }, { key: 'costo_unitario', label: 'Costo unit.', num: true, render: r => money(r.costo_unitario) }, { key: 'valor', label: 'Valor', num: true, render: r => money(r.valor) }],
        actions: (r) => edit ? [iconBtn('trash', 'Quitar este reparto', () => safe(null, async () => { const x = await del('/api/repartos/' + r.id_detalle_donacion_parcial); await refresh(); return x; }), 'danger')] : [] }),
      asignar,
      edit ? h('h4', { style: { margin: '14px 0 8px' } }, 'Líneas disponibles en el lote') : null,
      edit ? dataTable({ rows: s.lineas_lote, cols: [{ key: 'nombre_alimento', label: 'Alimento', render: r => h('span', null, r.nombre_alimento, r.requiere_refrigeracion ? h('span', { style: { color: 'var(--primary)', marginLeft: '6px' } }, ico('snow')) : null) },
        { key: 'cantidad_publicada', label: 'Publicado', num: true, render: r => `${numf(r.cantidad_publicada)} ${r.tipo_medida}` }, { key: 'saldo', label: 'Saldo', num: true, render: r => h('b', null, numf(r.saldo)) },
        { key: 'compatible', label: 'Compatible', render: r => r.compatible ? badge('Sí', 'b-green') : badge('Requiere frío', 'b-red') }] }) : null));
  };
  await refresh();
}
const kv = (k, v) => h('div', { class: 'card', style: { padding: '10px 14px', boxShadow: 'none' } }, h('small', { class: 'muted' }, k), h('div', { style: { fontWeight: '700', marginTop: '2px' } }, v));
