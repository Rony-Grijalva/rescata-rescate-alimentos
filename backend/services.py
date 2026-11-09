"""Consultas de lectura compuestas para pantallas (listados enriquecidos, panel y esquema)."""
import re
import business as B
from errors import AppError

LOTES_SQL = """
SELECT l.id_donacion_ofrecida, l.fecha_publicacion, l.direccion, l.id_donante, l.id_zona,
       don.nombre_donante, z.nombre_zona, dis.nombre_distrito, s.estado,
       COUNT(det.id_detalle_donacion_ofrecida) AS lineas,
       IFNULL(SUM(det.cantidad*det.costo_unitario),0) AS valor,
       IFNULL(SUM(det.peso_total_kg),0) AS peso_kg,
       MIN(det.fecha_vencimiento) AS vence,
       ROUND((julianday(MIN(det.fecha_vencimiento))-julianday('now','localtime'))*24,1) AS horas_vence,
       (SELECT IFNULL(SUM(sl.saldo),0) FROM v_saldo_linea sl WHERE sl.id_donacion_ofrecida=l.id_donacion_ofrecida) AS saldo_total,
       (SELECT IFNULL(SUM(sl.cantidad_publicada),0) FROM v_saldo_linea sl WHERE sl.id_donacion_ofrecida=l.id_donacion_ofrecida) AS cantidad_total,
       (SELECT COUNT(*) FROM donacion_parcial p WHERE p.id_donacion_ofrecida=l.id_donacion_ofrecida) AS solicitudes,
       (SELECT MAX(a.requiere_refrigeracion) FROM detalle_donacion_ofrecida d2 JOIN alimento a ON a.id_alimento=d2.id_alimento
         WHERE d2.id_donacion_ofrecida=l.id_donacion_ofrecida) AS requiere_frio
  FROM donacion_ofrecida l
  JOIN donante don ON don.id_donante=l.id_donante
  JOIN zona z ON z.id_zona=l.id_zona JOIN distrito dis ON dis.id_distrito=z.id_distrito
  JOIN estado_donacion_ofrecida s ON s.id_estado_donacion_ofrecida=l.id_estado_donacion_ofrecida
  LEFT JOIN detalle_donacion_ofrecida det ON det.id_donacion_ofrecida=l.id_donacion_ofrecida
 {where} GROUP BY l.id_donacion_ofrecida ORDER BY l.fecha_publicacion DESC, l.id_donacion_ofrecida DESC"""


def lotes(db, q=None, estado=None, donante=None, org=None):
    """donante -> solo sus lotes; org -> lotes disponibles (PUBLICADO con saldo) y los que ya solicito."""
    where, args = [], []
    if q: where.append("(don.nombre_donante LIKE ? OR z.nombre_zona LIKE ? OR dis.nombre_distrito LIKE ? OR l.id_donacion_ofrecida = ?)"); args += [f"%{q}%", f"%{q}%", f"%{q}%", q if str(q).isdigit() else -1]
    if estado: where.append("s.estado = ?"); args.append(estado)
    if donante: where.append("l.id_donante = ?"); args.append(donante)
    rows = db.all(LOTES_SQL.format(where=("WHERE " + " AND ".join(where)) if where else ""), args)
    for r in rows:
        r["urgencia"] = B.fn_urgencia(r["horas_vence"]) if r["horas_vence"] is not None else None
    if org:
        mias = {r["id_donacion_ofrecida"]: r for r in db.all("""SELECT p.id_donacion_ofrecida, p.id_donacion_parcial, e.estado FROM donacion_parcial p
            JOIN estado_donacion e ON e.id_estado_donacion=p.id_estado_donacion WHERE p.id_organizacion=?""", (org,))}
        frio = db.val("SELECT tiene_refrigeracion FROM organizacion WHERE id_organizacion=?", (org,), 0)
        out = []
        for r in rows:
            m = mias.get(r["id_donacion_ofrecida"])
            r["mi_solicitud"] = m["id_donacion_parcial"] if m else None
            r["mi_estado"] = m["estado"] if m else None
            r["frio_ok"] = bool(frio) or not r["requiere_frio"]
            r["solicitudes"] = None                                  # no se expone la competencia
            if m or (r["estado"] == "PUBLICADO" and (r["saldo_total"] or 0) > 0): out.append(r)
        rows = out
    return rows


def lote_detalle(db, id_, org=None):
    r = next(iter(db.all(LOTES_SQL.format(where="WHERE l.id_donacion_ofrecida = ?"), (id_,))), None)
    if not r: raise AppError("ORA-01403", f"El lote {id_} no existe", 404)
    r["urgencia"] = B.fn_urgencia(r["horas_vence"]) if r["horas_vence"] is not None else None
    r["lineas_detalle"] = db.all("""
        SELECT det.*, a.nombre_alimento, a.requiere_refrigeracion, m.tipo_medida, sl.saldo, sl.cantidad_repartida,
               ROUND((julianday(det.fecha_vencimiento)-julianday('now','localtime'))*24,1) AS horas
          FROM detalle_donacion_ofrecida det JOIN alimento a ON a.id_alimento=det.id_alimento
          JOIN unidad_medida m ON m.id_unidad_medida=det.id_unidad_medida
          JOIN v_saldo_linea sl ON sl.id_detalle_donacion_ofrecida=det.id_detalle_donacion_ofrecida
         WHERE det.id_donacion_ofrecida=? ORDER BY det.id_detalle_donacion_ofrecida""", (id_,))
    for l in r["lineas_detalle"]: l["urgencia"] = B.fn_urgencia(l["horas"])
    if org is None:
        r["solicitudes_lista"] = db.all("""SELECT p.id_donacion_parcial, o.nombre_organizacion, e.estado FROM donacion_parcial p
            JOIN organizacion o ON o.id_organizacion=p.id_organizacion JOIN estado_donacion e ON e.id_estado_donacion=p.id_estado_donacion
            WHERE p.id_donacion_ofrecida=? ORDER BY p.id_donacion_parcial""", (id_,))
    else:
        frio = db.val("SELECT tiene_refrigeracion FROM organizacion WHERE id_organizacion=?", (org,), 0)
        for l in r["lineas_detalle"]: l["compatible"] = bool(frio) or not l["requiere_refrigeracion"]
        m = db.one("SELECT id_donacion_parcial FROM donacion_parcial WHERE id_donacion_ofrecida=? AND id_organizacion=?", (id_, org))
        r["mi_solicitud"] = m["id_donacion_parcial"] if m else None
        r["solicitudes"] = None
    return r


SOL_SQL = """
SELECT p.id_donacion_parcial, p.id_donacion_ofrecida, p.id_organizacion, p.fecha_solicitud, e.estado,
       o.nombre_organizacion, o.tiene_refrigeracion, don.nombre_donante,
       (SELECT IFNULL(SUM(dd.cantidad*det.costo_unitario),0) FROM detalle_donacion_parcial dd
          JOIN detalle_donacion_ofrecida det ON det.id_detalle_donacion_ofrecida=dd.id_detalle_donacion_ofrecida
         WHERE dd.id_donacion_parcial=p.id_donacion_parcial) AS valor,
       (SELECT ROUND(IFNULL(SUM(dd.cantidad/det.cantidad*IFNULL(det.peso_total_kg,0)),0),2) FROM detalle_donacion_parcial dd
          JOIN detalle_donacion_ofrecida det ON det.id_detalle_donacion_ofrecida=dd.id_detalle_donacion_ofrecida
         WHERE dd.id_donacion_parcial=p.id_donacion_parcial) AS peso_kg,
       (SELECT COUNT(*) FROM detalle_donacion_parcial dd WHERE dd.id_donacion_parcial=p.id_donacion_parcial) AS lineas,
       (SELECT id_despacho FROM despacho d WHERE d.id_donacion_parcial=p.id_donacion_parcial ORDER BY 1 DESC LIMIT 1) AS id_despacho,
       (SELECT c.serie||'-'||printf('%08d',c.numero) FROM comprobante c WHERE c.id_donacion_parcial=p.id_donacion_parcial) AS comprobante
  FROM donacion_parcial p
  JOIN estado_donacion e ON e.id_estado_donacion=p.id_estado_donacion
  JOIN organizacion o ON o.id_organizacion=p.id_organizacion
  JOIN donacion_ofrecida l ON l.id_donacion_ofrecida=p.id_donacion_ofrecida
  JOIN donante don ON don.id_donante=l.id_donante {where} ORDER BY p.id_donacion_parcial DESC"""


def solicitudes(db, q=None, estado=None, org=None, donante=None):
    where, args = [], []
    if q: where.append("(o.nombre_organizacion LIKE ? OR don.nombre_donante LIKE ? OR p.id_donacion_parcial = ?)"); args += [f"%{q}%", f"%{q}%", q if str(q).isdigit() else -1]
    if estado: where.append("e.estado=?"); args.append(estado)
    if org: where.append("p.id_organizacion=?"); args.append(org)
    if donante: where.append("l.id_donante=?"); args.append(donante)
    return db.all(SOL_SQL.format(where=("WHERE " + " AND ".join(where)) if where else ""), args)


def solicitud_detalle(db, id_):
    r = next(iter(db.all(SOL_SQL.format(where="WHERE p.id_donacion_parcial = ?"), (id_,))), None)
    if not r: raise AppError("ORA-01403", f"La solicitud {id_} no existe", 404)
    r["reparto"] = db.all("""SELECT dd.id_detalle_donacion_parcial, dd.cantidad, det.id_detalle_donacion_ofrecida, a.nombre_alimento, m.tipo_medida,
          det.costo_unitario, dd.cantidad*det.costo_unitario AS valor FROM detalle_donacion_parcial dd
          JOIN detalle_donacion_ofrecida det ON det.id_detalle_donacion_ofrecida=dd.id_detalle_donacion_ofrecida
          JOIN alimento a ON a.id_alimento=det.id_alimento JOIN unidad_medida m ON m.id_unidad_medida=det.id_unidad_medida
          WHERE dd.id_donacion_parcial=? ORDER BY 1""", (id_,))
    r["lineas_lote"] = db.all("""SELECT det.id_detalle_donacion_ofrecida id, a.nombre_alimento, a.requiere_refrigeracion, m.tipo_medida, sl.saldo, sl.cantidad_publicada
          FROM detalle_donacion_ofrecida det JOIN alimento a ON a.id_alimento=det.id_alimento
          JOIN unidad_medida m ON m.id_unidad_medida=det.id_unidad_medida
          JOIN v_saldo_linea sl ON sl.id_detalle_donacion_ofrecida=det.id_detalle_donacion_ofrecida
          WHERE det.id_donacion_ofrecida=? ORDER BY 1""", (r["id_donacion_ofrecida"],))
    for l in r["lineas_lote"]:
        l["compatible"] = not (l["requiere_refrigeracion"] == 1 and r["tiene_refrigeracion"] == 0)
    return r


def despachos(db, org=None):
    rows = db.all("""SELECT d.*, v.placa, v.modelo, v.capacidad_kg, o.nombre_organizacion, e.estado AS estado_solicitud,
        (SELECT ROUND(IFNULL(SUM(dd.cantidad/det.cantidad*IFNULL(det.peso_total_kg,0)),0),2) FROM detalle_donacion_parcial dd
           JOIN detalle_donacion_ofrecida det ON det.id_detalle_donacion_ofrecida=dd.id_detalle_donacion_ofrecida
          WHERE dd.id_donacion_parcial=d.id_donacion_parcial) AS peso_kg
        FROM despacho d JOIN vehiculo v ON v.id_vehiculo=d.id_vehiculo
        JOIN donacion_parcial p ON p.id_donacion_parcial=d.id_donacion_parcial
        JOIN organizacion o ON o.id_organizacion=p.id_organizacion
        JOIN estado_donacion e ON e.id_estado_donacion=p.id_estado_donacion
        WHERE (? IS NULL OR p.id_organizacion=?) ORDER BY d.id_despacho DESC""", (org, org))
    for r in rows:
        r["responsables"] = db.all("""SELECT dr.id_persona_recojo, p.nombres||' '||p.apellidos AS nombre FROM despacho_responsable dr
            JOIN persona_recojo p ON p.id_persona_recojo=dr.id_persona_recojo WHERE dr.id_despacho=?""", (r["id_despacho"],))
        r["fase"] = "Entregado" if r["fecha_arribo"] else "En ruta" if r["fecha_salida"] else "En punto de recojo" if r["fecha_llegada"] else "Programado"
    return rows


COMP_ALCANCE = {"donante": "l.id_donante = ?", "organizacion": "p.id_organizacion = ?"}

def comprobantes(db, rol, actor):
    if rol in COMP_ALCANCE:
        return db.all(f"""SELECT v.* FROM v_comprobante_valorizado v JOIN donacion_parcial p ON p.id_donacion_parcial=v.id_donacion_parcial
            JOIN donacion_ofrecida l ON l.id_donacion_ofrecida=p.id_donacion_ofrecida WHERE {COMP_ALCANCE[rol]} ORDER BY v.id_comprobante DESC""", (actor,))
    return db.all("SELECT * FROM v_comprobante_valorizado ORDER BY id_comprobante DESC")


def comprobante_detalle(db, id_):
    c = db.one("SELECT * FROM v_comprobante_valorizado WHERE id_comprobante=?", (id_,))
    if not c: raise AppError("ORA-01403", "El comprobante no existe", 404)
    c["lineas"] = db.all("""SELECT a.nombre_alimento, dd.cantidad, m.tipo_medida, det.costo_unitario, dd.cantidad*det.costo_unitario AS importe
        FROM detalle_donacion_parcial dd JOIN detalle_donacion_ofrecida det ON det.id_detalle_donacion_ofrecida=dd.id_detalle_donacion_ofrecida
        JOIN alimento a ON a.id_alimento=det.id_alimento JOIN unidad_medida m ON m.id_unidad_medida=det.id_unidad_medida
        WHERE dd.id_donacion_parcial=? ORDER BY 1""", (c["id_donacion_parcial"],))
    c["coincide"] = abs((c["monto_emitido"] or 0) - (c["monto_recalculado"] or 0)) < 0.005
    return c


def _kpi(ic, tone, v, lab, fmt="n"): return {"ic": ic, "tone": tone, "v": v, "fmt": fmt, "lab": lab}

KG_ENT = """SELECT IFNULL(SUM(dd.cantidad/det.cantidad*IFNULL(det.peso_total_kg,0)),0) FROM detalle_donacion_parcial dd
    JOIN detalle_donacion_ofrecida det ON det.id_detalle_donacion_ofrecida=dd.id_detalle_donacion_ofrecida
    JOIN donacion_parcial p ON p.id_donacion_parcial=dd.id_donacion_parcial JOIN estado_donacion e ON e.id_estado_donacion=p.id_estado_donacion
    JOIN donacion_ofrecida l ON l.id_donacion_ofrecida=p.id_donacion_ofrecida WHERE e.estado='ENTREGADA' AND {w}"""
ESTADOS_SOL = """SELECT e.estado AS etiqueta, COUNT(x.id_donacion_parcial) AS valor FROM estado_donacion e
    LEFT JOIN (SELECT p.* FROM donacion_parcial p JOIN donacion_ofrecida l ON l.id_donacion_ofrecida=p.id_donacion_ofrecida WHERE {w}) x
      ON x.id_estado_donacion=e.id_estado_donacion GROUP BY e.id_estado_donacion ORDER BY e.id_estado_donacion"""


def dashboard(db, rol="admin", actor=None):
    if rol == "donante": return _dash_donante(db, actor)
    if rol == "organizacion": return _dash_org(db, actor)
    return _dash_global(db, rol)


def _dash_donante(db, d):
    w = "l.id_donante=?"
    mis = "FROM donacion_ofrecida l JOIN estado_donacion_ofrecida s ON s.id_estado_donacion_ofrecida=l.id_estado_donacion_ofrecida WHERE l.id_donante=?"
    pub = db.val(f"SELECT COUNT(*) {mis} AND s.estado='PUBLICADO'", (d,), 0)
    kg = round(db.val("SELECT IFNULL(SUM(det.peso_total_kg),0) FROM detalle_donacion_ofrecida det JOIN donacion_ofrecida l ON l.id_donacion_ofrecida=det.id_donacion_ofrecida WHERE l.id_donante=?", (d,), 0), 1)
    kge = round(db.val(KG_ENT.format(w=w), (d,), 0), 1)
    donado = round(db.val("SELECT IFNULL(SUM(c.monto_total),0) FROM comprobante c JOIN donacion_parcial p ON p.id_donacion_parcial=c.id_donacion_parcial JOIN donacion_ofrecida l ON l.id_donacion_ofrecida=p.id_donacion_ofrecida WHERE l.id_donante=?", (d,), 0), 2)
    esperan = db.val("""SELECT COUNT(*) FROM donacion_parcial p JOIN estado_donacion e ON e.id_estado_donacion=p.id_estado_donacion
        JOIN donacion_ofrecida l ON l.id_donacion_ofrecida=p.id_donacion_ofrecida WHERE l.id_donante=? AND e.estado<>'ENTREGADA'""", (d,), 0)
    mine = {r[0] for r in db.conn.execute("SELECT id_donacion_ofrecida FROM donacion_ofrecida WHERE id_donante=?", (d,)).fetchall()}
    alertas = [a for a in B.sp_alerta_vencimientos(db, 24) if a["id_donacion_ofrecida"] in mine][:6]
    comps = db.val("SELECT COUNT(*) FROM comprobante c JOIN donacion_parcial p ON p.id_donacion_parcial=c.id_donacion_parcial JOIN donacion_ofrecida l ON l.id_donacion_ofrecida=p.id_donacion_ofrecida WHERE l.id_donante=?", (d,), 0)
    return {"rol": "donante", "intro": "Publique sus excedentes y siga qué pasó con cada uno: quién lo pidió, si ya se entregó y su constancia de donación.",
        "kpi": [_kpi("package", "t-blue", pub, "Lotes publicados vigentes"), _kpi("scale", "t-green", kg, "Alimento ofrecido (kg)", "kg"),
                _kpi("truck", "t-green", kge, "Ya entregado (kg)", "kg"), _kpi("hand", "t-amber", esperan, "Solicitudes en curso"),
                _kpi("coin", "t-amber", donado, "Donado con constancia", "money"), _kpi("receipt", "t-blue", comps, "Constancias emitidas")],
        "graficos": [{"titulo": "Mis lotes por estado", "tipo": "donut", "datos": db.all("""SELECT s.estado AS etiqueta, COUNT(l.id_donacion_ofrecida) AS valor FROM estado_donacion_ofrecida s
                LEFT JOIN donacion_ofrecida l ON l.id_estado_donacion_ofrecida=s.id_estado_donacion_ofrecida AND l.id_donante=? GROUP BY s.id_estado_donacion_ofrecida ORDER BY s.id_estado_donacion_ofrecida""", (d,))},
            {"titulo": "Valor por lote", "sub": "S/", "tipo": "hbars", "fmt": "money", "datos": db.all("""SELECT 'Lote #'||l.id_donacion_ofrecida AS etiqueta, ROUND(SUM(det.cantidad*det.costo_unitario),2) AS valor
                FROM donacion_ofrecida l JOIN detalle_donacion_ofrecida det ON det.id_donacion_ofrecida=l.id_donacion_ofrecida WHERE l.id_donante=? GROUP BY l.id_donacion_ofrecida ORDER BY l.id_donacion_ofrecida DESC LIMIT 6""", (d,))}],
        "alertas": alertas, "alertas_titulo": "Mis alimentos por vencer (24 h)",
        "acciones": [{"t": "Publicar un lote", "ir": "#/lotes?nuevo=1"}, {"t": "Ver mis constancias", "ir": "#/comprobantes"}]}


def _dash_org(db, o):
    w = "p.id_organizacion=?"
    est = {r["estado"]: r["n"] for r in db.all("""SELECT e.estado, COUNT(*) n FROM donacion_parcial p JOIN estado_donacion e ON e.id_estado_donacion=p.id_estado_donacion WHERE p.id_organizacion=? GROUP BY e.estado""", (o,))}
    ya = {r[0] for r in db.conn.execute("SELECT id_donacion_ofrecida FROM donacion_parcial WHERE id_organizacion=?", (o,)).fetchall()}
    disp = [l for l in lotes(db, org=o) if not l["mi_solicitud"]]
    kg = round(db.val("""SELECT IFNULL(SUM(dd.cantidad/det.cantidad*IFNULL(det.peso_total_kg,0)),0) FROM detalle_donacion_parcial dd
        JOIN detalle_donacion_ofrecida det ON det.id_detalle_donacion_ofrecida=dd.id_detalle_donacion_ofrecida
        JOIN donacion_parcial p ON p.id_donacion_parcial=dd.id_donacion_parcial JOIN estado_donacion e ON e.id_estado_donacion=p.id_estado_donacion
        WHERE e.estado='ENTREGADA' AND p.id_organizacion=?""", (o,), 0), 1)
    val = round(db.val("""SELECT IFNULL(SUM(dd.cantidad*det.costo_unitario),0) FROM detalle_donacion_parcial dd JOIN detalle_donacion_ofrecida det ON det.id_detalle_donacion_ofrecida=dd.id_detalle_donacion_ofrecida
        JOIN donacion_parcial p ON p.id_donacion_parcial=dd.id_donacion_parcial JOIN estado_donacion e ON e.id_estado_donacion=p.id_estado_donacion WHERE e.estado='ENTREGADA' AND p.id_organizacion=?""", (o,), 0), 2)
    sin_desp = db.val("""SELECT COUNT(*) FROM donacion_parcial p JOIN estado_donacion e ON e.id_estado_donacion=p.id_estado_donacion
        WHERE p.id_organizacion=? AND e.estado='ASIGNADA' AND NOT EXISTS (SELECT 1 FROM despacho d WHERE d.id_donacion_parcial=p.id_donacion_parcial)""", (o,), 0)
    en_curso = db.val("""SELECT COUNT(*) FROM despacho d JOIN donacion_parcial p ON p.id_donacion_parcial=d.id_donacion_parcial WHERE p.id_organizacion=? AND d.fecha_arribo IS NULL""", (o,), 0)
    pend = []
    if sin_desp: pend.append({"t": "solicitud(es) con alimentos asignados esperan que programe el recojo", "ir": "#/logistica", "n": sin_desp})
    if est.get("PENDIENTE"): pend.append({"t": "solicitud(es) esperan que el coordinador les asigne alimentos", "ir": "#/solicitudes", "n": est["PENDIENTE"]})
    alertas = [a for a in B.sp_alerta_vencimientos(db, 24) if a["id_donacion_ofrecida"] not in ya][:6]
    return {"rol": "organizacion", "intro": "Elija un lote disponible y pida lo que necesita. El coordinador le asigna los alimentos y usted programa el recojo.",
        "kpi": [_kpi("package", "t-blue", len(disp), "Lotes disponibles para pedir"), _kpi("hand", "t-amber", est.get("PENDIENTE", 0), "Solicitudes por asignar"),
                _kpi("check", "t-green", est.get("ASIGNADA", 0), "Asignadas (listas para recoger)"), _kpi("truck", "t-blue", en_curso, "Despachos en curso"),
                _kpi("scale", "t-green", kg, "Alimento recibido (kg)", "kg"), _kpi("coin", "t-amber", val, "Valor recibido", "money")],
        "graficos": [{"titulo": "Mis solicitudes por estado", "tipo": "donut", "datos": db.all(ESTADOS_SOL.format(w="p.id_organizacion=?"), (o,))},
            {"titulo": "Valor asignado por donante", "sub": "S/", "tipo": "hbars", "fmt": "money", "datos": db.all("""SELECT don.nombre_donante AS etiqueta, ROUND(SUM(dd.cantidad*det.costo_unitario),2) AS valor FROM donacion_parcial p
                JOIN detalle_donacion_parcial dd ON dd.id_donacion_parcial=p.id_donacion_parcial JOIN detalle_donacion_ofrecida det ON det.id_detalle_donacion_ofrecida=dd.id_detalle_donacion_ofrecida
                JOIN donacion_ofrecida l ON l.id_donacion_ofrecida=p.id_donacion_ofrecida JOIN donante don ON don.id_donante=l.id_donante WHERE p.id_organizacion=? GROUP BY don.id_donante ORDER BY valor DESC LIMIT 6""", (o,))}],
        "pendientes": pend, "alertas": alertas, "alertas_titulo": "Lotes disponibles que vencen pronto",
        "acciones": [{"t": "Ver lotes disponibles", "ir": "#/lotes"}, {"t": "Mis despachos", "ir": "#/logistica"}]}


def _dash_global(db, rol):
    one = lambda sql: db.val(sql, (), 0)
    k = [_kpi("package", "t-blue", one("SELECT COUNT(*) FROM donacion_ofrecida l JOIN estado_donacion_ofrecida s ON s.id_estado_donacion_ofrecida=l.id_estado_donacion_ofrecida WHERE s.estado='PUBLICADO'"), "Lotes publicados disponibles"),
         _kpi("scale", "t-green", round(one("SELECT SUM(peso_total_kg) FROM detalle_donacion_ofrecida"), 1), "Alimento ofrecido (kg)", "kg"),
         _kpi("coin", "t-amber", round(one("SELECT SUM(dd.cantidad*det.costo_unitario) FROM detalle_donacion_parcial dd JOIN detalle_donacion_ofrecida det ON det.id_detalle_donacion_ofrecida=dd.id_detalle_donacion_ofrecida"), 2), "Valor ya repartido", "money"),
         _kpi("truck", "t-green", round(one(KG_ENT.format(w="1=1")), 1), "Entregado a organizaciones (kg)", "kg"),
         _kpi("clock", "t-red" if one("SELECT COUNT(*) FROM v_lotes_disponibles WHERE horas_para_vencer <= 24") else "t-gray", one("SELECT COUNT(*) FROM v_lotes_disponibles WHERE horas_para_vencer <= 24"), "Líneas que vencen en 24 h"),
         _kpi("hand", "t-amber", one("SELECT COUNT(*) FROM donacion_parcial p JOIN estado_donacion e ON e.id_estado_donacion=p.id_estado_donacion WHERE e.estado='PENDIENTE'"), "Solicitudes pendientes"),
         _kpi("users", "t-blue", one("SELECT COUNT(*) FROM donante"), "Donantes registrados"), _kpi("building", "t-blue", one("SELECT COUNT(*) FROM organizacion"), "Organizaciones receptoras")]
    sol = {r["estado"]: r["n"] for r in db.all("SELECT e.estado, COUNT(*) n FROM donacion_parcial p JOIN estado_donacion e ON e.id_estado_donacion=p.id_estado_donacion GROUP BY e.estado")}
    lotes_total, desp, comps = one("SELECT COUNT(*) FROM donacion_ofrecida"), one("SELECT COUNT(*) FROM despacho"), one("SELECT COUNT(*) FROM comprobante")
    flujo = [["Lotes publicados", lotes_total, "Donantes ofrecen excedentes"], ["Solicitudes", sum(sol.values()), "Organizaciones piden"],
             ["Asignadas", sol.get("ASIGNADA", 0) + sol.get("ENTREGADA", 0), "Se reparte por línea"], ["Despachos", desp, "Vehículo + responsables"],
             ["Entregadas", sol.get("ENTREGADA", 0), "Arribo registrado"], ["Comprobantes", comps, "Constancia al donante"]]
    g = [{"titulo": "Valor publicado por donante", "sub": "S/", "tipo": "hbars", "fmt": "money", "datos": db.all("""SELECT don.nombre_donante AS etiqueta, ROUND(SUM(det.cantidad*det.costo_unitario),2) AS valor FROM donante don
            JOIN donacion_ofrecida l ON l.id_donante=don.id_donante JOIN detalle_donacion_ofrecida det ON det.id_donacion_ofrecida=l.id_donacion_ofrecida GROUP BY don.id_donante ORDER BY valor DESC LIMIT 6""")},
         {"titulo": "Solicitudes por estado", "tipo": "donut", "datos": db.all("""SELECT e.estado AS etiqueta, COUNT(p.id_donacion_parcial) AS valor FROM estado_donacion e
            LEFT JOIN donacion_parcial p ON p.id_estado_donacion=e.id_estado_donacion GROUP BY e.id_estado_donacion ORDER BY e.id_estado_donacion""")},
         {"titulo": "Valor repartido por organización", "sub": "S/", "tipo": "vbars", "fmt": "money0", "datos": db.all("""SELECT o.nombre_organizacion AS etiqueta, ROUND(IFNULL(SUM(dd.cantidad*det.costo_unitario),0),2) AS valor FROM organizacion o
            LEFT JOIN donacion_parcial p ON p.id_organizacion=o.id_organizacion LEFT JOIN detalle_donacion_parcial dd ON dd.id_donacion_parcial=p.id_donacion_parcial
            LEFT JOIN detalle_donacion_ofrecida det ON det.id_detalle_donacion_ofrecida=dd.id_detalle_donacion_ofrecida GROUP BY o.id_organizacion ORDER BY valor DESC""")},
         {"titulo": "Lotes por zona", "tipo": "hbars", "color": "#0e9f6e", "datos": db.all("""SELECT z.nombre_zona AS etiqueta, COUNT(l.id_donacion_ofrecida) AS valor FROM zona z
            LEFT JOIN donacion_ofrecida l ON l.id_zona=z.id_zona GROUP BY z.id_zona ORDER BY valor DESC""")}]
    out = {"rol": rol, "kpi": k, "graficos": g, "flujo": flujo, "alertas": B.sp_alerta_vencimientos(db, 24)[:6], "alertas_titulo": "Alertas de vencimiento (24 h)",
           "actividad": db.all("SELECT fecha, rol, accion, entidad, detalle, resultado FROM bitacora ORDER BY id_bitacora DESC LIMIT 8")}
    if rol == "admin":
        sin_rep = sol.get("PENDIENTE", 0)
        sin_desp = one("""SELECT COUNT(*) FROM donacion_parcial p JOIN estado_donacion e ON e.id_estado_donacion=p.id_estado_donacion
            WHERE e.estado='ASIGNADA' AND NOT EXISTS (SELECT 1 FROM despacho d WHERE d.id_donacion_parcial=p.id_donacion_parcial)""")
        sin_comp = one("""SELECT COUNT(*) FROM donacion_parcial p JOIN estado_donacion e ON e.id_estado_donacion=p.id_estado_donacion
            WHERE e.estado='ENTREGADA' AND NOT EXISTS (SELECT 1 FROM comprobante c WHERE c.id_donacion_parcial=p.id_donacion_parcial)""")
        out["pendientes"] = [x for x in [
            {"t": "solicitud(es) pendientes de reparto", "ir": "#/solicitudes", "n": sin_rep},
            {"t": "solicitud(es) asignadas aún sin despacho (lo programa la organización)", "ir": "#/logistica", "n": sin_desp},
            {"t": "entrega(s) sin comprobante emitido", "ir": "#/comprobantes", "n": sin_comp}] if x["n"]]
    return out


def esquema(db):
    tablas = [r["name"] for r in db.all("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT IN ('usuario','sesion') ORDER BY name")]
    out = []
    for t in tablas:
        cols = db.all(f"PRAGMA table_info({t})")
        fks = db.all(f"PRAGMA foreign_key_list({t})")
        out.append({"tabla": t, "filas": db.val(f"SELECT COUNT(*) FROM {t}", (), 0), "app": t == "bitacora",
                    "columnas": [{"nombre": c["name"], "tipo": c["type"], "pk": bool(c["pk"]), "obligatorio": bool(c["notnull"]), "defecto": c["dflt_value"]} for c in cols],
                    "fks": [{"columna": f["from"], "tabla": f["table"], "destino": f["to"]} for f in fks]})
    return out
