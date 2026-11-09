"""Autenticacion y sesiones (solo libreria estandar).
 - Contrasenas: PBKDF2-HMAC-SHA256, 150 000 iteraciones, sal aleatoria por usuario, comparacion en tiempo constante.
 - Sesiones: token aleatorio de 256 bits en cookie HttpOnly + SameSite=Strict; en la base solo se guarda su SHA-256.
 - Bloqueo temporal tras 5 intentos fallidos; expiracion por inactividad y absoluta; cierre de sesion invalida el token."""
import hashlib, hmac, os, re, secrets, unicodedata
import config  # noqa: F401  (carga .env)
from errors import AppError

ITER = 150_000
MAX_INTENTOS, BLOQUEO_MIN, INACTIVIDAD_MIN, MAX_HORAS = 5, 5, 120, 12
DEMO = os.environ.get("RESCATA_DEMO", "1") != "0"
DEMO_PASSWORD = os.environ.get("RESCATA_DEMO_PASSWORD", "Rescata#2026")   # solo para las cuentas de demostracion (configurable)


def hash_password(pw, salt=None):
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salt, ITER)
    return f"pbkdf2_sha256${ITER}${salt.hex()}${dk.hex()}"


def verify_password(pw, stored):
    try:
        alg, it, salt, dk = stored.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), bytes.fromhex(salt), int(it))
        return alg == "pbkdf2_sha256" and hmac.compare_digest(calc.hex(), dk)
    except (ValueError, AttributeError):
        return False


_FALSO = hash_password("x" * 12)         # para igualar tiempos cuando el correo no existe


def validar_password(pw):
    if not isinstance(pw, str) or len(pw) < 8: raise AppError("VALIDACION", "La contraseña debe tener al menos 8 caracteres.", 422, {"password": "Mínimo 8 caracteres"})
    if not (re.search(r"[A-Za-z]", pw) and re.search(r"\d", pw)):
        raise AppError("VALIDACION", "La contraseña debe combinar letras y números.", 422, {"password": "Use letras y números"})
    if len(pw) > 128: raise AppError("VALIDACION", "La contraseña es demasiado larga.", 422, {"password": "Máximo 128 caracteres"})


EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
def validar_email(e):
    if not isinstance(e, str) or not EMAIL.match(e.strip()) or len(e) > 120:
        raise AppError("VALIDACION", "Correo electrónico no válido.", 422, {"email": "Correo no válido"})
    return e.strip().lower()


def _tok(token): return hashlib.sha256(token.encode()).hexdigest()


def _slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", ".", s).strip(".")[:40]


def seed_users(conn):
    """Crea las cuentas de demostracion si la tabla esta vacia (admin, auditor y una por donante/organizacion)."""
    if conn.execute("SELECT COUNT(*) FROM usuario").fetchone()[0]: return
    h = lambda: hash_password(DEMO_PASSWORD)
    ins = "INSERT INTO usuario (email,nombre,password_hash,rol,id_donante,id_organizacion) VALUES (?,?,?,?,?,?)"
    conn.execute(ins, ("coordinador@rescata.pe", "Coordinación RESCATA", h(), "admin", None, None))
    conn.execute(ins, ("auditor@rescata.pe", "Auditoría RESCATA", h(), "auditor", None, None))
    for r in conn.execute("SELECT id_donante, nombre_donante FROM donante ORDER BY 1").fetchall():
        conn.execute(ins, (f"{_slug(r[1])}@donante.rescata.pe", r[1], h(), "donante", r[0], None))
    for r in conn.execute("SELECT id_organizacion, nombre_organizacion FROM organizacion ORDER BY 1").fetchall():
        conn.execute(ins, (f"{_slug(r[1])}@org.rescata.pe", r[1], h(), "organizacion", None, r[0]))


# ------------------------------------------------------------------ operaciones (reciben un Db con transaccion abierta)
def login(db, email, password, ip="-"):
    """Devuelve (token, usuario) o lanza AppError. Los fallos se registran en la misma llamada (el llamador hace COMMIT)."""
    email = (email or "").strip().lower()
    if not email or not password: raise AppError("AUTH", "Ingrese su correo y su contraseña.", 422, {"email": "Obligatorio" if not email else "", "password": "Obligatorio" if not password else ""})
    u = db.one("SELECT * FROM usuario WHERE email=?", (email,))
    ahora = db.val("SELECT datetime('now','localtime')")
    if u and u["bloqueado_hasta"] and u["bloqueado_hasta"] > ahora:
        mins = max(1, int(db.val("SELECT (julianday(?)-julianday(?))*1440", (u["bloqueado_hasta"], ahora), 1) + 0.99))
        raise AppError("AUTH_BLOQUEO", f"Cuenta bloqueada temporalmente por intentos fallidos. Intente de nuevo en {mins} minuto(s).", 429)
    ok = verify_password(password, u["password_hash"] if u else _FALSO)
    if not u or not ok:
        if u:
            n = u["intentos_fallidos"] + 1
            if n >= MAX_INTENTOS:
                db.run("UPDATE usuario SET intentos_fallidos=0, bloqueado_hasta=datetime('now','localtime',?) WHERE id_usuario=?", (f"+{BLOQUEO_MIN} minutes", u["id_usuario"]))
            else:
                db.run("UPDATE usuario SET intentos_fallidos=? WHERE id_usuario=?", (n, u["id_usuario"]))
        db.log("anonimo", "LOGIN_FALLIDO", "sesion", f"{email} desde {ip}", "ERROR")
        raise AppError("AUTH", "Correo o contraseña incorrectos.", 401)
    if not u["activo"]: raise AppError("AUTH", "Su cuenta está desactivada. Contacte al coordinador.", 403)
    token = secrets.token_urlsafe(32)
    db.run("UPDATE usuario SET intentos_fallidos=0, bloqueado_hasta=NULL, ultimo_acceso=? WHERE id_usuario=?", (ahora, u["id_usuario"]))
    db.run("DELETE FROM sesion WHERE expira < ?", (ahora,))
    db.run("INSERT INTO sesion (token_hash,id_usuario,expira) VALUES (?,?,datetime('now','localtime',?))", (_tok(token), u["id_usuario"], f"+{MAX_HORAS} hours"))
    db.log(u["rol"], "LOGIN", "sesion", f"Ingreso de {u['nombre']}")
    return token, u


def resolver(db, token):
    """Usuario de una sesion vigente (o None). Renueva la actividad."""
    if not token or len(token) > 100: return None
    s = db.one("""SELECT u.*, s.ultima_actividad, s.expira, s.token_hash FROM sesion s JOIN usuario u ON u.id_usuario=s.id_usuario
                  WHERE s.token_hash=? AND u.activo=1""", (_tok(token),))
    if not s: return None
    ahora = db.val("SELECT datetime('now','localtime')")
    inactivo = db.val("SELECT (julianday(?)-julianday(?))*1440", (ahora, s["ultima_actividad"]), 0)
    if s["expira"] < ahora or inactivo > INACTIVIDAD_MIN:
        db.run("DELETE FROM sesion WHERE token_hash=?", (s["token_hash"],)); return None
    if inactivo > 1: db.run("UPDATE sesion SET ultima_actividad=? WHERE token_hash=?", (ahora, s["token_hash"]))
    s["actor"] = s["id_donante"] or s["id_organizacion"]
    return s


def logout(db, token, usuario=None):
    if token: db.run("DELETE FROM sesion WHERE token_hash=?", (_tok(token),))
    if usuario: db.log(usuario["rol"], "LOGOUT", "sesion", f"Salida de {usuario['nombre']}")


def cambiar_password(db, usuario, actual, nueva, token):
    u = db.one("SELECT password_hash FROM usuario WHERE id_usuario=?", (usuario["id_usuario"],))
    if not verify_password(actual or "", u["password_hash"]): raise AppError("AUTH", "La contraseña actual no es correcta.", 422, {"actual": "Incorrecta"})
    validar_password(nueva)
    if nueva == actual: raise AppError("VALIDACION", "La nueva contraseña debe ser distinta de la actual.", 422, {"nueva": "Debe ser distinta"})
    db.run("UPDATE usuario SET password_hash=? WHERE id_usuario=?", (hash_password(nueva), usuario["id_usuario"]))
    db.run("DELETE FROM sesion WHERE id_usuario=? AND token_hash<>?", (usuario["id_usuario"], _tok(token)))   # cierra las demas sesiones


def cuentas_demo(db):
    return db.all("SELECT email, nombre, rol FROM usuario WHERE activo=1 ORDER BY CASE rol WHEN 'admin' THEN 0 WHEN 'auditor' THEN 1 WHEN 'organizacion' THEN 2 ELSE 3 END, nombre")


def restaurar_sesion(db, token, id_usuario):
    """Tras reiniciar la demo se recrean las cuentas; la sesion del coordinador que reinicio sigue valida."""
    db.run("INSERT OR REPLACE INTO sesion (token_hash,id_usuario,expira) VALUES (?,?,datetime('now','localtime',?))", (_tok(token), id_usuario, f"+{MAX_HORAS} hours"))
