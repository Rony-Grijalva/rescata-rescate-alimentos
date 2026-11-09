-- =========================================================
-- RESCATA - Triggers de reglas de negocio (Oracle XE 21c)
-- Version 2: corrige errores de mutating table (ORA-04091)
-- y cierra brechas de autorizacion por rol.
-- Complementa a rescata_ddl_oracle.sql
-- =========================================================

-- =========================================================
-- FUNCIONES AUXILIARES (PRAGMA AUTONOMOUS_TRANSACTION)
-- Necesarias porque un trigger de "asignacion" NO puede
-- consultar la propia tabla "asignacion" (ORA-04091: mutating
-- table). Al declarar la funcion como transaccion autonoma,
-- Oracle la trata como una sesion independiente y permite la
-- lectura. Se hace COMMIT antes de salir (obligatorio en toda
-- transaccion autonoma, aunque sea de solo lectura, para evitar
-- ORA-06519).
-- =========================================================
CREATE OR REPLACE FUNCTION fn_total_asignado_detalle(p_id_detalle NUMBER)
RETURN NUMBER IS
    PRAGMA AUTONOMOUS_TRANSACTION;
    v_total NUMBER;
BEGIN
    SELECT NVL(SUM(cantidad_asignada_kg), 0) INTO v_total
      FROM asignacion
     WHERE id_detalle = p_id_detalle
       AND estado_asignacion = 'ACTIVA';
    COMMIT;
    RETURN v_total;
END;
/

CREATE OR REPLACE FUNCTION fn_total_asignado_solicitud(p_id_solicitud NUMBER)
RETURN NUMBER IS
    PRAGMA AUTONOMOUS_TRANSACTION;
    v_total NUMBER;
BEGIN
    SELECT NVL(SUM(cantidad_asignada_kg), 0) INTO v_total
      FROM asignacion
     WHERE id_solicitud = p_id_solicitud
       AND estado_asignacion = 'ACTIVA';
    COMMIT;
    RETURN v_total;
END;
/

-- =========================================================
-- 1. La fecha de vencimiento de un detalle no puede ser
--    anterior a la fecha de la donacion que lo contiene.
-- =========================================================
CREATE OR REPLACE TRIGGER trg_detalle_venc_check
BEFORE INSERT OR UPDATE ON detalle_donacion
FOR EACH ROW
DECLARE
    v_fecha_donacion DATE;
BEGIN
    SELECT fecha_donacion INTO v_fecha_donacion
      FROM donacion
     WHERE id_donacion = :NEW.id_donacion;

    IF :NEW.fecha_vencimiento < v_fecha_donacion THEN
        RAISE_APPLICATION_ERROR(-20001,
            'La fecha de vencimiento no puede ser anterior a la fecha de la donacion');
    END IF;
END;
/

-- =========================================================
-- 2. Solo un usuario INSPECTOR puede registrar inspecciones.
--    Valida antes de insertar (tabla distinta: usuario -> sin
--    riesgo de mutating table).
-- =========================================================
CREATE OR REPLACE TRIGGER trg_inspeccion_rol_check
BEFORE INSERT ON inspeccion
FOR EACH ROW
DECLARE
    v_rol usuario.rol%TYPE;
BEGIN
    SELECT rol INTO v_rol FROM usuario WHERE id_usuario = :NEW.id_usuario;
    IF v_rol <> 'INSPECTOR' THEN
        RAISE_APPLICATION_ERROR(-20006,
            'Solo un usuario con rol INSPECTOR puede registrar inspecciones');
    END IF;
END;
/

-- =========================================================
-- 3. Despues de registrar una inspeccion, se actualiza
--    detalle_donacion segun el resultado. La inspeccion
--    "vigente" de un detalle es, por definicion, la de mayor
--    id_inspeccion: no se guarda una bandera redundante (esa
--    bandera era la causa de un ORA-04091 en la version 1).
-- =========================================================
CREATE OR REPLACE TRIGGER trg_inspeccion_after
AFTER INSERT ON inspeccion
FOR EACH ROW
BEGIN
    IF :NEW.resultado = 'APTO' THEN
        UPDATE detalle_donacion
           SET estado_sanitario = 'APTO',
               estado_disponibilidad = 'DISPONIBLE'
         WHERE id_detalle = :NEW.id_detalle;
    ELSE
        UPDATE detalle_donacion
           SET estado_sanitario = 'NO_APTO',
               estado_disponibilidad = 'RECHAZADO'
         WHERE id_detalle = :NEW.id_detalle;
    END IF;
END;
/

-- =========================================================
-- 4. Antes de crear una asignacion:
--    - solo un usuario COORDINADOR puede asignar
--    - el detalle debe estar APTO y DISPONIBLE
--    - la suma asignada al detalle no puede superar su peso_kg
--    - la suma asignada a la solicitud no puede superar lo
--      requerido
--    Los topes usan las funciones autonomas para evitar
--    consultar "asignacion" desde su propio trigger.
-- =========================================================
CREATE OR REPLACE TRIGGER trg_asignacion_before
BEFORE INSERT ON asignacion
FOR EACH ROW
DECLARE
    v_rol_usuario           usuario.rol%TYPE;
    v_estado_sanitario      detalle_donacion.estado_sanitario%TYPE;
    v_estado_disponibilidad detalle_donacion.estado_disponibilidad%TYPE;
    v_peso_kg               detalle_donacion.peso_kg%TYPE;
    v_asignado_detalle      NUMBER;
    v_requerido             solicitud.cantidad_requerida_kg%TYPE;
    v_asignado_solicitud    NUMBER;
BEGIN
    SELECT rol INTO v_rol_usuario FROM usuario WHERE id_usuario = :NEW.id_usuario;
    IF v_rol_usuario <> 'COORDINADOR' THEN
        RAISE_APPLICATION_ERROR(-20007,
            'Solo un usuario con rol COORDINADOR puede crear asignaciones');
    END IF;

    SELECT estado_sanitario, estado_disponibilidad, peso_kg
      INTO v_estado_sanitario, v_estado_disponibilidad, v_peso_kg
      FROM detalle_donacion
     WHERE id_detalle = :NEW.id_detalle;

    IF v_estado_sanitario <> 'APTO' OR v_estado_disponibilidad <> 'DISPONIBLE' THEN
        RAISE_APPLICATION_ERROR(-20002,
            'Solo se puede asignar un detalle APTO y DISPONIBLE');
    END IF;

    v_asignado_detalle := fn_total_asignado_detalle(:NEW.id_detalle);
    IF v_asignado_detalle + :NEW.cantidad_asignada_kg > v_peso_kg THEN
        RAISE_APPLICATION_ERROR(-20003,
            'La cantidad asignada supera el peso disponible del detalle');
    END IF;

    SELECT cantidad_requerida_kg INTO v_requerido
      FROM solicitud
     WHERE id_solicitud = :NEW.id_solicitud;

    v_asignado_solicitud := fn_total_asignado_solicitud(:NEW.id_solicitud);
    IF v_asignado_solicitud + :NEW.cantidad_asignada_kg > v_requerido THEN
        RAISE_APPLICATION_ERROR(-20004,
            'La cantidad asignada supera lo requerido por la solicitud');
    END IF;
END;
/

-- =========================================================
-- 5. Despues de crear una asignacion activa:
--    - el detalle pasa a ASIGNADO
--    - si la solicitud quedo totalmente cubierta, pasa a ATENDIDA
-- =========================================================
CREATE OR REPLACE TRIGGER trg_asignacion_after
AFTER INSERT ON asignacion
FOR EACH ROW
DECLARE
    v_requerido          solicitud.cantidad_requerida_kg%TYPE;
    v_asignado_solicitud NUMBER;
BEGIN
    IF :NEW.estado_asignacion = 'ACTIVA' THEN
        UPDATE detalle_donacion
           SET estado_disponibilidad = 'ASIGNADO'
         WHERE id_detalle = :NEW.id_detalle;

        SELECT cantidad_requerida_kg INTO v_requerido
          FROM solicitud
         WHERE id_solicitud = :NEW.id_solicitud;

        v_asignado_solicitud := fn_total_asignado_solicitud(:NEW.id_solicitud);

        IF v_asignado_solicitud >= v_requerido THEN
            UPDATE solicitud
               SET estado_solicitud = 'ATENDIDA'
             WHERE id_solicitud = :NEW.id_solicitud;
        END IF;
    END IF;
END;
/

-- =========================================================
-- 6. Si una asignacion se cancela (la organizacion no recogio):
--    - el detalle vuelve a DISPONIBLE para reasignarse
--    - si la solicitud ya no esta cubierta, vuelve a PENDIENTE
--      (antes quedaba "ATENDIDA" de forma incorrecta)
-- =========================================================
CREATE OR REPLACE TRIGGER trg_asignacion_cancelada
AFTER UPDATE OF estado_asignacion ON asignacion
FOR EACH ROW
WHEN (NEW.estado_asignacion = 'CANCELADA' AND OLD.estado_asignacion = 'ACTIVA')
DECLARE
    v_requerido          solicitud.cantidad_requerida_kg%TYPE;
    v_asignado_solicitud NUMBER;
BEGIN
    UPDATE detalle_donacion
       SET estado_disponibilidad = 'DISPONIBLE'
     WHERE id_detalle = :NEW.id_detalle;

    SELECT cantidad_requerida_kg INTO v_requerido
      FROM solicitud
     WHERE id_solicitud = :NEW.id_solicitud;

    v_asignado_solicitud := fn_total_asignado_solicitud(:NEW.id_solicitud);

    IF v_asignado_solicitud < v_requerido THEN
        UPDATE solicitud
           SET estado_solicitud = 'PENDIENTE'
         WHERE id_solicitud = :NEW.id_solicitud
           AND estado_solicitud = 'ATENDIDA';
    END IF;
END;
/

-- =========================================================
-- 7. Al registrar la entrega:
--    - si es CONFORME, el detalle pasa a ENTREGADO
--    - si es NO_CONFORME, se cancela la asignacion (dispara el
--      trigger anterior y libera el detalle automaticamente)
-- =========================================================
CREATE OR REPLACE TRIGGER trg_entrega_after
AFTER INSERT ON entrega
FOR EACH ROW
DECLARE
    v_id_detalle detalle_donacion.id_detalle%TYPE;
BEGIN
    SELECT id_detalle INTO v_id_detalle
      FROM asignacion
     WHERE id_asignacion = :NEW.id_asignacion;

    IF :NEW.estado_conformidad = 'CONFORME' THEN
        UPDATE detalle_donacion
           SET estado_disponibilidad = 'ENTREGADO'
         WHERE id_detalle = v_id_detalle;
    ELSIF :NEW.estado_conformidad = 'NO_CONFORME' THEN
        UPDATE asignacion
           SET estado_asignacion = 'CANCELADA'
         WHERE id_asignacion = :NEW.id_asignacion;
    END IF;
END;
/

-- =========================================================
-- 8. Solo un usuario ADMINISTRADOR puede habilitar una
--    organizacion.
-- =========================================================
CREATE OR REPLACE TRIGGER trg_organizacion_habilitador_check
BEFORE INSERT OR UPDATE OF id_usuario_habilitador ON organizacion
FOR EACH ROW
DECLARE
    v_rol usuario.rol%TYPE;
BEGIN
    IF :NEW.id_usuario_habilitador IS NOT NULL THEN
        SELECT rol INTO v_rol FROM usuario WHERE id_usuario = :NEW.id_usuario_habilitador;
        IF v_rol <> 'ADMINISTRADOR' THEN
            RAISE_APPLICATION_ERROR(-20009,
                'Solo un usuario con rol ADMINISTRADOR puede habilitar organizaciones');
        END IF;
    END IF;
END;
/

-- =========================================================
-- 9. El certificado:
--    - solo lo emite un usuario ADMINISTRADOR
--    - no se puede emitir si quedan items sin inspeccionar
--      en la donacion (evita certificados con valor incompleto)
--    - el valor total se calcula automaticamente (suma de los
--      detalles APTOS), no se confia en el valor enviado
-- =========================================================
CREATE OR REPLACE TRIGGER trg_certificado_before
BEFORE INSERT ON certificado_donacion
FOR EACH ROW
DECLARE
    v_rol_usuario     usuario.rol%TYPE;
    v_pendientes      NUMBER;
    v_valor_calculado NUMBER(10,2);
BEGIN
    SELECT rol INTO v_rol_usuario FROM usuario WHERE id_usuario = :NEW.id_usuario;
    IF v_rol_usuario <> 'ADMINISTRADOR' THEN
        RAISE_APPLICATION_ERROR(-20008,
            'Solo un usuario con rol ADMINISTRADOR puede emitir certificados');
    END IF;

    SELECT COUNT(*) INTO v_pendientes
      FROM detalle_donacion
     WHERE id_donacion = :NEW.id_donacion
       AND estado_sanitario = 'PENDIENTE';

    IF v_pendientes > 0 THEN
        RAISE_APPLICATION_ERROR(-20005,
            'No se puede emitir el certificado: hay items sin inspeccionar en esta donacion');
    END IF;

    SELECT NVL(SUM(valor_estimado_soles), 0) INTO v_valor_calculado
      FROM detalle_donacion
     WHERE id_donacion = :NEW.id_donacion
       AND estado_sanitario = 'APTO';

    :NEW.valor_total_soles := v_valor_calculado;
END;
/
