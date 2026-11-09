import { h, ico, badge, dataTable, safe, run, toast, loading } from '../ui.js';
import { get, post } from '../api.js';

export async function pruebas(root) {
  const lista = await get('/api/pruebas'); const res = {};
  const tbody = h('tbody'), resumen = h('div', { class: 'kpis', style: { marginBottom: '16px' } });
  const kp = (t, v, tone) => h('div', { class: 'kpi' }, h('div', { class: 'ico ' + tone }, ico(tone === 't-green' ? 'check' : tone === 't-red' ? 'x' : 'flask')), h('div', null, h('b', null, v), h('span', null, t)));
  const drawSum = () => { const n = Object.values(res); const ok = n.filter(r => r.aprobada).length; resumen.replaceChildren(kp('Pruebas ejecutadas', `${n.length} / ${lista.length}`, 't-blue'), kp('Aprobadas', ok, 't-green'), kp('Fallidas', n.length - ok, n.length - ok ? 't-red' : 't-gray')); };
  const drawRow = (t, tr) => {
    const r = res[t.id];
    tr.className = 'test-row ' + (r ? (r.aprobada ? 'pass' : 'fail') : '');
    const btn = h('button', { class: 'btn ghost xs' }, ico('play'), r ? 'Repetir' : 'Ejecutar');
    btn.addEventListener('click', async () => { await ejecutar(t, btn); });
    tr.replaceChildren(h('td', null, h('b', null, t.id)), h('td', null, h('b', null, t.regla), h('div', { class: 'muted' }, t.accion)), h('td', null, h('span', { class: 'badge ' + (t.esperado === 'OK' ? 'b-green' : 'b-gray'), style: { fontFamily: 'var(--mono)' } }, t.esperado)),
      h('td', null, r ? h('span', { class: 'badge ' + (r.aprobada ? 'b-green' : 'b-red'), style: { fontFamily: 'var(--mono)' } }, r.obtenido) : h('span', { class: 'muted' }, '—')),
      h('td', { style: { maxWidth: '420px' } }, r ? h('span', { class: 'muted' }, r.mensaje) : null), h('td', null, r ? (r.aprobada ? badge('APROBADA', 'b-green') : badge('FALLIDA', 'b-red')) : badge('Pendiente', 'b-gray')), h('td', { class: 'actions' }, btn));
  };
  const rows = {}; lista.forEach(t => { const tr = h('tr'); rows[t.id] = tr; tbody.appendChild(tr); drawRow(t, tr); });
  const ejecutar = async (t, btn) => {
    try { const r = await run(btn, () => post(`/api/pruebas/${t.id}/ejecutar`)); res[t.id] = r.data; } catch (e) { return; }
    drawRow(t, rows[t.id]); drawSum();
  };
  const all = h('button', { class: 'btn accent' }, ico('play'), 'Ejecutar las 17 pruebas');
  all.addEventListener('click', async () => {
    all.disabled = true; all.classList.add('loading');
    for (const t of lista) { try { const r = await post(`/api/pruebas/${t.id}/ejecutar`); res[t.id] = r.data; } catch (e) { toast(e.message, 'err'); } drawRow(t, rows[t.id]); drawSum(); }
    all.disabled = false; all.classList.remove('loading');
    const ok = Object.values(res).filter(r => r.aprobada).length; toast(`${ok} de ${lista.length} pruebas se comportaron como se esperaba`, ok === lista.length ? 'ok' : 'warn', 'Pruebas completadas');
  });
  drawSum();
  root.append(h('div', { class: 'callout info', style: { marginBottom: '14px' } }, h('b', null, 'Laboratorio de integridad. '), 'Cada prueba arma sus propios datos, intenta una operación que debe ser rechazada (o aceptada) y hace ROLLBACK: no deja rastro en la base. Es la versión interactiva del archivo 09_pruebas.sql.'),
    h('div', { class: 'toolbar' }, all, h('span', { class: 'grow' })), resumen,
    h('div', { class: 'table-wrap' }, h('table', null, h('thead', null, h('tr', null, ['Id', 'Regla probada', 'Esperado', 'Obtenido', 'Mensaje del sistema', 'Resultado', ''].map(x => h('th', null, x)))), tbody)));
}
