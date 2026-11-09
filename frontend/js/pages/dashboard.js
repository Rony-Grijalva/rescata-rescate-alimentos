import { h, ico, badge, hbars, vbars, donut, money, numf, horas, fdate, loading, state } from '../ui.js';
import { get } from '../api.js';

const FMT = { n: (v) => numf(v, 0), kg: (v) => numf(v, 1) + ' kg', money: money, money0: (v) => 'S/ ' + numf(v, 0) };
const kpi = (k) => h('div', { class: 'kpi' }, h('div', { class: 'ico ' + k.tone }, ico(k.ic)), h('div', null, h('b', null, (FMT[k.fmt] || FMT.n)(k.v)), h('span', null, k.lab)));
const card = (title, sub, body) => h('div', { class: 'card' }, h('div', { class: 'card-h' }, h('h3', null, title), sub ? h('small', null, sub) : null), h('div', { class: 'card-b' }, body));
const chart = (g) => card(g.titulo, g.sub, !g.datos.length || g.datos.every(x => !x.valor) ? h('div', { class: 'empty' }, 'Todavía no hay datos para mostrar.')
  : g.tipo === 'donut' ? donut(g.datos) : g.tipo === 'vbars' ? vbars(g.datos, { fmt: FMT[g.fmt] }) : hbars(g.datos, { fmt: FMT[g.fmt] || numf, color: g.color }));

const BAN = {
  admin: ['Coordinación del rescate', 'Reparta cada lote entre las organizaciones que lo pidieron y emita la constancia de cada entrega.', 'banner-admin'],
  donante: ['Su aporte cuenta', 'Publique sus excedentes antes de que venzan y vea a quién ayudaron.', 'banner-donante'],
  organizacion: ['Alimentos para su comunidad', 'Elija lo que necesita, programe el recojo y reciba su constancia.', 'banner-org'],
  auditor: ['Auditoría y transparencia', 'Verifique comprobantes, reglas y bitácora. Solo lectura.', 'banner-auditor'],
};
const banner = () => { const b = BAN[state.rol]; return b && h('div', { class: 'banner ' + state.rol }, h('div', null, h('h2', null, b[0]), h('p', null, b[1])), h('img', { src: `/assets/img/${b[2]}.svg`, alt: '', width: 360, height: 200, loading: 'lazy' })); };

export async function dashboard(root) {
  root.append(loading());
  const d = await get('/api/dashboard');
  const rows = [];
  for (let i = 0; i < d.graficos.length; i += 2) rows.push(h('div', { class: 'grid g2', style: { marginTop: '18px' } }, d.graficos.slice(i, i + 2).map(chart)));
  root.replaceChildren(...[
    banner(),
    d.intro ? h('div', { class: 'hint-box' }, ico('info'), h('div', null, d.intro)) : null,
    d.pendientes ? h('div', { style: { marginBottom: '18px' } }, h('h3', { style: { marginBottom: '10px' } }, d.pendientes.length ? 'Requiere su atención' : 'Todo al día'),
      d.pendientes.length ? d.pendientes.map(p => h('a', { class: 'todo', href: p.ir }, h('span', { class: 'n' }, p.n), h('span', { class: 'grow' }, p.t), ico('arrow'))) : h('p', { class: 'muted' }, 'No tiene tareas pendientes en este momento.')) : null,
    d.acciones ? h('div', { class: 'mini-actions' }, d.acciones.map((a, i) => h('a', { class: 'btn ' + (i ? 'ghost' : 'accent'), href: a.ir }, a.t))) : null,
    h('div', { class: 'kpis' }, d.kpi.map(kpi)),
    d.flujo ? card('Ciclo del rescate', 'Datos en vivo de la base: cada paso es un módulo del sistema', h('div', { class: 'flow' }, d.flujo.map(([t, n, s]) => h('div', { class: 'step ' + (n ? 'done' : 'zero') }, h('div', { class: 'n' }, n), h('b', null, t), h('small', null, s))))) : null,
    ...rows,
    h('div', { class: 'grid g2', style: { marginTop: '18px' } },
      card(d.alertas_titulo || 'Alertas de vencimiento', 'fn_urgencia', d.alertas.length ? d.alertas.map(a => h('div', { class: 'alert-item' }, badge(a.urgencia), h('div', { class: 'grow' }, h('b', null, `${a.nombre_alimento} · ${numf(a.saldo)} ${a.tipo_medida}`), h('small', null, `${a.nombre_donante} · ${a.nombre_distrito}`)), h('b', null, horas(a.horas_para_vencer)))) : h('div', { class: 'empty' }, ico('check'), h('div', null, 'Nada vence en las próximas 24 horas'))),
      d.actividad ? card('Actividad reciente', 'Bitácora de operaciones', h('div', { class: 'timeline' }, d.actividad.map(a => h('div', { class: 'it' }, h('span', { class: 'when' }, fdate(a.fecha)), h('div', null, h('b', null, a.accion), ' · ', a.entidad, h('div', { class: 'muted' }, a.detalle), a.resultado === 'ERROR' ? badge('ERROR') : null))))) : null)].filter(Boolean));
}
