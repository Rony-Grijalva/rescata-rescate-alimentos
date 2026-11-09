-- =========================================================
-- RESCATA - Base de Datos 2 (UNMSM 2026-II)
-- Script para Oracle Database (XE 21c)
-- Version 5: modelo integral - 12 tablas. Corrige errores
-- encontrados en revision exhaustiva (ver rescata_triggers_oracle.sql
-- para el detalle de los ORA-04091 corregidos):
--   + Distrito (normaliza ubicacion para reportes RF08)
--   + Detalle_Donacion.estado_disponibilidad (ciclo de vida
--     completo: permite rastrear cada kilo que se pierde)
--   + Inspeccion permite re-evaluacion (1:N). YA NO tiene columna
--     "vigente": era un dato redundante/derivable y causaba un
--     error de tabla mutante en su trigger
--   + Organizacion.fecha_habilitacion / id_usuario_habilitador
--     (trazabilidad de "organizaciones receptoras habilitadas")
--   + Solicitud admite estado CANCELADA
--   + Detalle_Donacion nace PENDIENTE_INSPECCION (ya no se puede
--     asignar algo que no fue evaluado sanitariamente)
--   + Asignacion.estado_asignacion (ACTIVA/CANCELADA): permite
--     liberar el kilo si la organizacion no recoge lo asignado
--
-- Politica de borrado: NINGUNA tabla con historial (donante,
-- organizacion, usuario, alimento) se elimina fisicamente.
-- Todas usan el campo "estado" como baja logica. Solo
-- detalle_donacion tiene ON DELETE CASCADE porque es una
-- entidad debil sin existencia propia fuera de su donacion.
-- Alcance: sin acopio, transporte ni seguimiento continuo
--
-- Companero: rescata_triggers_oracle.sql aplica las reglas de
-- negocio (inspeccion obligatoria antes de asignar, topes de
-- kg, liberacion de detalle si una asignacion se cancela,
-- calculo automatico del certificado). Ejecutar ese script
-- despues de este si se desea que las reglas se auto-apliquen.
-- =========================================================

-- =========================================================
-- DDL - Creacion de tablas (orden segun dependencias FK)
-- =========================================================

-- 1. USUARIO (staff interno de RESCATA: da trazabilidad a
--    inspecciones, asignaciones, certificados y habilitaciones)
CREATE TABLE usuario (
    id_usuario      NUMBER GENERATED ALWAYS AS IDENTITY,
    nombre_usuario  VARCHAR2(150) NOT NULL,
    email           VARCHAR2(100) NOT NULL,
    rol             VARCHAR2(30)  NOT NULL,
    estado          VARCHAR2(20) DEFAULT 'ACTIVO' NOT NULL,
    CONSTRAINT pk_usuario PRIMARY KEY (id_usuario),
    CONSTRAINT uq_usuario_email UNIQUE (email),
    CONSTRAINT ck_usuario_rol CHECK (rol IN
        ('ADMINISTRADOR','INSPECTOR','COORDINADOR')),
    CONSTRAINT ck_usuario_estado CHECK (estado IN ('ACTIVO','INACTIVO'))
);

-- 2. DISTRITO (catalogo: evita anomalias de texto libre en
--    direcciones y habilita reportes confiables por zona - RF08)
CREATE TABLE distrito (
    id_distrito     NUMBER GENERATED ALWAYS AS IDENTITY,
    nombre_distrito VARCHAR2(80) NOT NULL,
    provincia       VARCHAR2(80) DEFAULT 'LIMA' NOT NULL,
    CONSTRAINT pk_distrito PRIMARY KEY (id_distrito),
    CONSTRAINT uq_distrito_nombre UNIQUE (nombre_distrito)
);

-- 3. DONANTE
CREATE TABLE donante (
    id_donante      NUMBER GENERATED ALWAYS AS IDENTITY,
    nombre_donante  VARCHAR2(150) NOT NULL,
    tipo_donante    VARCHAR2(50)  NOT NULL,
    direccion       VARCHAR2(200),
    id_distrito     NUMBER,
    telefono        VARCHAR2(30),
    email           VARCHAR2(100),
    estado          VARCHAR2(20) DEFAULT 'ACTIVO' NOT NULL,
    CONSTRAINT pk_donante PRIMARY KEY (id_donante),
    CONSTRAINT fk_donante_distrito FOREIGN KEY (id_distrito)
        REFERENCES distrito (id_distrito),
    CONSTRAINT ck_donante_estado CHECK (estado IN ('ACTIVO','INACTIVO')),
    CONSTRAINT ck_donante_tipo CHECK (tipo_donante IN
        ('RESTAURANTE','PANADERIA','HOTEL','SUPERMERCADO','OTRO'))
);

-- 4. ALIMENTO (catalogo de tipos de alimento)
CREATE TABLE alimento (
    id_alimento            NUMBER GENERATED ALWAYS AS IDENTITY,
    nombre_alimento        VARCHAR2(150) NOT NULL,
    categoria              VARCHAR2(30)  NOT NULL,
    requiere_refrigeracion NUMBER(1) DEFAULT 0 NOT NULL,
    alergenos              VARCHAR2(200),
    CONSTRAINT pk_alimento PRIMARY KEY (id_alimento),
    CONSTRAINT ck_alimento_categoria CHECK (categoria IN ('PERECIBLE','NO_PERECIBLE')),
    CONSTRAINT ck_alimento_refrig CHECK (requiere_refrigeracion IN (0,1))
);

-- 5. ORGANIZACION
CREATE TABLE organizacion (
    id_organizacion      NUMBER GENERATED ALWAYS AS IDENTITY,
    nombre_organizacion  VARCHAR2(150) NOT NULL,
    tipo_organizacion    VARCHAR2(50)  NOT NULL,
    direccion            VARCHAR2(200),
    id_distrito          NUMBER,
    telefono             VARCHAR2(30),
    capacidad_diaria_kg  NUMBER(8,2),
    tiene_refrigeracion  NUMBER(1) DEFAULT 0 NOT NULL,
    responsable          VARCHAR2(150),
    fecha_habilitacion   DATE,
    id_usuario_habilitador NUMBER,
    estado               VARCHAR2(20) DEFAULT 'ACTIVO' NOT NULL,
    CONSTRAINT pk_organizacion PRIMARY KEY (id_organizacion),
    CONSTRAINT fk_organizacion_distrito FOREIGN KEY (id_distrito)
        REFERENCES distrito (id_distrito),
    CONSTRAINT fk_organizacion_usuario FOREIGN KEY (id_usuario_habilitador)
        REFERENCES usuario (id_usuario),
    CONSTRAINT ck_organizacion_estado CHECK (estado IN ('ACTIVO','INACTIVO')),
    CONSTRAINT ck_organizacion_refrig CHECK (tiene_refrigeracion IN (0,1))
);

-- 6. DONACION (cabecera: evento en el que un donante ofrece alimentos)
CREATE TABLE donacion (
    id_donacion     NUMBER GENERATED ALWAYS AS IDENTITY,
    id_donante      NUMBER NOT NULL,
    fecha_donacion  DATE DEFAULT SYSDATE NOT NULL,
    CONSTRAINT pk_donacion PRIMARY KEY (id_donacion),
    CONSTRAINT fk_donacion_donante FOREIGN KEY (id_donante)
        REFERENCES donante (id_donante)
);

-- 7. DETALLE_DONACION (entidad debil: depende de donacion).
--    fecha_vencimiento es DATE -> Oracle ya guarda hora:minuto:segundo,
--    usar TO_DATE('...','YYYY-MM-DD HH24:MI') para reflejar urgencia
--    por horas, tal como exige el planteamiento del proyecto.
CREATE TABLE detalle_donacion (
    id_detalle            NUMBER GENERATED ALWAYS AS IDENTITY,
    id_donacion            NUMBER NOT NULL,
    id_alimento            NUMBER NOT NULL,
    peso_kg                NUMBER(8,2) NOT NULL,
    fecha_vencimiento       DATE NOT NULL,
    valor_estimado_soles   NUMBER(10,2) NOT NULL,
    estado_sanitario        VARCHAR2(20) DEFAULT 'PENDIENTE' NOT NULL,
    estado_disponibilidad   VARCHAR2(20) DEFAULT 'PENDIENTE_INSPECCION' NOT NULL,
    CONSTRAINT pk_detalle_donacion PRIMARY KEY (id_detalle),
    CONSTRAINT fk_detalle_donacion FOREIGN KEY (id_donacion)
        REFERENCES donacion (id_donacion) ON DELETE CASCADE,
    CONSTRAINT fk_detalle_alimento FOREIGN KEY (id_alimento)
        REFERENCES alimento (id_alimento),
    CONSTRAINT ck_detalle_peso CHECK (peso_kg > 0),
    CONSTRAINT ck_detalle_valor CHECK (valor_estimado_soles >= 0),
    CONSTRAINT ck_detalle_estado CHECK (estado_sanitario IN
        ('PENDIENTE','APTO','NO_APTO')),
    CONSTRAINT ck_detalle_disponibilidad CHECK (estado_disponibilidad IN
        ('PENDIENTE_INSPECCION','DISPONIBLE','ASIGNADO','ENTREGADO','VENCIDO','RECHAZADO'))
);

-- 8. INSPECCION (evaluacion sanitaria obligatoria; 1:N con
--    detalle_donacion para permitir re-inspeccion). No se
--    guarda una bandera "vigente": la inspeccion vigente de un
--    detalle es, por definicion, la de MAX(id_inspeccion) -- un
--    dato derivable no debe duplicarse (y hacerlo causaba un
--    ORA-04091 de tabla mutante en el trigger correspondiente).
CREATE TABLE inspeccion (
    id_inspeccion    NUMBER GENERATED ALWAYS AS IDENTITY,
    id_detalle       NUMBER NOT NULL,
    id_usuario       NUMBER NOT NULL,
    fecha_inspeccion DATE DEFAULT SYSDATE NOT NULL,
    resultado        VARCHAR2(20) NOT NULL,
    motivo_rechazo   VARCHAR2(200),
    CONSTRAINT pk_inspeccion PRIMARY KEY (id_inspeccion),
    CONSTRAINT fk_inspeccion_detalle FOREIGN KEY (id_detalle)
        REFERENCES detalle_donacion (id_detalle),
    CONSTRAINT fk_inspeccion_usuario FOREIGN KEY (id_usuario)
        REFERENCES usuario (id_usuario),
    CONSTRAINT ck_inspeccion_resultado CHECK (resultado IN ('APTO','NO_APTO'))
);

-- 9. CERTIFICADO_DONACION (comprobante fiscal Ley 30498; 1:1 con donacion)
CREATE TABLE certificado_donacion (
    id_certificado     NUMBER GENERATED ALWAYS AS IDENTITY,
    id_donacion        NUMBER NOT NULL,
    id_usuario         NUMBER NOT NULL,
    nro_certificado    VARCHAR2(30) NOT NULL,
    fecha_emision      DATE DEFAULT SYSDATE NOT NULL,
    valor_total_soles  NUMBER(10,2) NOT NULL,
    CONSTRAINT pk_certificado PRIMARY KEY (id_certificado),
    CONSTRAINT fk_certificado_donacion FOREIGN KEY (id_donacion)
        REFERENCES donacion (id_donacion),
    CONSTRAINT uq_certificado_donacion UNIQUE (id_donacion),
    CONSTRAINT fk_certificado_usuario FOREIGN KEY (id_usuario)
        REFERENCES usuario (id_usuario),
    CONSTRAINT uq_certificado_nro UNIQUE (nro_certificado),
    CONSTRAINT ck_certificado_valor CHECK (valor_total_soles >= 0)
);

-- 10. SOLICITUD
CREATE TABLE solicitud (
    id_solicitud          NUMBER GENERATED ALWAYS AS IDENTITY,
    id_organizacion       NUMBER NOT NULL,
    fecha_solicitud       DATE DEFAULT SYSDATE NOT NULL,
    cantidad_requerida_kg NUMBER(8,2) NOT NULL,
    categoria_preferida   VARCHAR2(30),
    estado_solicitud      VARCHAR2(20) DEFAULT 'PENDIENTE' NOT NULL,
    CONSTRAINT pk_solicitud PRIMARY KEY (id_solicitud),
    CONSTRAINT fk_solicitud_organizacion FOREIGN KEY (id_organizacion)
        REFERENCES organizacion (id_organizacion),
    CONSTRAINT ck_solicitud_categoria CHECK (categoria_preferida IN
        ('PERECIBLE','NO_PERECIBLE')),
    CONSTRAINT ck_solicitud_estado CHECK (estado_solicitud IN
        ('PENDIENTE','ATENDIDA','CANCELADA'))
);

-- 11. ASIGNACION (entidad asociativa N:M entre detalle_donacion y solicitud)
CREATE TABLE asignacion (
    id_asignacion        NUMBER GENERATED ALWAYS AS IDENTITY,
    id_detalle           NUMBER NOT NULL,
    id_solicitud         NUMBER NOT NULL,
    id_usuario           NUMBER NOT NULL,
    fecha_asignacion     DATE DEFAULT SYSDATE NOT NULL,
    cantidad_asignada_kg NUMBER(8,2) NOT NULL,
    estado_asignacion    VARCHAR2(20) DEFAULT 'ACTIVA' NOT NULL,
    CONSTRAINT pk_asignacion PRIMARY KEY (id_asignacion),
    CONSTRAINT fk_asignacion_detalle FOREIGN KEY (id_detalle)
        REFERENCES detalle_donacion (id_detalle),
    CONSTRAINT fk_asignacion_solicitud FOREIGN KEY (id_solicitud)
        REFERENCES solicitud (id_solicitud),
    CONSTRAINT fk_asignacion_usuario FOREIGN KEY (id_usuario)
        REFERENCES usuario (id_usuario),
    CONSTRAINT ck_asignacion_cantidad CHECK (cantidad_asignada_kg > 0),
    CONSTRAINT ck_asignacion_estado CHECK (estado_asignacion IN
        ('ACTIVA','CANCELADA'))
);

-- 12. ENTREGA (registro puntual de conformidad ante la organizacion)
CREATE TABLE entrega (
    id_entrega          NUMBER GENERATED ALWAYS AS IDENTITY,
    id_asignacion       NUMBER NOT NULL,
    fecha_entrega       DATE DEFAULT SYSDATE NOT NULL,
    estado_conformidad  VARCHAR2(20) DEFAULT 'PENDIENTE' NOT NULL,
    nombre_receptor     VARCHAR2(150),
    CONSTRAINT pk_entrega PRIMARY KEY (id_entrega),
    CONSTRAINT fk_entrega_asignacion FOREIGN KEY (id_asignacion)
        REFERENCES asignacion (id_asignacion),
    CONSTRAINT uq_entrega_asignacion UNIQUE (id_asignacion),
    CONSTRAINT ck_entrega_estado CHECK (estado_conformidad IN
        ('PENDIENTE','CONFORME','NO_CONFORME'))
);

-- =========================================================
-- DML - Datos de prueba (flujo completo)
-- =========================================================

INSERT INTO usuario (nombre_usuario, email, rol)
VALUES ('Maria Lopez', 'mlopez@rescata.pe', 'INSPECTOR');
INSERT INTO usuario (nombre_usuario, email, rol)
VALUES ('Carlos Ruiz', 'cruiz@rescata.pe', 'COORDINADOR');
INSERT INTO usuario (nombre_usuario, email, rol)
VALUES ('Ana Torres', 'atorres@rescata.pe', 'ADMINISTRADOR');

INSERT INTO distrito (nombre_distrito) VALUES ('Surco');
INSERT INTO distrito (nombre_distrito) VALUES ('Los Olivos');
INSERT INTO distrito (nombre_distrito) VALUES ('San Isidro');

INSERT INTO donante (nombre_donante, tipo_donante, direccion, id_distrito, telefono, email)
VALUES ('Supermercado Metro', 'SUPERMERCADO', 'Av. Primavera 1280', 1,
        '014567890', 'info@metro.com.pe');

INSERT INTO alimento (nombre_alimento, categoria, requiere_refrigeracion)
VALUES ('Pan', 'PERECIBLE', 0);
INSERT INTO alimento (nombre_alimento, categoria, requiere_refrigeracion)
VALUES ('Yogurt', 'PERECIBLE', 1);

INSERT INTO organizacion (nombre_organizacion, tipo_organizacion, direccion, id_distrito,
        capacidad_diaria_kg, tiene_refrigeracion, responsable, fecha_habilitacion, id_usuario_habilitador)
VALUES ('Olla Comun Los Olivos', 'OLLA_COMUN', 'Jr. Los Alamos 220', 2,
        40, 1, 'Rosa Fernandez', SYSDATE, 3);

INSERT INTO donacion (id_donante) VALUES (1);

-- fecha_vencimiento se calcula relativa a SYSDATE (no una fecha fija)
-- para que siempre sea posterior a fecha_donacion y el trigger
-- trg_detalle_venc_check no rechace estos datos de prueba.
INSERT INTO detalle_donacion (id_donacion, id_alimento, peso_kg,
        fecha_vencimiento, valor_estimado_soles)
VALUES (1, 1, 25.5, SYSDATE + 2, 180.00);

-- Con los triggers instalados (rescata_triggers_oracle.sql), este
-- INSERT por si solo ya actualiza detalle_donacion.estado_sanitario
-- y estado_disponibilidad a 'APTO' / 'DISPONIBLE'. No se requiere
-- ningun UPDATE manual despues de esto.
INSERT INTO inspeccion (id_detalle, id_usuario, resultado)
VALUES (1, 1, 'APTO');

-- El valor_total_soles se recalcula solo en el trigger (180.00
-- en este caso); el valor enviado aqui es referencial.
INSERT INTO certificado_donacion (id_donacion, id_usuario, nro_certificado, valor_total_soles)
VALUES (1, 3, 'CERT-2026-0001', 0);

INSERT INTO solicitud (id_organizacion, cantidad_requerida_kg, categoria_preferida)
VALUES (1, 20, 'PERECIBLE');

-- Este INSERT, con los triggers activos, ya deja el detalle en
-- 'ASIGNADO' y marca la solicitud como 'ATENDIDA' automaticamente.
INSERT INTO asignacion (id_detalle, id_solicitud, id_usuario, cantidad_asignada_kg)
VALUES (1, 1, 2, 20);

-- Este INSERT, con los triggers activos, ya deja el detalle en
-- 'ENTREGADO' automaticamente.
INSERT INTO entrega (id_asignacion, estado_conformidad, nombre_receptor)
VALUES (1, 'CONFORME', 'Rosa Fernandez');

COMMIT;

-- Verificacion rapida del resultado final (todo quedo automatico):
-- SELECT id_detalle, estado_sanitario, estado_disponibilidad FROM detalle_donacion;
-- SELECT id_solicitud, estado_solicitud FROM solicitud;
-- SELECT valor_total_soles FROM certificado_donacion;

-- =========================================================
-- DDL ALTER - Ejemplo de modificacion de esquema (Semana 6)
-- =========================================================

ALTER TABLE donante
    MODIFY (telefono VARCHAR2(30));

ALTER TABLE organizacion
    ADD (horario_atencion VARCHAR2(100));
