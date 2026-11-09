import { h, ico, badge, dataTable, iconBtn, modal, safe, money, numf, fdate, fday, loading, can, state } from '../ui.js';
import { get, post } from '../api.js';

export async function comprobantes(root) {
  const rol = state.rol, emite = can('comprobantes', 'c');
  const box = h('div', null, loading()), pend = h('div');
  const reload = async () => {
    const [rows, sols] = await Promise.all([get('/api/comprobantes'), emite ? get('/api/solicitudes?estado=ENTREGADA') : Promise.resolve([])]);
    const sin = sols.filter(s => !s.comprobante);
    if (emite) pend.replaceChildren(h('div', { class: 'card', style: { marginBottom: '18px' } }, h('div', { class: 'card-h' }, ico('alert'), h('h3', null, 'Entregas pendientes de comprobante'), h('small', null, `${sin.length}`)),
      sin.length ? dataTable({ rows: sin, cols: [{ key: 'id_donacion_parcial', label: 'Solicitud', render: r => '#' + r.id_donacion_parcial }, { key: 'nombre_organizacion', label: 'Organización' }, { key: 'nombre_donante', label: 'Donante' }, { key: 'valor', label: 'Valor', num: true, render: r => money(r.valor) }],
        actions: (r) => [h('button', { class: 'btn accent xs', onClick: (e) => safe(e.currentTarget, async () => { const x = await post(`/api/solicitudes/${r.id_donacion_parcial}/comprobante`); await reload(); return x; }) }, ico('receipt'), 'Emitir')] })
        : h('div', { class: 'card-b muted' }, 'No hay entregas sin comprobante: todas las entregas ya tienen su constancia.')));
    box.replaceChildren(dataTable({ rows, empty: rol === 'donante' ? 'Aún no tiene constancias: se emiten cuando una organización recibe sus alimentos.' : rol === 'organizacion' ? 'Aún no tiene constancias: se emiten cuando se completa una entrega.' : 'Aún no se emitió ningún comprobante.', cols: [
      { key: 'comprobante', label: 'Comprobante', render: r => h('b', { class: 'mono' }, r.comprobante) }, { key: 'fecha_emision', label: 'Emitido', render: r => fdate(r.fecha_emision) },
      rol === 'donante' ? null : { key: 'nombre_donante', label: 'Donante', render: r => h('div', null, r.nombre_donante, h('div', { class: 'muted mono' }, r.ruc || 'sin RUC')) },
      rol === 'organizacion' ? null : { key: 'receptora', label: 'Receptora' },
      { key: 'monto_emitido', label: rol === 'auditor' || rol === 'admin' ? 'Monto emitido' : 'Monto donado', num: true, render: r => money(r.monto_emitido) },
      rol === 'auditor' || rol === 'admin' ? { key: 'monto_recalculado', label: 'Recalculado', num: true, render: r => money(r.monto_recalculado) } : null,
      rol === 'auditor' || rol === 'admin' ? { key: 'ok', label: 'Verificación', sort: false, render: r => Math.abs(r.monto_emitido - r.monto_recalculado) < 0.005 ? badge('Coincide', 'b-green') : badge('Difiere', 'b-red') } : null].filter(Boolean),
      actions: (r) => [iconBtn('eye', 'Ver e imprimir', () => ver(r.id_comprobante), 'info')], foot: `${rows.length} comprobante(s)` }));
  };
  const intro = { admin: 'Solo se emite comprobante de una donación ENTREGADA (ORA-20006) y una sola vez (ORA-20007). El monto se congela al emitir.',
    donante: 'Constancia de donación de los alimentos que ya recibieron las organizaciones; sirve como sustento según la Ley 30498. Puede verla e imprimirla.',
    organizacion: 'Comprobantes de los alimentos que su organización ya recibió. Puede verlos e imprimirlos.',
    auditor: 'Compruebe que el monto emitido (congelado al emitir) coincide con el valor recalculado del reparto. Solo lectura.' }[rol];
  root.append(h('p', { class: 'muted', style: { marginBottom: '14px' } }, intro), pend, emite ? h('h3', { style: { margin: '6px 0 10px' } }, 'Comprobantes emitidos') : null, box);
  await reload();
}

async function ver(id) {
  const c = await get('/api/comprobantes/' + id);
  modal({ title: 'Comprobante ' + c.comprobante, sub: 'Constancia de donación de alimentos', size: 'wide',
    body: h('div', null, h('div', { class: 'comp' },
      h('h2', null, 'RESCATA — Constancia de donación'), h('p', { class: 'mono' }, `N.º ${c.comprobante} · ${fday(c.fecha_emision)}`),
      h('hr'), h('p', null, h('b', null, 'Donante: '), c.nombre_donante, ' · RUC ', c.ruc || '—'), h('p', null, h('b', null, 'Receptora: '), c.receptora),
      h('table', { style: { width: '100%', margin: '12px 0', borderCollapse: 'collapse' } }, h('thead', null, h('tr', null, ['Alimento', 'Cant.', 'Costo unit.', 'Importe'].map((t, i) => h('th', { style: { textAlign: i ? 'right' : 'left', borderBottom: '2px solid #1f3864', background: '#fff', color: '#333' } }, t)))),
        h('tbody', null, c.lineas.map(l => h('tr', null, h('td', null, l.nombre_alimento), h('td', { style: { textAlign: 'right' } }, `${numf(l.cantidad)} ${l.tipo_medida}`), h('td', { style: { textAlign: 'right' } }, money(l.costo_unitario)), h('td', { style: { textAlign: 'right' } }, money(l.importe)))))),
      h('p', { style: { textAlign: 'right', fontSize: '17px' } }, h('b', null, 'Total donado: ', money(c.monto_emitido))),
      h('p', { style: { fontSize: '12px', color: '#666' } }, c.coincide ? '✔ El monto emitido coincide con el valor recalculado del reparto.' : '⚠ El monto emitido difiere del valor actual del reparto.')),
      h('div', { style: { textAlign: 'center', marginTop: '14px' } }, h('button', { class: 'btn', onClick: () => window.print() }, ico('print'), 'Imprimir')))
  });
}
