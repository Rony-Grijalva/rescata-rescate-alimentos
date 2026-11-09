"""Capa de negocio: equivalentes en Python de las funciones y procedimientos PL/SQL
(archivos 06 y 07). Cada regla lanza AppError con el mismo codigo ORA-200xx."""
from errors import AppError

# ---------------------------------------------------------------- funciones
def fn_saldo_linea(db, linea):                      # F1
    v = db.val("SELECT saldo FROM v_saldo_linea WHERE id_detalle_donacion_ofrecida=?", (linea,))
    if v is None: raise AppError("ORA-01403", f"La linea {linea} no existe", 404)
    return v

def fn_valor_donacion(db, donacion):                # F2
    return db.val("""SELECT IFNULL(SUM(dd.cantidad*det.costo_unitario),0) FROM detalle_donacion_parcial dd
                     JOIN detalle_donacion_ofrecida det ON det.id_detalle_donacion_ofrecida=dd.id_detalle_donacion_ofrecida
                     WHERE dd.id_donacion_parcial=?""", (donacion,), 0)

def fn_compatible_frio(db, linea, org):             # F3
    r = db.one("""SELECT a.requiere_refrigeracion rq FROM detalle_donacion_ofrecida det
                  JOIN alimento a ON a.id_alimento=det.id_alimento WHERE det.id_detalle_donacion_ofrecida=?""", (linea,))
    o = db.one("SELECT tiene_refrigeracion tf FROM organizacion WHERE id_organizacion=?", (org,))
    if not r or not o: raise AppError("ORA-01403", "Linea u organizacion inexistente", 404)
    return not (r["rq"] == 1 and o["tf"] == 0)

def fn_peso_donacion_kg(db, donacion):              # F4
    v = db.val("""SELECT IFNULL(SUM(dd.cantidad/det.cantidad*IFNULL(det.peso_total_kg,0)),0)
                  FROM detalle_donacion_parcial dd JOIN detalle_donacion_ofrecida det
                    ON det.id_detalle_donacion_ofrecida=dd.id_detalle_donacion_ofrecida
                  WHERE dd.id_donacion_parcial=?""", (donacion,), 0)
    return round(v, 2)

def fn_urgencia(horas):                             # U1 (VARRAY 6/12/24)
    um = (6, 12, 24)
    if horas <= um[0]: return "CRITICA"
    if horas <= um[1]: return "ALTA"
    if horas <= um[2]: return "MEDIA"
    return "NORMAL"

def _estado_id(db, tabla, col, estado):
    v = db.val(f"SELECT {col} FROM {tabla} WHERE estado=?", (estado,))
    if v is None: raise AppError("ORA-01403", f"Estado {estado} no existe", 500)
    return v

# --------------------------------------------------------------- procedimientos
def sp_asignar_linea(db, donacion, linea, cantidad):   # P1
    try: cantidad = float(cantidad)
    except (TypeError, ValueError): raise AppError("ORA-06502", "La cantidad debe ser numerica", 422, {"cantidad": "Numero invalido"})
    if cantidad <= 0: raise AppError("ORA-02290", "La cantidad debe ser mayor que cero (ck_det_parcial_cant)", 422, {"cantidad": "Debe ser > 0"})
    d = db.one("SELECT id_organizacion, id_donacion_ofrecida lote FROM donacion_parcial WHERE id_donacion_parcial=?", (donacion,))
    l = db.one("SELECT id_donacion_ofrecida lote FROM detalle_donacion_ofrecida WHERE id_detalle_donacion_ofrecida=?", (linea,))
    if not d or not l: raise AppError("ORA-20004", f"La donacion {donacion} o la linea {linea} no existe", 404)
    if d["lote"] != l["lote"]:
        raise AppError("ORA-20003", f"La linea {linea} no pertenece al lote de la donacion {donacion}", 409)
    if not fn_compatible_frio(db, linea, d["id_organizacion"]):
        raise AppError("ORA-20002", "La linea requiere refrigeracion y la organizacion no la tiene", 409)
    if db.val("SELECT 1 FROM detalle_donacion_parcial WHERE id_donacion_parcial=? AND id_detalle_donacion_ofrecida=?", (donacion, linea)):
        raise AppError("ORA-20005", f"La linea {linea} ya fue asignada a la donacion {donacion}", 409)
    saldo = fn_saldo_linea(db, linea)
    if cantidad > saldo:
        raise AppError("ORA-20001", f"Saldo insuficiente: se piden {cantidad:g} y quedan {saldo:g}", 409)
    db.insert("INSERT INTO detalle_donacion_parcial (id_donacion_parcial,id_detalle_donacion_ofrecida,cantidad) VALUES (?,?,?)",
              (donacion, linea, cantidad))
    refrescar_estado_lote(db, d["lote"])
    return f"Asignado: {cantidad:g} de la linea {linea} a la donacion {donacion}"

def refrescar_estado_lote(db, lote):
    """Lote PUBLICADO -> ASIGNADO cuando no queda saldo; vuelve a PUBLICADO si se libera saldo."""
    saldo = db.val("SELECT IFNULL(SUM(saldo),0) FROM v_saldo_linea WHERE id_donacion_ofrecida=?", (lote,), 0)
    actual = db.val("""SELECT s.estado FROM donacion_ofrecida l JOIN estado_donacion_ofrecida s
                       ON s.id_estado_donacion_ofrecida=l.id_estado_donacion_ofrecida WHERE l.id_donacion_ofrecida=?""", (lote,))
    if actual == "CERRADO": return
    nuevo = "ASIGNADO" if saldo <= 0 else "PUBLICADO"
    if nuevo != actual:
        db.run("UPDATE donacion_ofrecida SET id_estado_donacion_ofrecida=? WHERE id_donacion_ofrecida=?",
               (_estado_id(db, "estado_donacion_ofrecida", "id_estado_donacion_ofrecida", nuevo), lote))

def sp_programar_despacho(db, donacion, vehiculo_id, fecha=None):   # P2
    r = db.one("""SELECT e.estado, d.id_organizacion org FROM donacion_parcial d
                  JOIN estado_donacion e ON e.id_estado_donacion=d.id_estado_donacion WHERE d.id_donacion_parcial=?""", (donacion,))
    v = db.one("SELECT id_vehiculo, placa, capacidad_kg cap, id_organizacion org FROM vehiculo WHERE id_vehiculo=?", (vehiculo_id,))
    if not r or not v: raise AppError("ORA-20004", f"La donacion {donacion} o el vehiculo no existe", 404)
    if r["estado"] != "ASIGNADA":
        raise AppError("ORA-20010", f"Solo se programa despacho de una donacion ASIGNADA (estado actual: {r['estado']})", 409)
    if v["org"] is not None and v["org"] != r["org"]:
        raise AppError("ORA-20009", f"El vehiculo {v['placa']} pertenece a otra organizacion", 409)
    peso = fn_peso_donacion_kg(db, donacion)
    if peso > v["cap"]:
        raise AppError("ORA-20008", f"Capacidad insuficiente: la carga pesa {peso:g} kg y el vehiculo admite {v['cap']:g} kg", 409)
    if db.val("SELECT 1 FROM despacho WHERE id_donacion_parcial=? AND fecha_arribo IS NULL", (donacion,)):
        raise AppError("ORA-20011", "La donacion ya tiene un despacho en curso", 409)
    fecha = fecha or db.val("SELECT datetime('now','localtime','+2 hours')")
    did = db.insert("INSERT INTO despacho (id_donacion_parcial,id_vehiculo,fecha_programada) VALUES (?,?,?)", (donacion, vehiculo_id, fecha))
    return did, f"Despacho programado: donacion {donacion}, vehiculo {v['placa']}, carga {peso:g} kg de {v['cap']:g} kg"

def sp_registrar_hito(db, despacho, hito):  # llegada -> salida -> arribo (CHECK de fechas del modelo)
    campos = {"llegada": "fecha_llegada", "salida": "fecha_salida", "arribo": "fecha_arribo"}
    if hito not in campos: raise AppError("ORA-06502", "Hito invalido", 422)
    d = db.one("SELECT * FROM despacho WHERE id_despacho=?", (despacho,))
    if not d: raise AppError("ORA-20004", "El despacho no existe", 404)
    orden = ["llegada", "salida", "arribo"]
    previo = orden[orden.index(hito) - 1] if hito != "llegada" else None
    if previo and not d[campos[previo]]:
        raise AppError("ORA-20012", f"Primero debe registrarse la {previo} del vehiculo", 409)
    if d[campos[hito]]:
        raise AppError("ORA-20012", f"La {hito} ya fue registrada", 409)
    db.run(f"UPDATE despacho SET {campos[hito]}=datetime('now','localtime') WHERE id_despacho=?", (despacho,))
    msg = f"{hito.capitalize()} registrada"
    if hito == "arribo":                                    # el arribo cierra la entrega
        db.run("UPDATE donacion_parcial SET id_estado_donacion=? WHERE id_donacion_parcial=?",
               (_estado_id(db, "estado_donacion", "id_estado_donacion", "ENTREGADA"), d["id_donacion_parcial"]))
        msg += ": la donacion pasa a ENTREGADA"
    return msg

def sp_alerta_vencimientos(db, horas=24):           # P3
    rows = db.all("SELECT * FROM v_lotes_disponibles WHERE horas_para_vencer <= ? ORDER BY horas_para_vencer", (horas,))
    for r in rows: r["urgencia"] = fn_urgencia(r["horas_para_vencer"])
    return rows

def sp_resumen_organizacion(db, org):               # P4
    rows = db.all("""SELECT d.id_donacion_parcial, a.nombre_alimento, dd.cantidad, dd.cantidad*det.costo_unitario valor
        FROM donacion_parcial d JOIN detalle_donacion_parcial dd ON dd.id_donacion_parcial=d.id_donacion_parcial
        JOIN detalle_donacion_ofrecida det ON det.id_detalle_donacion_ofrecida=dd.id_detalle_donacion_ofrecida
        JOIN alimento a ON a.id_alimento=det.id_alimento WHERE d.id_organizacion=? ORDER BY 1,2""", (org,))
    return {"filas": rows, "total": round(sum(r["valor"] for r in rows), 2)}

def sp_sugerir_receptoras(db, lote):                # U2 (RECORD + BULK COLLECT)
    if not db.val("SELECT 1 FROM donacion_ofrecida WHERE id_donacion_ofrecida=?", (lote,)):
        raise AppError("ORA-20004", f"El lote {lote} no existe", 404)
    cand = db.all("""SELECT o.id_organizacion, o.nombre_organizacion nombre, t.tipo, o.tiene_refrigeracion,
        CASE WHEN o.id_zona=l.id_zona THEN 1 WHEN zo.id_distrito=zl.id_distrito THEN 2 ELSE 3 END nivel,
        CASE WHEN o.tiene_refrigeracion=0 AND EXISTS (SELECT 1 FROM detalle_donacion_ofrecida det
               JOIN alimento a ON a.id_alimento=det.id_alimento WHERE det.id_donacion_ofrecida=l.id_donacion_ofrecida
               AND a.requiere_refrigeracion=1) THEN 'N' ELSE 'S' END apta_frio,
        zo.nombre_zona
      FROM organizacion o JOIN estado_organizacion e ON e.id_estado_organizacion=o.id_estado_organizacion
      JOIN tipo_organizacion t ON t.id_tipo_organizacion=o.id_tipo_organizacion
      JOIN zona zo ON zo.id_zona=o.id_zona JOIN donacion_ofrecida l ON l.id_donacion_ofrecida=?
      JOIN zona zl ON zl.id_zona=l.id_zona
      WHERE e.estado='HABILITADA' ORDER BY 5, 2""", (lote,))
    etiqueta = {1: "misma zona", 2: "mismo distrito", 3: "otro distrito"}
    pos = 0
    for c in cand:
        c["cercania"] = etiqueta[c["nivel"]]
        if c["apta_frio"] == "S":
            pos += 1; c["posicion"] = pos
        else: c["posicion"] = None
    return cand

def sp_repartir_equitativo(db, lote):               # U3 (INDEX BY + WHILE)
    log = []
    saldos = {r["id_detalle_donacion_ofrecida"]: r["saldo"] for r in
              db.all("SELECT id_detalle_donacion_ofrecida, saldo FROM v_saldo_linea WHERE id_donacion_ofrecida=? AND saldo>0 ORDER BY 1", (lote,))}
    pend = db.all("""SELECT d.id_donacion_parcial id, d.id_organizacion org, o.nombre_organizacion nombre FROM donacion_parcial d
        JOIN estado_donacion e ON e.id_estado_donacion=d.id_estado_donacion
        JOIN organizacion o ON o.id_organizacion=d.id_organizacion
        WHERE d.id_donacion_ofrecida=? AND e.estado='PENDIENTE' ORDER BY d.fecha_solicitud, d.id_donacion_parcial""", (lote,))
    if not saldos or not pend:
        return ["Nada que repartir en el lote %s" % lote]
    for linea, saldo in saldos.items():
        nom = db.val("SELECT a.nombre_alimento FROM detalle_donacion_ofrecida det JOIN alimento a ON a.id_alimento=det.id_alimento WHERE det.id_detalle_donacion_ofrecida=?", (linea,))
        aptas = [p for p in pend if fn_compatible_frio(db, linea, p["org"])]
        if not aptas:
            log.append(f"Linea {linea} ({nom}): sin receptora compatible (requiere frio)"); continue
        parte = int(saldo / len(aptas) * 100) / 100             # TRUNC(x, 2)
        if parte <= 0: continue
        for p in aptas:
            try:
                with db.savepoint("rep"):
                    sp_asignar_linea(db, p["id"], linea, parte)
                log.append(f"{nom}: {parte:g} para {p['nombre']}")
            except AppError as e:
                log.append(f"Omitida linea {linea} / donacion {p['id']}: {e.code} {e.message}")
    asig = _estado_id(db, "estado_donacion", "id_estado_donacion", "ASIGNADA")
    pend_id = _estado_id(db, "estado_donacion", "id_estado_donacion", "PENDIENTE")
    db.run("""UPDATE donacion_parcial SET id_estado_donacion=? WHERE id_donacion_ofrecida=? AND id_estado_donacion=?
              AND EXISTS (SELECT 1 FROM detalle_donacion_parcial x WHERE x.id_donacion_parcial=donacion_parcial.id_donacion_parcial)""",
           (asig, lote, pend_id))
    refrescar_estado_lote(db, lote)
    return log

def sp_emitir_comprobante(db, donacion):            # U4
    r = db.one("""SELECT e.estado FROM donacion_parcial d JOIN estado_donacion e ON e.id_estado_donacion=d.id_estado_donacion
                  WHERE d.id_donacion_parcial=?""", (donacion,))
    if not r: raise AppError("ORA-20004", f"La donacion {donacion} no existe", 404)
    if r["estado"] != "ENTREGADA":
        raise AppError("ORA-20006", f"Solo se emite comprobante de una donacion ENTREGADA (estado actual: {r['estado']})", 409)
    if db.val("SELECT 1 FROM comprobante WHERE id_donacion_parcial=?", (donacion,)):
        raise AppError("ORA-20007", f"La donacion {donacion} ya tiene comprobante", 409)
    monto = fn_valor_donacion(db, donacion)
    num = db.val("SELECT IFNULL(MAX(numero),0)+1 FROM comprobante WHERE serie='F001'", (), 1)
    db.insert("INSERT INTO comprobante (id_donacion_parcial,serie,numero,monto_total) VALUES (?,?,?,?)", (donacion, "F001", num, monto))
    cerrar_lote_si_corresponde(db, donacion)
    return f"Comprobante F001-{num:08d} por S/ {monto:.2f}"

def cerrar_lote_si_corresponde(db, donacion):
    lote = db.val("SELECT id_donacion_ofrecida FROM donacion_parcial WHERE id_donacion_parcial=?", (donacion,))
    abiertas = db.val("""SELECT COUNT(*) FROM donacion_parcial d JOIN estado_donacion e ON e.id_estado_donacion=d.id_estado_donacion
                         WHERE d.id_donacion_ofrecida=? AND e.estado<>'ENTREGADA'""", (lote,), 0)
    saldo = db.val("SELECT IFNULL(SUM(saldo),0) FROM v_saldo_linea WHERE id_donacion_ofrecida=?", (lote,), 0)
    if abiertas == 0 and saldo <= 0:
        db.run("UPDATE donacion_ofrecida SET id_estado_donacion_ofrecida=? WHERE id_donacion_ofrecida=?",
               (_estado_id(db, "estado_donacion_ofrecida", "id_estado_donacion_ofrecida", "CERRADO"), lote))

def sincronizar_estado_solicitud(db, donacion):
    """El estado de la solicitud se DERIVA del reparto (nadie lo cambia a mano):
    con al menos una linea repartida -> ASIGNADA; sin lineas y sin despacho -> PENDIENTE; ENTREGADA solo lo fija el arribo."""
    est = db.val("""SELECT e.estado FROM donacion_parcial d JOIN estado_donacion e ON e.id_estado_donacion=d.id_estado_donacion
                    WHERE d.id_donacion_parcial=?""", (donacion,))
    if est is None or est == "ENTREGADA": return est
    lineas = db.val("SELECT COUNT(*) FROM detalle_donacion_parcial WHERE id_donacion_parcial=?", (donacion,), 0)
    nuevo = "ASIGNADA" if lineas else "PENDIENTE"
    if nuevo != est:
        db.run("UPDATE donacion_parcial SET id_estado_donacion=? WHERE id_donacion_parcial=?",
               (_estado_id(db, "estado_donacion", "id_estado_donacion", nuevo), donacion))
    return nuevo

def publicar_lote(db, donante, direccion, zona, lineas):
    """Crea un lote con sus lineas en la misma transaccion (todo o nada)."""
    lote = db.insert("INSERT INTO donacion_ofrecida (id_donante,id_estado_donacion_ofrecida,direccion,id_zona) VALUES (?,?,?,?)",
                     (donante, _estado_id(db, "estado_donacion_ofrecida", "id_estado_donacion_ofrecida", "PUBLICADO"), direccion, zona))
    for l in lineas:
        db.insert("""INSERT INTO detalle_donacion_ofrecida (id_donacion_ofrecida,id_alimento,marca,codigo_lote,fecha_vencimiento,
                     cantidad,id_unidad_medida,peso_total_kg,costo_unitario) VALUES (?,?,?,?,?,?,?,?,?)""",
                  (lote, l["id_alimento"], l.get("marca"), l.get("codigo_lote"), l["fecha_vencimiento"], l["cantidad"],
                   l["id_unidad_medida"], l.get("peso_total_kg"), l["costo_unitario"]))
    return lote
