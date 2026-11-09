import { h, ico, badge, dataTable, iconBtn, modal, confirmar, formModal, safe, run, tabs, toast, money, numf, fdate, loading, lk, options, can } from '../ui.js';
import { get, post, del } from '../api.js';
import { state, param } from '../state.js';
const ORG = () => state.rol === 'organizacion';
import { crudPage } from './crudpage.js';

const vehiculos = crudPage({
  res: 'vehiculos', perm: 'vehiculos', singular: 'vehículo', newLabel: 'Nuevo vehículo',
  intro: 'La flota tiene capacidad válida (CHECK > 0), placa única y, opcionalmente, una organización propietaria: un vehículo con dueño solo puede usarse para sus propios despachos. Los vehículos de voluntarios son compartidos y no se pueden modificar.',
  rowOk: (r) => !ORG() || r.id_organizacion != null,
  cols: () => [{ key: 'id_vehiculo', label: '#' }, { key: 'placa', label: 'Placa', render: r => h('b', { class: 'mono' }, r.placa) }, { key: 'marca', label: 'Marca' }, { key: 'modelo', label: 'Modelo' },
    { key: 'capacidad_kg', label: 'Capacidad', num: true, render: r => numf(r.capacidad_kg) + ' kg' }, { key: 'nombre_organizacion', label: 'Propietaria', render: r => r.nombre_organizacion || h('span', { class: 'badge b-gray' }, 'Voluntarios (compartido)') }, { key: 'despachos', label: 'Despachos', num: true }],
  fields: () => [{ name: 'placa', label: 'Placa', required: true, placeholder: 'ABC-123', hint: 'Formato ABC-123, única' }, { name: 'marca', label: 'Marca' }, { name: 'modelo', label: 'Modelo' },
    { name: 'capacidad_kg', label: 'Capacidad (kg)', type: 'number', step: 'any', required: true }, ...(ORG() ? [] : [{ name: 'id_organizacion', label: 'Organización propietaria', type: 'select', options: options(lk('organizaciones')), placeholder: 'Ninguna (voluntarios)', full: true }])],
  onChange: async () => { await import('../app.js').then(m => m.refreshLookups()); },
});
const personas = crudPage({
  res: 'personas', perm: 'personas', singular: 'persona de recojo', newLabel: 'Nueva persona',
  intro: 'Personas autorizadas por cada organización para recoger los alimentos. El documento es único por organización y tipo (uq_persona_org_doc).',
  cols: () => [{ key: 'id_persona_recojo', label: '#' }, { key: 'apellidos', label: 'Nombre', render: r => h('b', null, `${r.nombres} ${r.apellidos}`) }, ORG() ? null : { key: 'nombre_organizacion', label: 'Organización' },
    { key: 'num_documento', label: 'Documento', render: r => `${r.tipo_doc} ${r.num_documento}` }, { key: 'telefono', label: 'Teléfono' }, { key: 'sexo', label: 'Sexo' }].filter(Boolean),
  filters: () => ORG() ? [] : [{ name: 'id_organizacion', label: 'Organización', lookup: 'organizaciones' }],
  fields: () => [...(ORG() ? [] : [{ name: 'id_organizacion', label: 'Organización', type: 'select', options: options(lk('organizaciones')), required: true, full: true }]), { name: 'nombres', label: 'Nombres', required: true }, { name: 'apellidos', label: 'Apellidos', required: true },
    { name: 'id_tipo_documento', label: 'Tipo de documento', type: 'select', options: options(lk('tipos_doc')), required: true }, { name: 'num_documento', label: 'N.º de documento', required: true },
    { name: 'sexo', label: 'Sexo', type: 'select', options: [{ id: 'M', nombre: 'Masculino' }, { id: 'F', nombre: 'Femenino' }] }, { name: 'telefono', label: 'Teléfono' }, { name: 'email', label: 'Correo', type: 'email' }],
});

const FASES = [['Programado', 'Programado'], ['llegada', 'Llegada al recojo'], ['salida', 'Salida'], ['arribo', 'Entrega']];

async function despachos(root) {
  const box = h('div', null, loading());
  const reload = async () => {
    const rows = await get('/api/despachos');
    box.replaceChildren(rows.length ? h('div', { class: 'card' }, rows.map(d => card(d, reload))) : h('div', { class: 'card' }, h('div', { class: 'empty' }, ico('truck'), h('div', null, ORG() ? 'Aún no tiene despachos. Cuando una solicitud suya esté ASIGNADA podrá programar el recojo aquí.' : 'Aún no hay despachos. Una organización debe programar uno para una solicitud ASIGNADA.'))));
  };
  root.append(h('div', { class: 'toolbar' }, h('p', { class: 'muted grow' }, (ORG() ? 'Programe el recojo de una solicitud ASIGNADA con uno de sus vehículos (o uno de voluntarios), designe a las personas autorizadas y registre llegada, salida y entrega en orden. Al registrar la entrega, su solicitud pasa a ENTREGADA.' : 'Un despacho une una solicitud ASIGNADA con un vehículo. Se valida propietario, capacidad y estado; los hitos deben registrarse en orden y el arribo marca la donación como ENTREGADA.')),
    can('despachos', 'c') ? h('button', { class: 'btn accent', onClick: () => programar(reload) }, ico('plus'), 'Programar despacho') : null), box);
  await reload();
  if (ORG() && param('programar')) { const id = param('programar'); history.replaceState(null, '', '#/logistica'); programar(reload, id); }
}

function card(d, reload) {
  const hitos = [d.fecha_programada, d.fecha_llegada, d.fecha_salida, d.fecha_arribo];
  const idx = hitos.findLastIndex(x => !!x), sig = FASES[idx + 1];
  const stepper = h('div', { class: 'stepper' });
  FASES.forEach(([k, lab], i) => { if (i) stepper.appendChild(h('div', { class: 'ln' + (hitos[i] ? ' on' : '') })); stepper.appendChild(h('div', { class: 's' + (hitos[i] ? ' on' : i === idx + 1 ? ' cur' : '') }, h('i', null, hitos[i] ? '✓' : i + 1), lab, h('small', null, hitos[i] ? fdate(hitos[i]) : ''))); });
  const pct = d.capacidad_kg ? Math.min(100, d.peso_kg / d.capacidad_kg * 100) : 0;
  return h('div', { class: 'dcard' },
    h('div', { style: { display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' } }, h('h3', null, `Despacho #${d.id_despacho}`), badge(d.fase), h('span', { class: 'muted' }, `Solicitud #${d.id_donacion_parcial} · ${d.nombre_organizacion}`), h('span', { style: { flex: 1 } }),
      sig && sig[0] !== 'Programado' && can('despachos', 'u') ? h('button', { class: 'btn ok sm', onClick: (e) => safe(e.currentTarget, async () => { const x = await post(`/api/despachos/${d.id_despacho}/hito`, { hito: sig[0] }); await reload(); return x; }) }, ico('check'), `Registrar: ${sig[1]}`) : null,
      !d.fecha_arribo && can('despachos', 'd') ? iconBtn('trash', 'Cancelar despacho', async () => { if (await confirmar({ titulo: 'Cancelar despacho', mensaje: `¿Cancelar el despacho #${d.id_despacho}?`, ok: 'Cancelar despacho' })) safe(null, async () => { const x = await del('/api/despachos/' + d.id_despacho); await reload(); return x; }); }, 'danger') : null),
    h('div', { class: 'meta' }, h('span', null, 'Vehículo: ', h('b', null, `${d.placa} · ${d.modelo || ''}`)), h('span', null, 'Carga: ', h('b', null, `${numf(d.peso_kg)} kg de ${numf(d.capacidad_kg)} kg`)), h('span', null, 'Programado: ', h('b', null, fdate(d.fecha_programada)))),
    h('div', { class: 'bar' + (pct > 85 ? ' warn' : ''), style: { maxWidth: '320px', margin: '8px 0' } }, h('i', { style: { width: pct + '%' } })), stepper,
    h('div', { style: { display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap', marginTop: '8px' } }, h('span', { class: 'muted' }, 'Responsables de recojo:'),
      d.responsables.length ? d.responsables.map(r => h('span', { class: 'chip' }, r.nombre, can('despachos', 'u') ? h('button', { title: 'Retirar', onClick: () => safe(null, async () => { const x = await del(`/api/despachos/${d.id_despacho}/responsables/${r.id_persona_recojo}`); await reload(); return x; }) }, '×') : null)) : h('span', { class: 'muted' }, 'ninguno'),
      can('despachos', 'u') && !d.fecha_arribo ? h('button', { class: 'btn ghost xs', onClick: () => responsable(d, reload) }, ico('plus'), 'Asignar') : null));
}

async function responsable(d, reload) {
  const per = await get('/api/crud/personas?f_id_organizacion=' + (await get('/api/solicitudes/' + d.id_donacion_parcial)).id_organizacion);
  formModal({ title: 'Asignar responsable de recojo', sub: `Despacho #${d.id_despacho} — solo personas de ${d.nombre_organizacion}`, submitText: 'Asignar',
    fields: [{ name: 'id_persona_recojo', label: 'Persona', type: 'select', required: true, full: true, options: per.map(p => ({ id: p.id_persona_recojo, nombre: `${p.nombres} ${p.apellidos} (${p.tipo_doc} ${p.num_documento})` })), hint: per.length ? '' : 'Esta organización no tiene personas de recojo: regístralas en la pestaña correspondiente.' }],
    onSubmit: async (v) => { const r = await post(`/api/despachos/${d.id_despacho}/responsables`, v); await reload(); return r; } });
}

async function programar(reload, preselect) {
  const [sols, vehs] = await Promise.all([get('/api/solicitudes?estado=ASIGNADA'), get('/api/crud/vehiculos')]);
  const libres = sols.filter(s => !s.id_despacho);
  const m = formModal({ title: 'Programar despacho', sub: 'Elija la solicitud y el vehículo que hará el recojo', submitText: 'Programar', values: preselect ? { id_donacion_parcial: preselect } : {},
    fields: [{ name: 'id_donacion_parcial', label: 'Solicitud ASIGNADA', type: 'select', required: true, full: true, options: libres.map(s => ({ id: s.id_donacion_parcial, nombre: `#${s.id_donacion_parcial} · ${s.nombre_organizacion} · ${numf(s.peso_kg)} kg` })), hint: libres.length ? '' : 'No hay solicitudes ASIGNADAS sin despacho.' },
      { name: 'id_vehiculo', label: 'Vehículo', type: 'select', required: true, full: true, options: vehs.map(v => ({ id: v.id_vehiculo, nombre: `${v.placa} · ${v.modelo || ''} · ${numf(v.capacidad_kg)} kg · ${v.nombre_organizacion || 'voluntarios'}` })), hint: 'Se valida que el vehículo sea suyo o compartido y que soporte el peso de la carga.' },
      { name: 'fecha_programada', label: 'Fecha y hora programada', type: 'datetime' }],
    onSubmit: async (v) => { const r = await post('/api/despachos', v); await reload(); return r; } });
}

export async function logistica(root) {
  const body = h('div'); const V = { despachos, vehiculos, personas };
  const show = async (k) => { body.replaceChildren(); await V[k](body); };
  root.append(tabs(ORG() ? [['despachos', 'Mis despachos'], ['vehiculos', 'Mi flota'], ['personas', 'Mi personal de recojo']] : [['despachos', 'Despachos'], ['vehiculos', 'Vehículos'], ['personas', 'Personas de recojo']], 'despachos', show), body);
  await show('despachos');
}
