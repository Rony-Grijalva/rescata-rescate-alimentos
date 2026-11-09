import { h, badge, dataTable, seg, fdate, loading } from '../ui.js';
import { get } from '../api.js';

export async function bitacora(root) {
  let rows = await get('/api/bitacora?limit=300'), f = '';
  const box = h('div');
  const draw = () => box.replaceChildren(dataTable({ rows: rows.filter(r => !f || r.resultado === f), empty: 'Sin registros.', foot: 'Últimos 300 eventos',
    cols: [{ key: 'id_bitacora', label: '#' }, { key: 'fecha', label: 'Fecha', render: r => fdate(r.fecha) }, { key: 'rol', label: 'Rol', render: r => badge(r.rol, 'b-navy') }, { key: 'accion', label: 'Acción', render: r => badge(r.accion, r.accion === 'RECHAZADO' ? 'b-red' : 'b-blue') }, { key: 'entidad', label: 'Entidad' }, { key: 'detalle', label: 'Detalle' }, { key: 'resultado', label: 'Resultado', render: r => badge(r.resultado) }] }));
  root.append(h('p', { class: 'muted', style: { marginBottom: '14px' } }, 'Registro de auditoría de todas las operaciones de escritura, incluidas las rechazadas por una regla o por falta de privilegios.'),
    h('div', { class: 'toolbar' }, seg([['', 'Todo'], ['OK', 'Correctas'], ['ERROR', 'Rechazadas']], '', (v) => { f = v; draw(); }), h('span', { class: 'grow' }), h('button', { class: 'btn ghost sm', onClick: async () => { rows = await get('/api/bitacora?limit=300'); draw(); } }, 'Actualizar')), box);
  draw();
}
