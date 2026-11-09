-- =====================================================================
-- RESCATA - Archivo 08: privilegios sobre objetos (gestion de usuarios, parte B)
-- Ejecutar como RESCATA, despues de crear tablas, vistas y procedimientos
-- (archivos 02 a 07). Los usuarios y roles se crearon en el archivo 01.
-- Los procedimientos usan derechos del definidor (por defecto), de modo
-- que quien los ejecuta no necesita privilegios directos sobre las tablas
-- que ellos modifican.
-- =====================================================================

-- ---- Administrador: mantiene catalogos y entidades base ----
BEGIN
  FOR t IN (SELECT table_name FROM user_tables
             WHERE table_name IN ('DISTRITO','ZONA','ESTADO_DONANTE','TIPO_ORGANIZACION',
                                  'ESTADO_ORGANIZACION','ESTADO_DONACION_OFRECIDA','ESTADO_DONACION',
                                  'TIPO_DOCUMENTO','UNIDAD_MEDIDA','CATEGORIA_ALIMENTO',
                                  'ALIMENTO','DONANTE','ORGANIZACION','VEHICULO')) LOOP
    EXECUTE IMMEDIATE 'GRANT SELECT, INSERT, UPDATE, DELETE ON ' || t.table_name ||
                      ' TO rol_rescata_admin';
  END LOOP;
END;
/
GRANT SELECT ON donacion_ofrecida         TO rol_rescata_admin;
GRANT SELECT ON detalle_donacion_ofrecida TO rol_rescata_admin;
GRANT SELECT ON donacion_parcial          TO rol_rescata_admin;
GRANT SELECT ON despacho                  TO rol_rescata_admin;
GRANT SELECT ON v_demanda_organizacion    TO rol_rescata_admin;
GRANT EXECUTE ON sp_repartir_equitativo   TO rol_rescata_admin;
GRANT EXECUTE ON sp_emitir_comprobante    TO rol_rescata_admin;
GRANT EXECUTE ON sp_programar_despacho    TO rol_rescata_admin;

-- ---- Donante: publica y corrige sus lotes; no los borra ----
GRANT SELECT ON zona                      TO rol_rescata_donante;
GRANT SELECT ON distrito                  TO rol_rescata_donante;
GRANT SELECT ON alimento                  TO rol_rescata_donante;
GRANT SELECT ON unidad_medida             TO rol_rescata_donante;
GRANT SELECT ON estado_donacion_ofrecida  TO rol_rescata_donante;
GRANT SELECT, INSERT, UPDATE ON donacion_ofrecida         TO rol_rescata_donante;
GRANT SELECT, INSERT, UPDATE ON detalle_donacion_ofrecida TO rol_rescata_donante;
GRANT SELECT ON v_lotes_disponibles       TO rol_rescata_donante;
GRANT EXECUTE ON sp_sugerir_receptoras    TO rol_rescata_donante;

-- ---- Organizacion receptora: busca oferta, solicita, registra el recojo y programa el despacho ----
GRANT SELECT ON v_lotes_disponibles       TO rol_rescata_organizacion;
GRANT SELECT ON estado_donacion           TO rol_rescata_organizacion;
GRANT SELECT ON tipo_documento            TO rol_rescata_organizacion;
GRANT SELECT ON vehiculo                  TO rol_rescata_organizacion;
GRANT SELECT, INSERT ON donacion_parcial  TO rol_rescata_organizacion;
GRANT SELECT ON detalle_donacion_parcial  TO rol_rescata_organizacion;
GRANT SELECT, INSERT, UPDATE ON persona_recojo        TO rol_rescata_organizacion;
GRANT SELECT, INSERT, UPDATE ON despacho              TO rol_rescata_organizacion;
GRANT SELECT, INSERT         ON despacho_responsable  TO rol_rescata_organizacion;
GRANT EXECUTE ON sp_asignar_linea         TO rol_rescata_organizacion;
GRANT EXECUTE ON sp_resumen_organizacion  TO rol_rescata_organizacion;
GRANT EXECUTE ON sp_programar_despacho    TO rol_rescata_organizacion;

-- ---- Auditor: solo lectura, sin tocar datos ----
GRANT SELECT ON v_lotes_disponibles       TO rol_rescata_auditor;
GRANT SELECT ON v_demanda_organizacion    TO rol_rescata_auditor;
GRANT SELECT ON v_comprobante_valorizado  TO rol_rescata_auditor;
GRANT SELECT ON v_saldo_linea             TO rol_rescata_auditor;
GRANT SELECT ON comprobante               TO rol_rescata_auditor;
GRANT SELECT ON donacion_parcial          TO rol_rescata_auditor;
GRANT SELECT ON detalle_donacion_parcial  TO rol_rescata_auditor;
GRANT SELECT ON despacho                  TO rol_rescata_auditor;
GRANT SELECT ON vehiculo                  TO rol_rescata_auditor;
GRANT EXECUTE ON sp_alerta_vencimientos   TO rol_rescata_auditor;

-- ---- Retirar un privilegio (ejemplo de REVOKE) ----
-- Se otorga y se retira en el mismo script para mostrar el efecto
GRANT UPDATE ON vehiculo TO rol_rescata_organizacion;
REVOKE UPDATE ON vehiculo FROM rol_rescata_organizacion;

-- ---- Verificacion: que tiene cada rol ----
SELECT grantee, COUNT(*) AS privilegios
  FROM user_tab_privs_made
 WHERE grantee LIKE 'ROL_RESCATA%'
 GROUP BY grantee
 ORDER BY grantee;

SELECT grantee, table_name, privilege
  FROM user_tab_privs_made
 WHERE grantee LIKE 'ROL_RESCATA%'
 ORDER BY grantee, table_name, privilege;
