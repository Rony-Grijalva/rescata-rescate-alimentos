// Coordinador: administracion de cuentas de acceso (credenciales por rol). Las contrasenas nunca se muestran: solo se guardan como hash.
import { h, ico, badge, dataTable, iconBtn, searchBox, formModal, confirmar, safe, loading, toast, fdate, options, lk, seg } from '../ui.js';
import { get, post, put } from '../api.js';
import { state } from '../state.js';

const ROL = { admin: 'Coordinador', donante: 'Donante', organizacion: 'Organización', auditor: 'Auditor' };
const ROLB = { admin: 'b-navy', donante: 'b-amber', organizacion: 'b-green', auditor: 'b-blue' };

export async function usuarios(root) {
  let rows = [], q = '', rol = '';
  const box = h('div', null, loading());
  const reload = async () => { rows = await get('/api/usuarios'); draw(); };
  const yo = () => state.me?.usuario?.email;
  const nueva = () => {
    const sel = { admin: [], auditor: [] };
    const m = formModal({
      title: 'Nueva cuenta de acceso', sub: 'La contraseña se guarda cifrada (PBKDF2); no podrá volver a verla',
      fields: [
        { name: 'rol', label: 'Rol', type: 'select', required: true, options: Object.entries(ROL).map(([id, nombre]) => ({ id, nombre })), full: true },
        { name: 'nombre', label: 'Nombre a mostrar', required: true, full: true, maxlength: 120 },
        { name: 'email', label: 'Correo (usuario de acceso)', type: 'email', required: true, full: true },
        { name: 'id_donante', label: 'Donante vinculado', type: 'select', options: options(lk('donantes')), hint: 'Solo para el rol Donante' },
        { name: 'id_organizacion', label: 'Organización vinculada', type: 'select', options: options(lk('organizaciones')), hint: 'Solo para el rol Organización' },
        { name: 'password', label: 'Contraseña inicial', type: 'password', required: true, full: true, hint: 'Mínimo 8 caracteres, con letras y números' },
      ],
      submitText: 'Crear cuenta',
      onSubmit: async (v) => { const r = await post('/api/usuarios', v); await reload(); return r; },
    });
    return m;
  };
  const cambiarClave = (u) => formModal({
    title: 'Restablecer contraseña', sub: u.email,
    fields: [{ name: 'password', label: 'Nueva contraseña', type: 'password', required: true, full: true, hint: 'Se cerrarán sus sesiones abiertas y se desbloqueará la cuenta' }],
    submitText: 'Restablecer', onSubmit: async (v) => { const r = await put(`/api/usuarios/${u.id_usuario}`, v); await reload(); return r; },
  });
  const draw = () => {
    const f = rows.filter(r => (!rol || r.rol === rol) && (!q || (r.email + ' ' + r.nombre).toLowerCase().includes(q.toLowerCase())));
    box.replaceChildren(dataTable({
      cols: [
        { key: 'nombre', label: 'Nombre', render: (r) => h('b', null, r.nombre) },
        { key: 'email', label: 'Correo de acceso' },
        { key: 'rol', label: 'Rol', render: (r) => badge(ROL[r.rol], ROLB[r.rol]) },
        { key: 'activo', label: 'Estado', render: (r) => r.bloqueado ? badge('Bloqueada', 'b-red') : r.activo ? badge('Activa', 'b-green') : badge('Desactivada', 'b-gray') },
        { key: 'ultimo_acceso', label: 'Último acceso', render: (r) => r.ultimo_acceso ? fdate(r.ultimo_acceso) : h('span', { class: 'muted' }, 'Nunca') },
      ],
      rows: f, empty: 'No hay cuentas con ese criterio.', foot: `${f.length} cuenta(s)`,
      actions: (r) => {
        const yoMismo = r.email === yo();
        return [
          iconBtn('refresh', 'Restablecer contraseña', () => cambiarClave(r), 'info'),
          r.bloqueado ? iconBtn('check', 'Desbloquear cuenta', (e) => safe(e.currentTarget, async () => { const x = await put(`/api/usuarios/${r.id_usuario}`, { desbloquear: true }); await reload(); return x; }), 'ok') : null,
          yoMismo ? null : iconBtn(r.activo ? 'x' : 'check', r.activo ? 'Desactivar cuenta' : 'Activar cuenta', async (e) => {
            if (r.activo && !await confirmar({ titulo: 'Desactivar cuenta', ok: 'Desactivar', mensaje: `${r.nombre} ya no podrá iniciar sesión y se cerrarán sus sesiones abiertas.` })) return;
            await safe(e.currentTarget, async () => { const x = await put(`/api/usuarios/${r.id_usuario}`, { activo: r.activo ? 0 : 1 }); await reload(); return x; });
          }, r.activo ? 'danger' : 'ok'),
        ];
      },
    }));
  };
  const filtro = seg([['', 'Todos'], ...Object.entries(ROL)], '', (v) => { rol = v; draw(); });
  root.replaceChildren(
    h('div', { class: 'hint-box' }, ico('shield'), h('div', null, 'Cada persona entra con su propio correo y contraseña. Las contraseñas se almacenan con hash PBKDF2-SHA256 y sal individual; aquí nunca se muestran. Tras 5 intentos fallidos la cuenta se bloquea 5 minutos.')),
    h('div', { class: 'toolbar' }, searchBox((v) => { q = v; draw(); }, 'Buscar por nombre o correo…'), filtro, h('span', { class: 'grow' }), h('button', { class: 'btn', onClick: nueva }, ico('plus'), 'Nueva cuenta')),
    box);
  await reload();
}
