"""CRUD generico dirigido por metadatos: validacion de campos + SQL parametrizado."""
import re
from errors import AppError

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2})?)?$")


def F(name, kind="str", req=False, max=None, label=None, min=None, choices=None):
    return dict(name=name, kind=kind, req=req, max=max, label=label or name.replace("id_", "").replace("_", " ").capitalize(), min=min, choices=choices)


def clean(spec, data, partial=False):
    out, errs = {}, {}
    for f in spec["fields"]:
        n = f["name"]
        if n not in data:
            if f["req"] and not partial: errs[n] = f"{f['label']} es obligatorio"
            continue
        v = data[n]
        if isinstance(v, str): v = v.strip()
        if v in ("", None):
            if f["req"]: errs[n] = f"{f['label']} es obligatorio"
            else: out[n] = None
            continue
        k = f["kind"]
        try:
            if k == "str":
                if f["max"] and len(str(v)) > f["max"]: raise ValueError(f"Maximo {f['max']} caracteres")
                v = str(v)
            elif k == "int" or k == "fk":
                v = int(v)
            elif k == "num":
                v = float(v)
                if f["min"] is not None and v < f["min"]: raise ValueError(f"Debe ser >= {f['min']}")
            elif k == "bool":
                v = 1 if v in (1, "1", True, "true", "on", "si") else 0
            elif k == "email":
                if not EMAIL.match(v): raise ValueError("Correo no valido")
            elif k == "ruc":
                if not re.fullmatch(r"\d{11}", str(v)): raise ValueError("El RUC debe tener exactamente 11 digitos")
                v = str(v)
            elif k == "placa":
                v = str(v).upper()
                if not re.fullmatch(r"[A-Z0-9]{3}-[A-Z0-9]{3,4}", v): raise ValueError("Formato de placa: ABC-123")
            elif k == "fecha":
                if not FECHA.match(str(v)): raise ValueError("Fecha no valida (AAAA-MM-DD)")
                v = str(v).replace("T", " ")
            elif k == "sexo":
                v = str(v).upper()
                if v not in ("M", "F"): raise ValueError("Use M o F")
            elif k == "doc":
                if not re.fullmatch(r"[A-Za-z0-9]{6,15}", str(v)): raise ValueError("Documento de 6 a 15 caracteres alfanumericos")
                v = str(v)
        except (ValueError, TypeError) as e:
            errs[n] = str(e) if str(e) and "invalid literal" not in str(e) and "could not convert" not in str(e) else f"{f['label']}: valor no valido"
            continue
        out[n] = v
    if errs:
        raise AppError("VALIDACION", "Revise los campos marcados.", 422, errs)
    return out


class Resource:
    def __init__(self, table, pk, fields, list_sql, search=(), filters=(), order="1 DESC", perm=None, label=None, unique_msgs=None):
        self.spec = dict(table=table, pk=pk, fields=fields)
        self.table, self.pk, self.fields = table, pk, fields
        self.list_sql, self.search, self.filters, self.order = list_sql, search, filters, order
        self.perm, self.label = perm or table, label or table

    def list(self, db, q=None, params=None, scope=None):
        where, args = [], []
        if scope:                                    # alcance por rol: (columna, valor, incluir_nulos)
            col, val, nulos = scope
            where.append(f"({col} = ?" + (f" OR {col} IS NULL)" if nulos else ")")); args.append(val)
        if q and self.search:
            where.append("(" + " OR ".join(f"{c} LIKE ?" for c in self.search) + ")")
            args += [f"%{q}%"] * len(self.search)
        for f in self.filters:
            v = (params or {}).get("f_" + f)
            if v not in (None, ""):
                where.append(f"{f} = ?"); args.append(v)
        sql = f"SELECT * FROM ({self.list_sql}) t"
        if where: sql += " WHERE " + " AND ".join(where)
        return db.all(sql + f" ORDER BY {self.order}", args)

    def get(self, db, id_):
        r = db.one(f"SELECT * FROM ({self.list_sql}) t WHERE {self.pk}=?", (id_,))
        if not r: raise AppError("ORA-01403", f"No existe el registro {id_} en {self.table}", 404)
        return r

    def create(self, db, data):
        d = clean(self.spec, data)
        cols = ",".join(d)
        id_ = db.insert(f"INSERT INTO {self.table} ({cols}) VALUES ({','.join('?' * len(d))})", list(d.values()))
        return id_

    def update(self, db, id_, data):
        self.get(db, id_)
        d = clean(self.spec, data, partial=True)
        if not d: raise AppError("VALIDACION", "No hay cambios que guardar", 422)
        db.run(f"UPDATE {self.table} SET {','.join(k + '=?' for k in d)} WHERE {self.pk}=?", list(d.values()) + [id_])
        return id_

    def delete(self, db, id_):
        self.get(db, id_)
        db.run(f"DELETE FROM {self.table} WHERE {self.pk}=?", (id_,))


def build_registry():
    R = {}
    R["donantes"] = Resource("donante", "id_donante", [
        F("nombre_donante", req=True, max=150, label="Nombre"), F("ruc", "ruc", label="RUC"), F("direccion", max=200, label="Direccion"),
        F("id_zona", "fk", req=True, label="Zona"), F("telefono", max=30, label="Telefono"), F("email", "email", max=100, label="Correo"),
        F("id_estado_donante", "fk", req=True, label="Estado")],
        """SELECT d.*, z.nombre_zona, dis.nombre_distrito, e.estado,
                  (SELECT COUNT(*) FROM donacion_ofrecida l WHERE l.id_donante=d.id_donante) AS lotes
           FROM donante d LEFT JOIN zona z ON z.id_zona=d.id_zona LEFT JOIN distrito dis ON dis.id_distrito=z.id_distrito
           JOIN estado_donante e ON e.id_estado_donante=d.id_estado_donante""",
        search=("nombre_donante", "ruc", "nombre_zona"), filters=("id_estado_donante",), order="nombre_donante", perm="donantes")
    R["organizaciones"] = Resource("organizacion", "id_organizacion", [
        F("nombre_organizacion", req=True, max=150, label="Nombre"), F("direccion", max=200, label="Direccion"),
        F("id_zona", "fk", req=True, label="Zona"), F("id_estado_organizacion", "fk", req=True, label="Estado"),
        F("id_tipo_organizacion", "fk", req=True, label="Tipo"), F("tiene_refrigeracion", "bool", label="Refrigeracion")],
        """SELECT o.*, z.nombre_zona, dis.nombre_distrito, e.estado, t.tipo,
                  (SELECT COUNT(*) FROM donacion_parcial p WHERE p.id_organizacion=o.id_organizacion) AS solicitudes
           FROM organizacion o JOIN zona z ON z.id_zona=o.id_zona JOIN distrito dis ON dis.id_distrito=z.id_distrito
           JOIN estado_organizacion e ON e.id_estado_organizacion=o.id_estado_organizacion
           JOIN tipo_organizacion t ON t.id_tipo_organizacion=o.id_tipo_organizacion""",
        search=("nombre_organizacion", "nombre_zona", "tipo"), filters=("id_tipo_organizacion", "id_estado_organizacion"), order="nombre_organizacion", perm="organizaciones")
    R["personas"] = Resource("persona_recojo", "id_persona_recojo", [
        F("id_organizacion", "fk", req=True, label="Organizacion"), F("nombres", req=True, max=100), F("apellidos", req=True, max=100),
        F("id_tipo_documento", "fk", req=True, label="Tipo de documento"), F("num_documento", "doc", req=True, label="N.o de documento"),
        F("sexo", "sexo", label="Sexo"), F("telefono", max=30, label="Telefono"), F("email", "email", max=100, label="Correo")],
        """SELECT p.*, o.nombre_organizacion, t.tipo_doc FROM persona_recojo p
           JOIN organizacion o ON o.id_organizacion=p.id_organizacion JOIN tipo_documento t ON t.id_tipo_documento=p.id_tipo_documento""",
        search=("nombres", "apellidos", "num_documento", "nombre_organizacion"), filters=("id_organizacion",), order="apellidos", perm="personas")
    R["vehiculos"] = Resource("vehiculo", "id_vehiculo", [
        F("placa", "placa", req=True, label="Placa"), F("marca", max=50), F("modelo", max=50),
        F("capacidad_kg", "num", req=True, min=0.01, label="Capacidad (kg)"), F("id_organizacion", "fk", label="Organizacion propietaria")],
        """SELECT v.*, o.nombre_organizacion,
                  (SELECT COUNT(*) FROM despacho d WHERE d.id_vehiculo=v.id_vehiculo) AS despachos
           FROM vehiculo v LEFT JOIN organizacion o ON o.id_organizacion=v.id_organizacion""",
        search=("placa", "marca", "modelo", "nombre_organizacion"), order="placa", perm="vehiculos")
    # Catalogos
    cat = lambda t, pk, fields, label, lsql=None, order=None: Resource(t, pk, fields, lsql or f"SELECT * FROM {t}", search=tuple(f["name"] for f in fields if f["kind"] == "str"), order=order or "2", perm="catalogos", label=label)
    R["cat_distritos"] = cat("distrito", "id_distrito", [F("nombre_distrito", req=True, max=80, label="Distrito"), F("provincia", req=True, max=80, label="Provincia")], "Distritos")
    R["cat_zonas"] = cat("zona", "id_zona", [F("id_distrito", "fk", req=True, label="Distrito"), F("nombre_zona", req=True, max=100, label="Zona")], "Zonas",
        "SELECT z.*, d.nombre_distrito FROM zona z JOIN distrito d ON d.id_distrito=z.id_distrito", "nombre_distrito, nombre_zona")
    R["cat_categorias"] = cat("categoria_alimento", "id_categoria_alimento", [F("nombre_categoria", req=True, max=50, label="Categoria")], "Categorias")
    R["cat_alimentos"] = cat("alimento", "id_alimento", [F("nombre_alimento", req=True, max=150, label="Alimento"), F("id_categoria_alimento", "fk", req=True, label="Categoria"), F("requiere_refrigeracion", "bool", label="Requiere frio")], "Alimentos",
        "SELECT a.*, c.nombre_categoria FROM alimento a JOIN categoria_alimento c ON c.id_categoria_alimento=a.id_categoria_alimento", "nombre_alimento")
    R["cat_unidades"] = cat("unidad_medida", "id_unidad_medida", [F("tipo_medida", req=True, max=30, label="Unidad de medida")], "Unidades de medida")
    R["cat_tipos_org"] = cat("tipo_organizacion", "id_tipo_organizacion", [F("tipo", req=True, max=50, label="Tipo de organizacion")], "Tipos de organizacion")
    R["cat_tipos_doc"] = cat("tipo_documento", "id_tipo_documento", [F("tipo_doc", req=True, max=30, label="Tipo de documento")], "Tipos de documento")
    return R


LOOKUPS = {
    "zonas": "SELECT z.id_zona id, z.nombre_zona || ' (' || d.nombre_distrito || ')' nombre FROM zona z JOIN distrito d ON d.id_distrito=z.id_distrito ORDER BY 2",
    "distritos": "SELECT id_distrito id, nombre_distrito nombre FROM distrito ORDER BY 2",
    "estados_donante": "SELECT id_estado_donante id, estado nombre FROM estado_donante ORDER BY 1",
    "estados_org": "SELECT id_estado_organizacion id, estado nombre FROM estado_organizacion ORDER BY 1",
    "tipos_org": "SELECT id_tipo_organizacion id, tipo nombre FROM tipo_organizacion ORDER BY 2",
    "tipos_doc": "SELECT id_tipo_documento id, tipo_doc nombre FROM tipo_documento ORDER BY 1",
    "unidades": "SELECT id_unidad_medida id, tipo_medida nombre FROM unidad_medida ORDER BY 2",
    "categorias": "SELECT id_categoria_alimento id, nombre_categoria nombre FROM categoria_alimento ORDER BY 2",
    "alimentos": "SELECT id_alimento id, nombre_alimento nombre, requiere_refrigeracion frio FROM alimento ORDER BY 2",
    "donantes": "SELECT id_donante id, nombre_donante nombre, id_zona, direccion FROM donante ORDER BY 2",
    "organizaciones": "SELECT id_organizacion id, nombre_organizacion nombre, tiene_refrigeracion frio FROM organizacion ORDER BY 2",
    "vehiculos": "SELECT id_vehiculo id, placa || ' · ' || IFNULL(modelo,'') nombre, id_organizacion, capacidad_kg FROM vehiculo ORDER BY 2",
}
