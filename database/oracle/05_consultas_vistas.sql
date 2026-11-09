-- =====================================================================
-- RESCATA - 3.er avance | Archivo 05: JOINs y vistas
-- Ejecutar como RESCATA, despues del archivo 04.
-- =====================================================================

-- ---------- Consultas con JOIN ----------

-- C1 (corrige M1 del 2.o entregable): "atendidas" debe filtrar por estado.
--    Se cuentan las solicitudes ASIGNADA o ENTREGADA por organizacion.
SELECT o.nombre_organizacion,
       COUNT(d.id_donacion) AS donaciones_atendidas
  FROM organizacion o
  INNER JOIN donacion d        ON d.id_organizacion = o.id_organizacion
  INNER JOIN donacionEstado e  ON e.id_donacionEstado = d.id_donacionEstado
 WHERE e.estado IN ('ASIGNADA', 'ENTREGADA')
 GROUP BY o.nombre_organizacion
 ORDER BY donaciones_atendidas DESC;

-- C2 (M2 del 2.o entregable): valor publicado por donante.
SELECT don.nombre_donante,
       SUM(det.cantidad * det.costoUnitario) AS total_valor_soles
  FROM donante don
  INNER JOIN donacionLote l          ON l.id_donante = don.id_donante
  INNER JOIN donacionLoteDetalle det ON det.id_donacionLote = l.id_donacionLote
 GROUP BY don.nombre_donante
 HAVING SUM(det.cantidad * det.costoUnitario) > 100
 ORDER BY total_valor_soles DESC;

-- C3: LEFT JOIN. Todas las organizaciones, tengan o no solicitudes
--     (un INNER JOIN ocultaria las que aun no piden nada).
SELECT o.nombre_organizacion, t.tipo, COUNT(d.id_donacion) AS solicitudes
  FROM organizacion o
  INNER JOIN organizacionTipo t ON t.id_organizacionTipo = o.id_organizacionTipo
  LEFT  JOIN donacion d         ON d.id_organizacion = o.id_organizacion
 GROUP BY o.nombre_organizacion, t.tipo
 ORDER BY solicitudes DESC, o.nombre_organizacion;

-- C4: donde esta cada lote (cinco tablas: lote, donante, zona, distrito, estado)
SELECT l.id_donacionLote, don.nombre_donante, dis.nombre_distrito, z.zona_nombre,
       s.estadoLote, l.fechaPublicacion
  FROM donacionLote l
  INNER JOIN donante don          ON don.id_donante = l.id_donante
  INNER JOIN zona z               ON z.id_zona = l.id_zona
  INNER JOIN distrito dis         ON dis.id_distrito = z.id_distrito
  INNER JOIN donacionLoteEstado s ON s.id_donacionLoteEstado = l.id_donacionLoteEstado
 ORDER BY l.fechaPublicacion DESC;

-- ---------- Vistas ----------

-- V1: saldo por linea = lo publicado menos lo ya repartido. Es la base
--     del control "no repartir mas de lo publicado".
CREATE OR REPLACE VIEW v_saldo_linea AS
SELECT l.id_donacionLoteDetalle,
       l.id_donacionLote,
       l.id_alimento,
       l.cantidad                           AS cantidad_publicada,
       NVL(SUM(dd.cantidad), 0)             AS cantidad_repartida,
       l.cantidad - NVL(SUM(dd.cantidad), 0) AS saldo
  FROM donacionLoteDetalle l
  LEFT JOIN donacionDetalle dd ON dd.id_donacionLoteDetalle = l.id_donacionLoteDetalle
 GROUP BY l.id_donacionLoteDetalle, l.id_donacionLote, l.id_alimento, l.cantidad;

-- V2: oferta vigente. Lineas con saldo, no vencidas y de lotes no cerrados,
--     con la zona, la unidad y las horas que faltan para vencer.
CREATE OR REPLACE VIEW v_lotes_disponibles AS
SELECT l.id_donacionLote,
       don.nombre_donante,
       dis.nombre_distrito,
       z.zona_nombre,
       a.nombre_alimento,
       a.requiere_refrigeracion,
       m.tipoMedida,
       sl.saldo,
       det.costoUnitario,
       det.fechaVencimiento,
       ROUND((det.fechaVencimiento - SYSDATE) * 24, 1) AS horas_para_vencer
  FROM donacionLote l
  INNER JOIN donacionLoteEstado s    ON s.id_donacionLoteEstado = l.id_donacionLoteEstado
  INNER JOIN donante don             ON don.id_donante = l.id_donante
  INNER JOIN zona z                  ON z.id_zona = l.id_zona
  INNER JOIN distrito dis            ON dis.id_distrito = z.id_distrito
  INNER JOIN donacionLoteDetalle det ON det.id_donacionLote = l.id_donacionLote
  INNER JOIN v_saldo_linea sl        ON sl.id_donacionLoteDetalle = det.id_donacionLoteDetalle
  INNER JOIN alimento a              ON a.id_alimento = det.id_alimento
  INNER JOIN medidaCantidad m        ON m.id_medidaCantidad = det.id_medidaCantidad
 WHERE s.estadoLote <> 'CERRADO'
   AND sl.saldo > 0
   AND det.fechaVencimiento > SYSDATE;

-- V3: demanda por organizacion (solicitudes por estado y valor repartido)
CREATE OR REPLACE VIEW v_demanda_organizacion AS
SELECT o.id_organizacion,
       o.nombre_organizacion,
       e.estado                              AS estado_solicitud,
       COUNT(DISTINCT d.id_donacion)         AS solicitudes,
       NVL(SUM(dd.cantidad * det.costoUnitario), 0) AS valor_repartido_soles
  FROM organizacion o
  INNER JOIN donacion d        ON d.id_organizacion = o.id_organizacion
  INNER JOIN donacionEstado e  ON e.id_donacionEstado = d.id_donacionEstado
  LEFT  JOIN donacionDetalle dd ON dd.id_donacion = d.id_donacion
  LEFT  JOIN donacionLoteDetalle det ON det.id_donacionLoteDetalle = dd.id_donacionLoteDetalle
 GROUP BY o.id_organizacion, o.nombre_organizacion, e.estado;

-- V4: comprobante con el valor recalculado desde el reparto, para
--     contrastarlo con el monto congelado al emitirse.
CREATE OR REPLACE VIEW v_comprobante_valorizado AS
SELECT c.id_comprobante,
       c.serie || '-' || LPAD(c.numero, 8, '0') AS comprobante,
       c.fechaEmision,
       don.nombre_donante,
       don.ruc,
       o.nombre_organizacion                    AS receptora,
       c.monto_total                            AS monto_emitido,
       SUM(dd.cantidad * det.costoUnitario)     AS monto_recalculado
  FROM comprobante c
  INNER JOIN donacion d              ON d.id_donacion = c.id_donacion
  INNER JOIN organizacion o          ON o.id_organizacion = d.id_organizacion
  INNER JOIN donacionLote l          ON l.id_donacionLote = d.id_donacionLote
  INNER JOIN donante don             ON don.id_donante = l.id_donante
  INNER JOIN donacionDetalle dd      ON dd.id_donacion = d.id_donacion
  INNER JOIN donacionLoteDetalle det ON det.id_donacionLoteDetalle = dd.id_donacionLoteDetalle
 GROUP BY c.id_comprobante, c.serie, c.numero, c.fechaEmision, c.monto_total,
          don.nombre_donante, don.ruc, o.nombre_organizacion;

-- Prueba de las vistas
SELECT * FROM v_lotes_disponibles ORDER BY horas_para_vencer;
SELECT * FROM v_demanda_organizacion ORDER BY nombre_organizacion;
