// Cliente de la API: todo dato que se muestra viene del servidor (y de la base de datos).
import { state, emit } from './state.js';

let pending = 0;
const bar = () => document.getElementById('progress');
function busy(d) {
  pending += d; const b = bar(); if (!b) return;
  if (pending > 0) { b.classList.add('on'); b.style.width = '70%'; }
  else { b.style.width = '100%'; setTimeout(() => { if (!pending) { b.classList.remove('on'); b.style.width = '0'; } }, 250); }
}

export class ApiError extends Error {
  constructor(err) { super(err.message); this.code = err.code; this.fields = err.fields || {}; }
}

export async function api(method, url, body) {
  busy(1);
  try {
    const res = await fetch(url, {
      method, credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    let out;
    try { out = await res.json(); } catch { throw new ApiError({ code: 'RED', message: 'Respuesta no válida del servidor' }); }
    if (out.sql && out.sql.length) emit('sql', { sql: out.sql, mensaje: out.mensaje, ok: out.ok });
    if (!out.ok) { if (out.error && out.error.code === 'SESION' && !url.startsWith('/api/auth/')) emit('sesion', out.error.message); throw new ApiError(out.error); }
    return out;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    throw new ApiError({ code: 'RED', message: 'No se pudo conectar con el servidor. ¿Sigue ejecutándose?' });
  } finally { busy(-1); }
}
export const get = (u) => api('GET', u).then(r => r.data);
export const post = (u, b = {}) => api('POST', u, b);
export const put = (u, b = {}) => api('PUT', u, b);
export const del = (u) => api('DELETE', u);
