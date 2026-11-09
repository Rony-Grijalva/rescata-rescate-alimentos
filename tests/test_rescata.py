"""Pruebas automaticas del backend (sin servidor): python -m unittest discover -s tests -v"""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))
os.environ["RESCATA_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
import database as D, server as S, reglas as T, queries as Q   # noqa: E402


def call(method, path, body=None, rol="admin", q=None, actor=None):
    return S.dispatch(method, path, q or {}, body or {}, rol, actor)


class Rescata(unittest.TestCase):
    @classmethod
    def setUpClass(cls): D.init_db(force=True)

    def test_01_esquema_tiene_22_tablas_mas_bitacora(self):
        r = call("GET", "/api/esquema")["data"]
        self.assertEqual(len(r), 23)
        self.assertIn("vehiculo", [t["tabla"] for t in r])

    def test_02_crud_donante_completo(self):
        r = call("POST", "/api/crud/donantes", {"nombre_donante": "T", "ruc": "20999999991", "id_zona": 1, "id_estado_donante": 1})
        self.assertTrue(r["ok"]); i = r["data"]["id"]
        self.assertEqual(call("GET", f"/api/crud/donantes/{i}")["data"]["nombre_donante"], "T")
        self.assertTrue(call("PUT", f"/api/crud/donantes/{i}", {"nombre_donante": "T2"})["ok"])
        self.assertEqual(call("GET", f"/api/crud/donantes/{i}")["data"]["nombre_donante"], "T2")
        self.assertTrue(call("DELETE", f"/api/crud/donantes/{i}")["ok"])
        self.assertEqual(call("GET", f"/api/crud/donantes/{i}")["error"]["code"], "ORA-01403")

    def test_03_validaciones(self):
        r = call("POST", "/api/crud/donantes", {"nombre_donante": "T", "ruc": "12", "id_zona": 1, "id_estado_donante": 1})
        self.assertEqual(r["error"]["code"], "VALIDACION"); self.assertIn("ruc", r["error"]["fields"])

    def test_04_privilegios(self):
        r = call("DELETE", "/api/crud/vehiculos/1", rol="auditor")
        self.assertEqual(r["error"]["code"], "ORA-01031")

    def test_05_las_17_pruebas_de_reglas_se_comportan_como_se_espera(self):
        for t in T.catalogo():
            r = call("POST", f"/api/pruebas/{t['id']}/ejecutar")["data"]
            self.assertTrue(r["aprobada"], f"{t['id']} {r}")

    def test_06_pruebas_no_dejan_rastro(self):
        antes = call("POST", "/api/sql", {"sql": "SELECT COUNT(*) FROM donante"})["data"]["filas"]
        call("POST", "/api/pruebas/P17/ejecutar")
        self.assertEqual(antes, call("POST", "/api/sql", {"sql": "SELECT COUNT(*) FROM donante"})["data"]["filas"])

    def test_07_resultados_de_los_joins(self):
        esperado = {"J1": 2, "J2": 3, "J3": 4, "J4": 4, "J5": 1, "J6": 4, "J7": 5, "J8": 4, "J9": 3, "J10": 4}
        for qid, n in esperado.items():
            self.assertEqual(call("POST", f"/api/consultas/{qid}/ejecutar")["data"]["total"], n, qid)

    def test_08_flujo_completo_publicar_a_comprobante(self):
        lote = call("POST", "/api/lotes", {"id_donante": 4, "id_zona": 5, "lineas": [{"id_alimento": 3, "cantidad": 10, "id_unidad_medida": 2, "peso_total_kg": 10, "costo_unitario": 4, "fecha_vencimiento": "2099-01-01"}]})["data"]["id"]
        sol = call("POST", "/api/solicitudes", {"id_donacion_ofrecida": lote}, rol="organizacion", actor=2)["data"]["id"]
        linea = call("GET", f"/api/solicitudes/{sol}")["data"]["lineas_lote"][0]["id"]
        self.assertEqual(call("POST", f"/api/solicitudes/{sol}/asignar", {"linea": linea, "cantidad": 99})["error"]["code"], "ORA-20001")
        self.assertTrue(call("POST", f"/api/solicitudes/{sol}/asignar", {"linea": linea, "cantidad": 10})["ok"])
        self.assertEqual(call("GET", f"/api/lotes/{lote}")["data"]["estado"], "ASIGNADO")      # sin saldo -> ASIGNADO
        self.assertEqual(call("GET", f"/api/solicitudes/{sol}")["data"]["estado"], "ASIGNADA")       # estado derivado del reparto
        self.assertEqual(call("POST", f"/api/solicitudes/{sol}/comprobante")["error"]["code"], "ORA-20006")
        d = call("POST", "/api/despachos", {"id_donacion_parcial": sol, "id_vehiculo": 3}, rol="organizacion", actor=2)["data"]["id"]
        for h in ("llegada", "salida", "arribo"): self.assertTrue(call("POST", f"/api/despachos/{d}/hito", {"hito": h}, rol="organizacion", actor=2)["ok"])
        self.assertEqual(call("GET", f"/api/solicitudes/{sol}")["data"]["estado"], "ENTREGADA")
        self.assertIn("F001", call("POST", f"/api/solicitudes/{sol}/comprobante")["mensaje"])
        self.assertEqual(call("POST", f"/api/solicitudes/{sol}/comprobante")["error"]["code"], "ORA-20007")
        self.assertEqual(call("GET", f"/api/lotes/{lote}")["data"]["estado"], "CERRADO")

    def test_09_consola_sql_solo_lectura(self):
        self.assertEqual(call("POST", "/api/sql", {"sql": "DELETE FROM donante"})["error"]["code"], "ORA-01031")
        self.assertEqual(call("POST", "/api/sql", {"sql": "SELECT 1; DROP TABLE donante"})["error"]["code"], "ORA-00911")

    def test_10_reinicio_restaura_datos(self):
        call("POST", "/api/sistema/reiniciar")
        self.assertEqual(call("POST", "/api/sql", {"sql": "SELECT COUNT(*) FROM comprobante"})["data"]["filas"][0][0], 0)


if __name__ == "__main__":
    unittest.main()
