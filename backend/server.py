"""Servidor HTTP (solo libreria estandar): API JSON + archivos estaticos del frontend."""
import json, os, re, sys, mimetypes, threading, webbrowser, sqlite3
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: F401  (carga .env)
import database as D, business as B, services as S, queries as Q, reglas as T, auth as A
from crud import build_registry, LOOKUPS
from errors import AppError, translate_db_error

FRONT = os.path.join(D.BASE, "frontend")
REG = build_registry()

# Privilegios por rol (equivalente a los GRANT del archivo 08): r=leer c=crear u=actualizar d=eliminar
# Cada rol solo recibe los recursos que su trabajo necesita; ademas, donante y organizacion solo ven y tocan SUS datos (alcance por cuenta).
ADMIN_RES = ["dashboard", "lotes", "donantes", "organizaciones", "personas", "vehiculos", "catalogos", "solicitudes",
             "despachos", "comprobantes", "consultas", "pruebas", "esquema", "alertas", "reparto", "usuarios"]
PERMISOS = {
    "admin": {k: "rcud" for k in ADMIN_RES} | {"solicitudes": "rud", "bitacora": "r", "sistema": "rcud"},
    "donante": {"dashboard": "r", "alertas": "r", "lotes": "rcd", "comprobantes": "r", "perfil": "ru"},
    "organizacion": {"dashboard": "r", "alertas": "r", "lotes": "r", "solicitudes": "rcd", "despachos": "rcud", "vehiculos": "rcud",
                     "personas": "rcud", "comprobantes": "r", "organizaciones": "r", "perfil": "ru"},
    "auditor": {"dashboard": "r", "alertas": "r", "comprobantes": "r", "consultas": "r", "pruebas": "r", "esquema": "r", "bitacora": "r"},
}
ROLES = {"admin": "Coordinador", "donante": "Donante", "organizacion": "Organización receptora", "auditor": "Auditor"}


def need(rol, recurso, accion):
    if accion not in PERMISOS.get(rol, {}).get(recurso, ""):
        raise AppError("ORA-01031", f"Privilegios insuficientes: el rol «{ROLES.get(rol, rol)}» no puede {({'r':'consultar','c':'crear','u':'modificar','d':'eliminar'})[accion]} en «{recurso}».", 403)


def prohibido(msg="Ese registro no pertenece a su cuenta."):
    return AppError("ORA-01031", msg, 403)


class Ctx:
    def __init__(self, db, rol, body, q, actor=None, nombre=None, user=None, token=None):
        self.db, self.rol, self.body, self.q, self.actor, self.nombre, self.user, self.token = db, rol, body, q, actor, nombre, user, token

    # ---- alcance por cuenta: cada comprobacion devuelve 404 si no existe y 403 si es de otra cuenta
    def lote(self, id_):
        r = self.db.one("SELECT id_donante FROM donacion_ofrecida WHERE id_donacion_ofrecida=?", (id_,))
        if not r: raise AppError("ORA-01403", f"El lote {id_} no existe", 404)
        if self.rol == "donante" and r["id_donante"] != self.actor: raise prohibido("Ese lote pertenece a otro donante.")
        return r

    def solicitud(self, id_):
        r = self.db.one("""SELECT p.id_organizacion org, l.id_donante don FROM donacion_parcial p
                           JOIN donacion_ofrecida l ON l.id_donacion_ofrecida=p.id_donacion_ofrecida WHERE p.id_donacion_parcial=?""", (id_,))
        if not r: raise AppError("ORA-01403", f"La solicitud {id_} no existe", 404)
        if (self.rol == "organizacion" and r["org"] != self.actor) or (self.rol == "donante" and r["don"] != self.actor):
            raise prohibido("Esa solicitud pertenece a otra cuenta.")
        return r

    def despacho(self, id_):
        r = self.db.one("""SELECT p.id_organizacion org FROM despacho d JOIN donacion_parcial p ON p.id_donacion_parcial=d.id_donacion_parcial WHERE d.id_despacho=?""", (id_,))
        if not r: raise AppError("ORA-01403", f"El despacho {id_} no existe", 404)
        if self.rol == "organizacion" and r["org"] != self.actor: raise prohibido("Ese despacho pertenece a otra organización.")
        return r

    def req(self, *names):
        miss = {n: "Campo obligatorio" for n in names if self.body.get(n) in (None, "")}
        if miss: raise AppError("VALIDACION", "Faltan datos obligatorios.", 422, miss)
        return [self.body[n] for n in names]


def num(v, name, minv=None):
    try: x = float(v)
    except (TypeError, ValueError): raise AppError("VALIDACION", f"{name}: numero no valido", 422, {name: "Numero no valido"})
    if minv is not None and x <= minv: raise AppError("VALIDACION", f"{name} debe ser mayor que {minv:g}", 422, {name: f"Debe ser > {minv:g}"})
    return x


# ---------------------------------------------------------------- handlers  (devuelven (datos, mensaje, entidad))
def h_lookups(c):
    L = {k: c.db.all(v) for k, v in LOOKUPS.items()}
    if c.rol == "donante":
        L["donantes"] = [d for d in L["donantes"] if d["id"] == c.actor]; L["organizaciones"] = []; L["vehiculos"] = []
    elif c.rol == "organizacion":
        L["donantes"] = []; L["organizaciones"] = [o for o in L["organizaciones"] if o["id"] == c.actor]
        L["vehiculos"] = [v for v in L["vehiculos"] if v["id_organizacion"] in (c.actor, None)]
    return L, None, None

def h_password(c):
    if not c.user: raise AppError("SESION", "Inicie sesión para cambiar su contraseña.", 401)
    A.cambiar_password(c.db, c.user, c.body.get("actual"), c.body.get("nueva"), c.token)
    return None, "Contraseña actualizada. Se cerraron sus otras sesiones.", "usuario"

USR_SQL = ("SELECT u.id_usuario, u.email, u.nombre, u.rol, u.activo, u.ultimo_acceso, u.bloqueado_hasta, u.id_donante, u.id_organizacion, "
           "CASE WHEN u.bloqueado_hasta > datetime('now','localtime') THEN 1 ELSE 0 END AS bloqueado FROM usuario u ORDER BY u.rol, u.nombre")
def h_usuarios(c): return c.db.all(USR_SQL), None, None
def h_usuario_post(c):
    rol, nombre = c.req("rol", "nombre"); email = A.validar_email(c.body.get("email")); pw = c.body.get("password"); A.validar_password(pw)
    if rol not in ROLES: raise AppError("VALIDACION", "Rol no válido.", 422, {"rol": "Rol no válido"})
    don = org = None
    if rol == "donante": (don,) = c.req("id_donante")
    if rol == "organizacion": (org,) = c.req("id_organizacion")
    if c.db.val("SELECT 1 FROM usuario WHERE email=?", (email,)): raise AppError("ORA-00001", "Ya existe una cuenta con ese correo.", 409, {"email": "Correo ya registrado"})
    uid = c.db.insert("INSERT INTO usuario (email,nombre,password_hash,rol,id_donante,id_organizacion) VALUES (?,?,?,?,?,?)", (email, str(nombre).strip()[:120], A.hash_password(pw), rol, don, org))
    return {"id": uid}, f"Cuenta creada para {email}", "usuario"
def h_usuario_put(c, id_):
    u = c.db.one("SELECT * FROM usuario WHERE id_usuario=?", (id_,))
    if not u: raise AppError("ORA-01403", "La cuenta no existe", 404)
    b = c.body; msg = []
    if "activo" in b:
        if int(id_) == c.user["id_usuario"] and not b["activo"]: raise AppError("ORA-20017", "No puede desactivar su propia cuenta.", 409)
        c.db.run("UPDATE usuario SET activo=? WHERE id_usuario=?", (1 if b["activo"] else 0, id_))
        if not b["activo"]: c.db.run("DELETE FROM sesion WHERE id_usuario=?", (id_,))
        msg.append("activada" if b["activo"] else "desactivada")
    if b.get("password"):
        A.validar_password(b["password"]); c.db.run("UPDATE usuario SET password_hash=?, intentos_fallidos=0, bloqueado_hasta=NULL WHERE id_usuario=?", (A.hash_password(b["password"]), id_))
        c.db.run("DELETE FROM sesion WHERE id_usuario=?", (id_,)); msg.append("contraseña restablecida")
    if b.get("desbloquear"):
        c.db.run("UPDATE usuario SET intentos_fallidos=0, bloqueado_hasta=NULL WHERE id_usuario=?", (id_,)); msg.append("desbloqueada")
    if not msg: raise AppError("VALIDACION", "No hay cambios que guardar", 422)
    return {"id": id_}, f"Cuenta {u['email']}: " + ", ".join(msg), "usuario"

def h_me(c):
    return {"rol": c.rol, "roles": ROLES, "permisos": PERMISOS[c.rol], "actor": {"id": c.actor, "nombre": c.nombre} if c.actor else None,
            "usuario": {"nombre": c.user["nombre"], "email": c.user["email"]} if c.user else None,
            "sqlite": sqlite3.sqlite_version, "motor_full_join": D.SQLITE_OK_FULL_JOIN}, None, None

def h_dashboard(c): return S.dashboard(c.db, c.rol, c.actor), None, None

def h_alertas(c):
    horas = int(c.q.get("horas", 24)); rows = B.sp_alerta_vencimientos(c.db, horas)
    if c.rol == "donante":
        mine = {r["id"] for r in c.db.all("SELECT id_donacion_ofrecida id FROM donacion_ofrecida WHERE id_donante=?", (c.actor,))}
        rows = [r for r in rows if r["id_donacion_ofrecida"] in mine]
    return rows, None, None

def h_lotes_list(c):
    return S.lotes(c.db, c.q.get("q"), c.q.get("estado"), donante=c.actor if c.rol == "donante" else None, org=c.actor if c.rol == "organizacion" else None), None, None

def h_lote_get(c, id_):
    c.lote(int(id_))
    if c.rol == "organizacion":
        l = S.lote_detalle(c.db, int(id_), org=c.actor)
        if l["estado"] != "PUBLICADO" and not l["mi_solicitud"]: raise prohibido("Ese lote ya no está disponible.")
        return l, None, None
    return S.lote_detalle(c.db, int(id_)), None, None

def h_perfil_get(c):
    res = REG["donantes" if c.rol == "donante" else "organizaciones"]
    return res.get(c.db, c.actor), None, None

PERFIL_CAMPOS = {"donante": ("nombre_donante", "direccion", "id_zona", "telefono", "email"),
                 "organizacion": ("nombre_organizacion", "direccion", "id_zona", "tiene_refrigeracion")}
def h_perfil_put(c):
    res = REG["donantes" if c.rol == "donante" else "organizaciones"]
    cuerpo = {k: v for k, v in c.body.items() if k in PERFIL_CAMPOS[c.rol]}
    res.update(c.db, c.actor, cuerpo)
    return {"id": c.actor}, "Sus datos fueron actualizados", "perfil"

def validar_linea(l, i):
    errs = {}
    for k in ("id_alimento", "id_unidad_medida", "fecha_vencimiento", "cantidad", "costo_unitario"):
        if l.get(k) in (None, ""): errs[f"lineas[{i}].{k}"] = "Obligatorio"
    if errs: raise AppError("VALIDACION", f"Complete la linea {i+1}.", 422, errs)
    num(l["cantidad"], "cantidad", 0)
    if float(l["costo_unitario"]) < 0: raise AppError("VALIDACION", f"Linea {i+1}: el costo no puede ser negativo", 422)
    if l.get("peso_total_kg") not in (None, ""): num(l["peso_total_kg"], "peso_total_kg", 0)
    else: l["peso_total_kg"] = None
    if not re.match(r"^\d{4}-\d{2}-\d{2}", str(l["fecha_vencimiento"])): raise AppError("VALIDACION", f"Linea {i+1}: fecha de vencimiento no valida", 422)
    l["fecha_vencimiento"] = str(l["fecha_vencimiento"]).replace("T", " ")
    if len(l["fecha_vencimiento"]) == 10: l["fecha_vencimiento"] += " 23:59:00"
    elif len(l["fecha_vencimiento"]) == 16: l["fecha_vencimiento"] += ":00"

def h_lote_post(c):
    if c.rol == "donante":
        c.body["id_donante"] = c.actor
        d = c.db.one("SELECT id_zona, direccion FROM donante WHERE id_donante=?", (c.actor,))
        c.body.setdefault("id_zona", d["id_zona"]); c.body["id_zona"] = c.body["id_zona"] or d["id_zona"]
        if not c.body.get("direccion"): c.body["direccion"] = d["direccion"]
    don, zona = c.req("id_donante", "id_zona")
    lineas = c.body.get("lineas") or []
    if not lineas: raise AppError("VALIDACION", "El lote debe tener al menos una linea (alimento).", 422, {"lineas": "Agregue al menos un alimento"})
    for i, l in enumerate(lineas): validar_linea(l, i)
    lote = B.publicar_lote(c.db, int(don), c.body.get("direccion"), int(zona), lineas)
    return {"id": lote}, f"Lote #{lote} publicado con {len(lineas)} linea(s)", "lote"

def h_lote_del(c, id_):
    c.lote(int(id_)); S.lote_detalle(c.db, int(id_))
    if c.db.val("SELECT 1 FROM donacion_parcial WHERE id_donacion_ofrecida=?", (id_,)):
        raise AppError("ORA-02292", "No se puede eliminar el lote: tiene solicitudes de organizaciones (registros hijos).", 409)
    c.db.run("DELETE FROM detalle_donacion_ofrecida WHERE id_donacion_ofrecida=?", (id_,))
    c.db.run("DELETE FROM donacion_ofrecida WHERE id_donacion_ofrecida=?", (id_,))
    return None, f"Lote #{id_} eliminado", "lote"

def h_linea_post(c, lote):
    c.lote(int(lote)); S.lote_detalle(c.db, int(lote)); l = dict(c.body); validar_linea(l, 0)
    if c.db.val("SELECT s.estado FROM donacion_ofrecida x JOIN estado_donacion_ofrecida s ON s.id_estado_donacion_ofrecida=x.id_estado_donacion_ofrecida WHERE x.id_donacion_ofrecida=?", (lote,)) == "CERRADO":
        raise AppError("ORA-20015", "El lote está CERRADO y no admite nuevas líneas", 409)
    c.db.insert("""INSERT INTO detalle_donacion_ofrecida (id_donacion_ofrecida,id_alimento,marca,codigo_lote,fecha_vencimiento,cantidad,id_unidad_medida,peso_total_kg,costo_unitario)
                   VALUES (?,?,?,?,?,?,?,?,?)""", (lote, l["id_alimento"], l.get("marca"), l.get("codigo_lote"), l["fecha_vencimiento"], l["cantidad"], l["id_unidad_medida"], l["peso_total_kg"], l["costo_unitario"]))
    B.refrescar_estado_lote(c.db, int(lote))
    return None, "Linea agregada al lote", "lote"

def h_linea_del(c, id_):
    r = c.db.one("SELECT id_donacion_ofrecida lote FROM detalle_donacion_ofrecida WHERE id_detalle_donacion_ofrecida=?", (id_,))
    if not r: raise AppError("ORA-01403", "La linea no existe", 404)
    c.lote(r["lote"])
    if c.db.val("SELECT 1 FROM detalle_donacion_parcial WHERE id_detalle_donacion_ofrecida=?", (id_,)):
        raise AppError("ORA-02292", "No se puede eliminar la linea: ya fue repartida a una solicitud.", 409)
    if c.db.val("SELECT COUNT(*) FROM detalle_donacion_ofrecida WHERE id_donacion_ofrecida=?", (r["lote"],)) <= 1:
        raise AppError("ORA-20014", "Un lote debe conservar al menos una linea; elimine el lote completo.", 409)
    c.db.run("DELETE FROM detalle_donacion_ofrecida WHERE id_detalle_donacion_ofrecida=?", (id_,))
    B.refrescar_estado_lote(c.db, r["lote"])
    return None, "Linea eliminada", "lote"

def h_sugerir(c, lote): return B.sp_sugerir_receptoras(c.db, int(lote)), None, None
def h_repartir(c, lote):
    log = B.sp_repartir_equitativo(c.db, int(lote)); return {"log": log}, "Reparto equitativo ejecutado", "lote"

def h_sol_list(c):
    return S.solicitudes(c.db, c.q.get("q"), c.q.get("estado"), org=c.actor if c.rol == "organizacion" else c.q.get("org")), None, None

def h_sol_get(c, id_):
    c.solicitud(int(id_)); return S.solicitud_detalle(c.db, int(id_)), None, None

def h_sol_post(c):
    if c.rol == "organizacion": c.body["id_organizacion"] = c.actor
    lote, org = c.req("id_donacion_ofrecida", "id_organizacion")
    if not c.db.val("SELECT 1 FROM donacion_ofrecida WHERE id_donacion_ofrecida=?", (lote,)):
        raise AppError("ORA-02291", f"El lote {lote} no existe (fk_parcial_ofrecida)", 409, {"id_donacion_ofrecida": "Lote inexistente"})
    est = c.db.val("SELECT e.estado FROM organizacion o JOIN estado_organizacion e ON e.id_estado_organizacion=o.id_estado_organizacion WHERE o.id_organizacion=?", (org,))
    if est != "HABILITADA": raise AppError("ORA-20015", f"Solo una organizacion HABILITADA puede solicitar (estado actual: {est})", 409, {"id_organizacion": "Organizacion no habilitada"})
    if c.db.val("SELECT estado FROM donacion_ofrecida l JOIN estado_donacion_ofrecida s ON s.id_estado_donacion_ofrecida=l.id_estado_donacion_ofrecida WHERE l.id_donacion_ofrecida=?", (lote,)) != "PUBLICADO":
        raise AppError("ORA-20015", "Solo se pueden pedir lotes PUBLICADOS con saldo disponible (este lote ya está asignado o cerrado).", 409)
    if c.db.val("SELECT 1 FROM donacion_parcial WHERE id_donacion_ofrecida=? AND id_organizacion=?", (lote, org)):
        raise AppError("ORA-20015", "Esa organizacion ya solicito este lote", 409)
    pid = c.db.insert("INSERT INTO donacion_parcial (id_donacion_ofrecida,id_organizacion,id_estado_donacion) VALUES (?,?,1)", (lote, org))
    return {"id": pid}, f"Solicitud #{pid} registrada (PENDIENTE)", "solicitud"

def h_sol_del(c, id_):
    c.solicitud(int(id_)); s = S.solicitud_detalle(c.db, int(id_))
    if s["estado"] == "ENTREGADA": raise AppError("ORA-02292", "No se elimina una solicitud ENTREGADA: tiene historial de despacho y comprobante.", 409)
    if s["id_despacho"]: raise AppError("ORA-02292", "No se puede eliminar: la solicitud tiene un despacho (registro hijo).", 409)
    if c.rol == "organizacion" and s["lineas"]:
        raise AppError("ORA-20013", "La solicitud ya tiene alimentos asignados por el coordinador; ya no puede cancelarla desde su cuenta.", 409)
    c.db.run("DELETE FROM detalle_donacion_parcial WHERE id_donacion_parcial=?", (id_,))
    c.db.run("DELETE FROM donacion_parcial WHERE id_donacion_parcial=?", (id_,))
    B.refrescar_estado_lote(c.db, s["id_donacion_ofrecida"])
    return None, f"Solicitud #{id_} eliminada y saldo liberado al lote", "solicitud"

def h_asignar(c, id_):
    c.solicitud(int(id_)); linea, cant = c.req("linea", "cantidad")
    msg = B.sp_asignar_linea(c.db, int(id_), int(linea), cant); B.sincronizar_estado_solicitud(c.db, int(id_)); return None, msg, "reparto"

def h_repartir(c, lote):
    log = B.sp_repartir_equitativo(c.db, int(lote)); return {"log": log}, "Reparto equitativo ejecutado", "lote"

def h_reparto_del(c, id_):
    r = c.db.one("""SELECT dd.id_donacion_parcial sol, p.id_donacion_ofrecida lote, e.estado FROM detalle_donacion_parcial dd
        JOIN donacion_parcial p ON p.id_donacion_parcial=dd.id_donacion_parcial JOIN estado_donacion e ON e.id_estado_donacion=p.id_estado_donacion
        WHERE dd.id_detalle_donacion_parcial=?""", (id_,))
    if not r: raise AppError("ORA-01403", "El reparto no existe", 404)
    if r["estado"] == "ENTREGADA": raise AppError("ORA-20013", "No se modifica el reparto de una solicitud ENTREGADA", 409)
    if c.db.val("SELECT 1 FROM despacho WHERE id_donacion_parcial=?", (r["sol"],)):
        raise AppError("ORA-20013", "La solicitud ya tiene despacho: cancélelo antes de quitar alimentos del reparto.", 409)
    c.db.run("DELETE FROM detalle_donacion_parcial WHERE id_detalle_donacion_parcial=?", (id_,))
    B.sincronizar_estado_solicitud(c.db, r["sol"]); B.refrescar_estado_lote(c.db, r["lote"])
    return None, "Reparto quitado; el saldo vuelve al lote", "reparto"

def h_comprobante_emitir(c, id_):
    msg = B.sp_emitir_comprobante(c.db, int(id_)); return None, msg, "comprobante"

def h_despachos(c): return S.despachos(c.db, c.actor if c.rol == "organizacion" else None), None, None
def h_despacho_post(c):
    sol, veh = c.req("id_donacion_parcial", "id_vehiculo")
    c.solicitud(int(sol))
    did, msg = B.sp_programar_despacho(c.db, int(sol), int(veh), (c.body.get("fecha_programada") or "").replace("T", " ") or None)
    return {"id": did}, msg, "despacho"
def h_hito(c, id_):
    c.despacho(int(id_)); (h,) = c.req("hito"); return None, B.sp_registrar_hito(c.db, int(id_), h), "despacho"
def h_resp_post(c, id_):
    c.despacho(int(id_)); (p,) = c.req("id_persona_recojo")
    d = c.db.one("SELECT p.id_organizacion org FROM despacho d JOIN donacion_parcial p ON p.id_donacion_parcial=d.id_donacion_parcial WHERE d.id_despacho=?", (id_,))
    per = c.db.one("SELECT id_organizacion org FROM persona_recojo WHERE id_persona_recojo=?", (p,))
    if not d or not per: raise AppError("ORA-20004", "Despacho o persona inexistente", 404)
    if d["org"] != per["org"]: raise AppError("ORA-20016", "La persona de recojo debe pertenecer a la organizacion receptora", 409)
    if c.db.val("SELECT 1 FROM despacho_responsable WHERE id_despacho=? AND id_persona_recojo=?", (id_, p)):
        raise AppError("ORA-00001", "Esa persona ya es responsable de este despacho", 409)
    c.db.insert("INSERT INTO despacho_responsable (id_despacho,id_persona_recojo) VALUES (?,?)", (id_, p))
    return None, "Responsable de recojo asignado", "despacho"
def h_resp_del(c, id_, pid):
    c.despacho(int(id_))
    c.db.run("DELETE FROM despacho_responsable WHERE id_despacho=? AND id_persona_recojo=?", (id_, pid)); return None, "Responsable retirado", "despacho"
def h_despacho_del(c, id_):
    c.despacho(int(id_)); d = c.db.one("SELECT * FROM despacho WHERE id_despacho=?", (id_,))
    if d["fecha_arribo"]: raise AppError("ORA-20013", "No se elimina un despacho ya entregado", 409)
    c.db.run("DELETE FROM despacho_responsable WHERE id_despacho=?", (id_,)); c.db.run("DELETE FROM despacho WHERE id_despacho=?", (id_,))
    return None, f"Despacho #{id_} cancelado", "despacho"

def h_comp_list(c): return S.comprobantes(c.db, c.rol, c.actor), None, None
def h_comp_get(c, id_):
    cp = S.comprobante_detalle(c.db, int(id_))
    if c.rol in ("donante", "organizacion") and not any(x["id_comprobante"] == int(id_) for x in S.comprobantes(c.db, c.rol, c.actor)):
        raise prohibido("Ese comprobante pertenece a otra cuenta.")
    return cp, None, None
def h_resumen_org(c, id_):
    if c.rol == "organizacion" and int(id_) != c.actor: raise prohibido("Solo puede ver el resumen de su propia organización.")
    return B.sp_resumen_organizacion(c.db, int(id_)), None, None

def h_consultas(c): return Q.catalogo(), None, None
def h_consulta_run(c, qid): return Q.ejecutar(c.db, qid), None, None
def h_sql(c): return Q.sql_libre(c.db, c.body.get("sql")), None, None
def h_pruebas(c): return T.catalogo(), None, None
def h_prueba_run(c, tid): return T.ejecutar(c.db, tid), None, None
def h_esquema(c): return S.esquema(c.db), None, None
def h_bitacora(c): return c.db.all("SELECT * FROM bitacora ORDER BY id_bitacora DESC LIMIT ?", (int(c.q.get("limit", 200)),)), None, None
def h_reiniciar(c):
    raise AppError("REINICIAR", "")


ROUTES = []
def route(method, pattern, fn, recurso, accion):
    ROUTES.append((method, re.compile("^" + pattern + "$"), fn, recurso, accion))

route("GET", "/api/lookups", h_lookups, "dashboard", "r"); route("GET", "/api/me", h_me, "dashboard", "r")
route("GET", "/api/dashboard", h_dashboard, "dashboard", "r"); route("GET", "/api/alertas", h_alertas, "alertas", "r")
route("GET", "/api/perfil", h_perfil_get, "perfil", "r"); route("PUT", "/api/perfil", h_perfil_put, "perfil", "u")
route("GET", "/api/lotes", h_lotes_list, "lotes", "r"); route("POST", "/api/lotes", h_lote_post, "lotes", "c")
route("GET", r"/api/lotes/(\d+)", h_lote_get, "lotes", "r")
route("DELETE", r"/api/lotes/(\d+)", h_lote_del, "lotes", "d"); route("POST", r"/api/lotes/(\d+)/lineas", h_linea_post, "lotes", "c")
route("DELETE", r"/api/lineas/(\d+)", h_linea_del, "lotes", "d")
route("POST", r"/api/lotes/(\d+)/sugerir", h_sugerir, "reparto", "r"); route("POST", r"/api/lotes/(\d+)/repartir", h_repartir, "reparto", "u")
route("GET", "/api/solicitudes", h_sol_list, "solicitudes", "r"); route("POST", "/api/solicitudes", h_sol_post, "solicitudes", "c")
route("GET", r"/api/solicitudes/(\d+)", h_sol_get, "solicitudes", "r"); route("DELETE", r"/api/solicitudes/(\d+)", h_sol_del, "solicitudes", "d")
route("POST", r"/api/solicitudes/(\d+)/asignar", h_asignar, "reparto", "c"); route("DELETE", r"/api/repartos/(\d+)", h_reparto_del, "reparto", "d")
route("POST", r"/api/solicitudes/(\d+)/comprobante", h_comprobante_emitir, "comprobantes", "c")
route("GET", "/api/despachos", h_despachos, "despachos", "r"); route("POST", "/api/despachos", h_despacho_post, "despachos", "c")
route("POST", r"/api/despachos/(\d+)/hito", h_hito, "despachos", "u"); route("DELETE", r"/api/despachos/(\d+)", h_despacho_del, "despachos", "d")
route("POST", r"/api/despachos/(\d+)/responsables", h_resp_post, "despachos", "u"); route("DELETE", r"/api/despachos/(\d+)/responsables/(\d+)", h_resp_del, "despachos", "u")
route("GET", "/api/comprobantes", h_comp_list, "comprobantes", "r"); route("GET", r"/api/comprobantes/(\d+)", h_comp_get, "comprobantes", "r")
route("GET", r"/api/organizaciones/(\d+)/resumen", h_resumen_org, "organizaciones", "r")
route("GET", "/api/consultas", h_consultas, "consultas", "r"); route("POST", r"/api/consultas/(J\d+)/ejecutar", h_consulta_run, "consultas", "r")
route("POST", "/api/sql", h_sql, "consultas", "r")
route("GET", "/api/pruebas", h_pruebas, "pruebas", "r"); route("POST", r"/api/pruebas/(P\d+)/ejecutar", h_prueba_run, "pruebas", "r")
route("POST", "/api/auth/password", h_password, None, None)
route("GET", "/api/usuarios", h_usuarios, "usuarios", "r"); route("POST", "/api/usuarios", h_usuario_post, "usuarios", "c"); route("PUT", r"/api/usuarios/(\d+)", h_usuario_put, "usuarios", "u")
route("GET", "/api/esquema", h_esquema, "esquema", "r"); route("GET", "/api/bitacora", h_bitacora, "bitacora", "r")
route("POST", "/api/sistema/reiniciar", h_reiniciar, "sistema", "d")

CRUD_RE = re.compile(r"^/api/crud/(\w+)(?:/(\d+))?$")
DESTRUCTIVE = {"DELETE": "d", "POST": "c", "PUT": "u", "GET": "r"}


ROL_TABLA = {"donante": ("donante", "id_donante", "nombre_donante"), "organizacion": ("organizacion", "id_organizacion", "nombre_organizacion")}


def resolver_actor(db, rol, actor):
    """Nombre de la cuenta (donante u organizacion) vinculada a la sesion autenticada; el id sale de la tabla usuario, nunca del cliente."""
    if rol not in ROL_TABLA: return None, None
    t, pk, nom = ROL_TABLA[rol]
    try: actor = int(actor)
    except (TypeError, ValueError): actor = None
    r = db.one(f"SELECT {pk} id, {nom} nombre FROM {t} WHERE {pk}=?", (actor,)) if actor else None
    if not r: raise AppError("SESION", f"La cuenta de {'donante' if rol == 'donante' else 'organización'} vinculada a su usuario ya no existe.", 401)
    return r["id"], r["nombre"]


CRUD_ALCANCE = {"personas": ("id_organizacion", False), "vehiculos": ("id_organizacion", True)}


def alcance_crud(db, res, method, id_, body, rol, actor):
    """Una organizacion solo ve y modifica su propia flota y su propio personal (los vehiculos sin duenio se pueden ver, no editar)."""
    if rol != "organizacion" or res.perm not in CRUD_ALCANCE: return None
    col, nulos = CRUD_ALCANCE[res.perm]
    if id_:
        fila = res.get(db, id_)
        if fila[col] != actor and not (method == "GET" and nulos and fila[col] is None):
            raise prohibido("Ese registro pertenece a otra organización o es de uso compartido (solo lectura).")
    if method in ("POST", "PUT"): body[col] = actor
    return (col, actor, nulos)


def dispatch(method, path, q, body, rol, actor=None, user=None, token=None):
    if rol not in PERMISOS: rol = "auditor"
    # reinicio de la demo
    if method == "POST" and path == "/api/sistema/reiniciar":
        try: need(rol, "sistema", "d")
        except AppError as e: return {"ok": False, "error": e.to_dict(), "_status": e.status}
        D.init_db(force=True)
        db = D.Db(); db.log(rol, "REINICIAR", "sistema", "Base restaurada a los datos de demostracion")
        if user and token: A.restaurar_sesion(db, token, user["id_usuario"])
        db.commit(); db.close()
        return {"ok": True, "mensaje": "Base de datos restaurada a los datos de demostracion", "data": None, "sql": []}
    m = CRUD_RE.match(path)
    db = D.Db()
    nombre = None
    try:
        actor, nombre = resolver_actor(db, rol, actor)
        c = Ctx(db, rol, body, q, actor, nombre, user, token); mensaje = entidad = None; data = None
        if m:
            res = REG.get(m.group(1))
            if not res: raise AppError("ORA-00942", "Recurso inexistente", 404)
            id_ = int(m.group(2)) if m.group(2) else None
            need(rol, res.perm, DESTRUCTIVE[method]); entidad = res.label
            scope = alcance_crud(db, res, method, id_, body, rol, actor)
            try:
                if method == "GET": data = res.get(db, id_) if id_ else res.list(db, q.get("q"), q, scope)
                elif method == "POST": data = {"id": res.create(db, body)}; mensaje = f"{res.label}: registro creado (#{data['id']})"
                elif method == "PUT": res.update(db, id_, body); mensaje = f"{res.label}: registro #{id_} actualizado"
                elif method == "DELETE":
                    try: res.delete(db, id_)
                    except sqlite3.IntegrityError as e: raise translate_db_error(e, "delete")
                    mensaje = f"{res.label}: registro #{id_} eliminado"
            except sqlite3.IntegrityError as e:
                raise translate_db_error(e, "write")
        else:
            for mt, rx, fn, recurso, accion in ROUTES:
                mm = rx.match(path)
                if mt == method and mm:
                    if recurso: need(rol, recurso, accion)
                    try: data, mensaje, entidad = fn(c, *mm.groups())
                    except sqlite3.Error as e: raise translate_db_error(e, "delete" if method == "DELETE" else "write")
                    break
            else:
                raise AppError("404", "Ruta no encontrada", 404)
        if method != "GET" and mensaje:
            db.log(rol, {"POST": "CREAR", "PUT": "MODIFICAR", "DELETE": "ELIMINAR"}[method], entidad or "-", (f"[{nombre}] " if nombre else "") + mensaje)
        sql = [] if path.startswith("/api/pruebas") else dml(db)   # las pruebas hacen ROLLBACK: no se muestran
        db.commit()
        return {"ok": True, "data": data, "mensaje": mensaje, "sql": sql}
    except AppError as e:
        db.rollback()
        if method != "GET" and e.code not in ("VALIDACION", "SESION"):
            try:
                d2 = D.Db(trace=False); d2.log(rol, "RECHAZADO", path.split("/")[2] if path.count("/") >= 2 else "-", (f"[{nombre}] " if nombre else "") + f"{e.code} {e.message}", "ERROR"); d2.commit(); d2.close()
            except Exception: pass
        return {"ok": False, "error": e.to_dict(), "_status": e.status, "sql": dml(db)}
    except sqlite3.Error as e:
        db.rollback(); ae = translate_db_error(e)
        return {"ok": False, "error": ae.to_dict(), "_status": ae.status}
    except Exception as e:
        db.rollback()
        import traceback; traceback.print_exc()
        return {"ok": False, "error": {"code": "ERROR-INTERNO", "message": str(e), "fields": {}}, "_status": 500}
    finally:
        db.close()


def dml(db):
    """Solo las sentencias que modifican datos, sin repetidos consecutivos (los disparadores las repiten en la traza)."""
    out = []
    for s in (db.trace.items if db.trace else []):
        if re.match(r"^(INSERT|UPDATE|DELETE)", s, re.I) and (not out or out[-1] != s): out.append(s)
    return out[-10:]


COOKIE = "rescata_sid"


def _err(e, extra=None):
    out = {"ok": False, "error": e.to_dict(), "_status": e.status}
    if extra: out.update(extra)
    return out


def entrada(method, path, q, body, token, ip="-"):
    """Punto de entrada HTTP: autentica ANTES de despachar. El rol y la cuenta salen de la sesion del servidor, nunca de lo que envie el cliente."""
    if path == "/api/auth/login" and method == "POST":
        db = D.Db(trace=False)
        try:
            tk, u = A.login(db, body.get("email"), body.get("password"), ip); db.commit()
            return {"ok": True, "data": {"rol": u["rol"], "nombre": u["nombre"]}, "mensaje": f"Bienvenido, {u['nombre']}", "sql": [], "_cookie": ("set", tk)}
        except AppError as e:
            db.commit()                                   # conserva el contador de intentos y la bitacora aunque falle
            return _err(e)
        finally: db.close()
    if path == "/api/auth/demo" and method == "GET":
        if not A.DEMO: return {"ok": True, "data": {"activo": False, "cuentas": []}, "sql": []}
        db = D.Db(trace=False)
        try: return {"ok": True, "data": {"activo": True, "password": A.DEMO_PASSWORD, "cuentas": A.cuentas_demo(db)}, "sql": []}
        finally: db.close()
    db = D.Db(trace=False)
    try:
        user = A.resolver(db, token)
        if path == "/api/auth/logout" and method == "POST":
            A.logout(db, token, user); db.commit()
            return {"ok": True, "data": None, "mensaje": "Sesión cerrada", "sql": [], "_cookie": ("clear", None)}
        db.commit()
    finally: db.close()
    if not user:
        return _err(AppError("SESION", "Su sesión no es válida o expiró. Inicie sesión nuevamente.", 401), {"_cookie": ("clear", None)} if token else None)
    return dispatch(method, path, q, body, user["rol"], user["actor"], user, token)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "RESCATA/1.0"

    def log_message(self, fmt, *a):
        if os.environ.get("RESCATA_VERBOSE"): sys.stderr.write("  " + fmt % a + "\n")

    def _send(self, status, payload, ctype="application/json; charset=utf-8", extra=None):
        data = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff"); self.send_header("X-Frame-Options", "DENY"); self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-ancestors 'none'")
        for k, v in (extra or {}).items(): self.send_header(k, v)
        self.end_headers(); self.wfile.write(data)

    def _api(self, method):
        u = urlparse(self.path); q = {k: v[0] for k, v in parse_qs(u.query).items()}
        body = {}
        n = min(int(self.headers.get("Content-Length") or 0), 1_000_000)
        if n:
            try: body = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
            except ValueError: return self._send(400, {"ok": False, "error": {"code": "JSON", "message": "Cuerpo JSON invalido", "fields": {}}})
        if method != "GET":                                   # defensa CSRF: el origen debe ser este mismo servidor
            org = self.headers.get("Origin")
            if org and urlparse(org).netloc != self.headers.get("Host"):
                return self._send(403, {"ok": False, "error": {"code": "ORIGEN", "message": "Origen no permitido.", "fields": {}}})
        ck = {}
        for part in (self.headers.get("Cookie") or "").split(";"):
            if "=" in part: k, v = part.strip().split("=", 1); ck[k] = v
        out = entrada(method, u.path, q, body, ck.get(COOKIE), self.client_address[0])
        cookie = out.pop("_cookie", None); extra = {}
        if cookie:
            extra["Set-Cookie"] = (f"{COOKIE}={cookie[1]}; HttpOnly; SameSite=Strict; Path=/; Max-Age={A.MAX_HORAS * 3600}" if cookie[0] == "set"
                                   else f"{COOKIE}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")
        self._send(out.pop("_status", 200), out, extra=extra)

    def _static(self):
        p = urlparse(self.path).path
        if p == "/": p = "/index.html"
        f = os.path.normpath(os.path.join(FRONT, p.lstrip("/")))
        if not f.startswith(FRONT) or not os.path.isfile(f):
            f = os.path.join(FRONT, "index.html")
        ctype = mimetypes.guess_type(f)[0] or "application/octet-stream"
        if f.endswith(".js"): ctype = "text/javascript; charset=utf-8"
        elif ctype.startswith("text/") or f.endswith(".svg"): ctype += "; charset=utf-8" if "charset" not in ctype else ""
        self._send(200, open(f, "rb").read(), ctype)

    def do_GET(self):
        self._api("GET") if self.path.startswith("/api/") else self._static()
    def do_POST(self): self._api("POST")
    def do_PUT(self): self._api("PUT")
    def do_DELETE(self): self._api("DELETE")


def main(port=8000, abrir=True):
    D.init_db()
    srv = None
    for p in range(port, port + 10):          # si el puerto esta ocupado se prueba el siguiente
        try: srv = ThreadingHTTPServer(("127.0.0.1", p), Handler); port = p; break
        except OSError: continue
    if srv is None:
        sys.exit("No se pudo abrir ningun puerto entre %d y %d." % (port, port + 9))
    url = f"http://127.0.0.1:{port}"
    print(f"\n  RESCATA en marcha: {url}\n  Base de datos: {D.DB_PATH}\n  (Ctrl+C para detener)\n")
    if abrir: threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try: srv.serve_forever()
    except KeyboardInterrupt: print("\n  Servidor detenido."); srv.server_close()


if __name__ == "__main__":
    p = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else int(os.environ.get("PORT", 8000))
    main(p, abrir="--no-browser" not in sys.argv)
