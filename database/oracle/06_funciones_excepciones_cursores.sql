-- =====================================================================
-- RESCATA - Archivo 06: funciones, excepciones y cursores
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
   WHERE id_detalle_donacion_ofrecida = p_linea;
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
  SELECT NVL(SUM(dd.cantidad * det.costo_unitario), 0) INTO v_valor
    FROM detalle_donacion_parcial dd
    JOIN detalle_donacion_ofrecida det
      ON det.id_detalle_donacion_ofrecida = dd.id_detalle_donacion_ofrecida
   WHERE dd.id_donacion_parcial = p_donacion;
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
    FROM detalle_donacion_ofrecida det
    JOIN alimento a ON a.id_alimento = det.id_alimento
   WHERE det.id_detalle_donacion_ofrecida = p_linea;

  SELECT tiene_refrigeracion INTO v_tiene
    FROM organizacion WHERE id_organizacion = p_org;

  RETURN CASE WHEN v_requiere = 1 AND v_tiene = 0 THEN 'N' ELSE 'S' END;
END fn_compatible_frio;
/

-- F4. Peso en kg de lo asignado a una solicitud: cada linea aporta la
--     fraccion asignada de su peso total (lineas sin peso cuentan 0).
CREATE OR REPLACE FUNCTION fn_peso_donacion_kg (p_donacion IN NUMBER)
RETURN NUMBER
IS
  v_peso NUMBER;
BEGIN
  SELECT NVL(SUM(dd.cantidad / det.cantidad * NVL(det.peso_total_kg, 0)), 0) INTO v_peso
    FROM detalle_donacion_parcial dd
    JOIN detalle_donacion_ofrecida det
      ON det.id_detalle_donacion_ofrecida = dd.id_detalle_donacion_ofrecida
   WHERE dd.id_donacion_parcial = p_donacion;
  RETURN ROUND(v_peso, 2);
END fn_peso_donacion_kg;
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

  v_org        donacion_parcial.id_organizacion%TYPE;
  v_lote_don   donacion_parcial.id_donacion_ofrecida%TYPE;
  v_lote_lin   detalle_donacion_ofrecida.id_donacion_ofrecida%TYPE;
  v_saldo      NUMBER;
BEGIN
  SELECT id_organizacion, id_donacion_ofrecida INTO v_org, v_lote_don
    FROM donacion_parcial WHERE id_donacion_parcial = p_donacion;
  SELECT id_donacion_ofrecida INTO v_lote_lin
    FROM detalle_donacion_ofrecida WHERE id_detalle_donacion_ofrecida = p_linea;

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

  INSERT INTO detalle_donacion_parcial (id_donacion_parcial, id_detalle_donacion_ofrecida, cantidad)
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
    -- viola uq_det_parcial_linea: la linea ya se asigno a esa donacion
    RAISE_APPLICATION_ERROR(-20005, 'La linea ' || p_linea ||
                            ' ya fue asignada a la donacion ' || p_donacion);
END sp_asignar_linea;
/

-- P2. Programar el despacho de una solicitud ASIGNADA con un vehiculo.
--     Reglas: la solicitud debe estar ASIGNADA, el vehiculo debe existir,
--     si tiene duenio debe ser la organizacion receptora y su capacidad
--     debe alcanzar para el peso asignado. No hace COMMIT.
CREATE OR REPLACE PROCEDURE sp_programar_despacho (
  p_donacion IN NUMBER,
  p_placa    IN VARCHAR2,
  p_fecha    IN TIMESTAMP DEFAULT SYSTIMESTAMP + INTERVAL '2' HOUR
)
IS
  v_estado     estado_donacion.estado%TYPE;
  v_org        donacion_parcial.id_organizacion%TYPE;
  v_veh        vehiculo.id_vehiculo%TYPE;
  v_cap        vehiculo.capacidad_kg%TYPE;
  v_org_veh    vehiculo.id_organizacion%TYPE;
  v_peso       NUMBER;
BEGIN
  SELECT e.estado, d.id_organizacion INTO v_estado, v_org
    FROM donacion_parcial d
    JOIN estado_donacion e ON e.id_estado_donacion = d.id_estado_donacion
   WHERE d.id_donacion_parcial = p_donacion;

  SELECT id_vehiculo, capacidad_kg, id_organizacion INTO v_veh, v_cap, v_org_veh
    FROM vehiculo WHERE placa = p_placa;

  IF v_estado <> 'ASIGNADA' THEN
    RAISE_APPLICATION_ERROR(-20010, 'Solo se programa despacho de una donacion ASIGNADA (estado actual: ' || v_estado || ')');
  END IF;

  IF v_org_veh IS NOT NULL AND v_org_veh <> v_org THEN
    RAISE_APPLICATION_ERROR(-20009, 'El vehiculo ' || p_placa || ' pertenece a otra organizacion');
  END IF;

  v_peso := fn_peso_donacion_kg(p_donacion);
  IF v_peso > v_cap THEN
    RAISE_APPLICATION_ERROR(-20008, 'Capacidad insuficiente: la carga pesa ' || v_peso ||
                            ' kg y el vehiculo admite ' || v_cap || ' kg');
  END IF;

  INSERT INTO despacho (id_donacion_parcial, id_vehiculo, fecha_programada)
  VALUES (p_donacion, v_veh, p_fecha);

  DBMS_OUTPUT.PUT_LINE('Despacho programado: donacion ' || p_donacion || ', vehiculo ' ||
                       p_placa || ', carga ' || v_peso || ' kg de ' || v_cap || ' kg');
EXCEPTION
  WHEN NO_DATA_FOUND THEN
    RAISE_APPLICATION_ERROR(-20004, 'La donacion ' || p_donacion || ' o el vehiculo ' ||
                            p_placa || ' no existe');
END sp_programar_despacho;
/

-- P3. Cursor explicito: lineas que vencen dentro de N horas y todavia
--     tienen saldo, para avisar a las organizaciones cercanas.
CREATE OR REPLACE PROCEDURE sp_alerta_vencimientos (p_horas IN NUMBER DEFAULT 24)
IS
  CURSOR c_por_vencer IS
    SELECT nombre_donante, nombre_distrito, nombre_alimento, saldo,
           tipo_medida, horas_para_vencer
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
      r_linea.tipo_medida || ') - ' || r_linea.nombre_donante || ', ' || r_linea.nombre_distrito ||
      ' - vence en ' || r_linea.horas_para_vencer || ' h');
  END LOOP;
  CLOSE c_por_vencer;

  IF v_total = 0 THEN
    DBMS_OUTPUT.PUT_LINE('Sin lineas que venzan en las proximas ' || p_horas || ' horas.');
  END IF;
END sp_alerta_vencimientos;
/

-- P4. Cursor FOR con parametro: resumen de lo repartido a una organizacion.
CREATE OR REPLACE PROCEDURE sp_resumen_organizacion (p_id_org IN NUMBER)
IS
  CURSOR c_reparto (cp_org NUMBER) IS
    SELECT d.id_donacion_parcial, a.nombre_alimento, dd.cantidad,
           dd.cantidad * det.costo_unitario AS valor
      FROM donacion_parcial d
      JOIN detalle_donacion_parcial dd  ON dd.id_donacion_parcial = d.id_donacion_parcial
      JOIN detalle_donacion_ofrecida det ON det.id_detalle_donacion_ofrecida = dd.id_detalle_donacion_ofrecida
      JOIN alimento a                   ON a.id_alimento = det.id_alimento
     WHERE d.id_organizacion = cp_org
     ORDER BY d.id_donacion_parcial, a.nombre_alimento;
  v_acum NUMBER := 0;
BEGIN
  FOR r IN c_reparto(p_id_org) LOOP
    v_acum := v_acum + r.valor;
    DBMS_OUTPUT.PUT_LINE('Donacion ' || r.id_donacion_parcial || ' | ' || r.nombre_alimento ||
                         ' | cant ' || r.cantidad || ' | S/ ' || TO_CHAR(r.valor, 'FM999990.00'));
  END LOOP;
  DBMS_OUTPUT.PUT_LINE('Total repartido: S/ ' || TO_CHAR(v_acum, 'FM999990.00'));
END sp_resumen_organizacion;
/
