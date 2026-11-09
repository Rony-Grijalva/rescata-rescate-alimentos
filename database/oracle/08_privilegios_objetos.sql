-- =====================================================================
-- RESCATA - 3.er avance | Archivo 08: privilegios sobre objetos (parte B)
-- Ejecutar como RESCATA, despues de crear tablas, vistas y procedimientos
-- (archivos 02 a 07). Los usuarios y roles se crearon en el archivo 01.
-- Los procedimientos usan derechos del definidor (por defecto), de modo
-- que quien los ejecuta no necesita privilegios directos sobre las tablas
-- que ellos modifican.
-- =====================================================================

-- ---- Administrador: mantiene catalogos y entidades base ----
BEGIN
  FOR t IN (SELECT table_name FROM user_tables
             WHERE table_name IN ('DISTRITO','ZONA','ESTADODONANTE','ORGANIZACIONTIPO',
                                  'ORGANIZACIONESTADO','DONACIONLOTEESTADO','DONACIONESTADO',
                                  'TIPODOCUMENTO','MEDIDACANTIDAD','CATEGORIAALIMENTO',
                                  'ALIMENTO','DONANTE','ORGANIZACION')) LOOP
    EXECUTE IMMEDIATE 'GRANT SELECT, INSERT, UPDATE, DELETE ON ' || t.table_name ||
                      ' TO rol_rescata_admin';
  END LOOP;
END;
/
GRANT SELECT ON donacionLote          TO rol_rescata_admin;
GRANT SELECT ON donacionLoteDetalle   TO rol_rescata_admin;
GRANT SELECT ON donacion              TO rol_rescata_admin;
GRANT SELECT ON v_demanda_organizacion TO rol_rescata_admin;
GRANT EXECUTE ON sp_repartir_equitativo TO rol_rescata_admin;
GRANT EXECUTE ON sp_emitir_comprobante  TO rol_rescata_admin;

-- ---- Donante: publica y corrige sus lotes; no los borra ----
GRANT SELECT ON zona                 TO rol_rescata_donante;
GRANT SELECT ON distrito             TO rol_rescata_donante;
GRANT SELECT ON alimento             TO rol_rescata_donante;
GRANT SELECT ON medidaCantidad       TO rol_rescata_donante;
GRANT SELECT ON donacionLoteEstado   TO rol_rescata_donante;
GRANT SELECT, INSERT, UPDATE ON donacionLote        TO rol_rescata_donante;
GRANT SELECT, INSERT, UPDATE ON donacionLoteDetalle TO rol_rescata_donante;
GRANT SELECT ON v_lotes_disponibles  TO rol_rescata_donante;
GRANT EXECUTE ON sp_sugerir_receptoras TO rol_rescata_donante;

-- ---- Organizacion receptora: busca oferta, solicita y registra el recojo ----
GRANT SELECT ON v_lotes_disponibles  TO rol_rescata_organizacion;
GRANT SELECT ON donacionEstado       TO rol_rescata_organizacion;
GRANT SELECT ON tipoDocumento        TO rol_rescata_organizacion;
GRANT SELECT, INSERT ON donacion     TO rol_rescata_organizacion;
GRANT SELECT ON donacionDetalle      TO rol_rescata_organizacion;
GRANT SELECT, INSERT, UPDATE ON personaRecojo             TO rol_rescata_organizacion;
GRANT SELECT, INSERT, UPDATE ON despachoRecojo            TO rol_rescata_organizacion;
GRANT SELECT, INSERT         ON detalleResponsableRecojo  TO rol_rescata_organizacion;
GRANT EXECUTE ON sp_asignar_linea       TO rol_rescata_organizacion;
GRANT EXECUTE ON sp_resumen_organizacion TO rol_rescata_organizacion;

-- ---- Auditor: solo lectura, sin tocar datos ----
GRANT SELECT ON v_lotes_disponibles    TO rol_rescata_auditor;
GRANT SELECT ON v_demanda_organizacion TO rol_rescata_auditor;
GRANT SELECT ON v_comprobante_valorizado TO rol_rescata_auditor;
GRANT SELECT ON v_saldo_linea          TO rol_rescata_auditor;
GRANT SELECT ON comprobante            TO rol_rescata_auditor;
GRANT SELECT ON donacion               TO rol_rescata_auditor;
GRANT SELECT ON donacionDetalle        TO rol_rescata_auditor;
GRANT SELECT ON despachoRecojo         TO rol_rescata_auditor;
GRANT EXECUTE ON sp_alerta_vencimientos TO rol_rescata_auditor;

-- ---- Retirar un privilegio (ejemplo de REVOKE, sin ejecutar por defecto) ----
-- REVOKE UPDATE ON personaRecojo FROM rol_rescata_organizacion;

-- ---- Verificacion: que tiene cada rol ----
SELECT grantee, table_name, privilege
  FROM user_tab_privs_made
 WHERE grantee LIKE 'ROL_RESCATA%'
 ORDER BY grantee, table_name, privilege;
