"""Errores de aplicacion con codigo estilo Oracle (ORA-xxxxx) para la demostracion."""
import sqlite3, re


class AppError(Exception):
    def __init__(self, code, message, status=400, fields=None):
        super().__init__(message)
        self.code, self.message, self.status, self.fields = code, message, status, fields or {}

    def to_dict(self):
        return {"code": self.code, "message": self.message, "fields": self.fields}


def translate_db_error(exc, op=None):
    """Convierte una excepcion de SQLite en el AppError equivalente de Oracle."""
    msg = str(exc)
    if isinstance(exc, sqlite3.IntegrityError):
        if "UNIQUE constraint failed" in msg:
            cols = msg.split("failed:")[1].strip()
            return AppError("ORA-00001", f"Restriccion UNIQUE violada: ya existe un registro con el mismo valor en {cols}.", 409)
        if "CHECK constraint failed" in msg:
            name = msg.split("failed:")[1].strip()
            return AppError("ORA-02290", f"Restriccion CHECK violada: {name} (el valor no cumple la regla del modelo).", 422)
        if "FOREIGN KEY constraint failed" in msg:
            if op == "delete":
                return AppError("ORA-02292", "No se puede eliminar: existen registros hijos que dependen de este registro (integridad referencial).", 409)
            return AppError("ORA-02291", "Integridad referencial: el registro padre referenciado no existe (clave foranea).", 409)
        if "NOT NULL constraint failed" in msg:
            return AppError("ORA-01400", f"Valor obligatorio vacio: {msg.split('failed:')[1].strip()}.", 422)
        m = re.search(r"(ORA-\d+):\s*(.*)", msg)
        if m:
            return AppError(m.group(1), m.group(2), 409)
    m = re.search(r"(ORA-\d+):\s*(.*)", msg)
    if m:
        return AppError(m.group(1), m.group(2), 409)
    return AppError("DB-ERROR", msg, 500)
