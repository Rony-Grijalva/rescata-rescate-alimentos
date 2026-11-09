-- =====================================================================
-- RESCATA - Archivo 05: JOINs y vistas
-- Ejecutar como RESCATA, despues del archivo 04.
-- Cubre INNER, LEFT, RIGHT, FULL OUTER, CROSS, SELF y JOIN ... USING.
-- =====================================================================

-- ---------- Consultas con JOIN ----------

-- J1 INNER JOIN (corrige M1 del 2.o entregable): "atendidas" debe filtrar
--    por estado. Se cuentan las solicitudes ASIGNADA o ENTREGADA.
SELECT o.nombre_organizacion,
       COUNT(d.id_donacion_parcial) AS donaciones_atendidas
  FROM organizacion o
  INNER JOIN donacion_parcial d ON d.id_organizacion = o.id_organizacion
  INNER JOIN estado_donacion e  ON e.id_estado_donacion = d.id_estado_donacion
 WHERE e.estado IN ('ASIGNADA', 'ENTREGADA')
 GROUP BY o.nombre_organizacion
 ORDER BY donaciones_atendidas DESC, o.nombre_organizacion;

-- J2 INNER JOIN con GROUP BY y HAVING (M2 del 2.o entregable): valor
--    publicado por donante, solo los que superan S/ 100.
SELECT don.nombre_donante,
       SUM(det.cantidad * det.costo_unitario) AS total_valor_soles
  FROM donante don
  INNER JOIN donacion_ofrecida l          ON l.id_donante = don.id_donante
  INNER JOIN detalle_donacion_ofrecida det ON det.id_donacion_ofrecida = l.id_donacion_ofrecida
 GROUP BY don.nombre_donante
HAVING SUM(det.cantidad * det.costo_unitario) > 100
 ORDER BY total_valor_soles DESC;

-- J3 INNER JOIN de cinco tablas: donde esta cada lote
SELECT l.id_donacion_ofrecida, don.nombre_donante, dis.nombre_distrito, z.nombre_zona,
       s.estado AS estado_lote, l.fecha_publicacion
  FROM donacion_ofrecida l
  INNER JOIN donante don                 ON don.id_donante = l.id_donante
  INNER JOIN zona z                      ON z.id_zona = l.id_zona
  INNER JOIN distrito dis                ON dis.id_distrito = z.id_distrito
  INNER JOIN estado_donacion_ofrecida s  ON s.id_estado_donacion_ofrecida = l.id_estado_donacion_ofrecida
 ORDER BY l.fecha_publicacion DESC, l.id_donacion_ofrecida;

-- J4 LEFT JOIN: todas las organizaciones, tengan o no solicitudes (un INNER
--    JOIN ocultaria a las que aun no piden nada).
SELECT o.nombre_organizacion, t.tipo, COUNT(d.id_donacion_parcial) AS solicitudes
  FROM organizacion o
  INNER JOIN tipo_organizacion t ON t.id_tipo_organizacion = o.id_tipo_organizacion
  LEFT  JOIN donacion_parcial d  ON d.id_organizacion = o.id_organizacion
 GROUP BY o.nombre_organizacion, t.tipo
 ORDER BY solicitudes DESC, o.nombre_organizacion;

-- J5 LEFT JOIN como anti-join: donantes que nunca han publicado un lote
SELECT don.nombre_donante, don.ruc
  FROM donante don
  LEFT JOIN donacion_ofrecida l ON l.id_donante = don.id_donante
 WHERE l.id_donacion_ofrecida IS NULL;

-- J6 RIGHT JOIN: toda la flota, haya despachado o no. Los vehiculos sin
--    despachos aparecen con columnas vacias en la parte de despacho.
SELECT v.placa, v.modelo, v.capacidad_kg, d.id_despacho, d.fecha_programada
  FROM despacho d
  RIGHT JOIN vehiculo v ON v.id_vehiculo = d.id_vehiculo
 ORDER BY v.placa;

-- J7 FULL OUTER JOIN: cobertura por zona. Zonas con solo donantes, solo
--    organizaciones o ambos (insumo del emparejamiento por cercania).
SELECT z.nombre_zona,
       NVL(d.n, 0) AS donantes,
       NVL(o.n, 0) AS organizaciones,
       CASE WHEN d.n IS NULL THEN 'Solo organizaciones'
            WHEN o.n IS NULL THEN 'Solo donantes'
            ELSE 'Cubierta' END AS cobertura
  FROM (SELECT id_zona, COUNT(*) AS n FROM donante      GROUP BY id_zona) d
  FULL OUTER JOIN
       (SELECT id_zona, COUNT(*) AS n FROM organizacion GROUP BY id_zona) o
    ON o.id_zona = d.id_zona
  INNER JOIN zona z ON z.id_zona = COALESCE(d.id_zona, o.id_zona)
 ORDER BY z.nombre_zona;

-- J8 CROSS JOIN: matriz organizacion x alimento refrigerado; marca las
--    parejas que NO se pueden atender por falta de cadena de frio.
SELECT o.nombre_organizacion, a.nombre_alimento
  FROM organizacion o
  CROSS JOIN alimento a
 WHERE a.requiere_refrigeracion = 1
   AND o.tiene_refrigeracion = 0
 ORDER BY o.nombre_organizacion, a.nombre_alimento;

-- J9 SELF JOIN: pares de organizaciones de la misma zona (posibles
--    coordinadoras de un reparto compartido). a.id < b.id evita repetir.
SELECT a.nombre_organizacion AS organizacion_a,
       b.nombre_organizacion AS organizacion_b,
       a.id_zona
  FROM organizacion a
  INNER JOIN organizacion b ON b.id_zona = a.id_zona AND a.id_organizacion < b.id_organizacion;

-- J10 JOIN ... USING: donantes y su zona (columna comun id_zona)
SELECT nombre_donante, nombre_zona
  FROM donante
  JOIN zona USING (id_zona)
 ORDER BY nombre_donante;

-- ---------- Vistas ----------

-- V1: saldo por linea = lo publicado menos lo ya repartido. Es la base
--     del control "no repartir mas de lo publicado".
CREATE OR REPLACE VIEW v_saldo_linea AS
SELECT l.id_detalle_donacion_ofrecida,
       l.id_donacion_ofrecida,
       l.id_alimento,
       l.cantidad                            AS cantidad_publicada,
       NVL(SUM(dd.cantidad), 0)              AS cantidad_repartida,
       l.cantidad - NVL(SUM(dd.cantidad), 0) AS saldo
  FROM detalle_donacion_ofrecida l
  LEFT JOIN detalle_donacion_parcial dd
         ON dd.id_detalle_donacion_ofrecida = l.id_detalle_donacion_ofrecida
 GROUP BY l.id_detalle_donacion_ofrecida, l.id_donacion_ofrecida, l.id_alimento, l.cantidad;

-- V2: oferta vigente. Lineas con saldo, no vencidas y de lotes no cerrados,
--     con la zona, la unidad y las horas que faltan para vencer.
CREATE OR REPLACE VIEW v_lotes_disponibles AS
SELECT l.id_donacion_ofrecida,
       don.nombre_donante,
       dis.nombre_distrito,
       z.nombre_zona,
       a.nombre_alimento,
       a.requiere_refrigeracion,
       m.tipo_medida,
       sl.saldo,
       det.costo_unitario,
       det.fecha_vencimiento,
       ROUND((det.fecha_vencimiento - SYSDATE) * 24, 1) AS horas_para_vencer
  FROM donacion_ofrecida l
  INNER JOIN estado_donacion_ofrecida s   ON s.id_estado_donacion_ofrecida = l.id_estado_donacion_ofrecida
  INNER JOIN donante don                  ON don.id_donante = l.id_donante
  INNER JOIN zona z                       ON z.id_zona = l.id_zona
  INNER JOIN distrito dis                 ON dis.id_distrito = z.id_distrito
  INNER JOIN detalle_donacion_ofrecida det ON det.id_donacion_ofrecida = l.id_donacion_ofrecida
  INNER JOIN v_saldo_linea sl             ON sl.id_detalle_donacion_ofrecida = det.id_detalle_donacion_ofrecida
  INNER JOIN alimento a                   ON a.id_alimento = det.id_alimento
  INNER JOIN unidad_medida m              ON m.id_unidad_medida = det.id_unidad_medida
 WHERE s.estado <> 'CERRADO'
   AND sl.saldo > 0
   AND det.fecha_vencimiento > SYSDATE;

-- V3: demanda por organizacion (solicitudes por estado y valor repartido)
CREATE OR REPLACE VIEW v_demanda_organizacion AS
SELECT o.id_organizacion,
       o.nombre_organizacion,
       e.estado                                      AS estado_solicitud,
       COUNT(DISTINCT d.id_donacion_parcial)         AS solicitudes,
       NVL(SUM(dd.cantidad * det.costo_unitario), 0) AS valor_repartido_soles
  FROM organizacion o
  INNER JOIN donacion_parcial d ON d.id_organizacion = o.id_organizacion
  INNER JOIN estado_donacion e  ON e.id_estado_donacion = d.id_estado_donacion
  LEFT  JOIN detalle_donacion_parcial dd ON dd.id_donacion_parcial = d.id_donacion_parcial
  LEFT  JOIN detalle_donacion_ofrecida det ON det.id_detalle_donacion_ofrecida = dd.id_detalle_donacion_ofrecida
 GROUP BY o.id_organizacion, o.nombre_organizacion, e.estado;

-- V4: comprobante con el valor recalculado desde el reparto, para
--     contrastarlo con el monto congelado al emitirse.
CREATE OR REPLACE VIEW v_comprobante_valorizado AS
SELECT c.id_comprobante,
       c.serie || '-' || LPAD(c.numero, 8, '0') AS comprobante,
       c.fecha_emision,
       don.nombre_donante,
       don.ruc,
       o.nombre_organizacion                    AS receptora,
       c.monto_total                            AS monto_emitido,
       SUM(dd.cantidad * det.costo_unitario)    AS monto_recalculado
  FROM comprobante c
  INNER JOIN donacion_parcial d            ON d.id_donacion_parcial = c.id_donacion_parcial
  INNER JOIN organizacion o                ON o.id_organizacion = d.id_organizacion
  INNER JOIN donacion_ofrecida l           ON l.id_donacion_ofrecida = d.id_donacion_ofrecida
  INNER JOIN donante don                   ON don.id_donante = l.id_donante
  INNER JOIN detalle_donacion_parcial dd   ON dd.id_donacion_parcial = d.id_donacion_parcial
  INNER JOIN detalle_donacion_ofrecida det ON det.id_detalle_donacion_ofrecida = dd.id_detalle_donacion_ofrecida
 GROUP BY c.id_comprobante, c.serie, c.numero, c.fecha_emision, c.monto_total,
          don.nombre_donante, don.ruc, o.nombre_organizacion;

-- Prueba de las vistas
SELECT * FROM v_lotes_disponibles ORDER BY horas_para_vencer;
SELECT * FROM v_demanda_organizacion ORDER BY nombre_organizacion;
