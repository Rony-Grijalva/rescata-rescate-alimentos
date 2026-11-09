import { h, ico, badge, sqlBlock, venn, safe, run, toast, toastErr, loading, esc, state } from '../ui.js';
import { get, post, ApiError } from '../api.js';

function resultTable(r) {
  const fmt = (v) => v === null ? h('span', { class: 'badge b-gray', title: 'Valor NULL: no hubo pareja en la otra tabla' }, 'NULL') : (typeof v === 'number' ? Number(v.toFixed(2)).toLocaleString('es-PE') : String(v));
  return h('div', null, h('div', { class: 'table-wrap', style: { maxHeight: '380px' } }, h('table', null, h('thead', null, h('tr', null, r.columnas.map(c => h('th', null, c)))),
    h('tbody', null, r.filas.length ? r.filas.map(f => h('tr', null, f.map(v => h('td', { class: typeof v === 'number' ? 'num' : '' }, fmt(v))))) : h('tr', null, h('td', { colspan: r.columnas.length }, h('div', { class: 'empty' }, 'La consulta no devolvió filas.')))))),
    h('div', { class: 'tfoot' }, `${r.total} fila(s)`));
}

export async function consultas(root) {
  const lista = await get('/api/consultas');
  const me = state.me;
  let cur = lista[0];
  const side = h('div', { class: 'qlist' }), main = h('div');
  const pickQ = (q) => { cur = q; [...side.children].forEach((b, i) => b.classList.toggle('on', lista[i].id === q.id)); showQ(); };
  lista.forEach(q => side.appendChild(h('button', { class: 'qitem' + (q.id === cur.id ? ' on' : ''), onClick: () => pickQ(q) }, venn(q.tipo), h('div', null, h('span', { class: 'id' }, q.id), ' ', h('b', null, q.tipo), h('small', null, q.pregunta.length > 58 ? q.pregunta.slice(0, 56) + '…' : q.pregunta)))));
  const showQ = () => {
    const out = h('div', { style: { marginTop: '14px' } }, h('p', { class: 'muted' }, 'Pulsa «Ejecutar» para correr la consulta sobre la base de datos real.'));
    const btn = h('button', { class: 'btn accent' }, ico('play'), 'Ejecutar consulta');
    btn.addEventListener('click', async () => {
      out.replaceChildren(loading());
      try { const t0 = performance.now(); const r = await run(btn, () => post(`/api/consultas/${cur.id}/ejecutar`)); out.replaceChildren(resultTable(r.data), h('p', { class: 'muted', style: { marginTop: '6px', fontSize: '12.5px' } }, `Ejecutada en ${Math.round(performance.now() - t0)} ms`)); }
      catch (e) { out.replaceChildren(h('div', { class: 'callout' }, e.message)); }
    });
    main.replaceChildren(h('div', { class: 'card' }, h('div', { class: 'card-h' }, venn(cur.tipo), h('div', { style: { flex: 1 } }, h('h3', null, `${cur.id} · ${cur.tipo}`), h('small', null, cur.pregunta)), btn),
      h('div', { class: 'card-b' },
        h('div', { class: 'callout info' }, h('b', null, 'Qué demuestra: '), cur.concepto), h('div', { class: 'callout' }, h('b', null, 'Importancia: '), cur.importancia),
        cur.emulado ? h('div', { class: 'callout' }, 'Tu motor SQLite no soporta este JOIN de forma nativa; se ejecuta la forma equivalente con LEFT JOIN.') : null,
        h('h4', { style: { margin: '14px 0 8px' } }, 'Código SQL'), sqlBlock(cur.sql), out)));
  };
  // consola libre
  const ta = h('textarea', { rows: 5, spellcheck: 'false', placeholder: 'SELECT * FROM v_lotes_disponibles;\n-- Solo lectura: INSERT/UPDATE/DELETE se rechazan.' }, 'SELECT o.nombre_organizacion, COUNT(p.id_donacion_parcial) AS solicitudes\n  FROM organizacion o\n  LEFT JOIN donacion_parcial p ON p.id_organizacion = o.id_organizacion\n GROUP BY o.nombre_organizacion');
  const free = h('div', { style: { marginTop: '14px' } });
  const go = h('button', { class: 'btn' }, ico('terminal'), 'Ejecutar SQL');
  go.addEventListener('click', async () => {
    free.replaceChildren(loading());
    try { const r = await run(go, () => post('/api/sql', { sql: ta.value })); free.replaceChildren(resultTable(r.data)); }
    catch (e) { free.replaceChildren(h('div', { class: 'callout', style: { borderColor: 'var(--bad)', background: 'var(--bad-bg)' } }, h('b', null, e.code + ': '), e.message)); }
  });
  ta.addEventListener('keydown', (e) => { if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') go.click(); });
  const consola = h('div', { class: 'card', style: { marginTop: '22px' } }, h('div', { class: 'card-h' }, ico('terminal'), h('h3', null, 'Consola SQL de solo lectura'), h('small', null, 'Ctrl+Enter para ejecutar')),
    h('div', { class: 'card-b' }, h('p', { class: 'muted', style: { marginBottom: '8px' } }, 'Escribe tu propio SELECT sobre cualquiera de las 22 tablas o las 4 vistas (v_saldo_linea, v_lotes_disponibles, v_demanda_organizacion, v_comprobante_valorizado). Cambia datos en otros módulos y vuelve a ejecutar para ver el efecto.'), ta, h('div', { style: { marginTop: '10px' } }, go), free));
  root.append(h('div', { class: 'grid g-1-2', style: { gridTemplateColumns: '340px 1fr', alignItems: 'start' } }, side, main), consola);
  showQ();
}
