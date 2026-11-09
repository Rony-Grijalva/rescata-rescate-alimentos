-- =====================================================================
-- RESCATA - Archivo 10: verificacion de la creacion del esquema
-- Ejecutar como RESCATA despues de los archivos 02 a 08.
-- =====================================================================

-- V1. Tablas creadas (esperado: 22)
SELECT COUNT(*) AS tablas FROM user_tables;

-- V2. Restricciones por tipo (P = clave primaria, R = foranea,
--     U = unica, C = check/not null)
SELECT constraint_type, COUNT(*) AS cantidad
  FROM user_constraints
 GROUP BY constraint_type
 ORDER BY constraint_type;

-- V3. Claves foraneas: hija -> padre (esperado: 26, incluidas
--     fk_despacho_vehiculo, fk_parcial_ofrecida y fk_vehiculo_organizacion)
SELECT c.table_name AS hija, p.table_name AS padre, c.constraint_name
  FROM user_constraints c
  JOIN user_constraints p ON p.constraint_name = c.r_constraint_name
 WHERE c.constraint_type = 'R'
 ORDER BY c.table_name, c.constraint_name;

-- V4. Indices creados en el archivo 03 (esperado: 21)
SELECT COUNT(*) AS indices_ix FROM user_indexes WHERE index_name LIKE 'IX\_%' ESCAPE '\';

-- V5. Vistas, funciones y procedimientos y su estado (todos deben ser VALID)
SELECT object_type, object_name, status
  FROM user_objects
 WHERE object_type IN ('VIEW', 'FUNCTION', 'PROCEDURE')
 ORDER BY object_type, object_name;

-- V6. Errores de compilacion (esperado: ninguna fila)
SELECT name, type, line, text FROM user_errors ORDER BY name, sequence;

-- V7. Columnas de la tabla vehiculo
SELECT column_name, data_type, data_length, nullable
  FROM user_tab_columns
 WHERE table_name = 'VEHICULO'
 ORDER BY column_id;

-- V8. Filas cargadas por tabla (despues del archivo 04)
SELECT 'distrito' AS tabla, COUNT(*) AS filas FROM distrito
UNION ALL SELECT 'zona', COUNT(*) FROM zona
UNION ALL SELECT 'donante', COUNT(*) FROM donante
UNION ALL SELECT 'organizacion', COUNT(*) FROM organizacion
UNION ALL SELECT 'vehiculo', COUNT(*) FROM vehiculo
UNION ALL SELECT 'alimento', COUNT(*) FROM alimento
UNION ALL SELECT 'donacion_ofrecida', COUNT(*) FROM donacion_ofrecida
UNION ALL SELECT 'detalle_donacion_ofrecida', COUNT(*) FROM detalle_donacion_ofrecida
UNION ALL SELECT 'donacion_parcial', COUNT(*) FROM donacion_parcial
UNION ALL SELECT 'detalle_donacion_parcial', COUNT(*) FROM detalle_donacion_parcial
UNION ALL SELECT 'despacho', COUNT(*) FROM despacho;
