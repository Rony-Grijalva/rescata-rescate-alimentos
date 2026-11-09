"""Acceso a datos: conexion SQLite, inicializacion del esquema y trazado de SQL."""
import sqlite3, os, threading, re
import config  # noqa: F401  (carga .env antes de leer variables)
from contextlib import contextmanager

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("RESCATA_DB", os.path.join(BASE, "data", "rescata.db"))
SCHEMA = os.path.join(BASE, "database", "schema.sql")
SEED = os.path.join(BASE, "database", "seed.sql")
AUTH_SQL = os.path.join(BASE, "database", "auth.sql")
SQLITE_OK_FULL_JOIN = tuple(int(x) for x in sqlite3.sqlite_version.split(".")) >= (3, 39, 0)

_local = threading.local()


def connect(path=None):
    path = path or DB_PATH
    conn = sqlite3.connect(path, timeout=15, isolation_level=None)  # transacciones manuales
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


def init_db(force=False):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if force and os.path.exists(DB_PATH):
        for ext in ("", "-wal", "-shm"):
            try: os.remove(DB_PATH + ext)
            except OSError: pass
    fresh = not os.path.exists(DB_PATH)
    conn = connect()
    if fresh:
        with open(SCHEMA, encoding="utf-8") as f: conn.executescript(f.read())
        with open(SEED, encoding="utf-8") as f: conn.executescript(f.read())
    with open(AUTH_SQL, encoding="utf-8") as f: conn.executescript(f.read())     # idempotente: tambien migra bases anteriores
    import auth; auth.seed_users(conn)
    conn.close()
    return fresh


class Trace:
    """Captura las sentencias SQL ejecutadas durante una peticion (se muestran en la consola SQL de la interfaz)."""
    NOISE = re.compile(r"^\s*(PRAGMA|BEGIN|COMMIT|ROLLBACK|SAVEPOINT|RELEASE)", re.I)

    def __init__(self):
        self.items = []

    def __call__(self, sql):
        s = " ".join(sql.split())
        if not s or self.NOISE.match(s) or "bitacora" in s.lower():
            return
        if len(s) > 600: s = s[:600] + " ..."
        self.items.append(s)


class Db:
    """Conexion por peticion con transaccion explicita."""

    def __init__(self, trace=True):
        self.conn = connect()
        self.trace = Trace() if trace else None
        if self.trace: self.conn.set_trace_callback(self.trace)
        self.conn.execute("BEGIN")

    def all(self, sql, params=()):
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def one(self, sql, params=()):
        r = self.conn.execute(sql, params).fetchone()
        return dict(r) if r else None

    def val(self, sql, params=(), default=None):
        r = self.conn.execute(sql, params).fetchone()
        return r[0] if r and r[0] is not None else default

    def run(self, sql, params=()):
        return self.conn.execute(sql, params)

    def insert(self, sql, params=()):
        return self.conn.execute(sql, params).lastrowid

    @contextmanager
    def savepoint(self, name="sp"):
        self.conn.execute(f"SAVEPOINT {name}")
        try:
            yield
            self.conn.execute(f"RELEASE {name}")
        except BaseException:
            self.conn.execute(f"ROLLBACK TO {name}")
            self.conn.execute(f"RELEASE {name}")
            raise

    def log(self, rol, accion, entidad, detalle="", resultado="OK"):
        self.conn.execute("INSERT INTO bitacora (rol,accion,entidad,detalle,resultado) VALUES (?,?,?,?,?)",
                          (rol, accion, entidad, (detalle or "")[:300], resultado))

    def commit(self): self.conn.execute("COMMIT")
    def rollback(self):
        try: self.conn.execute("ROLLBACK")
        except sqlite3.Error: pass
    def close(self):
        try: self.conn.close()
        except sqlite3.Error: pass
