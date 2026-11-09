-- =====================================================================
-- RESCATA - Archivo 99: reinicio del entorno de pruebas.
-- Parte 1: ejecutar como RESCATA. Elimina objetos en orden inverso.
-- =====================================================================
DROP PROCEDURE sp_emitir_comprobante;
DROP PROCEDURE sp_repartir_equitativo;
DROP PROCEDURE sp_sugerir_receptoras;
DROP FUNCTION  fn_urgencia;
DROP PROCEDURE sp_resumen_organizacion;
DROP PROCEDURE sp_alerta_vencimientos;
DROP PROCEDURE sp_asignar_linea;
DROP FUNCTION  fn_compatible_frio;
DROP FUNCTION  fn_valor_donacion;
DROP FUNCTION  fn_saldo_linea;
DROP VIEW v_comprobante_valorizado;
DROP VIEW v_demanda_organizacion;
DROP VIEW v_lotes_disponibles;
DROP VIEW v_saldo_linea;
-- CASCADE CONSTRAINTS elimina las claves foraneas que apuntan a cada tabla
DROP TABLE comprobante              CASCADE CONSTRAINTS PURGE;
DROP TABLE detalleResponsableRecojo CASCADE CONSTRAINTS PURGE;
DROP TABLE despachoRecojo           CASCADE CONSTRAINTS PURGE;
DROP TABLE personaRecojo            CASCADE CONSTRAINTS PURGE;
DROP TABLE donacionDetalle          CASCADE CONSTRAINTS PURGE;
DROP TABLE donacion                 CASCADE CONSTRAINTS PURGE;
DROP TABLE donacionLoteDetalle      CASCADE CONSTRAINTS PURGE;
DROP TABLE donacionLote             CASCADE CONSTRAINTS PURGE;
DROP TABLE organizacion             CASCADE CONSTRAINTS PURGE;
DROP TABLE donante                  CASCADE CONSTRAINTS PURGE;
DROP TABLE alimento                 CASCADE CONSTRAINTS PURGE;
DROP TABLE categoriaAlimento        CASCADE CONSTRAINTS PURGE;
DROP TABLE medidaCantidad           CASCADE CONSTRAINTS PURGE;
DROP TABLE tipoDocumento            CASCADE CONSTRAINTS PURGE;
DROP TABLE donacionEstado           CASCADE CONSTRAINTS PURGE;
DROP TABLE donacionLoteEstado       CASCADE CONSTRAINTS PURGE;
DROP TABLE organizacionEstado       CASCADE CONSTRAINTS PURGE;
DROP TABLE organizacionTipo         CASCADE CONSTRAINTS PURGE;
DROP TABLE estadoDonante            CASCADE CONSTRAINTS PURGE;
DROP TABLE zona                     CASCADE CONSTRAINTS PURGE;
DROP TABLE distrito                 CASCADE CONSTRAINTS PURGE;

-- Parte 2: ejecutar como SYS en XEPDB1 (solo si tambien se reinician usuarios)
-- DROP USER usr_admin_demo CASCADE;   DROP USER usr_donante_demo CASCADE;
-- DROP USER usr_org_demo CASCADE;     DROP USER usr_auditor_demo CASCADE;
-- DROP USER rescata CASCADE;          DROP PROFILE perfil_rescata;
-- DROP ROLE rol_rescata_admin;        DROP ROLE rol_rescata_donante;
-- DROP ROLE rol_rescata_organizacion; DROP ROLE rol_rescata_auditor;
