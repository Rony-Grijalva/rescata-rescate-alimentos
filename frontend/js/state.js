const L = { get(k, d) { try { return localStorage.getItem(k) ?? d; } catch { return d; } }, set(k, v) { try { localStorage.setItem(k, v); } catch {} }, del(k) { try { localStorage.removeItem(k); } catch {} } };
// La identidad (rol y cuenta) vive en la sesion del servidor (cookie HttpOnly). Aqui solo se guarda lo que el servidor devuelve en /api/me.
export const state = { rol: '', actor: '', actorNombre: '', tema: L.get('rescata.tema', 'light'), perm: {}, lookups: {}, me: null };
export const store = L;
const subs = {};
export const on = (ev, fn) => (subs[ev] ||= []).push(fn);
export const emit = (ev, data) => (subs[ev] || []).forEach(f => f(data));
export const can = (rec, acc) => (state.perm[rec] || '').includes(acc);
export const param = (k) => new URLSearchParams((location.hash.split('?')[1] || '')).get(k);
