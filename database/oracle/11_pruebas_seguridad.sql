-- =====================================================================
-- RESCATA - Archivo 11: pruebas de gestion de usuarios (roles y privilegios)
-- Ejecutar con la herramienta de scripts (F5) de SQL Developer, DESPUES de
-- los archivos 01 a 08. Cada bloque cambia de usuario con CONNECT; sustituir
-- <host>:<puerto> (por defecto localhost:1521) y las claves marcadoras si
-- fueron cambiadas. Cada prueba imprime lo que la base permite o rechaza.
-- =====================================================================
SET SERVEROUTPUT ON

-- S1. Donante: puede ver la oferta y publicar, no puede borrar lotes
CONNECT usr_donante_demo/"Cambiar#Don26"@//localhost:1521/XE
SELECT USER AS usuario FROM dual;
SELECT COUNT(*) AS lineas_visibles FROM rescata.v_lotes_disponibles;
BEGIN
  DELETE FROM rescata.donacion_ofrecida;
  DBMS_OUTPUT.PUT_LINE('ERROR: el donante pudo borrar lotes');
EXCEPTION
  WHEN OTHERS THEN DBMS_OUTPUT.PUT_LINE('RECHAZADO ' || SQLERRM);
END;
/
BEGIN
  FOR r IN (SELECT 1 FROM rescata.comprobante) LOOP NULL; END LOOP;
  DBMS_OUTPUT.PUT_LINE('ERROR: el donante pudo leer comprobantes');
EXCEPTION
  WHEN OTHERS THEN DBMS_OUTPUT.PUT_LINE('RECHAZADO ' || SQLERRM);
END;
/

-- S2. Auditor: lee las vistas, no puede modificar
CONNECT usr_auditor_demo/"Cambiar#Aud26"@//localhost:1521/XE
SELECT USER AS usuario FROM dual;
SELECT comprobante, monto_emitido FROM rescata.v_comprobante_valorizado;
SELECT COUNT(*) AS solicitudes FROM rescata.donacion_parcial;
BEGIN
  UPDATE rescata.donacion_parcial SET id_estado_donacion = id_estado_donacion;
  DBMS_OUTPUT.PUT_LINE('ERROR: el auditor pudo modificar');
EXCEPTION
  WHEN OTHERS THEN DBMS_OUTPUT.PUT_LINE('RECHAZADO ' || SQLERRM);
END;
/

-- S3. Organizacion: puede consultar la flota, no puede crear vehiculos ni borrar
CONNECT usr_org_demo/"Cambiar#Org26"@//localhost:1521/XE
SELECT USER AS usuario FROM dual;
SELECT placa, capacidad_kg FROM rescata.vehiculo ORDER BY placa;
BEGIN
  INSERT INTO rescata.vehiculo (placa, capacidad_kg) VALUES ('ZZZ-999', 50);
  DBMS_OUTPUT.PUT_LINE('ERROR: la organizacion pudo crear vehiculos');
EXCEPTION
  WHEN OTHERS THEN DBMS_OUTPUT.PUT_LINE('RECHAZADO ' || SQLERRM);
END;
/

-- S4. Administrador: mantiene catalogos y vehiculos (se deshace con ROLLBACK)
CONNECT usr_admin_demo/"Cambiar#Adm26"@//localhost:1521/XE
SELECT USER AS usuario FROM dual;
INSERT INTO rescata.vehiculo (placa, marca, modelo, capacidad_kg) VALUES ('ADM-001', 'Test', 'Prueba', 300);
SELECT placa, capacidad_kg FROM rescata.vehiculo WHERE placa = 'ADM-001';
ROLLBACK;
