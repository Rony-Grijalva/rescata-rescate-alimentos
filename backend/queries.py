"""Laboratorio de consultas JOIN (archivo 05) ejecutables sobre la base real."""
import re, sqlite3
from database import SQLITE_OK_FULL_JOIN
from errors import AppError

J = [
 dict(id="J1", tipo="INNER JOIN", pregunta="¿Cuántas donaciones atendió cada organización?",
      concepto="INNER JOIN devuelve solo las filas que tienen pareja en ambas tablas. Aquí se unen organización, solicitud y estado, y se filtran las solicitudes ASIGNADA o ENTREGADA.",
      importancia="Mide el impacto real del rescate por organización y prioriza a las que menos han recibido.",
      sql="""SELECT o.nombre_organizacion,
       COUNT(d.id_donacion_parcial) AS donaciones_atendidas
  FROM organizacion o
  INNER JOIN donacion_parcial d ON d.id_organizacion = o.id_organizacion
  INNER JOIN estado_donacion e  ON e.id_estado_donacion = d.id_estado_donacion
 WHERE e.estado IN ('ASIGNADA', 'ENTREGADA')
 GROUP BY o.nombre_organizacion
 ORDER BY donaciones_atendidas DESC, o.nombre_organizacion"""),
 dict(id="J2", tipo="INNER JOIN + GROUP BY + HAVING", pregunta="¿Qué donantes publicaron más de S/ 100 en alimentos y cuánto vale lo publicado?",
      concepto="HAVING filtra sobre el total ya agregado (SUM), algo que WHERE no puede hacer porque se evalúa antes de agrupar.",
      importancia="Reconoce a los donantes más relevantes y respalda el valor donado ante la constancia que exige la Ley 30498.",
      sql="""SELECT don.nombre_donante,
       SUM(det.cantidad * det.costo_unitario) AS total_valor_soles
  FROM donante don
  INNER JOIN donacion_ofrecida l          ON l.id_donante = don.id_donante
  INNER JOIN detalle_donacion_ofrecida det ON det.id_donacion_ofrecida = l.id_donacion_ofrecida
 GROUP BY don.nombre_donante
HAVING SUM(det.cantidad * det.costo_unitario) > 100
 ORDER BY total_valor_soles DESC"""),
 dict(id="J3", tipo="INNER JOIN de cinco tablas", pregunta="¿Dónde está cada lote publicado y en qué estado se encuentra?",
      concepto="Encadena cinco tablas por sus claves foráneas: lote → donante, zona → distrito y estado.",
      importancia="Es la base del emparejamiento por cercanía entre la oferta y la demanda.",
      sql="""SELECT l.id_donacion_ofrecida, don.nombre_donante, dis.nombre_distrito, z.nombre_zona,
       s.estado AS estado_lote, l.fecha_publicacion
  FROM donacion_ofrecida l
  INNER JOIN donante don                 ON don.id_donante = l.id_donante
  INNER JOIN zona z                      ON z.id_zona = l.id_zona
  INNER JOIN distrito dis                ON dis.id_distrito = z.id_distrito
  INNER JOIN estado_donacion_ofrecida s  ON s.id_estado_donacion_ofrecida = l.id_estado_donacion_ofrecida
 ORDER BY l.fecha_publicacion DESC, l.id_donacion_ofrecida"""),
 dict(id="J4", tipo="LEFT JOIN", pregunta="¿Qué organizaciones existen y cuántas solicitudes tiene cada una, incluso las que no han pedido nada?",
      concepto="LEFT JOIN conserva todas las filas de la tabla izquierda; si no hay pareja, las columnas de la derecha salen NULL y COUNT da 0.",
      importancia="Permite detectar organizaciones habilitadas que aún no reciben alimentos. Un INNER JOIN las habría ocultado.",
      sql="""SELECT o.nombre_organizacion, t.tipo, COUNT(d.id_donacion_parcial) AS solicitudes
  FROM organizacion o
  INNER JOIN tipo_organizacion t ON t.id_tipo_organizacion = o.id_tipo_organizacion
  LEFT  JOIN donacion_parcial d  ON d.id_organizacion = o.id_organizacion
 GROUP BY o.nombre_organizacion, t.tipo
 ORDER BY solicitudes DESC, o.nombre_organizacion"""),
 dict(id="J5", tipo="LEFT JOIN como anti-join", pregunta="¿Qué donantes registrados nunca han publicado un lote?",
      concepto="LEFT JOIN + WHERE columna_derecha IS NULL deja solo las filas SIN pareja (anti-join).",
      importancia="Identifica a donantes inactivos para contactarlos y reactivarlos.",
      sql="""SELECT don.nombre_donante, don.ruc
  FROM donante don
  LEFT JOIN donacion_ofrecida l ON l.id_donante = don.id_donante
 WHERE l.id_donacion_ofrecida IS NULL"""),
 dict(id="J6", tipo="RIGHT JOIN", pregunta="¿Qué vehículos tiene la flota y cuáles se han usado en un despacho?",
      concepto="RIGHT JOIN conserva todas las filas de la tabla derecha (vehículo): los que nunca despacharon salen con NULL en las columnas del despacho.",
      importancia="Muestra la capacidad ociosa y ayuda a planificar el transporte de los lotes.",
      sql="""SELECT v.placa, v.modelo, v.capacidad_kg, d.id_despacho, d.fecha_programada
  FROM despacho d
  RIGHT JOIN vehiculo v ON v.id_vehiculo = d.id_vehiculo
 ORDER BY v.placa""",
      compat="""SELECT v.placa, v.modelo, v.capacidad_kg, d.id_despacho, d.fecha_programada
  FROM vehiculo v
  LEFT JOIN despacho d ON v.id_vehiculo = d.id_vehiculo
 ORDER BY v.placa"""),
 dict(id="J7", tipo="FULL OUTER JOIN", pregunta="¿En qué zonas hay solo donantes, solo organizaciones o ambos?",
      concepto="FULL OUTER JOIN conserva las filas sin pareja de ambos lados: zonas con solo donantes, solo organizaciones o ambos.",
      importancia="Señala zonas sin cobertura donde conviene captar donantes u organizaciones.",
      sql="""SELECT z.nombre_zona,
       IFNULL(d.n, 0) AS donantes,
       IFNULL(o.n, 0) AS organizaciones,
       CASE WHEN d.n IS NULL THEN 'Solo organizaciones'
            WHEN o.n IS NULL THEN 'Solo donantes'
            ELSE 'Cubierta' END AS cobertura
  FROM (SELECT id_zona, COUNT(*) AS n FROM donante      GROUP BY id_zona) d
  FULL OUTER JOIN
       (SELECT id_zona, COUNT(*) AS n FROM organizacion GROUP BY id_zona) o
    ON o.id_zona = d.id_zona
  INNER JOIN zona z ON z.id_zona = COALESCE(d.id_zona, o.id_zona)
 ORDER BY z.nombre_zona""",
      compat="""SELECT z.nombre_zona, IFNULL(d.n, 0) AS donantes, IFNULL(o.n, 0) AS organizaciones,
       CASE WHEN d.n IS NULL THEN 'Solo organizaciones' WHEN o.n IS NULL THEN 'Solo donantes' ELSE 'Cubierta' END AS cobertura
  FROM zona z
  LEFT JOIN (SELECT id_zona, COUNT(*) AS n FROM donante      GROUP BY id_zona) d ON d.id_zona = z.id_zona
  LEFT JOIN (SELECT id_zona, COUNT(*) AS n FROM organizacion GROUP BY id_zona) o ON o.id_zona = z.id_zona
 WHERE d.n IS NOT NULL OR o.n IS NOT NULL
 ORDER BY z.nombre_zona"""),
 dict(id="J8", tipo="CROSS JOIN", pregunta="¿Qué combinaciones de organización y alimento refrigerado no se pueden atender por falta de frío?",
      concepto="CROSS JOIN produce el producto cartesiano (todas las parejas); el WHERE deja solo las incompatibles.",
      importancia="Evita entregar alimentos que se echarían a perder; la regla se prueba en el módulo de pruebas (P5).",
      sql="""SELECT o.nombre_organizacion, a.nombre_alimento
  FROM organizacion o
  CROSS JOIN alimento a
 WHERE a.requiere_refrigeracion = 1
   AND o.tiene_refrigeracion = 0
 ORDER BY o.nombre_organizacion, a.nombre_alimento"""),
 dict(id="J9", tipo="SELF JOIN", pregunta="¿Qué alimentos de la misma categoría pueden sustituirse entre sí?",
      concepto="SELF JOIN une una tabla consigo misma con alias distintos; a.id < b.id evita pares repetidos y un alimento con él mismo.",
      importancia="Sugiere sustitutos cuando un alimento pedido por una organización ya no tiene saldo.",
      sql="""SELECT c.nombre_categoria,
       a.nombre_alimento AS alimento_a,
       b.nombre_alimento AS alimento_b
  FROM alimento a
  INNER JOIN alimento b ON b.id_categoria_alimento = a.id_categoria_alimento
                       AND a.id_alimento < b.id_alimento
  INNER JOIN categoria_alimento c ON c.id_categoria_alimento = a.id_categoria_alimento
 ORDER BY c.nombre_categoria, a.nombre_alimento"""),
 dict(id="J10", tipo="JOIN … USING", pregunta="¿En qué zona está cada donante?",
      concepto="USING (columna) es la forma abreviada cuando ambas tablas tienen una columna con el mismo nombre; la columna sale una sola vez.",
      importancia="Sintaxis compacta para uniones simples por clave común.",
      sql="""SELECT nombre_donante, nombre_zona
  FROM donante
  JOIN zona USING (id_zona)
 ORDER BY nombre_donante"""),
]
BY_ID = {q["id"]: q for q in J}


def catalogo():
    return [{k: v for k, v in q.items() if k != "compat"} | {"soportado": True, "emulado": ("compat" in q and not SQLITE_OK_FULL_JOIN)} for q in J]


def ejecutar(db, qid):
    q = BY_ID.get(qid)
    if not q: raise AppError("ORA-00942", "Consulta no existe", 404)
    sql = q["compat"] if ("compat" in q and not SQLITE_OK_FULL_JOIN) else q["sql"]
    cur = db.run(sql)
    cols = [c[0] for c in cur.description]
    rows = [list(r) for r in cur.fetchall()]
    return {"columnas": cols, "filas": rows, "sql": sql, "total": len(rows)}


FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|vacuum|reindex|truncate|grant|revoke)\b", re.I)


def sql_libre(db, texto):
    """Consola de consulta: solo SELECT / WITH, una sentencia, maximo 500 filas, en modo solo lectura."""
    s = (texto or "").strip().rstrip(";").strip()
    if not s: raise AppError("VALIDACION", "Escriba una consulta SELECT.", 422)
    if ";" in s: raise AppError("ORA-00911", "Solo se permite una sentencia por ejecucion.", 422)
    if not re.match(r"^(select|with)\b", s, re.I): raise AppError("ORA-01031", "Solo se permiten consultas SELECT.", 403)
    if FORBIDDEN.search(s): raise AppError("ORA-01031", "La consola es de solo lectura: no se permiten sentencias que modifiquen datos.", 403)
    db.run("PRAGMA query_only = ON")
    def _auth(action, a1, a2, dbn, src):           # las tablas de seguridad (credenciales y sesiones) no se pueden leer desde la consola
        return sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_READ and a1 in ("usuario", "sesion") else sqlite3.SQLITE_OK
    db.conn.set_authorizer(_auth)
    try:
        try:
            cur = db.run(s)
        except Exception as e:
            if "not authorized" in str(e) or "prohibited" in str(e): raise AppError("ORA-01031", "Esa tabla pertenece al módulo de seguridad y no se puede consultar desde la consola.", 403)
            raise AppError("ORA-00933", f"Error de sintaxis o de objeto: {e}", 400)
        cols = [c[0] for c in cur.description]
        rows = [list(r) for r in cur.fetchmany(500)]
    finally:
        db.conn.set_authorizer(None); db.run("PRAGMA query_only = OFF")
    return {"columnas": cols, "filas": rows, "sql": s, "total": len(rows)}
