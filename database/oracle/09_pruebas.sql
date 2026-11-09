-- =====================================================================
-- RESCATA - Archivo 09: pruebas de la logica (PL/SQL, restricciones)
-- Ejecutar como RESCATA despues de los archivos 02 a 08 y con
--   SET SERVEROUTPUT ON SIZE UNLIMITED
-- Las pruebas negativas atrapan el error y lo imprimen con el prefijo
-- "RECHAZADO", para que quede visible que la base impidio la operacion.
-- Todo termina en ROLLBACK: la base queda igual que despues del archivo 04.
-- =====================================================================
SET SERVEROUTPUT ON SIZE UNLIMITED

-- P1. Alerta de vencimientos (24 h). Esperado: arroz con pollo (~6 h),
--     papa a la huancaina (~10 h) y pan frances (~24 h).
EXEC sp_alerta_vencimientos(24);

-- P2. Urgencia por horas. Esperado: CRITICA, ALTA, MEDIA, NORMAL
SELECT fn_urgencia(5) a, fn_urgencia(10) b, fn_urgencia(20) c, fn_urgencia(72) d FROM dual;

-- P3. Receptoras sugeridas para el lote del Restaurante El Fogon (platos
--     refrigerados, zona Villa Los Olivos). Esperado:
--       1. Olla Comun Santa Rosa [Olla comun] - misma zona
--       2. Albergue Casa Hogar [Albergue] - otro distrito
--       3. Comedor Parroquial San Martin [Comedor popular] - otro distrito
--       Descartada (sin refrigeracion): Comedor Popular Las Flores
DECLARE
  v_lote donacion_ofrecida.id_donacion_ofrecida%TYPE;
BEGIN
  SELECT l.id_donacion_ofrecida INTO v_lote
    FROM donacion_ofrecida l JOIN donante d ON d.id_donante = l.id_donante
   WHERE d.nombre_donante = 'Restaurante El Fogon';
  sp_sugerir_receptoras(v_lote);
END;
/

-- P4. Saldo: la olla ya recibio 30 L de 60 de la leche. Se piden 31.
--     Esperado: RECHAZADO ORA-20001 Saldo insuficiente: se piden 31 y quedan 30
DECLARE
  v_don   NUMBER;
  v_linea NUMBER;
BEGIN
  SELECT d.id_donacion_parcial INTO v_don
    FROM donacion_parcial d JOIN donacion_ofrecida l ON l.id_donacion_ofrecida = d.id_donacion_ofrecida
                            JOIN donante dn ON dn.id_donante = l.id_donante
   WHERE dn.nombre_donante = 'Supermercado Metro Surco'
     AND d.id_organizacion = (SELECT id_organizacion FROM organizacion
                               WHERE nombre_organizacion = 'Olla Comun Santa Rosa');
  SELECT det.id_detalle_donacion_ofrecida INTO v_linea
    FROM detalle_donacion_ofrecida det JOIN alimento a ON a.id_alimento = det.id_alimento
   WHERE a.nombre_alimento = 'Leche UHT entera 1L';
  sp_asignar_linea(v_don, v_linea, 31);
EXCEPTION
  WHEN OTHERS THEN DBMS_OUTPUT.PUT_LINE('RECHAZADO ' || SQLERRM);
END;
/

-- P5. Frio incompatible: la torta requiere refrigeracion y el comedor no la tiene.
--     Esperado: RECHAZADO ORA-20002 La linea requiere refrigeracion y la organizacion no la tiene
DECLARE
  v_don   NUMBER;
  v_linea NUMBER;
BEGIN
  SELECT d.id_donacion_parcial INTO v_don
    FROM donacion_parcial d JOIN organizacion o ON o.id_organizacion = d.id_organizacion
   WHERE o.nombre_organizacion = 'Comedor Popular Las Flores';
  SELECT det.id_detalle_donacion_ofrecida INTO v_linea
    FROM detalle_donacion_ofrecida det JOIN alimento a ON a.id_alimento = det.id_alimento
   WHERE a.nombre_alimento = 'Torta de chocolate';
  sp_asignar_linea(v_don, v_linea, 1);
EXCEPTION
  WHEN OTHERS THEN DBMS_OUTPUT.PUT_LINE('RECHAZADO ' || SQLERRM);
END;
/

-- P6. Despacho de una solicitud todavia PENDIENTE (la de la olla sobre el lote
--     de El Fogon). Esperado: RECHAZADO ORA-20010 ... (estado actual: PENDIENTE)
DECLARE
  v_don NUMBER;
BEGIN
  SELECT d.id_donacion_parcial INTO v_don
    FROM donacion_parcial d
    JOIN donacion_ofrecida l ON l.id_donacion_ofrecida = d.id_donacion_ofrecida
    JOIN donante dn          ON dn.id_donante = l.id_donante
   WHERE dn.nombre_donante = 'Restaurante El Fogon';
  sp_programar_despacho(v_don, 'TRI-001');
EXCEPTION
  WHEN OTHERS THEN DBMS_OUTPUT.PUT_LINE('RECHAZADO ' || SQLERRM);
END;
/

-- P7. Reparto automatico del lote de El Fogon (una sola solicitud compatible).
--     Esperado: dos lineas "Asignado: 25 de la linea X a la donacion Y"
DECLARE
  v_lote NUMBER;
BEGIN
  SELECT l.id_donacion_ofrecida INTO v_lote
    FROM donacion_ofrecida l JOIN donante d ON d.id_donante = l.id_donante
   WHERE d.nombre_donante = 'Restaurante El Fogon';
  sp_repartir_equitativo(v_lote);
END;
/

-- P8. Despacho valido: la solicitud ya esta ASIGNADA, el triciclo es de la
--     olla y carga 18 kg (10 + 8) de 120 kg.
--     Esperado: Despacho programado: donacion X, vehiculo TRI-001, carga 18 kg de 120 kg
DECLARE
  v_don NUMBER;
BEGIN
  SELECT d.id_donacion_parcial INTO v_don
    FROM donacion_parcial d
    JOIN donacion_ofrecida l ON l.id_donacion_ofrecida = d.id_donacion_ofrecida
    JOIN donante dn          ON dn.id_donante = l.id_donante
   WHERE dn.nombre_donante = 'Restaurante El Fogon';
  sp_programar_despacho(v_don, 'TRI-001');
END;
/

-- P9. Capacidad: la moto admite 10 kg y la carga pesa 18 kg.
--     Esperado: RECHAZADO ORA-20008 Capacidad insuficiente: la carga pesa 18 kg y el vehiculo admite 10 kg
DECLARE
  v_don NUMBER;
BEGIN
  SELECT d.id_donacion_parcial INTO v_don
    FROM donacion_parcial d
    JOIN donacion_ofrecida l ON l.id_donacion_ofrecida = d.id_donacion_ofrecida
    JOIN donante dn          ON dn.id_donante = l.id_donante
   WHERE dn.nombre_donante = 'Restaurante El Fogon';
  sp_programar_despacho(v_don, 'MOT-010');
EXCEPTION
  WHEN OTHERS THEN DBMS_OUTPUT.PUT_LINE('RECHAZADO ' || SQLERRM);
END;
/

-- P10. Vehiculo de otra organizacion: la H100 es del albergue.
--      Esperado: RECHAZADO ORA-20009 El vehiculo XYZ-789 pertenece a otra organizacion
DECLARE
  v_don NUMBER;
BEGIN
  SELECT d.id_donacion_parcial INTO v_don
    FROM donacion_parcial d
    JOIN donacion_ofrecida l ON l.id_donacion_ofrecida = d.id_donacion_ofrecida
    JOIN donante dn          ON dn.id_donante = l.id_donante
   WHERE dn.nombre_donante = 'Restaurante El Fogon';
  sp_programar_despacho(v_don, 'XYZ-789');
EXCEPTION
  WHEN OTHERS THEN DBMS_OUTPUT.PUT_LINE('RECHAZADO ' || SQLERRM);
END;
/

-- P11. Cierre del ciclo con la primera solicitud: se marca ENTREGADA y se
--      emite el comprobante. Esperado: Comprobante F001-00000001 por S/ 386.00
--      (40 x 6.50 + 30 x 4.20).
DECLARE
  v_don NUMBER;
BEGIN
  SELECT d.id_donacion_parcial INTO v_don
    FROM donacion_parcial d JOIN donacion_ofrecida l ON l.id_donacion_ofrecida = d.id_donacion_ofrecida
                            JOIN donante dn ON dn.id_donante = l.id_donante
   WHERE dn.nombre_donante = 'Supermercado Metro Surco'
     AND d.id_organizacion = (SELECT id_organizacion FROM organizacion
                               WHERE nombre_organizacion = 'Olla Comun Santa Rosa');
  UPDATE donacion_parcial
     SET id_estado_donacion = (SELECT id_estado_donacion FROM estado_donacion WHERE estado = 'ENTREGADA')
   WHERE id_donacion_parcial = v_don;
  sp_emitir_comprobante(v_don);
END;
/
SELECT comprobante, nombre_donante, receptora, monto_emitido, monto_recalculado
  FROM v_comprobante_valorizado;

-- P12. Segundo comprobante para la misma donacion.
--      Esperado: RECHAZADO ORA-20007 ... ya tiene comprobante
DECLARE
  v_don NUMBER;
BEGIN
  SELECT id_donacion_parcial INTO v_don FROM comprobante;
  sp_emitir_comprobante(v_don);
EXCEPTION
  WHEN OTHERS THEN DBMS_OUTPUT.PUT_LINE('RECHAZADO ' || SQLERRM);
END;
/

-- P13. Clave foranea restituida (C0): solicitud sobre un lote inexistente.
--      Esperado: RECHAZADO ORA-02291 integrity constraint (RESCATA.FK_PARCIAL_OFRECIDA) violated
BEGIN
  INSERT INTO donacion_parcial (id_donacion_ofrecida, id_organizacion, id_estado_donacion)
  VALUES (999999, (SELECT MIN(id_organizacion) FROM organizacion),
                  (SELECT MIN(id_estado_donacion) FROM estado_donacion));
EXCEPTION
  WHEN OTHERS THEN DBMS_OUTPUT.PUT_LINE('RECHAZADO ' || SQLERRM);
END;
/

-- P14. CHECK de cantidad: un reparto en cero.
--      Esperado: RECHAZADO ORA-02290 check constraint (RESCATA.CK_DET_PARCIAL_CANT) violated
BEGIN
  INSERT INTO detalle_donacion_parcial (id_donacion_parcial, id_detalle_donacion_ofrecida, cantidad)
  VALUES ((SELECT MIN(id_donacion_parcial) FROM donacion_parcial),
          (SELECT MIN(id_detalle_donacion_ofrecida) FROM detalle_donacion_ofrecida), 0);
EXCEPTION
  WHEN OTHERS THEN DBMS_OUTPUT.PUT_LINE('RECHAZADO ' || SQLERRM);
END;
/

-- P15. CHECK de tiempos del despacho: salida antes de la llegada.
--      Esperado: RECHAZADO ORA-02290 check constraint (RESCATA.CK_DESPACHO_SALIDA) violated
BEGIN
  INSERT INTO despacho (id_donacion_parcial, id_vehiculo, fecha_programada, fecha_llegada, fecha_salida)
  VALUES ((SELECT MIN(id_donacion_parcial) FROM donacion_parcial),
          (SELECT MIN(id_vehiculo) FROM vehiculo),
          SYSTIMESTAMP, SYSTIMESTAMP, SYSTIMESTAMP - INTERVAL '1' HOUR);
EXCEPTION
  WHEN OTHERS THEN DBMS_OUTPUT.PUT_LINE('RECHAZADO ' || SQLERRM);
END;
/

-- P16. Placa duplicada.
--      Esperado: RECHAZADO ORA-00001 unique constraint (RESCATA.UQ_VEHICULO_PLACA) violated
BEGIN
  INSERT INTO vehiculo (placa, marca, modelo, capacidad_kg) VALUES ('TRI-001', 'X', 'Y', 50);
EXCEPTION
  WHEN OTHERS THEN DBMS_OUTPUT.PUT_LINE('RECHAZADO ' || SQLERRM);
END;
/

-- P17. RUC con formato invalido (A1).
--      Esperado: RECHAZADO ORA-02290 check constraint (RESCATA.CK_DONANTE_RUC) violated
BEGIN
  UPDATE donante SET ruc = '123' WHERE nombre_donante = 'Bodega Don Pepe';
EXCEPTION
  WHEN OTHERS THEN DBMS_OUTPUT.PUT_LINE('RECHAZADO ' || SQLERRM);
END;
/

ROLLBACK;
