-- =====================================================================
-- RESCATA - 3.er avance | Archivo 07: estructuras de control, RECORDS y
-- colecciones. Ejecutar como RESCATA, despues del archivo 06.
-- =====================================================================

-- U1. VARRAY de umbrales + CASE: clasifica la urgencia de una linea
--     segun las horas que faltan para su vencimiento.
CREATE OR REPLACE FUNCTION fn_urgencia (p_horas IN NUMBER)
RETURN VARCHAR2
IS
  TYPE t_umbrales IS VARRAY(3) OF NUMBER;
  v_um t_umbrales := t_umbrales(6, 12, 24);   -- horas
BEGIN
  RETURN CASE
           WHEN p_horas <= v_um(1) THEN 'CRITICA'
           WHEN p_horas <= v_um(2) THEN 'ALTA'
           WHEN p_horas <= v_um(3) THEN 'MEDIA'
           ELSE 'NORMAL'
         END;
END fn_urgencia;
/

-- U2. RECORD definido por el usuario + tabla anidada + BULK COLLECT:
--     ranking de receptoras para un lote (matching por cercania). Solo
--     se consideran organizaciones HABILITADAS; las que no tienen frio
--     se descartan si el lote trae algo que lo requiere.
CREATE OR REPLACE PROCEDURE sp_sugerir_receptoras (p_lote IN NUMBER)
IS
  TYPE t_candidata IS RECORD (
    id_organizacion organizacion.id_organizacion%TYPE,
    nombre          organizacion.nombre_organizacion%TYPE,
    tipo            organizacionTipo.tipo%TYPE,
    nivel           PLS_INTEGER,     -- 1 misma zona, 2 mismo distrito, 3 otro
    apta_frio       CHAR(1)
  );
  TYPE t_candidatas IS TABLE OF t_candidata;
  v_cand   t_candidatas;
  v_pos    PLS_INTEGER := 0;
  v_existe NUMBER;
BEGIN
  SELECT COUNT(*) INTO v_existe FROM donacionLote WHERE id_donacionLote = p_lote;
  IF v_existe = 0 THEN
    RAISE_APPLICATION_ERROR(-20004, 'El lote ' || p_lote || ' no existe');
  END IF;

  SELECT o.id_organizacion, o.nombre_organizacion, t.tipo,
         CASE WHEN o.id_zona = l.id_zona THEN 1
              WHEN zo.id_distrito = zl.id_distrito THEN 2
              ELSE 3 END,
         CASE WHEN o.tiene_refrigeracion = 0
               AND EXISTS (SELECT 1
                             FROM donacionLoteDetalle det
                             JOIN alimento a ON a.id_alimento = det.id_alimento
                            WHERE det.id_donacionLote = l.id_donacionLote
                              AND a.requiere_refrigeracion = 1)
              THEN 'N' ELSE 'S' END
    BULK COLLECT INTO v_cand
    FROM organizacion o
    JOIN organizacionEstado e ON e.id_organizacionEstado = o.id_organizacionEstado
    JOIN organizacionTipo  t  ON t.id_organizacionTipo   = o.id_organizacionTipo
    JOIN zona zo              ON zo.id_zona = o.id_zona
    JOIN donacionLote l       ON l.id_donacionLote = p_lote
    JOIN zona zl              ON zl.id_zona = l.id_zona
   WHERE e.estado = 'HABILITADA'
   ORDER BY 4, 2;

  FOR i IN 1 .. v_cand.COUNT LOOP
    IF v_cand(i).apta_frio = 'N' THEN
      DBMS_OUTPUT.PUT_LINE('Descartada (sin refrigeracion): ' || v_cand(i).nombre);
    ELSE
      v_pos := v_pos + 1;
      DBMS_OUTPUT.PUT_LINE(v_pos || '. ' || v_cand(i).nombre || ' [' || v_cand(i).tipo || '] - ' ||
        CASE v_cand(i).nivel
          WHEN 1 THEN 'misma zona'
          WHEN 2 THEN 'mismo distrito'
          ELSE 'otro distrito'
        END);
    END IF;
  END LOOP;

  IF v_pos = 0 THEN
    DBMS_OUTPUT.PUT_LINE('Ninguna receptora habilitada y compatible para el lote ' || p_lote);
  END IF;
END sp_sugerir_receptoras;
/

-- U3. Arreglo asociativo (INDEX BY) + WHILE + FOR + IF/ELSE: reparte el
--     saldo de cada linea de un lote, en partes iguales, entre las
--     solicitudes PENDIENTES compatibles con el frio. Reusa sp_asignar_linea,
--     asi que respeta sus validaciones. No hace COMMIT: lo decide quien llama.
CREATE OR REPLACE PROCEDURE sp_repartir_equitativo (p_lote IN NUMBER)
IS
  TYPE t_saldos IS TABLE OF NUMBER INDEX BY PLS_INTEGER;       -- linea -> saldo
  TYPE t_ids    IS TABLE OF donacion.id_donacion%TYPE;
  v_saldos t_saldos;
  v_pend   t_ids;
  v_aptas  t_ids;
  v_linea  PLS_INTEGER;
  v_org    donacion.id_organizacion%TYPE;
  v_parte  NUMBER;
BEGIN
  FOR r IN (SELECT id_donacionLoteDetalle AS linea, saldo
              FROM v_saldo_linea
             WHERE id_donacionLote = p_lote AND saldo > 0) LOOP
    v_saldos(r.linea) := r.saldo;
  END LOOP;

  SELECT d.id_donacion BULK COLLECT INTO v_pend
    FROM donacion d
    JOIN donacionEstado e ON e.id_donacionEstado = d.id_donacionEstado
   WHERE d.id_donacionLote = p_lote AND e.estado = 'PENDIENTE'
   ORDER BY d.fechaSolicitud;

  IF v_saldos.COUNT = 0 OR v_pend.COUNT = 0 THEN
    DBMS_OUTPUT.PUT_LINE('Nada que repartir en el lote ' || p_lote);
    RETURN;
  END IF;

  v_linea := v_saldos.FIRST;
  WHILE v_linea IS NOT NULL LOOP
    v_aptas := t_ids();
    FOR i IN 1 .. v_pend.COUNT LOOP
      SELECT id_organizacion INTO v_org FROM donacion WHERE id_donacion = v_pend(i);
      IF fn_compatible_frio(v_linea, v_org) = 'S' THEN
        v_aptas.EXTEND;
        v_aptas(v_aptas.LAST) := v_pend(i);
      END IF;
    END LOOP;

    IF v_aptas.COUNT = 0 THEN
      DBMS_OUTPUT.PUT_LINE('Linea ' || v_linea || ' sin receptora compatible');
    ELSE
      v_parte := TRUNC(v_saldos(v_linea) / v_aptas.COUNT, 2);
      IF v_parte > 0 THEN
        FOR j IN 1 .. v_aptas.COUNT LOOP
          BEGIN
            sp_asignar_linea(v_aptas(j), v_linea, v_parte);
          EXCEPTION
            -- Se informa y se continua con la siguiente; no se oculta el error.
            WHEN OTHERS THEN
              DBMS_OUTPUT.PUT_LINE('Omitida linea ' || v_linea || ' / donacion ' ||
                                   v_aptas(j) || ': ' || SQLERRM);
          END;
        END LOOP;
      END IF;
    END IF;
    v_linea := v_saldos.NEXT(v_linea);
  END LOOP;

  -- Las solicitudes que ya recibieron reparto pasan a ASIGNADA
  UPDATE donacion d
     SET id_donacionEstado = (SELECT id_donacionEstado FROM donacionEstado WHERE estado = 'ASIGNADA')
   WHERE d.id_donacionLote = p_lote
     AND d.id_donacionEstado = (SELECT id_donacionEstado FROM donacionEstado WHERE estado = 'PENDIENTE')
     AND EXISTS (SELECT 1 FROM donacionDetalle x WHERE x.id_donacion = d.id_donacion);
END sp_repartir_equitativo;
/

-- U4. %ROWTYPE + IF: emite el comprobante de una donacion
--     entregada. La serie es fija ('F001') y el numero correlativo se
--     calcula con MAX+1 (suficiente para la demostracion; en produccion
--     debe usarse una SEQUENCE para evitar duplicados concurrentes).
CREATE OR REPLACE PROCEDURE sp_emitir_comprobante (p_donacion IN NUMBER)
IS
  r_don   donacion%ROWTYPE;
  v_estado donacionEstado.estado%TYPE;
  v_num   NUMBER;
  v_monto NUMBER;
BEGIN
  SELECT * INTO r_don FROM donacion WHERE id_donacion = p_donacion;
  SELECT estado INTO v_estado FROM donacionEstado WHERE id_donacionEstado = r_don.id_donacionEstado;

  IF v_estado <> 'ENTREGADA' THEN
    RAISE_APPLICATION_ERROR(-20006, 'Solo se emite comprobante de una donacion ENTREGADA (estado actual: ' || v_estado || ')');
  END IF;

  v_monto := fn_valor_donacion(p_donacion);
  SELECT NVL(MAX(numero), 0) + 1 INTO v_num FROM comprobante WHERE serie = 'F001';

  INSERT INTO comprobante (id_donacion, serie, numero, monto_total)
  VALUES (p_donacion, 'F001', v_num, v_monto);

  DBMS_OUTPUT.PUT_LINE('Comprobante F001-' || LPAD(v_num, 8, '0') || ' por S/ ' || TO_CHAR(v_monto, 'FM999990.00'));
EXCEPTION
  WHEN NO_DATA_FOUND THEN
    RAISE_APPLICATION_ERROR(-20004, 'La donacion ' || p_donacion || ' no existe');
  WHEN DUP_VAL_ON_INDEX THEN
    RAISE_APPLICATION_ERROR(-20007, 'La donacion ' || p_donacion || ' ya tiene comprobante');
END sp_emitir_comprobante;
/
