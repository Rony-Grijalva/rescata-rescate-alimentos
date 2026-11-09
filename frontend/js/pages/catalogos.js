import { crudPage } from './crudpage.js';
import { h, tabs, ico, lk, options, badge } from '../ui.js';

const refresh = async () => { await import('../app.js').then(m => m.refreshLookups()); };
const C = {
  alimentos: crudPage({ res: 'cat_alimentos', perm: 'catalogos', singular: 'alimento', onChange: refresh,
    cols: [{ key: 'id_alimento', label: '#' }, { key: 'nombre_alimento', label: 'Alimento', render: r => h('b', null, r.nombre_alimento) }, { key: 'nombre_categoria', label: 'Categoría' },
      { key: 'requiere_refrigeracion', label: 'Requiere frío', render: r => r.requiere_refrigeracion ? h('span', { class: 'badge b-blue' }, ico('snow'), 'Sí') : h('span', { class: 'badge b-gray' }, 'No') }],
    fields: () => [{ name: 'nombre_alimento', label: 'Alimento', required: true, full: true }, { name: 'id_categoria_alimento', label: 'Categoría', type: 'select', options: options(lk('categorias')), required: true },
      { name: 'requiere_refrigeracion', label: 'Requiere refrigeración', type: 'checkbox' }] }),
  categorias: crudPage({ res: 'cat_categorias', perm: 'catalogos', singular: 'categoría', onChange: refresh,
    cols: [{ key: 'id_categoria_alimento', label: '#' }, { key: 'nombre_categoria', label: 'Categoría' }], fields: () => [{ name: 'nombre_categoria', label: 'Nombre', required: true, full: true }] }),
  distritos: crudPage({ res: 'cat_distritos', perm: 'catalogos', singular: 'distrito', onChange: refresh,
    cols: [{ key: 'id_distrito', label: '#' }, { key: 'nombre_distrito', label: 'Distrito' }, { key: 'provincia', label: 'Provincia' }],
    fields: () => [{ name: 'nombre_distrito', label: 'Distrito', required: true }, { name: 'provincia', label: 'Provincia', required: true }],
    intro: 'La unicidad es el par (provincia, distrito): un mismo nombre de distrito puede repetirse en otra provincia (corrección A5).' }),
  zonas: crudPage({ res: 'cat_zonas', perm: 'catalogos', singular: 'zona', onChange: refresh,
    cols: [{ key: 'id_zona', label: '#' }, { key: 'nombre_zona', label: 'Zona' }, { key: 'nombre_distrito', label: 'Distrito' }],
    fields: () => [{ name: 'id_distrito', label: 'Distrito', type: 'select', options: options(lk('distritos')), required: true }, { name: 'nombre_zona', label: 'Zona', required: true }] }),
  unidades: crudPage({ res: 'cat_unidades', perm: 'catalogos', singular: 'unidad', onChange: refresh,
    cols: [{ key: 'id_unidad_medida', label: '#' }, { key: 'tipo_medida', label: 'Unidad de medida' }], fields: () => [{ name: 'tipo_medida', label: 'Unidad', required: true, full: true }] }),
  tipos_org: crudPage({ res: 'cat_tipos_org', perm: 'catalogos', singular: 'tipo', onChange: refresh,
    cols: [{ key: 'id_tipo_organizacion', label: '#' }, { key: 'tipo', label: 'Tipo de organización' }], fields: () => [{ name: 'tipo', label: 'Tipo', required: true, full: true }] }),
  tipos_doc: crudPage({ res: 'cat_tipos_doc', perm: 'catalogos', singular: 'tipo', onChange: refresh,
    cols: [{ key: 'id_tipo_documento', label: '#' }, { key: 'tipo_doc', label: 'Tipo de documento' }], fields: () => [{ name: 'tipo_doc', label: 'Tipo', required: true, full: true }] }),
};
const TABS = [['alimentos', 'Alimentos'], ['categorias', 'Categorías'], ['zonas', 'Zonas'], ['distritos', 'Distritos'], ['unidades', 'Unidades'], ['tipos_org', 'Tipos de organización'], ['tipos_doc', 'Tipos de documento']];

export async function catalogos(root) {
  const body = h('div');
  const show = async (k) => { body.replaceChildren(); await C[k](body); };
  root.append(tabs(TABS, 'alimentos', show), body);
  await show('alimentos');
}
