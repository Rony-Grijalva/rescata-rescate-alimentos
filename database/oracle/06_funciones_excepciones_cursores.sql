-- =====================================================================
-- RESCATA - 3.er avance | Archivo 06: funciones, excepciones y cursores
-- Ejecutar como RESCATA, despues del archivo 05. Activar la salida:
--   SET SERVEROUTPUT ON
-- =====================================================================

-- F1. Saldo disponible de una linea de lote. Lanza NO_DATA_FOUND si la
--     linea no existe (se maneja en el procedimiento que la usa).
CREATE OR REPLACE FUNCTION fn_saldo_linea (p_linea IN NUMBER)
RETURN NUMBER
IS
  v_saldo NUMBER;
BEGIN
  SELECT saldo INTO v_saldo
    FROM v_saldo_linea
   WHERE id_donacionLoteDetalle = p_linea;
  RETURN v_saldo;
END fn_saldo_linea;
/

-- F2. Valor en soles de una solicitud (suma de cantidad repartida por
--     costo unitario). Devuelve 0 si aun no tiene reparto.
CREATE OR REPLACE FUNCTION fn_valor_donacion (p_donacion IN NUMBER)
RETURN NUMBER
IS
  v_valor NUMBER;
BEGIN
  SELECT NVL(SUM(dd.cantidad * det.costoUnitario), 0) INTO v_valor
    FROM donacionDetalle dd
    JOIN donacionLoteDetalle det
      ON det.id_donacionLoteDetalle = dd.id_donacionLoteDetalle
   WHERE dd.id_donacion = p_donacion;
  RETURN v_valor;
END fn_valor_donacion;
/

-- F3. Compatibilidad de frio: una linea que requiere refrigeracion solo
--     puede ir a una organizacion que la tenga. Devuelve 'S' o 'N'.
CREATE OR REPLACE FUNCTION fn_compatible_frio (p_linea IN NUMBER, p_org IN NUMBER)
RETURN CHAR
IS
  v_requiere  alimento.requiere_refrigeracion%TYPE;
  v_tiene     organizacion.tiene_refrigeracion%TYPE;
BEGIN
  SELECT a.requiere_refrigeracion INTO v_requiere
    FROM donacionLoteDetalle det
    JOIN alimento a ON a.id_alimento = det.id_alimento
   WHERE det.id_donacionLoteDetalle = p_linea;

  SELECT tiene_refrigeracion INTO v_tiene
    FROM organizacion WHERE id_organizacion = p_org;

  RETURN CASE WHEN v_requiere = 1 AND v_tiene = 0 THEN 'N' ELSE 'S' END;
END fn_compatible_frio;
/

-- P1. Registrar el reparto de una linea a una solicitud, con excepciones
--     propias y predefinidas. Cierra la brecha del modelo: ningun
--     CHECK impide repartir mas de lo publicado ni a una receptora sin frio.
CREATE OR REPLACE PROCEDURE sp_asignar_linea (
  p_donacion IN NUMBER,
  p_linea    IN NUMBER,
  p_cantidad IN NUMBER
)
IS
  -- Excepciones propias de la regla de negocio
  e_saldo_insuficiente EXCEPTION;
  e_sin_frio           EXCEPTION;
  e_lote_distinto      EXCEPTION;

  v_org        donacion.id_organizacion%TYPE;
  v_lote_don   donacion.id_donacionLote%TYPE;
  v_lote_lin   donacionLoteDetalle.id_donacionLote%TYPE;
  v_saldo      NUMBER;
BEGIN
  SELECT id_organizacion, id_donacionLote INTO v_org, v_lote_don
    FROM donacion WHERE id_donacion = p_donacion;
  SELECT id_donacionLote INTO v_lote_lin
    FROM donacionLoteDetalle WHERE id_donacionLoteDetalle = p_linea;

  IF v_lote_don <> v_lote_lin THEN
    RAISE e_lote_distinto;
  END IF;

  IF fn_compatible_frio(p_linea, v_org) = 'N' THEN
    RAISE e_sin_frio;
  END IF;

  v_saldo := fn_saldo_linea(p_linea);
  IF p_cantidad > v_saldo THEN
    RAISE e_saldo_insuficiente;
  END IF;

  INSERT INTO donacionDetalle (id_donacion, id_donacionLoteDetalle, cantidad)
  VALUES (p_donacion, p_linea, p_cantidad);

  DBMS_OUTPUT.PUT_LINE('Asignado: ' || p_cantidad || ' de la linea ' || p_linea ||
                       ' a la donacion ' || p_donacion);
EXCEPTION
  WHEN e_lote_distinto THEN
    RAISE_APPLICATION_ERROR(-20003, 'La linea ' || p_linea ||
                            ' no pertenece al lote de la donacion ' || p_donacion);
  WHEN e_sin_frio THEN
    RAISE_APPLICATION_ERROR(-20002, 'La linea requiere refrigeracion y la organizacion no la tiene');
  WHEN e_saldo_insuficiente THEN
    RAISE_APPLICATION_ERROR(-20001, 'Saldo insuficiente: se piden ' || p_cantidad ||
                            ' y quedan ' || v_saldo);
  WHEN NO_DATA_FOUND THEN
    RAISE_APPLICATION_ERROR(-20004, 'La donacion ' || p_donacion || ' o la linea ' ||
                            p_linea || ' no existe');
  WHEN DUP_VAL_ON_INDEX THEN
    -- viola uq_donDet_donacion_linea: la linea ya se asigno a esa donacion
    RAISE_APPLICATION_ERROR(-20005, 'La linea ' || p_linea ||
                            ' ya fue asignada a la donacion ' || p_donacion);
END sp_asignar_linea;
/

-- P2. Cursor explicito: lineas que vencen dentro de N horas y todavia
--     tienen saldo, para avisar a las organizaciones cercanas.
CREATE OR REPLACE PROCEDURE sp_alerta_vencimientos (p_horas IN NUMBER DEFAULT 24)
IS
  CURSOR c_por_vencer IS
    SELECT nombre_donante, nombre_distrito, nombre_alimento, saldo,
           tipoMedida, horas_para_vencer
      FROM v_lotes_disponibles
     WHERE horas_para_vencer <= p_horas
     ORDER BY horas_para_vencer;
  r_linea c_por_vencer%ROWTYPE;
  v_total PLS_INTEGER := 0;
BEGIN
  OPEN c_por_vencer;
  LOOP
    FETCH c_por_vencer INTO r_linea;
    EXIT WHEN c_por_vencer%NOTFOUND;
    v_total := v_total + 1;
    DBMS_OUTPUT.PUT_LINE(
      LPAD(v_total, 2) || '. ' || r_linea.nombre_alimento || ' (' || r_linea.saldo || ' ' ||
      r_linea.tipoMedida || ') - ' || r_linea.nombre_donante || ', ' || r_linea.nombre_distrito ||
      ' - vence en ' || r_linea.horas_para_vencer || ' h');
  END LOOP;
  CLOSE c_por_vencer;

  IF v_total = 0 THEN
    DBMS_OUTPUT.PUT_LINE('Sin lineas que venzan en las proximas ' || p_horas || ' horas.');
  END IF;
END sp_alerta_vencimientos;
/

-- P3. Cursor FOR con parametro: resumen de lo repartido a una organizacion.
CREATE OR REPLACE PROCEDURE sp_resumen_organizacion (p_id_org IN NUMBER)
IS
  CURSOR c_reparto (cp_org NUMBER) IS
    SELECT d.id_donacion, a.nombre_alimento, dd.cantidad,
           dd.cantidad * det.costoUnitario AS valor
      FROM donacion d
      JOIN donacionDetalle dd        ON dd.id_donacion = d.id_donacion
      JOIN donacionLoteDetalle det   ON det.id_donacionLoteDetalle = dd.id_donacionLoteDetalle
      JOIN alimento a                ON a.id_alimento = det.id_alimento
     WHERE d.id_organizacion = cp_org
     ORDER BY d.id_donacion, a.nombre_alimento;
  v_acum NUMBER := 0;
BEGIN
  FOR r IN c_reparto(p_id_org) LOOP
    v_acum := v_acum + r.valor;
    DBMS_OUTPUT.PUT_LINE('Donacion ' || r.id_donacion || ' | ' || r.nombre_alimento ||
                         ' | cant ' || r.cantidad || ' | S/ ' || TO_CHAR(r.valor, 'FM999990.00'));
  END LOOP;
  DBMS_OUTPUT.PUT_LINE('Total repartido: S/ ' || TO_CHAR(v_acum, 'FM999990.00'));
END sp_resumen_organizacion;
/
