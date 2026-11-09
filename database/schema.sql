-- =====================================================================
-- RESCATA - esquema fisico (22 tablas del modelo corregido + bitacora)
-- Motor: SQLite 3. Es la traduccion fiel del DDL Oracle de los archivos
-- 02 y 03 (incluye FK restituida, vehiculo, RUC, refrigeracion, monto).
-- =====================================================================
PRAGMA foreign_keys = ON;

CREATE TABLE distrito (
  id_distrito     INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre_distrito TEXT NOT NULL,
  provincia       TEXT NOT NULL DEFAULT 'LIMA',
  CONSTRAINT uq_distrito_prov_nombre UNIQUE (provincia, nombre_distrito)
);
CREATE TABLE zona (
  id_zona     INTEGER PRIMARY KEY AUTOINCREMENT,
  id_distrito INTEGER NOT NULL REFERENCES distrito(id_distrito),
  nombre_zona TEXT NOT NULL,
  CONSTRAINT uq_zona_distrito_nombre UNIQUE (id_distrito, nombre_zona)
);
CREATE TABLE estado_donante      (id_estado_donante      INTEGER PRIMARY KEY AUTOINCREMENT, estado TEXT NOT NULL UNIQUE);
CREATE TABLE estado_organizacion (id_estado_organizacion INTEGER PRIMARY KEY AUTOINCREMENT, estado TEXT NOT NULL UNIQUE);
CREATE TABLE estado_donacion_ofrecida (id_estado_donacion_ofrecida INTEGER PRIMARY KEY AUTOINCREMENT, estado TEXT NOT NULL UNIQUE);
CREATE TABLE estado_donacion     (id_estado_donacion     INTEGER PRIMARY KEY AUTOINCREMENT, estado TEXT NOT NULL UNIQUE);
CREATE TABLE tipo_organizacion   (id_tipo_organizacion   INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT NOT NULL UNIQUE);
CREATE TABLE tipo_documento      (id_tipo_documento      INTEGER PRIMARY KEY AUTOINCREMENT, tipo_doc TEXT NOT NULL UNIQUE);
CREATE TABLE unidad_medida       (id_unidad_medida       INTEGER PRIMARY KEY AUTOINCREMENT, tipo_medida TEXT NOT NULL UNIQUE);
CREATE TABLE categoria_alimento  (id_categoria_alimento  INTEGER PRIMARY KEY AUTOINCREMENT, nombre_categoria TEXT NOT NULL UNIQUE);

CREATE TABLE alimento (
  id_alimento            INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre_alimento        TEXT NOT NULL,
  id_categoria_alimento  INTEGER NOT NULL REFERENCES categoria_alimento(id_categoria_alimento),
  requiere_refrigeracion INTEGER NOT NULL DEFAULT 0,
  CONSTRAINT uq_alimento_nombre UNIQUE (nombre_alimento),
  CONSTRAINT ck_alimento_refrig CHECK (requiere_refrigeracion IN (0,1))
);
CREATE TABLE donante (
  id_donante        INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre_donante    TEXT NOT NULL,
  direccion         TEXT,
  id_zona           INTEGER REFERENCES zona(id_zona),
  telefono          TEXT,
  email             TEXT,
  id_estado_donante INTEGER NOT NULL REFERENCES estado_donante(id_estado_donante),
  ruc               TEXT,
  CONSTRAINT uq_donante_ruc UNIQUE (ruc),
  CONSTRAINT ck_donante_ruc CHECK (ruc IS NULL OR (length(ruc) = 11 AND ruc NOT GLOB '*[^0-9]*'))
);
CREATE TABLE organizacion (
  id_organizacion        INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre_organizacion    TEXT NOT NULL,
  direccion              TEXT,
  id_zona                INTEGER NOT NULL REFERENCES zona(id_zona),
  fecha_habilitacion     TEXT DEFAULT (date('now','localtime')),
  id_estado_organizacion INTEGER NOT NULL REFERENCES estado_organizacion(id_estado_organizacion),
  id_tipo_organizacion   INTEGER NOT NULL REFERENCES tipo_organizacion(id_tipo_organizacion),
  tiene_refrigeracion    INTEGER NOT NULL DEFAULT 0,
  CONSTRAINT ck_org_refrigeracion CHECK (tiene_refrigeracion IN (0,1))
);
CREATE TABLE persona_recojo (
  id_persona_recojo INTEGER PRIMARY KEY AUTOINCREMENT,
  id_organizacion   INTEGER NOT NULL REFERENCES organizacion(id_organizacion),
  nombres           TEXT NOT NULL,
  apellidos         TEXT NOT NULL,
  id_tipo_documento INTEGER NOT NULL REFERENCES tipo_documento(id_tipo_documento),
  num_documento     TEXT NOT NULL,
  sexo              TEXT,
  telefono          TEXT,
  email             TEXT,
  CONSTRAINT uq_persona_org_doc UNIQUE (id_organizacion, id_tipo_documento, num_documento),
  CONSTRAINT ck_persona_sexo CHECK (sexo IN ('M','F'))
);
CREATE TABLE vehiculo (
  id_vehiculo     INTEGER PRIMARY KEY AUTOINCREMENT,
  placa           TEXT NOT NULL,
  marca           TEXT,
  modelo          TEXT,
  capacidad_kg    REAL,
  id_organizacion INTEGER REFERENCES organizacion(id_organizacion),
  CONSTRAINT uq_vehiculo_placa UNIQUE (placa),
  CONSTRAINT ck_vehiculo_capacidad CHECK (capacidad_kg > 0)
);
CREATE TABLE donacion_ofrecida (
  id_donacion_ofrecida        INTEGER PRIMARY KEY AUTOINCREMENT,
  id_donante                  INTEGER NOT NULL REFERENCES donante(id_donante),
  fecha_publicacion           TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  id_estado_donacion_ofrecida INTEGER NOT NULL REFERENCES estado_donacion_ofrecida(id_estado_donacion_ofrecida),
  direccion                   TEXT,
  id_zona                     INTEGER NOT NULL REFERENCES zona(id_zona)
);
CREATE TABLE detalle_donacion_ofrecida (
  id_detalle_donacion_ofrecida INTEGER PRIMARY KEY AUTOINCREMENT,
  id_donacion_ofrecida         INTEGER NOT NULL REFERENCES donacion_ofrecida(id_donacion_ofrecida),
  id_alimento                  INTEGER NOT NULL REFERENCES alimento(id_alimento),
  marca                        TEXT,
  codigo_lote                  TEXT,
  fecha_vencimiento            TEXT NOT NULL,
  cantidad                     REAL NOT NULL,
  id_unidad_medida             INTEGER NOT NULL REFERENCES unidad_medida(id_unidad_medida),
  peso_total_kg                REAL,
  costo_unitario               REAL NOT NULL,
  CONSTRAINT ck_det_ofrecida_cant  CHECK (cantidad > 0),
  CONSTRAINT ck_det_ofrecida_costo CHECK (costo_unitario >= 0),
  CONSTRAINT ck_det_ofrecida_peso  CHECK (peso_total_kg > 0)
);
-- FK restituida (C0): una solicitud no puede apuntar a un lote inexistente
CREATE TABLE donacion_parcial (
  id_donacion_parcial  INTEGER PRIMARY KEY AUTOINCREMENT,
  id_donacion_ofrecida INTEGER NOT NULL
      CONSTRAINT fk_parcial_ofrecida REFERENCES donacion_ofrecida(id_donacion_ofrecida),
  id_organizacion      INTEGER NOT NULL REFERENCES organizacion(id_organizacion),
  fecha_solicitud      TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  id_estado_donacion   INTEGER NOT NULL REFERENCES estado_donacion(id_estado_donacion)
);
CREATE TABLE detalle_donacion_parcial (
  id_detalle_donacion_parcial  INTEGER PRIMARY KEY AUTOINCREMENT,
  id_donacion_parcial          INTEGER NOT NULL REFERENCES donacion_parcial(id_donacion_parcial),
  id_detalle_donacion_ofrecida INTEGER NOT NULL REFERENCES detalle_donacion_ofrecida(id_detalle_donacion_ofrecida),
  cantidad                     REAL NOT NULL,
  CONSTRAINT uq_det_parcial_linea UNIQUE (id_donacion_parcial, id_detalle_donacion_ofrecida),
  CONSTRAINT ck_det_parcial_cant CHECK (cantidad > 0)
);
CREATE TABLE despacho (
  id_despacho         INTEGER PRIMARY KEY AUTOINCREMENT,
  id_donacion_parcial INTEGER NOT NULL REFERENCES donacion_parcial(id_donacion_parcial),
  id_vehiculo         INTEGER NOT NULL REFERENCES vehiculo(id_vehiculo),
  fecha_programada    TEXT NOT NULL,
  fecha_llegada       TEXT,
  fecha_salida        TEXT,
  fecha_arribo        TEXT,
  CONSTRAINT ck_despacho_salida CHECK (fecha_salida >= fecha_llegada),
  CONSTRAINT ck_despacho_arribo CHECK (fecha_arribo >= fecha_salida)
);
CREATE TABLE despacho_responsable (
  id_despacho_responsable INTEGER PRIMARY KEY AUTOINCREMENT,
  id_despacho             INTEGER NOT NULL REFERENCES despacho(id_despacho),
  id_persona_recojo       INTEGER NOT NULL REFERENCES persona_recojo(id_persona_recojo),
  CONSTRAINT uq_despacho_persona UNIQUE (id_despacho, id_persona_recojo)
);
CREATE TABLE comprobante (
  id_comprobante      INTEGER PRIMARY KEY AUTOINCREMENT,
  id_donacion_parcial INTEGER NOT NULL,
  serie               TEXT NOT NULL,
  numero              INTEGER NOT NULL,
  fecha_emision       TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  monto_total         REAL,
  CONSTRAINT fk_comprobante_parcial FOREIGN KEY (id_donacion_parcial) REFERENCES donacion_parcial(id_donacion_parcial),
  CONSTRAINT uq_comprobante_donacion UNIQUE (id_donacion_parcial),
  CONSTRAINT uq_comprobante_serie_numero UNIQUE (serie, numero),
  CONSTRAINT ck_comprobante_monto CHECK (monto_total >= 0)
);

-- Indices sobre claves foraneas y sobre la consulta mas frecuente
CREATE INDEX ix_alimento_categoria ON alimento (id_categoria_alimento);
CREATE INDEX ix_donante_zona ON donante (id_zona);
CREATE INDEX ix_org_zona ON organizacion (id_zona);
CREATE INDEX ix_ofrecida_donante ON donacion_ofrecida (id_donante);
CREATE INDEX ix_ofrecida_estado_fecha ON donacion_ofrecida (id_estado_donacion_ofrecida, fecha_publicacion);
CREATE INDEX ix_detofr_lote ON detalle_donacion_ofrecida (id_donacion_ofrecida);
CREATE INDEX ix_detofr_alimento ON detalle_donacion_ofrecida (id_alimento);
CREATE INDEX ix_parcial_lote ON donacion_parcial (id_donacion_ofrecida);
CREATE INDEX ix_parcial_org ON donacion_parcial (id_organizacion);
CREATE INDEX ix_detparc_detofr ON detalle_donacion_parcial (id_detalle_donacion_ofrecida);
CREATE INDEX ix_despacho_parcial ON despacho (id_donacion_parcial);
CREATE INDEX ix_despacho_vehiculo ON despacho (id_vehiculo);
CREATE INDEX ix_vehiculo_org ON vehiculo (id_organizacion);

-- Defensa en profundidad: aunque se salte el procedimiento, la base rechaza
-- repartir mas de lo publicado (el modelo no tenia un CHECK para esto).
CREATE TRIGGER trg_det_parcial_saldo BEFORE INSERT ON detalle_donacion_parcial
BEGIN
  SELECT RAISE(ABORT, 'ORA-20001: saldo insuficiente (disparador trg_det_parcial_saldo)')
   WHERE NEW.cantidad > (SELECT saldo FROM v_saldo_linea
                          WHERE id_detalle_donacion_ofrecida = NEW.id_detalle_donacion_ofrecida);
END;

-- Vistas (archivo 05)
CREATE VIEW v_saldo_linea AS
SELECT l.id_detalle_donacion_ofrecida, l.id_donacion_ofrecida, l.id_alimento,
       l.cantidad AS cantidad_publicada,
       IFNULL(SUM(dd.cantidad), 0) AS cantidad_repartida,
       l.cantidad - IFNULL(SUM(dd.cantidad), 0) AS saldo
  FROM detalle_donacion_ofrecida l
  LEFT JOIN detalle_donacion_parcial dd ON dd.id_detalle_donacion_ofrecida = l.id_detalle_donacion_ofrecida
 GROUP BY l.id_detalle_donacion_ofrecida;

CREATE VIEW v_lotes_disponibles AS
SELECT l.id_donacion_ofrecida, don.nombre_donante, dis.nombre_distrito, z.nombre_zona,
       a.nombre_alimento, a.requiere_refrigeracion, m.tipo_medida, sl.saldo, det.costo_unitario,
       det.fecha_vencimiento, det.id_detalle_donacion_ofrecida,
       ROUND((julianday(det.fecha_vencimiento) - julianday('now','localtime')) * 24, 1) AS horas_para_vencer
  FROM donacion_ofrecida l
  JOIN estado_donacion_ofrecida s ON s.id_estado_donacion_ofrecida = l.id_estado_donacion_ofrecida
  JOIN donante don ON don.id_donante = l.id_donante
  JOIN zona z ON z.id_zona = l.id_zona
  JOIN distrito dis ON dis.id_distrito = z.id_distrito
  JOIN detalle_donacion_ofrecida det ON det.id_donacion_ofrecida = l.id_donacion_ofrecida
  JOIN alimento a ON a.id_alimento = det.id_alimento
  JOIN unidad_medida m ON m.id_unidad_medida = det.id_unidad_medida
  JOIN v_saldo_linea sl ON sl.id_detalle_donacion_ofrecida = det.id_detalle_donacion_ofrecida
 WHERE s.estado = 'PUBLICADO' AND sl.saldo > 0 AND det.fecha_vencimiento > datetime('now','localtime');

CREATE VIEW v_demanda_organizacion AS
SELECT o.id_organizacion, o.nombre_organizacion, e.estado AS estado_solicitud,
       COUNT(DISTINCT d.id_donacion_parcial) AS solicitudes,
       IFNULL(SUM(dd.cantidad * det.costo_unitario), 0) AS valor_repartido_soles
  FROM organizacion o
  JOIN donacion_parcial d ON d.id_organizacion = o.id_organizacion
  JOIN estado_donacion e ON e.id_estado_donacion = d.id_estado_donacion
  LEFT JOIN detalle_donacion_parcial dd ON dd.id_donacion_parcial = d.id_donacion_parcial
  LEFT JOIN detalle_donacion_ofrecida det ON det.id_detalle_donacion_ofrecida = dd.id_detalle_donacion_ofrecida
 GROUP BY o.id_organizacion, o.nombre_organizacion, e.estado;

CREATE VIEW v_comprobante_valorizado AS
SELECT c.id_comprobante, c.serie || '-' || printf('%08d', c.numero) AS comprobante, c.fecha_emision,
       don.nombre_donante, don.ruc, o.nombre_organizacion AS receptora,
       c.monto_total AS monto_emitido,
       (SELECT IFNULL(SUM(dd.cantidad * det.costo_unitario),0)
          FROM detalle_donacion_parcial dd
          JOIN detalle_donacion_ofrecida det ON det.id_detalle_donacion_ofrecida = dd.id_detalle_donacion_ofrecida
         WHERE dd.id_donacion_parcial = d.id_donacion_parcial) AS monto_recalculado,
       d.id_donacion_parcial
  FROM comprobante c
  JOIN donacion_parcial d ON d.id_donacion_parcial = c.id_donacion_parcial
  JOIN organizacion o ON o.id_organizacion = d.id_organizacion
  JOIN donacion_ofrecida l ON l.id_donacion_ofrecida = d.id_donacion_ofrecida
  JOIN donante don ON don.id_donante = l.id_donante;

-- Tabla de apoyo de la aplicacion (no pertenece a las 22): registro de operaciones
CREATE TABLE bitacora (
  id_bitacora INTEGER PRIMARY KEY AUTOINCREMENT,
  fecha       TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  rol         TEXT NOT NULL,
  accion      TEXT NOT NULL,
  entidad     TEXT NOT NULL,
  detalle     TEXT,
  resultado   TEXT NOT NULL DEFAULT 'OK'
);
