-- =====================================================================
-- RESCATA - 3.er avance | Archivo 09: pruebas de humo
-- Ejecutar como RESCATA despues de los archivos 02 a 07.
--   SET SERVEROUTPUT ON SIZE UNLIMITED
-- Los "resultado esperado" se deducen de los datos del archivo 04; son lo
-- que debe aparecer, no una salida capturada. Todo termina en ROLLBACK,
-- por lo que la base queda igual que despues del archivo 04.
-- =====================================================================

-- P1. Alerta de vencimientos (24 h).
--     Esperado: arroz con pollo y papa a la huancaina (vencen en ~6 y ~10 h)
--     y pan frances (~24 h, puede aparecer o no segun el segundo exacto).
EXEC sp_alerta_vencimientos(24);

-- P2. Urgencia por horas. Esperado: CRITICA, ALTA, MEDIA, NORMAL
SELECT fn_urgencia(5) a, fn_urgencia(10) b, fn_urgencia(20) c, fn_urgencia(72) d FROM dual;

-- P3. Receptoras sugeridas para el lote del Restaurante El Fogon (platos
--     refrigerados, zona Villa Los Olivos).
--     Esperado: 1. Olla Comun Santa Rosa [Olla comun] - misma zona
--               2. Albergue Casa Hogar [Albergue] - otro distrito
--               Descartada (sin refrigeracion): Comedor Popular Las Flores
DECLARE
  v_lote donacionLote.id_donacionLote%TYPE;
BEGIN
  SELECT l.id_donacionLote INTO v_lote
    FROM donacionLote l JOIN donante d ON d.id_donante = l.id_donante
   WHERE d.nombre_donante = 'Restaurante El Fogon';
  sp_sugerir_receptoras(v_lote);
END;
/

-- P4. Saldo y asignacion invalida: la olla ya recibio 30 L de 60 de la leche.
--     Esperado: ORA-20001 Saldo insuficiente: se piden 31 y quedan 30
DECLARE
  v_don   NUMBER;
  v_linea NUMBER;
BEGIN
  SELECT d.id_donacion INTO v_don
    FROM donacion d JOIN donacionLote l ON l.id_donacionLote = d.id_donacionLote
                    JOIN donante dn ON dn.id_donante = l.id_donante
   WHERE dn.nombre_donante = 'Supermercado Metro Surco'
     AND d.id_organizacion = (SELECT id_organizacion FROM organizacion
                               WHERE nombre_organizacion = 'Olla Comun Santa Rosa')
     AND ROWNUM = 1;
  SELECT det.id_donacionLoteDetalle INTO v_linea
    FROM donacionLoteDetalle det JOIN alimento a ON a.id_alimento = det.id_alimento
   WHERE a.nombre_alimento = 'Leche UHT entera 1L';
  sp_asignar_linea(v_don, v_linea, 31);
END;
/

-- P5. Frio incompatible: la torta requiere refrigeracion y el comedor no la tiene.
--     Esperado: ORA-20002 La linea requiere refrigeracion y la organizacion no la tiene
DECLARE
  v_don   NUMBER;
  v_linea NUMBER;
BEGIN
  SELECT d.id_donacion INTO v_don
    FROM donacion d JOIN organizacion o ON o.id_organizacion = d.id_organizacion
   WHERE o.nombre_organizacion = 'Comedor Popular Las Flores';
  SELECT det.id_donacionLoteDetalle INTO v_linea
    FROM donacionLoteDetalle det JOIN alimento a ON a.id_alimento = det.id_alimento
   WHERE a.nombre_alimento = 'Torta de chocolate';
  sp_asignar_linea(v_don, v_linea, 1);
END;
/

-- P6. Reparto automatico del lote de El Fogon (una sola solicitud compatible).
--     Esperado: Asignado: 25 de la linea X a la donacion Y (dos veces, una por plato)
DECLARE
  v_lote NUMBER;
BEGIN
  SELECT l.id_donacionLote INTO v_lote
    FROM donacionLote l JOIN donante d ON d.id_donante = l.id_donante
   WHERE d.nombre_donante = 'Restaurante El Fogon';
  sp_repartir_equitativo(v_lote);
END;
/

-- P7. Cierre del ciclo con la primera solicitud: se marca ENTREGADA y se
--     emite el comprobante. Esperado: Comprobante F001-00000001 por S/ 386.00
--     (40 x 6.50 + 30 x 4.20).
DECLARE
  v_don NUMBER;
BEGIN
  SELECT d.id_donacion INTO v_don
    FROM donacion d JOIN donacionLote l ON l.id_donacionLote = d.id_donacionLote
                    JOIN donante dn ON dn.id_donante = l.id_donante
   WHERE dn.nombre_donante = 'Supermercado Metro Surco'
     AND d.id_organizacion = (SELECT id_organizacion FROM organizacion
                               WHERE nombre_organizacion = 'Olla Comun Santa Rosa');
  UPDATE donacion
     SET id_donacionEstado = (SELECT id_donacionEstado FROM donacionEstado WHERE estado = 'ENTREGADA')
   WHERE id_donacion = v_don;
  sp_emitir_comprobante(v_don);
END;
/
SELECT comprobante, nombre_donante, receptora, monto_emitido, monto_recalculado
  FROM v_comprobante_valorizado;

ROLLBACK;
