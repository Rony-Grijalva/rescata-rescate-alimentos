import { crudPage } from './crudpage.js';
import { h, ico, badge, iconBtn, modal, dataTable, money, numf, lk, options, safe } from '../ui.js';
import { get } from '../api.js';

const frio = (r) => r.tiene_refrigeracion ? h('span', { class: 'badge b-blue' }, ico('snow'), 'Con frío') : h('span', { class: 'badge b-gray' }, 'Sin frío');

export const donantes = crudPage({
  res: 'donantes', perm: 'donantes', singular: 'donante', newLabel: 'Nuevo donante',
  intro: 'Comercios y empresas que publican excedentes. El RUC se valida (11 dígitos) tanto aquí como en la base de datos (restricción CHECK ck_donante_ruc).',
  cols: [
    { key: 'id_donante', label: '#' }, { key: 'nombre_donante', label: 'Donante', render: r => h('b', null, r.nombre_donante) },
    { key: 'ruc', label: 'RUC', render: r => r.ruc ? h('span', { class: 'mono' }, r.ruc) : null },
    { key: 'nombre_zona', label: 'Zona', render: r => r.nombre_zona ? `${r.nombre_zona} · ${r.nombre_distrito}` : null },
    { key: 'telefono', label: 'Teléfono' }, { key: 'email', label: 'Correo' },
    { key: 'lotes', label: 'Lotes', num: true }, { key: 'estado', label: 'Estado', render: r => badge(r.estado) }],
  filters: [{ name: 'id_estado_donante', label: 'Estado', lookup: 'estados_donante' }],
  fields: () => [
    { name: 'nombre_donante', label: 'Nombre del donante', required: true, full: true, maxlength: 150 },
    { name: 'ruc', label: 'RUC', placeholder: '11 dígitos', maxlength: 11, hint: 'Opcional, único' }, { name: 'id_zona', label: 'Zona', type: 'select', options: options(lk('zonas')), required: true },
    { name: 'direccion', label: 'Dirección', full: true }, { name: 'telefono', label: 'Teléfono' }, { name: 'email', label: 'Correo', type: 'email' },
    { name: 'id_estado_donante', label: 'Estado', type: 'select', options: options(lk('estados_donante')), required: true }],
  onChange: async () => { await import('../app.js').then(m => m.refreshLookups()); },
});

export const organizaciones = crudPage({
  res: 'organizaciones', perm: 'organizaciones', singular: 'organización', newLabel: 'Nueva organización',
  intro: 'Ollas comunes, comedores y albergues receptores. Declarar si tienen refrigeración condiciona qué alimentos se les puede asignar.',
  cols: [
    { key: 'id_organizacion', label: '#' }, { key: 'nombre_organizacion', label: 'Organización', render: r => h('b', null, r.nombre_organizacion) },
    { key: 'tipo', label: 'Tipo' }, { key: 'nombre_zona', label: 'Zona', render: r => `${r.nombre_zona} · ${r.nombre_distrito}` },
    { key: 'tiene_refrigeracion', label: 'Cadena de frío', render: frio }, { key: 'solicitudes', label: 'Solicitudes', num: true },
    { key: 'estado', label: 'Estado', render: r => badge(r.estado) }],
  filters: [{ name: 'id_tipo_organizacion', label: 'Tipo', lookup: 'tipos_org' }, { name: 'id_estado_organizacion', label: 'Estado', lookup: 'estados_org' }],
  fields: () => [
    { name: 'nombre_organizacion', label: 'Nombre', required: true, full: true }, { name: 'id_tipo_organizacion', label: 'Tipo', type: 'select', options: options(lk('tipos_org')), required: true },
    { name: 'id_zona', label: 'Zona', type: 'select', options: options(lk('zonas')), required: true }, { name: 'direccion', label: 'Dirección', full: true },
    { name: 'id_estado_organizacion', label: 'Estado', type: 'select', options: options(lk('estados_org')), required: true },
    { name: 'tiene_refrigeracion', label: 'Cuenta con refrigeración', type: 'checkbox', hint: 'Necesaria para recibir alimentos perecibles' }],
  extraActions: (r) => [iconBtn('eye', 'Resumen de lo recibido (sp_resumen_organizacion)', () => resumen(r), 'ok')],
  onChange: async () => { await import('../app.js').then(m => m.refreshLookups()); },
});

async function resumen(org) {
  const d = await get(`/api/organizaciones/${org.id_organizacion}/resumen`).catch(() => null); if (!d) return;
  modal({ title: org.nombre_organizacion, sub: 'Procedimiento sp_resumen_organizacion (cursor con parámetro)', size: 'wide',
    body: d.filas.length ? [dataTable({ cols: [{ key: 'id_donacion_parcial', label: 'Solicitud' }, { key: 'nombre_alimento', label: 'Alimento' }, { key: 'cantidad', label: 'Cantidad', num: true, render: r => numf(r.cantidad) }, { key: 'valor', label: 'Valor', num: true, render: r => money(r.valor) }], rows: d.filas }),
      h('p', { style: { marginTop: '12px', textAlign: 'right' } }, 'Total repartido: ', h('b', null, money(d.total)))] : h('div', { class: 'empty' }, 'Esta organización aún no tiene reparto asignado.') });
}
