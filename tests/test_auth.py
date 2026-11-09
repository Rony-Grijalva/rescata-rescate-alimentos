"""Pruebas de seguridad: contrasenas con hash, sesiones, bloqueo, RBAC por sesion y administracion de cuentas."""
import os, sys, tempfile, unittest, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))
os.environ["RESCATA_DB"] = os.path.join(tempfile.mkdtemp(), "auth.db")
import database as D, server as S, auth as A   # noqa: E402

PW = A.DEMO_PASSWORD


def req(method, path, body=None, token=None, q=None):
    return S.entrada(method, path, q or {}, body or {}, token)


def login(email, pw=PW):
    r = req("POST", "/api/auth/login", {"email": email, "password": pw})
    return r, (r.get("_cookie") or (None, None))[1]


def code(r): return (r.get("error") or {}).get("code")


class Auth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        D.init_db(force=True)
        cls.cuentas = req("GET", "/api/auth/demo")["data"]["cuentas"]
        cls.by = lambda c, rol: [x for x in c.cuentas if x["rol"] == rol]

    def test_01_contrasenas_con_hash_y_sal(self):
        c = sqlite3.connect(D.DB_PATH); hs = [r[0] for r in c.execute("SELECT password_hash FROM usuario")]
        self.assertTrue(all(h.startswith("pbkdf2_sha256$") and PW not in h for h in hs))
        self.assertEqual(len(set(hs)), len(hs), "cada usuario debe tener su propia sal")
        self.assertTrue(A.verify_password(PW, hs[0])); self.assertFalse(A.verify_password("otra", hs[0]))

    def test_02_sin_sesion_todo_es_401(self):
        for m, p in [("GET", "/api/me"), ("GET", "/api/lotes"), ("GET", "/api/crud/donantes"), ("POST", "/api/sistema/reiniciar"), ("GET", "/api/usuarios")]:
            self.assertEqual(code(req(m, p)), "SESION", p)
        self.assertEqual(code(req("GET", "/api/me", token="x" * 40)), "SESION")

    def test_03_el_cliente_no_puede_elegir_rol_ni_cuenta(self):
        r, tk = login("auditor@rescata.pe"); self.assertTrue(r["ok"])
        self.assertEqual(req("GET", "/api/me", token=tk)["data"]["rol"], "auditor")
        self.assertEqual(code(req("POST", "/api/sistema/reiniciar", token=tk)), "ORA-01031")
        self.assertEqual(code(req("GET", "/api/usuarios", token=tk)), "ORA-01031")

    def test_04_credenciales_invalidas_mensaje_generico(self):
        a = req("POST", "/api/auth/login", {"email": "noexiste@x.pe", "password": "Algo1234"})
        b = req("POST", "/api/auth/login", {"email": "coordinador@rescata.pe", "password": "Incorrecta1"})
        self.assertEqual(a["error"]["message"], b["error"]["message"]); self.assertEqual(code(a), "AUTH")
        self.assertEqual(code(req("POST", "/api/auth/login", {"email": "", "password": ""})), "AUTH")

    def test_05_bloqueo_tras_cinco_intentos(self):
        em = self.by("auditor")[0]["email"]
        for _ in range(5): req("POST", "/api/auth/login", {"email": em, "password": "mala1234"})
        r, _ = login(em); self.assertEqual(code(r), "AUTH_BLOQUEO")           # ni con la clave correcta
        _, adm = login("coordinador@rescata.pe")
        uid = next(u["id_usuario"] for u in req("GET", "/api/usuarios", token=adm)["data"] if u["email"] == em)
        self.assertTrue(req("PUT", f"/api/usuarios/{uid}", {"desbloquear": True}, token=adm)["ok"])
        self.assertTrue(login(em)[0]["ok"])

    def test_06_logout_invalida_el_token(self):
        _, tk = login("coordinador@rescata.pe"); self.assertTrue(req("GET", "/api/me", token=tk)["ok"])
        self.assertTrue(req("POST", "/api/auth/logout", token=tk)["ok"])
        self.assertEqual(code(req("GET", "/api/me", token=tk)), "SESION")

    def test_07_rbac_con_sesion_real(self):
        d = self.by("donante")[0]; _, tk = login(d["email"])
        me = req("GET", "/api/me", token=tk)["data"]; self.assertEqual(me["rol"], "donante"); self.assertEqual(me["actor"]["nombre"], d["nombre"])
        for l in req("GET", "/api/lotes", token=tk)["data"]: self.assertEqual(l["nombre_donante"], d["nombre"])
        for m, p in [("GET", "/api/solicitudes"), ("GET", "/api/usuarios"), ("POST", "/api/lotes/1/repartir"), ("GET", "/api/bitacora")]:
            self.assertEqual(code(req(m, p, token=tk)), "ORA-01031", p)
        o = self.by("organizacion")[0]; _, to = login(o["email"])
        self.assertEqual(req("GET", "/api/me", token=to)["data"]["actor"]["nombre"], o["nombre"])

    def test_08_cambio_de_contrasena(self):
        em = self.by("donante")[1]["email"]; _, t1 = login(em); _, t2 = login(em)
        self.assertEqual(code(req("POST", "/api/auth/password", {"actual": "mal", "nueva": "Nueva1234"}, token=t1)), "AUTH")
        self.assertEqual(code(req("POST", "/api/auth/password", {"actual": PW, "nueva": "corta"}, token=t1)), "VALIDACION")
        self.assertEqual(code(req("POST", "/api/auth/password", {"actual": PW, "nueva": "sololetras"}, token=t1)), "VALIDACION")
        self.assertTrue(req("POST", "/api/auth/password", {"actual": PW, "nueva": "Nueva1234"}, token=t1)["ok"])
        self.assertEqual(code(req("GET", "/api/me", token=t2)), "SESION")        # se cerraron las otras sesiones
        self.assertEqual(code(login(em)[0]), "AUTH"); self.assertTrue(login(em, "Nueva1234")[0]["ok"])

    def test_09_administracion_de_cuentas(self):
        _, adm = login("coordinador@rescata.pe")
        don = req("GET", "/api/lotes", token=adm)["data"][0]["id_donante"]
        r = req("POST", "/api/usuarios", {"rol": "donante", "nombre": "Nueva Cuenta", "email": "nueva@donante.pe", "password": "Clave12345", "id_donante": don}, token=adm); self.assertTrue(r["ok"], r)
        self.assertEqual(code(req("POST", "/api/usuarios", {"rol": "donante", "nombre": "X", "email": "NUEVA@donante.pe", "password": "Clave12345", "id_donante": don}, token=adm)), "ORA-00001")
        self.assertEqual(code(req("POST", "/api/usuarios", {"rol": "donante", "nombre": "X", "email": "otra@d.pe", "password": "123", "id_donante": don}, token=adm)), "VALIDACION")
        _, tk = login("nueva@donante.pe", "Clave12345"); self.assertTrue(req("GET", "/api/me", token=tk)["ok"])
        self.assertTrue(req("PUT", f"/api/usuarios/{r['data']['id']}", {"activo": False}, token=adm)["ok"])
        self.assertEqual(code(req("GET", "/api/me", token=tk)), "SESION")        # desactivar corta la sesion
        self.assertEqual(code(login("nueva@donante.pe", "Clave12345")[0]), "AUTH")
        yo = next(u["id_usuario"] for u in req("GET", "/api/usuarios", token=adm)["data"] if u["email"] == "coordinador@rescata.pe")
        self.assertEqual(code(req("PUT", f"/api/usuarios/{yo}", {"activo": False}, token=adm)), "ORA-20017")

    def test_10_consola_sql_no_lee_credenciales(self):
        _, adm = login("coordinador@rescata.pe")
        r = req("POST", "/api/sql", {"sql": "SELECT password_hash FROM usuario"}, token=adm); self.assertEqual(code(r), "ORA-01031")
        self.assertEqual(code(req("POST", "/api/sql", {"sql": "SELECT * FROM sesion"}, token=adm)), "ORA-01031")
        self.assertTrue(req("POST", "/api/sql", {"sql": "SELECT COUNT(*) FROM donante"}, token=adm)["ok"])
        self.assertNotIn("usuario", [t["tabla"] for t in req("GET", "/api/esquema", token=adm)["data"]])

    def test_11_reiniciar_conserva_la_sesion_del_coordinador(self):
        _, adm = login("coordinador@rescata.pe"); self.assertTrue(req("POST", "/api/sistema/reiniciar", token=adm)["ok"])
        self.assertTrue(req("GET", "/api/me", token=adm)["ok"]); self.assertTrue(login("auditor@rescata.pe")[0]["ok"])


if __name__ == "__main__":
    unittest.main()
