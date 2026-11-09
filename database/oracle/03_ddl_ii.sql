-- =====================================================================
-- RESCATA - 3.er avance | Archivo 03: DDL SQL II (ALTER, restricciones,
-- indices). Ejecutar como RESCATA, despues del archivo 02 y ANTES de
-- cargar datos (algunos NOT NULL fallarian con filas ya existentes).
-- =====================================================================

-- A) Ajustes al modelo detectados al revisar el script del 2.o entregable

-- A1. El diagrama y la lamina de oferta incluyen el RUC del donante,
--     pero la tabla no lo tenia. Es el dato que identifica al donante
--     en el comprobante.
ALTER TABLE donante ADD (ruc VARCHAR2(11));
ALTER TABLE donante ADD CONSTRAINT uq_donante_ruc UNIQUE (ruc);
ALTER TABLE donante ADD CONSTRAINT ck_donante_ruc
  CHECK (REGEXP_LIKE(ruc, '^[0-9]{11}$'));

-- A2. alimento.requiere_refrigeracion "condiciona a quien se puede
--     asignar", pero la organizacion no declaraba si tiene cadena de frio.
ALTER TABLE organizacion ADD (tiene_refrigeracion NUMBER(1) DEFAULT 0 NOT NULL);
ALTER TABLE organizacion ADD CONSTRAINT ck_org_refrigeracion
  CHECK (tiene_refrigeracion IN (0, 1));

-- A3. El matching es por cercania: lote y organizacion deben tener zona.
ALTER TABLE donacionLote  MODIFY (id_zona NOT NULL);
ALTER TABLE organizacion  MODIFY (id_zona NOT NULL);

-- A4. La Ley 30498 exige dejar constancia de la fecha de vencimiento.
ALTER TABLE donacionLoteDetalle MODIFY (fechaVencimiento NOT NULL);

-- A5. Un distrito se repite entre provincias: la unicidad es el par.
ALTER TABLE distrito DROP CONSTRAINT uq_distrito_nombre;
ALTER TABLE distrito ADD CONSTRAINT uq_distrito_prov_nombre
  UNIQUE (provincia, nombre_distrito);

-- A6. Comprobante: monto congelado al emitirse y un comprobante por
--     donacion. DECISION A RATIFICAR por el equipo (ver documento).
ALTER TABLE comprobante ADD (monto_total NUMBER(12,2));
ALTER TABLE comprobante ADD CONSTRAINT ck_comprobante_monto
  CHECK (monto_total >= 0);
ALTER TABLE comprobante ADD CONSTRAINT uq_comprobante_donacion
  UNIQUE (id_donacion);

-- B) Indices sobre claves foraneas (Oracle no los crea solo). Se omiten
--    las FK que ya quedan cubiertas por el primer campo de un UNIQUE:
--    zona.id_distrito, donacionDetalle.id_donacion,
--    personaRecojo.id_organizacion, detalleResponsableRecojo.id_despachoRecojo
--    y comprobante.id_donacion.
CREATE INDEX ix_alimento_categoria  ON alimento (id_categoria);
CREATE INDEX ix_donante_zona        ON donante (id_zona);
CREATE INDEX ix_donante_estado      ON donante (id_estadoDonante);
CREATE INDEX ix_org_zona            ON organizacion (id_zona);
CREATE INDEX ix_org_estado          ON organizacion (id_organizacionEstado);
CREATE INDEX ix_org_tipo            ON organizacion (id_organizacionTipo);
CREATE INDEX ix_lote_donante        ON donacionLote (id_donante);
CREATE INDEX ix_lote_zona           ON donacionLote (id_zona);
-- Consulta mas frecuente: lotes publicados, los mas recientes primero
CREATE INDEX ix_lote_estado_fecha   ON donacionLote (id_donacionLoteEstado, fechaPublicacion);
CREATE INDEX ix_lotedet_lote        ON donacionLoteDetalle (id_donacionLote);
CREATE INDEX ix_lotedet_alimento    ON donacionLoteDetalle (id_alimento);
CREATE INDEX ix_lotedet_medida      ON donacionLoteDetalle (id_medidaCantidad);
CREATE INDEX ix_donacion_lote       ON donacion (id_donacionLote);
CREATE INDEX ix_donacion_org        ON donacion (id_organizacion);
CREATE INDEX ix_donacion_estado     ON donacion (id_donacionEstado);
CREATE INDEX ix_dondet_lotedetalle  ON donacionDetalle (id_donacionLoteDetalle);
CREATE INDEX ix_persona_tipodoc     ON personaRecojo (id_tipoDocumento);
CREATE INDEX ix_despacho_donacion   ON despachoRecojo (id_donacion);
CREATE INDEX ix_detresp_persona     ON detalleResponsableRecojo (id_personaRecojo);

-- C) Demostracion de ALTER sobre una tabla temporal, para no tocar el
--    modelo: ADD, MODIFY, RENAME COLUMN, DROP COLUMN, RENAME TO.
--    Sintaxis Oracle (no MySQL): sin FIRST/AFTER y con parentesis.
CREATE TABLE tmp_demo_alter (
  id_demo NUMBER(10) PRIMARY KEY,
  nota    VARCHAR2(50)
);
ALTER TABLE tmp_demo_alter ADD (color VARCHAR2(30), detalle VARCHAR2(255));
ALTER TABLE tmp_demo_alter MODIFY (nota VARCHAR2(100) NOT NULL);
ALTER TABLE tmp_demo_alter RENAME COLUMN nota TO nota_demo;
ALTER TABLE tmp_demo_alter DROP COLUMN detalle;
ALTER TABLE tmp_demo_alter RENAME TO tmp_demo_alter2;
TRUNCATE TABLE tmp_demo_alter2;
DROP TABLE tmp_demo_alter2;
