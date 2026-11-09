import { h, ico, badge, buildForm, run, toast, loading, lk, options, state } from '../ui.js';
import { get, put, ApiError } from '../api.js';

const kv = (k, v) => h('div', { class: 'card', style: { padding: '10px 14px', boxShadow: 'none' } }, h('small', { class: 'muted' }, k), h('div', { style: { fontWeight: '700', marginTop: '2px' } }, v || '—'));

export async function perfil(root) {
  const don = state.rol === 'donante';
  root.append(loading());
  const p = await get('/api/perfil');
  const campos = don
    ? [{ name: 'nombre_donante', label: 'Nombre o razón social', required: true, full: true, maxlength: 150 }, { name: 'id_zona', label: 'Zona', type: 'select', options: options(lk('zonas')), required: true },
       { name: 'direccion', label: 'Dirección', full: true, hint: 'Se propone al publicar un lote' }, { name: 'telefono', label: 'Teléfono' }, { name: 'email', label: 'Correo', type: 'email' }]
    : [{ name: 'nombre_organizacion', label: 'Nombre de la organización', required: true, full: true }, { name: 'id_zona', label: 'Zona', type: 'select', options: options(lk('zonas')), required: true },
       { name: 'direccion', label: 'Dirección', full: true }, { name: 'tiene_refrigeracion', label: 'Cuenta con refrigeración', type: 'checkbox', hint: 'Si la marca, podrá recibir alimentos perecibles (❄). Si no, solo se le asignarán líneas sin frío.' }];
  const f = buildForm(campos, p);
  const btn = h('button', { class: 'btn', type: 'button' }, ico('check'), 'Guardar cambios');
  btn.addEventListener('click', async () => {
    if (!f.check()) { toast('Complete los campos obligatorios.', 'warn', 'Faltan datos'); return; }
    try { await run(btn, () => put('/api/perfil', f.read())); await get('/api/lookups').then(l => { state.lookups = l; }); }
    catch (e) { if (e instanceof ApiError && e.fields) f.setErrors(e.fields); }
  });
  root.replaceChildren(
    h('div', { class: 'grid g3', style: { marginBottom: '16px' } }, don ? [kv('RUC', p.ruc), kv('Estado', badge(p.estado)), kv('Lotes publicados', p.lotes)] : [kv('Tipo', p.tipo), kv('Estado', badge(p.estado)), kv('Solicitudes realizadas', p.solicitudes)]),
    h('div', { class: 'card' }, h('div', { class: 'card-h' }, h('h3', null, don ? 'Datos de su empresa' : 'Datos de su organización'), h('small', null, 'Estado, tipo y RUC los administra el coordinador')), h('div', { class: 'card-b' }, f.el, h('div', { style: { marginTop: '14px' } }, btn))));
}
