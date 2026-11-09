-- =====================================================================
-- RESCATA - Archivo 03: DDL SQL II (ALTER, restricciones, indices)
-- Ejecutar como RESCATA, despues del archivo 02 (modelo de Data Modeler
-- del 08/11/2026, 22 tablas) y ANTES de cargar datos.
-- =====================================================================

-- C0. Relacion faltante. donacion_parcial.id_donacion_ofrecida es NOT NULL
--     pero la clave foranea se habia eliminado en el diagrama: una solicitud
--     podia apuntar a un lote inexistente. Se restituye.
ALTER TABLE donacion_parcial ADD CONSTRAINT fk_parcial_ofrecida
  FOREIGN KEY (id_donacion_ofrecida) REFERENCES donacion_ofrecida (id_donacion_ofrecida);

-- A1. El RUC identifica al donante en el comprobante (estaba en el
--     diagrama y en la lamina de oferta, no en la tabla).
ALTER TABLE donante ADD (ruc VARCHAR2(11));
ALTER TABLE donante ADD CONSTRAINT uq_donante_ruc UNIQUE (ruc);
ALTER TABLE donante ADD CONSTRAINT ck_donante_ruc
  CHECK (REGEXP_LIKE(ruc, '^[0-9]{11}$'));

-- A2. alimento.requiere_refrigeracion condiciona a quien se puede asignar,
--     pero la organizacion no declaraba si tiene cadena de frio.
ALTER TABLE organizacion ADD (tiene_refrigeracion NUMBER(1) DEFAULT 0 NOT NULL);
ALTER TABLE organizacion ADD CONSTRAINT ck_org_refrigeracion
  CHECK (tiene_refrigeracion IN (0, 1));

-- A3. El emparejamiento es por cercania: lote y organizacion deben tener zona.
ALTER TABLE donacion_ofrecida MODIFY (id_zona NOT NULL);
ALTER TABLE organizacion      MODIFY (id_zona NOT NULL);

-- A4. La Ley 30498 exige dejar constancia de la fecha de vencimiento.
ALTER TABLE detalle_donacion_ofrecida MODIFY (fecha_vencimiento NOT NULL);

-- A5. Un nombre de distrito se repite entre provincias: la unicidad es el par.
ALTER TABLE distrito DROP CONSTRAINT uq_distrito_nombre;
ALTER TABLE distrito ADD CONSTRAINT uq_distrito_prov_nombre
  UNIQUE (provincia, nombre_distrito);

-- A6. Comprobante: monto congelado al emitirse. La restriccion UNIQUE por
--     donacion (uq_comprobante_donacion) ya existe en el modelo; no se repite.
ALTER TABLE comprobante ADD (monto_total NUMBER(12,2));
ALTER TABLE comprobante ADD CONSTRAINT ck_comprobante_monto
  CHECK (monto_total >= 0);

-- V1. Vehiculo: de quien es y que capacidad es valida. id_organizacion es
--     opcional (hay vehiculos de voluntarios que no pertenecen a ninguna).
ALTER TABLE vehiculo ADD (id_organizacion NUMBER(10));
ALTER TABLE vehiculo ADD CONSTRAINT fk_vehiculo_organizacion
  FOREIGN KEY (id_organizacion) REFERENCES organizacion (id_organizacion);
ALTER TABLE vehiculo ADD CONSTRAINT ck_vehiculo_capacidad
  CHECK (capacidad_kg > 0);

-- B) Indices sobre claves foraneas (Oracle no los crea solo). Se omiten
--    las FK que ya quedan cubiertas por el primer campo de un UNIQUE:
--    zona.id_distrito, comprobante.id_donacion_parcial,
--    detalle_donacion_parcial.id_donacion_parcial,
--    persona_recojo.id_organizacion y despacho_responsable.id_despacho.
CREATE INDEX ix_alimento_categoria ON alimento (id_categoria_alimento);
CREATE INDEX ix_donante_zona       ON donante (id_zona);
CREATE INDEX ix_donante_estado     ON donante (id_estado_donante);
CREATE INDEX ix_org_zona           ON organizacion (id_zona);
CREATE INDEX ix_org_estado         ON organizacion (id_estado_organizacion);
CREATE INDEX ix_org_tipo           ON organizacion (id_tipo_organizacion);
CREATE INDEX ix_ofrecida_donante   ON donacion_ofrecida (id_donante);
CREATE INDEX ix_ofrecida_zona      ON donacion_ofrecida (id_zona);
-- Consulta mas frecuente: lotes publicados, los mas recientes primero
CREATE INDEX ix_ofrecida_estado_fecha ON donacion_ofrecida (id_estado_donacion_ofrecida, fecha_publicacion);
CREATE INDEX ix_detofr_lote        ON detalle_donacion_ofrecida (id_donacion_ofrecida);
CREATE INDEX ix_detofr_alimento    ON detalle_donacion_ofrecida (id_alimento);
CREATE INDEX ix_detofr_medida      ON detalle_donacion_ofrecida (id_unidad_medida);
CREATE INDEX ix_parcial_lote       ON donacion_parcial (id_donacion_ofrecida);
CREATE INDEX ix_parcial_org        ON donacion_parcial (id_organizacion);
CREATE INDEX ix_parcial_estado     ON donacion_parcial (id_estado_donacion);
CREATE INDEX ix_detparc_detofr     ON detalle_donacion_parcial (id_detalle_donacion_ofrecida);
CREATE INDEX ix_persona_tipodoc    ON persona_recojo (id_tipo_documento);
CREATE INDEX ix_despacho_parcial   ON despacho (id_donacion_parcial);
CREATE INDEX ix_despacho_vehiculo  ON despacho (id_vehiculo);
CREATE INDEX ix_resp_persona       ON despacho_responsable (id_persona_recojo);
CREATE INDEX ix_vehiculo_org       ON vehiculo (id_organizacion);

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
