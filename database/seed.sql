-- Datos de demostracion (equivalentes al archivo 04 Oracle). Las fechas de
-- vencimiento son relativas al momento de la carga, como SYSDATE + n.
INSERT INTO distrito (nombre_distrito) VALUES ('Santiago de Surco'),('Cercado de Lima'),('Los Olivos'),('San Juan de Lurigancho'),('Miraflores');
INSERT INTO zona (id_distrito, nombre_zona) VALUES
 ((SELECT id_distrito FROM distrito WHERE nombre_distrito='Santiago de Surco'),'Monterrico'),
 ((SELECT id_distrito FROM distrito WHERE nombre_distrito='Cercado de Lima'),'Barrios Altos'),
 ((SELECT id_distrito FROM distrito WHERE nombre_distrito='Los Olivos'),'Villa Los Olivos'),
 ((SELECT id_distrito FROM distrito WHERE nombre_distrito='San Juan de Lurigancho'),'Canto Grande'),
 ((SELECT id_distrito FROM distrito WHERE nombre_distrito='Miraflores'),'Larco');
INSERT INTO estado_donante (estado) VALUES ('ACTIVO'),('INACTIVO');
INSERT INTO estado_organizacion (estado) VALUES ('HABILITADA'),('PENDIENTE'),('SUSPENDIDA');
INSERT INTO tipo_organizacion (tipo) VALUES ('Olla comun'),('Comedor popular'),('Albergue');
INSERT INTO estado_donacion_ofrecida (estado) VALUES ('PUBLICADO'),('ASIGNADO'),('CERRADO');
INSERT INTO estado_donacion (estado) VALUES ('PENDIENTE'),('ASIGNADA'),('ENTREGADA');
INSERT INTO tipo_documento (tipo_doc) VALUES ('DNI'),('CE');
INSERT INTO unidad_medida (tipo_medida) VALUES ('Unidad'),('Litro'),('Kilogramo'),('Porcion');
INSERT INTO categoria_alimento (nombre_categoria) VALUES ('Panaderia'),('Lacteos'),('Platos preparados'),('Pasteleria');
INSERT INTO alimento (nombre_alimento, id_categoria_alimento, requiere_refrigeracion)
SELECT n, (SELECT id_categoria_alimento FROM categoria_alimento WHERE nombre_categoria=c), r FROM (
 SELECT 'Pan de molde integral' n,'Panaderia' c,0 r UNION ALL SELECT 'Pan frances','Panaderia',0
 UNION ALL SELECT 'Leche UHT entera 1L','Lacteos',0 UNION ALL SELECT 'Yogur natural 1L','Lacteos',1
 UNION ALL SELECT 'Torta de chocolate','Pasteleria',1 UNION ALL SELECT 'Arroz con pollo (porcion)','Platos preparados',1
 UNION ALL SELECT 'Papa a la huancaina (porcion)','Platos preparados',1);
INSERT INTO donante (nombre_donante,direccion,id_zona,telefono,email,id_estado_donante,ruc)
SELECT n,d,(SELECT id_zona FROM zona WHERE nombre_zona=z),t,e,(SELECT id_estado_donante FROM estado_donante WHERE estado='ACTIVO'),r FROM (
 SELECT 'Supermercado Metro Surco' n,'Av. Primavera 1200' d,'Monterrico' z,'016187000' t,'donaciones@metro.example' e,'20100000011' r
 UNION ALL SELECT 'Panaderia La Union','Jr. Ancash 300','Barrios Altos','014211234','contacto@launion.example','20100000022'
 UNION ALL SELECT 'Restaurante El Fogon','Av. Carlos Izaguirre 500','Villa Los Olivos','012457788','gerencia@elfogon.example','20100000033'
 UNION ALL SELECT 'Bodega Don Pepe','Av. Larco 800','Larco','014445566','donpepe@bodega.example','20100000044');
INSERT INTO organizacion (nombre_organizacion,direccion,id_zona,id_estado_organizacion,id_tipo_organizacion,tiene_refrigeracion)
SELECT n,d,(SELECT id_zona FROM zona WHERE nombre_zona=z),(SELECT id_estado_organizacion FROM estado_organizacion WHERE estado='HABILITADA'),
       (SELECT id_tipo_organizacion FROM tipo_organizacion WHERE tipo=t),f FROM (
 SELECT 'Olla Comun Santa Rosa' n,'Mz. B Lt. 4' d,'Villa Los Olivos' z,'Olla comun' t,1 f
 UNION ALL SELECT 'Comedor Popular Las Flores','Jr. Huanta 150','Barrios Altos','Comedor popular',0
 UNION ALL SELECT 'Albergue Casa Hogar','Av. Next 1020','Canto Grande','Albergue',1
 UNION ALL SELECT 'Comedor Parroquial San Martin','Calle Los Pinos 45','Monterrico','Comedor popular',1);
INSERT INTO vehiculo (placa,marca,modelo,capacidad_kg,id_organizacion) VALUES
 ('TRI-001','Artesanal','Triciclo de carga',120,(SELECT id_organizacion FROM organizacion WHERE nombre_organizacion='Olla Comun Santa Rosa')),
 ('XYZ-789','Hyundai','H100',1000,(SELECT id_organizacion FROM organizacion WHERE nombre_organizacion='Albergue Casa Hogar')),
 ('KLM-456','Toyota','Hilux (voluntarios)',800,NULL),
 ('MOT-010','Honda','Moto de carga',10,NULL);
INSERT INTO persona_recojo (id_organizacion,nombres,apellidos,id_tipo_documento,num_documento,sexo,telefono) VALUES
 ((SELECT id_organizacion FROM organizacion WHERE nombre_organizacion='Olla Comun Santa Rosa'),'Rosa','Quispe Huaman',1,'40111222','F','987000111');

-- Lotes publicados (id fijos para enlazar el resto)
INSERT INTO donacion_ofrecida (id_donacion_ofrecida,id_donante,id_estado_donacion_ofrecida,direccion,id_zona,fecha_publicacion)
SELECT n, d.id_donante, 1, d.direccion, d.id_zona, datetime('now','localtime', m) FROM (
 SELECT 1 n,'Supermercado Metro Surco' nom,'-30 minutes' m UNION ALL SELECT 2,'Panaderia La Union','-20 minutes'
 UNION ALL SELECT 3,'Restaurante El Fogon','-10 minutes' UNION ALL SELECT 4,'Supermercado Metro Surco','-5 minutes') x
JOIN donante d ON d.nombre_donante = x.nom;
INSERT INTO detalle_donacion_ofrecida (id_donacion_ofrecida,id_alimento,cantidad,id_unidad_medida,peso_total_kg,costo_unitario,fecha_vencimiento,codigo_lote)
SELECT l,(SELECT id_alimento FROM alimento WHERE nombre_alimento=a),c,(SELECT id_unidad_medida FROM unidad_medida WHERE tipo_medida=u),p,k,datetime('now','localtime',v),cod FROM (
 SELECT 1 l,'Pan de molde integral' a,40 c,'Unidad' u,16 p,6.5 k,'+3 days' v,'PM-0926' cod
 UNION ALL SELECT 1,'Leche UHT entera 1L',60,'Litro',60,4.2,'+90 days','LU-1126'
 UNION ALL SELECT 2,'Pan frances',15,'Kilogramo',15,8,'+1 days','PF-0001'
 UNION ALL SELECT 2,'Torta de chocolate',3,'Unidad',4,45,'+2 days','TC-0002'
 UNION ALL SELECT 3,'Arroz con pollo (porcion)',25,'Porcion',10,12,'+6 hours','AP-0003'
 UNION ALL SELECT 3,'Papa a la huancaina (porcion)',25,'Porcion',8,7,'+10 hours','PH-0003'
 UNION ALL SELECT 4,'Yogur natural 1L',30,'Litro',30,5.8,'+7 days','YN-0004');

-- Solicitudes (donacion_parcial)
INSERT INTO donacion_parcial (id_donacion_parcial,id_donacion_ofrecida,id_organizacion,id_estado_donacion) VALUES
 (1,1,(SELECT id_organizacion FROM organizacion WHERE nombre_organizacion='Olla Comun Santa Rosa'),2),
 (2,2,(SELECT id_organizacion FROM organizacion WHERE nombre_organizacion='Comedor Popular Las Flores'),2),
 (3,3,(SELECT id_organizacion FROM organizacion WHERE nombre_organizacion='Olla Comun Santa Rosa'),1),
 (4,4,(SELECT id_organizacion FROM organizacion WHERE nombre_organizacion='Albergue Casa Hogar'),1);
-- Reparto acordado: la olla recibe 40 u de pan y 30 L de leche del lote 1; el comedor recibe 5 kg de pan frances del lote 2 (ASIGNADA exige reparto)
INSERT INTO detalle_donacion_parcial (id_donacion_parcial,id_detalle_donacion_ofrecida,cantidad) VALUES (1,1,40),(1,2,30),(2,3,5);
INSERT INTO despacho (id_donacion_parcial,id_vehiculo,fecha_programada)
 VALUES (1,(SELECT id_vehiculo FROM vehiculo WHERE placa='TRI-001'),datetime('now','localtime','+2 hours'));
INSERT INTO despacho_responsable (id_despacho,id_persona_recojo) VALUES (1,1);
INSERT INTO bitacora (rol,accion,entidad,detalle) VALUES ('admin','SEED','sistema','Datos de demostracion cargados');
