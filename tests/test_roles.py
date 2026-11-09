"""Pruebas por rol: cada cuenta ve y toca solo lo suyo, en el servidor (no solo en la interfaz)."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))
os.environ["RESCATA_DB"] = os.path.join(tempfile.mkdtemp(), "roles.db")
import database as D, server as S   # noqa: E402


def call(method, path, body=None, rol="admin", actor=None, q=None):
    return S.dispatch(method, path, q or {}, body or {}, rol, actor)


def code(r): return (r.get("error") or {}).get("code")


class Roles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        D.init_db(force=True)
        cls.lotes = call("GET", "/api/lotes")["data"]
        cls.don_a = cls.lotes[0]["id_donante"]
        cls.don_b = next(l["id_donante"] for l in cls.lotes if l["id_donante"] != cls.don_a)
        cls.sols = call("GET", "/api/solicitudes")["data"]
        cls.org_a = cls.sols[0]["id_organizacion"]
        cls.org_b = next(s["id_organizacion"] for s in cls.sols if s["id_organizacion"] != cls.org_a)

    # --- identidad
    def test_01_donante_y_organizacion_exigen_cuenta(self):
        self.assertEqual(code(call("GET", "/api/lotes", rol="donante")), "SESION")
        self.assertEqual(code(call("GET", "/api/lotes", rol="organizacion", actor=99999)), "SESION")


    # --- donante
    def test_02_donante_solo_ve_sus_lotes(self):
        r = call("GET", "/api/lotes", rol="donante", actor=self.don_a)["data"]
        self.assertTrue(r and all(l["id_donante"] == self.don_a for l in r))

    def test_03_donante_no_toca_lotes_ajenos(self):
        ajeno = next(l["id_donacion_ofrecida"] for l in self.lotes if l["id_donante"] == self.don_b)
        self.assertEqual(code(call("GET", f"/api/lotes/{ajeno}", rol="donante", actor=self.don_a)), "ORA-01031")
        self.assertEqual(code(call("DELETE", f"/api/lotes/{ajeno}", rol="donante", actor=self.don_a)), "ORA-01031")
        self.assertEqual(code(call("POST", f"/api/lotes/{ajeno}/lineas", {}, rol="donante", actor=self.don_a)), "ORA-01031")

    def test_04_donante_publica_a_su_nombre_aunque_envie_otro_id(self):
        linea = {"id_alimento": 3, "cantidad": 5, "id_unidad_medida": 2, "peso_total_kg": 5, "costo_unitario": 2, "fecha_vencimiento": "2099-01-01"}
        r = call("POST", "/api/lotes", {"id_donante": self.don_b, "lineas": [linea]}, rol="donante", actor=self.don_a)
        self.assertTrue(r["ok"], r)
        self.assertEqual(call("GET", f"/api/lotes/{r['data']['id']}")["data"]["id_donante"], self.don_a)

    def test_05_donante_sin_acceso_a_modulos_ajenos(self):
        for m, p in [("GET", "/api/solicitudes"), ("GET", "/api/despachos"), ("GET", "/api/crud/donantes"), ("GET", "/api/bitacora"),
                     ("POST", "/api/solicitudes/1/asignar"), ("POST", "/api/lotes/1/repartir"), ("POST", "/api/sistema/reiniciar"), ("POST", "/api/sql")]:
            self.assertEqual(code(call(m, p, rol="donante", actor=self.don_a)), "ORA-01031", p)

    def test_06_donante_solo_ve_sus_comprobantes(self):
        call("GET", "/api/comprobantes", rol="donante", actor=self.don_a)
        r = call("GET", "/api/comprobantes", rol="admin")["data"]
        for cp in r:
            dueno = call("GET", f"/api/solicitudes/{cp['id_donacion_parcial']}")["data"]
            don = next(l["id_donante"] for l in self.lotes if l["id_donacion_ofrecida"] == dueno["id_donacion_ofrecida"])
            otro = self.don_b if don == self.don_a else self.don_a
            self.assertEqual(code(call("GET", f"/api/comprobantes/{cp['id_comprobante']}", rol="donante", actor=otro)), "ORA-01031")
            self.assertTrue(call("GET", f"/api/comprobantes/{cp['id_comprobante']}", rol="donante", actor=don)["ok"])

    def test_07_donante_perfil_no_cambia_estado_ni_ruc(self):
        r = call("PUT", "/api/perfil", {"telefono": "999111222", "id_estado_donante": 2, "ruc": "20111111111"}, rol="donante", actor=self.don_a)
        self.assertTrue(r["ok"], r)
        p = call("GET", "/api/perfil", rol="donante", actor=self.don_a)["data"]
        self.assertEqual(p["telefono"], "999111222"); self.assertNotEqual(p["ruc"], "20111111111")
        self.assertNotEqual(p["id_estado_donante"], 2)

    # --- organizacion
    def test_08_organizacion_solo_ve_sus_solicitudes(self):
        r = call("GET", "/api/solicitudes", rol="organizacion", actor=self.org_a)["data"]
        self.assertTrue(r and all(s["id_organizacion"] == self.org_a for s in r))
        ajena = next(s["id_donacion_parcial"] for s in self.sols if s["id_organizacion"] == self.org_b)
        self.assertEqual(code(call("GET", f"/api/solicitudes/{ajena}", rol="organizacion", actor=self.org_a)), "ORA-01031")
        self.assertEqual(code(call("DELETE", f"/api/solicitudes/{ajena}", rol="organizacion", actor=self.org_a)), "ORA-01031")

    def test_09_organizacion_no_reparte_ni_emite_ni_cambia_estados(self):
        s = self.sols[0]["id_donacion_parcial"]
        for m, p in [("POST", f"/api/solicitudes/{s}/asignar"), ("POST", f"/api/solicitudes/{s}/comprobante"), ("POST", f"/api/lotes/1/repartir"),
                     ("POST", f"/api/lotes/1/sugerir"), ("DELETE", "/api/repartos/1"), ("POST", f"/api/solicitudes/{s}/estado"), ("GET", "/api/crud/donantes")]:
            self.assertIn(code(call(m, p, {"linea": 1, "cantidad": 1}, rol="organizacion", actor=self.org_a)), ("ORA-01031", "404"), p)

    def test_10_organizacion_pide_solo_lotes_publicados_y_a_su_nombre(self):
        pub = next(l for l in call("GET", "/api/lotes", rol="organizacion", actor=self.org_b)["data"] if not l["mi_solicitud"])
        r = call("POST", "/api/solicitudes", {"id_donacion_ofrecida": pub["id_donacion_ofrecida"], "id_organizacion": self.org_a}, rol="organizacion", actor=self.org_b)
        self.assertTrue(r["ok"], r)
        self.assertEqual(call("GET", f"/api/solicitudes/{r['data']['id']}")["data"]["id_organizacion"], self.org_b)
        self.assertEqual(code(call("POST", "/api/solicitudes", {"id_donacion_ofrecida": pub["id_donacion_ofrecida"]}, rol="organizacion", actor=self.org_b)), "ORA-20015")  # ya lo pidio
        # cancelar la propia solicitud sin alimentos asignados esta permitido
        self.assertTrue(call("DELETE", f"/api/solicitudes/{r['data']['id']}", rol="organizacion", actor=self.org_b)["ok"])

    def test_11_organizacion_no_ve_la_competencia(self):
        for l in call("GET", "/api/lotes", rol="organizacion", actor=self.org_a)["data"]:
            self.assertIsNone(l["solicitudes"])
            d = call("GET", f"/api/lotes/{l['id_donacion_ofrecida']}", rol="organizacion", actor=self.org_a)["data"]
            self.assertNotIn("solicitudes_lista", d)

    def test_12_flota_y_personal_son_de_cada_organizacion(self):
        v = call("GET", "/api/crud/vehiculos", rol="organizacion", actor=self.org_a)["data"]
        self.assertTrue(all(x["id_organizacion"] in (self.org_a, None) for x in v))
        p = call("GET", "/api/crud/personas", rol="organizacion", actor=self.org_a)["data"]
        self.assertTrue(all(x["id_organizacion"] == self.org_a for x in p))
        r = call("POST", "/api/crud/vehiculos", {"placa": "ZZZ-999", "capacidad_kg": 50, "id_organizacion": self.org_b}, rol="organizacion", actor=self.org_a)
        self.assertTrue(r["ok"], r)
        self.assertEqual(call("GET", f"/api/crud/vehiculos/{r['data']['id']}", rol="admin")["data"]["id_organizacion"], self.org_a)
        self.assertEqual(code(call("PUT", f"/api/crud/vehiculos/{r['data']['id']}", {"modelo": "x"}, rol="organizacion", actor=self.org_b)), "ORA-01031")
        ajeno = next((x for x in call("GET", "/api/crud/vehiculos", rol="admin")["data"] if x["id_organizacion"] == self.org_b), None)
        if ajeno: self.assertEqual(code(call("DELETE", f"/api/crud/vehiculos/{ajeno['id_vehiculo']}", rol="organizacion", actor=self.org_a)), "ORA-01031")

    def test_13_despachos_solo_de_la_propia_organizacion(self):
        for d in call("GET", "/api/despachos", rol="organizacion", actor=self.org_a)["data"]:
            self.assertEqual(d["nombre_organizacion"], call("GET", "/api/perfil", rol="organizacion", actor=self.org_a)["data"]["nombre_organizacion"])
        ajeno = next((d for d in call("GET", "/api/despachos")["data"] if d["nombre_organizacion"] != call("GET", "/api/perfil", rol="organizacion", actor=self.org_a)["data"]["nombre_organizacion"]), None)
        if ajeno:
            self.assertEqual(code(call("POST", f"/api/despachos/{ajeno['id_despacho']}/hito", {"hito": "llegada"}, rol="organizacion", actor=self.org_a)), "ORA-01031")
            self.assertEqual(code(call("DELETE", f"/api/despachos/{ajeno['id_despacho']}", rol="organizacion", actor=self.org_a)), "ORA-01031")

    def test_14_resumen_solo_propio(self):
        self.assertTrue(call("GET", f"/api/organizaciones/{self.org_a}/resumen", rol="organizacion", actor=self.org_a)["ok"])
        self.assertEqual(code(call("GET", f"/api/organizaciones/{self.org_b}/resumen", rol="organizacion", actor=self.org_a)), "ORA-01031")

    # --- auditor
    def test_15_auditor_solo_lee_lo_suyo(self):
        for p in ["/api/dashboard", "/api/comprobantes", "/api/bitacora", "/api/esquema", "/api/consultas", "/api/pruebas"]:
            self.assertTrue(call("GET", p, rol="auditor")["ok"], p)
        for m, p in [("GET", "/api/lotes"), ("GET", "/api/solicitudes"), ("GET", "/api/despachos"), ("POST", "/api/lotes"),
                     ("DELETE", "/api/crud/vehiculos/1"), ("POST", "/api/sistema/reiniciar"), ("GET", "/api/perfil")]:
            self.assertEqual(code(call(m, p, rol="auditor")), "ORA-01031", p)

    # --- coordinador y estados derivados
    def test_16_estado_derivado_y_reparto(self):
        pub = next(l for l in call("GET", "/api/lotes", rol="organizacion", actor=self.org_a)["data"] if not l["mi_solicitud"] and l["frio_ok"])
        sid = call("POST", "/api/solicitudes", {"id_donacion_ofrecida": pub["id_donacion_ofrecida"]}, rol="organizacion", actor=self.org_a)["data"]["id"]
        self.assertEqual(call("GET", f"/api/solicitudes/{sid}")["data"]["estado"], "PENDIENTE")
        s = call("GET", f"/api/solicitudes/{sid}")["data"]
        linea = next(l for l in s["lineas_lote"] if l["compatible"] and l["saldo"] > 0)
        self.assertTrue(call("POST", f"/api/solicitudes/{sid}/asignar", {"linea": linea["id"], "cantidad": 1})["ok"])
        s = call("GET", f"/api/solicitudes/{sid}")["data"]
        self.assertEqual(s["estado"], "ASIGNADA")
        self.assertTrue(call("DELETE", f"/api/repartos/{s['reparto'][0]['id_detalle_donacion_parcial']}")["ok"])
        self.assertEqual(call("GET", f"/api/solicitudes/{sid}")["data"]["estado"], "PENDIENTE")
        self.assertTrue(call("DELETE", f"/api/solicitudes/{sid}", rol="organizacion", actor=self.org_a)["ok"])

    def test_17_organizacion_no_cancela_solicitud_ya_asignada(self):
        asignada = next((s for s in self.sols if s["estado"] == "ASIGNADA"), None)
        if asignada:
            self.assertEqual(code(call("DELETE", f"/api/solicitudes/{asignada['id_donacion_parcial']}", rol="organizacion", actor=asignada["id_organizacion"])), "ORA-20013")

    def test_18_dashboards_por_rol(self):
        a = call("GET", "/api/dashboard", rol="admin")["data"]; self.assertIn("pendientes", a); self.assertIn("flujo", a)
        d = call("GET", "/api/dashboard", rol="donante", actor=self.don_a)["data"]; self.assertEqual(d["rol"], "donante")
        o = call("GET", "/api/dashboard", rol="organizacion", actor=self.org_a)["data"]; self.assertEqual(o["rol"], "organizacion")
        self.assertTrue(call("GET", "/api/dashboard", rol="auditor")["ok"])


if __name__ == "__main__":
    unittest.main()
