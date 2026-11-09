import { h, ico, badge, modal, loading, safe, run, numf, sqlBlock } from '../ui.js';
import { get, post } from '../api.js';

const resultTable = (r) => h('div', null, h('div', { class: 'table-wrap', style: { maxHeight: '420px' } }, h('table', null, h('thead', null, h('tr', null, r.columnas.map(c => h('th', null, c)))),
  h('tbody', null, r.filas.map(f => h('tr', null, f.map(v => h('td', null, v === null ? h('span', { class: 'badge b-gray' }, 'NULL') : String(v)))))))), h('div', { class: 'tfoot' }, `${r.total} fila(s) (máx. 500)`));

export async function modelo(root) {
  const data = await get('/api/esquema');
  const nuevo = new Set(['vehiculo']);
  const grid = h('div', { class: 'tgrid' });
  data.forEach(t => {
    const card = h('div', { class: 'tcard' });
    const ul = h('ul', null, t.columnas.map(c => { const fk = t.fks.find(f => f.columna === c.nombre); return h('li', null, h('span', { class: c.pk ? 'pk' : fk ? 'fk' : '' }, c.pk ? 'PK' : fk ? 'FK' : '··'), h('b', null, c.nombre), h('span', { class: 'muted mono' }, c.tipo), fk ? h('span', { class: 'muted' }, `→ ${fk.tabla}`) : null, c.obligatorio && !c.pk ? h('span', { class: 'muted' }, '*') : null); }));
    card.append(h('h4', { style: { cursor: 'pointer' }, onClick: () => card.classList.toggle('open') }, ico('db'), t.tabla, nuevo.has(t.tabla) ? badge('NUEVA', 'b-amber') : t.app ? badge('APP', 'b-gray') : null, h('span', { class: 'badge b-blue' }, numf(t.filas, 0) + ' filas')),
      h('div', { class: 'muted', style: { fontSize: '12.5px', marginTop: '4px' } }, `${t.columnas.length} columnas · ${t.fks.length} claves foráneas`), ul,
      h('div', { style: { marginTop: '10px', display: 'flex', gap: '6px' } }, h('button', { class: 'btn ghost xs', onClick: () => card.classList.toggle('open') }, 'Columnas'),
        h('button', { class: 'btn ghost xs', onClick: async (e) => { const r = await run(e.currentTarget, () => post('/api/sql', { sql: `SELECT * FROM ${t.tabla} LIMIT 50` })).catch(() => null); if (r) modal({ title: t.tabla, sub: 'Primeras 50 filas leídas de la base de datos', size: 'xl', body: resultTable(r.data) }); } }, ico('eye'), 'Ver datos')));
    grid.appendChild(card);
  });
  const img = (f, t) => h('img', { src: '/assets/' + f, alt: t, style: { width: '100%', borderRadius: '12px', border: '1px solid var(--line)', cursor: 'zoom-in', background: '#fff' }, onClick: () => modal({ title: t, size: 'xl', body: h('img', { src: '/assets/' + f, alt: t, style: { width: '100%' } }) }) });
  root.append(h('div', { class: 'card', style: { marginBottom: '18px' } }, h('div', { class: 'card-h' }, h('h3', null, 'Modelo relacional corregido (22 tablas)'), h('small', null, 'Clic en la imagen para ampliar')),
    h('div', { class: 'card-b' }, h('div', { class: 'grid g2' }, img('modelo_22_general.png', 'Modelo general de 22 tablas'), img('modelo_22_detalle.png', 'Modelo detallado: columnas y llaves')),
      h('p', { class: 'muted', style: { marginTop: '10px' } }, 'Verde ★ = columna agregada con ALTER TABLE (ruc, tiene_refrigeracion, monto_total, id_organizacion) · rojo = FK restituida (fk_parcial_ofrecida) · ámbar = vehículo.'))),
    h('div', { class: 'toolbar' }, h('h3', { class: 'grow' }, 'Explorador de la base de datos real'), h('span', { class: 'muted' }, `${data.length} tablas (22 del modelo + bitácora de la aplicación)`)), grid);
}
