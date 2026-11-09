"""Laboratorio de reglas (archivo 09): cada prueba arma sus propios datos dentro de una
transaccion, ejecuta la operacion y hace ROLLBACK; no deja rastro en la base."""
import sqlite3
import business as B
from errors import AppError, translate_db_error


def _fx(db, frio_org=1, peso=10, cant=10, frio_alimento=0, cap=100, dueno=True):
    """Fixture: donante, organizacion, lote con una linea, solicitud y vehiculo."""
    z = db.val("SELECT MIN(id_zona) FROM zona")
    sd = db.val("SELECT MIN(id_estado_donante) FROM estado_donante")
    so = db.val("SELECT id_estado_organizacion FROM estado_organizacion WHERE estado='HABILITADA'")
    to = db.val("SELECT MIN(id_tipo_organizacion) FROM tipo_organizacion")
    um = db.val("SELECT MIN(id_unidad_medida) FROM unidad_medida")
    cat = db.val("SELECT MIN(id_categoria_alimento) FROM categoria_alimento")
    don = db.insert("INSERT INTO donante (nombre_donante,id_zona,id_estado_donante) VALUES ('__TEST donante',?,?)", (z, sd))
    org = db.insert("INSERT INTO organizacion (nombre_organizacion,id_zona,id_estado_organizacion,id_tipo_organizacion,tiene_refrigeracion) VALUES ('__TEST org',?,?,?,?)", (z, so, to, frio_org))
    ali = db.insert("INSERT INTO alimento (nombre_alimento,id_categoria_alimento,requiere_refrigeracion) VALUES ('__TEST alimento',?,?)", (cat, frio_alimento))
    lote = B.publicar_lote(db, don, "Dir test", z, [dict(id_alimento=ali, fecha_vencimiento="2099-01-01 10:00:00", cantidad=cant, id_unidad_medida=um, peso_total_kg=peso, costo_unitario=2)])
    linea = db.val("SELECT id_detalle_donacion_ofrecida FROM detalle_donacion_ofrecida WHERE id_donacion_ofrecida=?", (lote,))
    sol = db.insert("INSERT INTO donacion_parcial (id_donacion_ofrecida,id_organizacion,id_estado_donacion) VALUES (?,?,1)", (lote, org))
    veh = db.insert("INSERT INTO vehiculo (placa,modelo,capacidad_kg,id_organizacion) VALUES ('TST-001','Test',?,?)", (cap, org if dueno else None))
    return dict(don=don, org=org, ali=ali, lote=lote, linea=linea, sol=sol, veh=veh, z=z, um=um)


def _asignada(db, f, cantidad):
    B.sp_asignar_linea(db, f["sol"], f["linea"], cantidad)
    db.run("UPDATE donacion_parcial SET id_estado_donacion=2 WHERE id_donacion_parcial=?", (f["sol"],))


def t01(db):
    db.insert("INSERT INTO donacion_parcial (id_donacion_ofrecida,id_organizacion,id_estado_donacion) VALUES (999999,1,1)")
def t02(db): _fx(db); db.insert("INSERT INTO vehiculo (placa,capacidad_kg) VALUES ('TST-001',50)")
def t03(db): _fx(db); db.run("UPDATE donante SET ruc='123' WHERE nombre_donante='__TEST donante'")
def t04(db): db.insert("INSERT INTO vehiculo (placa,capacidad_kg) VALUES ('TST-CAP',0)")
def t05(db):
    f = _fx(db); db.insert("INSERT INTO detalle_donacion_parcial (id_donacion_parcial,id_detalle_donacion_ofrecida,cantidad) VALUES (?,?,0)", (f["sol"], f["linea"]))
def t06(db): f = _fx(db, cant=10); B.sp_asignar_linea(db, f["sol"], f["linea"], 31)
def t07(db): f = _fx(db, frio_org=0, frio_alimento=1); B.sp_asignar_linea(db, f["sol"], f["linea"], 1)
def t08(db):
    f = _fx(db); otro = db.insert("INSERT INTO donacion_ofrecida (id_donante,id_estado_donacion_ofrecida,id_zona) VALUES (?,1,?)", (f["don"], f["z"]))
    sol2 = db.insert("INSERT INTO donacion_parcial (id_donacion_ofrecida,id_organizacion,id_estado_donacion) VALUES (?,?,1)", (otro, f["org"]))
    B.sp_asignar_linea(db, sol2, f["linea"], 1)
def t09(db): f = _fx(db); B.sp_asignar_linea(db, f["sol"], f["linea"], 2); B.sp_asignar_linea(db, f["sol"], f["linea"], 2)
def t10(db): f = _fx(db, peso=50, cant=50, cap=10); _asignada(db, f, 50); B.sp_programar_despacho(db, f["sol"], f["veh"])
def t11(db):
    f = _fx(db); _asignada(db, f, 1)
    otra = db.val("SELECT MIN(id_organizacion) FROM organizacion WHERE nombre_organizacion<>'__TEST org'")
    db.run("UPDATE vehiculo SET id_organizacion=? WHERE id_vehiculo=?", (otra, f["veh"]))
    B.sp_programar_despacho(db, f["sol"], f["veh"])
def t12(db): f = _fx(db); B.sp_asignar_linea(db, f["sol"], f["linea"], 1); B.sp_programar_despacho(db, f["sol"], f["veh"])
def t13(db): f = _fx(db); _asignada(db, f, 1); B.sp_emitir_comprobante(db, f["sol"])
def t14(db):
    f = _fx(db); _asignada(db, f, 1); db.run("UPDATE donacion_parcial SET id_estado_donacion=3 WHERE id_donacion_parcial=?", (f["sol"],))
    B.sp_emitir_comprobante(db, f["sol"]); B.sp_emitir_comprobante(db, f["sol"])
def t15(db):
    f = _fx(db)
    try: db.run("DELETE FROM donante WHERE id_donante=?", (f["don"],))
    except sqlite3.IntegrityError as e: raise translate_db_error(e, "delete")
def t16(db):
    f = _fx(db); _asignada(db, f, 1); did, _ = B.sp_programar_despacho(db, f["sol"], f["veh"])
    db.run("UPDATE despacho SET fecha_salida='2026-01-02 10:00:00', fecha_arribo='2026-01-02 09:00:00' WHERE id_despacho=?", (did,))
def t17(db):
    f = _fx(db, cant=30)
    so = db.val("SELECT id_estado_organizacion FROM estado_organizacion WHERE estado='HABILITADA'")
    o2 = db.insert("INSERT INTO organizacion (nombre_organizacion,id_zona,id_estado_organizacion,id_tipo_organizacion,tiene_refrigeracion) VALUES ('__TEST org2',?,?,1,1)", (f["z"], so))
    db.insert("INSERT INTO donacion_parcial (id_donacion_ofrecida,id_organizacion,id_estado_donacion) VALUES (?,?,1)", (f["lote"], o2))
    log = B.sp_repartir_equitativo(db, f["lote"])
    return "Reparto equitativo OK: " + "; ".join(log)

TESTS = [
 ("P1",  "FK restituida (fk_parcial_ofrecida)", "Insertar una solicitud para un lote inexistente (999999)", "ORA-02291", t01),
 ("P2",  "Placa única", "Insertar un vehículo con una placa ya registrada", "ORA-00001", t02),
 ("P3",  "RUC de 11 dígitos", "Cambiar el RUC de un donante a '123'", "ORA-02290", t03),
 ("P4",  "Capacidad positiva", "Registrar un vehículo con capacidad 0 kg", "ORA-02290", t04),
 ("P5",  "Cantidad > 0 en el reparto", "Insertar un reparto de cantidad 0", "ORA-02290", t05),
 ("P6",  "Saldo insuficiente", "Pedir 31 de una línea que solo tiene 10", "ORA-20001", t06),
 ("P7",  "Cadena de frío", "Asignar un alimento refrigerado a una organización sin refrigeración", "ORA-20002", t07),
 ("P8",  "Línea de otro lote", "Asignar una línea que pertenece a un lote distinto al de la solicitud", "ORA-20003", t08),
 ("P9",  "Línea duplicada", "Asignar dos veces la misma línea a la misma solicitud", "ORA-20005", t09),
 ("P10", "Capacidad del vehículo", "Programar 50 kg en un vehículo de 10 kg", "ORA-20008", t10),
 ("P11", "Vehículo de otra organización", "Programar el despacho con un vehículo que pertenece a otra organización", "ORA-20009", t11),
 ("P12", "Despacho solo si ASIGNADA", "Programar despacho de una solicitud PENDIENTE", "ORA-20010", t12),
 ("P13", "Comprobante solo si ENTREGADA", "Emitir comprobante de una solicitud que no fue entregada", "ORA-20006", t13),
 ("P14", "Comprobante único", "Emitir dos veces el comprobante de la misma donación", "ORA-20007", t14),
 ("P15", "No borrar un padre con hijos", "Eliminar un donante que ya publicó lotes", "ORA-02292", t15),
 ("P16", "Orden cronológico del despacho", "Registrar arribo anterior a la salida", "ORA-02290", t16),
 ("P17", "Reparto equitativo (caso feliz)", "Repartir 30 unidades entre dos solicitudes pendientes", "OK", t17),
]


def catalogo():
    return [dict(id=i, regla=r, accion=a, esperado=e) for i, r, a, e, _ in TESTS]


def ejecutar(db, tid):
    for i, regla, accion, esperado, fn in TESTS:
        if i != tid: continue
        db.run("SAVEPOINT prueba")
        obtenido, mensaje = "OK", ""
        try:
            r = fn(db)
            mensaje = r or "La operación se completó sin error"
        except AppError as e:
            obtenido, mensaje = e.code.split("/")[0], e.message
        except sqlite3.Error as e:
            ae = translate_db_error(e); obtenido, mensaje = ae.code.split("/")[0], ae.message
        finally:
            db.run("ROLLBACK TO prueba"); db.run("RELEASE prueba")
        ok = obtenido == esperado
        return dict(id=i, regla=regla, accion=accion, esperado=esperado, obtenido=obtenido, mensaje=mensaje, aprobada=ok)
    raise AppError("ORA-00942", "Prueba inexistente", 404)
