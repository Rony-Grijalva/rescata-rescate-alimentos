// Pagina CRUD generica: lista (busqueda, filtros, orden) + crear / editar / eliminar con validacion
import { h, ico, dataTable, iconBtn, searchBox, formModal, confirmar, safe, loading, toast, can } from '../ui.js';
import { get, post, put, del } from '../api.js';
import { state } from '../state.js';

export function crudPage({ res, perm, singular, cols: colsDef, fields, filters: filtersDef = [], extraActions, newLabel, intro, onChange, rowsFoot, rowOk }) {
  return async function render(root) {
    const cols = typeof colsDef === 'function' ? colsDef() : colsDef, filters = typeof filtersDef === 'function' ? filtersDef() : filtersDef;
    let q = '', fvals = {}, rows = [];
    const listBox = h('div', null, loading());
    const url = () => {
      const p = new URLSearchParams(); if (q) p.set('q', q);
      Object.entries(fvals).forEach(([k, v]) => v && p.set('f_' + k, v));
      return `/api/crud/${res}?${p}`;
    };
    const reload = async () => {
      try { rows = await get(url()); } catch (e) { listBox.replaceChildren(h('div', { class: 'empty' }, e.message)); return; }
      draw();
    };
    const afterChange = async () => { onChange && (await onChange()); await reload(); };
    const edit = (row) => formModal({
      title: row ? `Editar ${singular}` : (newLabel || `Nuevo ${singular}`), sub: row ? `Registro #${row[Object.keys(row)[0]]}` : null,
      fields: fields(), values: row || {}, submitText: row ? 'Guardar cambios' : 'Crear',
      onSubmit: async (v) => { const r = row ? await put(`/api/crud/${res}/${row[Object.keys(row)[0]]}`, v) : await post(`/api/crud/${res}`, v); await afterChange(); return r; },
    });
    const draw = () => {
      listBox.replaceChildren(dataTable({
        cols, rows, empty: q ? 'Ningún registro coincide con la búsqueda.' : `Aún no hay ${singular}s. Crea el primero con el botón superior.`,
        foot: `${rows.length} registro(s)${rowsFoot ? ' · ' + rowsFoot(rows) : ''}`,
        actions: (r) => [
          ...(extraActions ? extraActions(r, afterChange) : []),
          can(perm, 'u') && (!rowOk || rowOk(r)) ? iconBtn('edit', 'Editar', () => edit(r), 'info') : null,
          can(perm, 'd') && (!rowOk || rowOk(r)) ? iconBtn('trash', 'Eliminar', async () => {
            const id = r[Object.keys(r)[0]];
            if (await confirmar({ titulo: `Eliminar ${singular}`, mensaje: `¿Seguro que deseas eliminar el registro #${id}? Si otros registros dependen de él, la base de datos lo impedirá (integridad referencial).` }))
              safe(null, async () => { const x = await del(`/api/crud/${res}/${id}`); await afterChange(); return x; });
          }, 'danger') : null],
      }));
    };
    const bar = h('div', { class: 'toolbar' }, searchBox((v) => { q = v; reload(); }, 'Buscar…'));
    for (const f of filters) {
      const sel = h('select', { style: { width: 'auto' }, 'aria-label': f.label, onChange: (e) => { fvals[f.name] = e.target.value; reload(); } },
        h('option', { value: '' }, `${f.label}: todos`), (state.lookups[f.lookup] || []).map(o => h('option', { value: o.id }, o.nombre)));
      bar.appendChild(sel);
    }
    bar.appendChild(h('span', { class: 'grow' }));
    if (can(perm, 'c')) bar.appendChild(h('button', { class: 'btn', onClick: () => edit(null) }, ico('plus'), newLabel || `Nuevo ${singular}`));
    root.append(intro ? h('p', { class: 'muted', style: { marginBottom: '14px' } }, intro) : null, bar, listBox);
    await reload();
  };
}
