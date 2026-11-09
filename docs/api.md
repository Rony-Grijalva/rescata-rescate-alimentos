# API REST

Base: `http://127.0.0.1:8000`. Todas las rutas `/api/*` devuelven JSON con el mismo formato:

```json
{ "ok": true,  "data": {…}, "mensaje": "Texto para el usuario", "sql": ["INSERT INTO …"] }
{ "ok": false, "error": { "code": "ORA-20001", "message": "Saldo insuficiente…", "fields": { "campo": "motivo" } } }
```

`sql` lista las sentencias que modificaron la base (se muestran en «SQL en vivo»). `fields` aparece en errores de validación (`422 VALIDACION`).

## Autenticación

Se usa una **cookie de sesión** `rescata_sid` (`HttpOnly; SameSite=Strict; Path=/`) emitida por `POST /api/auth/login`. El cliente no envía rol ni cuenta: el servidor los toma de la sesión. Las peticiones que no son `GET` con cabecera `Origin` distinta del `Host` se rechazan (`403 ORIGEN`).

| Método y ruta | Acceso | Cuerpo / respuesta |
|---|---|---|
| `POST /api/auth/login` | Público | `{email, password}` → `{rol, nombre}` y `Set-Cookie`. Error genérico «Correo o contraseña incorrectos.» (`AUTH`); bloqueo tras 5 fallos (`AUTH_BLOQUEO`, 429). |
| `GET /api/auth/demo` | Público | `{activo, password, cuentas:[{email,nombre,rol}]}`. Con `RESCATA_DEMO=0` devuelve `{activo:false, cuentas:[]}`. |
| `POST /api/auth/logout` | Sesión | Invalida la sesión en el servidor y borra la cookie. |
| `POST /api/auth/password` | Sesión | `{actual, nueva}`; cierra las demás sesiones del usuario. |
| `GET /api/me` | Sesión | `{rol, roles, permisos, actor, usuario:{nombre,email}, sqlite, motor_full_join}` |

## Códigos HTTP y de error

| HTTP | Código | Significado |
|---|---|---|
| 401 | `SESION` | Sin sesión, caducada o inválida |
| 401 / 403 / 422 | `AUTH` | Credenciales incorrectas (401), cuenta desactivada (403) o datos de ingreso incompletos (422) |
| 429 | `AUTH_BLOQUEO` | Cuenta bloqueada temporalmente por intentos fallidos |
| 403 | `ORA-01031` | El rol no tiene el privilegio o el registro es de otra cuenta |
| 403 | `ORIGEN` | Origen de la petición no permitido |
| 404 | `ORA-01403` / `ORA-20004` | El registro no existe |
| 409 | `ORA-200xx`, `ORA-00001`, `ORA-02292` | Regla de negocio o restricción violada |
| 422 | `VALIDACION`, `ORA-02290`, `ORA-01400`, `ORA-06502` | Datos inválidos |

## Endpoints por módulo

Columna **Permiso** = `recurso:acción` de la matriz `PERMISOS` (r leer, c crear, u modificar, d eliminar). Los roles que lo poseen se detallan en [seguridad.md](seguridad.md). «Alcance» indica el filtro por cuenta que aplica el servidor.

| Método y ruta | Permiso | Descripción |
|---|---|---|
| `GET /api/lookups` | dashboard:r | Listas para formularios (zonas, alimentos, unidades, donantes, organizaciones, vehículos, estados…) |
| `GET /api/dashboard` | dashboard:r | KPI, gráficos, tareas pendientes y alertas según el rol |
| `GET /api/alertas?horas=24` | alertas:r | Líneas que vencen en N horas con urgencia (`fn_urgencia`) |
| `GET /api/perfil` · `PUT /api/perfil` | perfil:r/u | Datos de la propia cuenta (donante u organización); solo campos permitidos |
| `GET /api/lotes?q=&estado=` | lotes:r | Lotes (donante: los suyos; organización: los publicados) |
| `GET /api/lotes/{id}` · `DELETE /api/lotes/{id}` | lotes:r/d | Detalle con líneas y saldos · eliminar (donante solo los suyos) |
| `POST /api/lotes` | lotes:c | Publica un lote con sus líneas en una transacción. Cuerpo: `{id_zona, direccion, lineas:[{id_alimento, cantidad, id_unidad_medida, peso_total_kg, costo_unitario, fecha_vencimiento, marca?, codigo_lote?}]}` (`id_donante` lo fija el servidor para un donante) |
| `POST /api/lotes/{id}/lineas` · `DELETE /api/lineas/{id}` | lotes:c/d | Agregar o quitar una línea (un lote conserva al menos una) |
| `POST /api/lotes/{id}/sugerir` | reparto:r | Organizaciones receptoras sugeridas (`sp_sugerir_receptoras`) |
| `POST /api/lotes/{id}/repartir` | reparto:u | Reparto equitativo entre solicitudes pendientes (`sp_repartir_equitativo`) |
| `GET /api/solicitudes?q=&estado=` | solicitudes:r | Solicitudes (organización: las suyas) |
| `POST /api/solicitudes` | solicitudes:c | `{id_donacion_ofrecida}`; la organización sale de la sesión |
| `GET /api/solicitudes/{id}` · `DELETE …` | solicitudes:r/d | Detalle (reparto, despacho, comprobante) · cancelar si aún no tiene alimentos asignados |
| `POST /api/solicitudes/{id}/asignar` | reparto:c | `{linea, cantidad}` → `sp_asignar_linea` |
| `DELETE /api/repartos/{id}` | reparto:d | Quita una línea asignada |
| `POST /api/solicitudes/{id}/comprobante` | comprobantes:c | Emite el comprobante (`sp_emitir_comprobante`) |
| `GET /api/despachos` · `POST /api/despachos` | despachos:r/c | Lista · programa `{id_donacion_parcial, id_vehiculo, fecha_programada?}` |
| `POST /api/despachos/{id}/hito` | despachos:u | `{hito: "llegada"\|"salida"\|"arribo"}` en ese orden |
| `POST /api/despachos/{id}/responsables` · `DELETE …/{persona}` | despachos:u | Asigna o retira personas de recojo `{id_persona_recojo}` |
| `DELETE /api/despachos/{id}` | despachos:d | Cancela un despacho no entregado |
| `GET /api/comprobantes` · `GET /api/comprobantes/{id}` | comprobantes:r | Lista y detalle (cada cuenta ve solo los suyos) |
| `GET /api/organizaciones/{id}/resumen` | organizaciones:r | `sp_resumen_organizacion` |
| `GET\|POST\|PUT\|DELETE /api/crud/{recurso}[/{id}]` | según recurso | CRUD genérico con validación: `donantes`, `organizaciones`, `personas`, `vehiculos`, `cat_distritos`, `cat_zonas`, `cat_categorias`, `cat_alimentos`, `cat_unidades`, `cat_tipos_org`, `cat_tipos_doc`. Búsqueda `?q=` y filtros `?f_campo=`. Una organización solo accede a sus `personas` y `vehiculos`. |
| `GET /api/consultas` · `POST /api/consultas/{J1..J10}/ejecutar` | consultas:r | Catálogo y ejecución de las 10 consultas JOIN |
| `POST /api/sql` | consultas:r | `{sql}` — consola de **solo lectura** (un único `SELECT`; no puede leer `usuario` ni `sesion`) |
| `GET /api/pruebas` · `POST /api/pruebas/{P1..P17}/ejecutar` | pruebas:r | Pruebas de reglas con `ROLLBACK` |
| `GET /api/esquema` | esquema:r | Tablas del modelo, columnas, FK y contenido (oculta `usuario` y `sesion`) |
| `GET /api/bitacora?limit=200` | bitacora:r | Bitácora de operaciones |
| `GET /api/usuarios` · `POST /api/usuarios` · `PUT /api/usuarios/{id}` | usuarios:r/c/u | Cuentas de acceso (solo Coordinador). `PUT` admite `{activo}`, `{password}`, `{desbloquear:true}` |
| `POST /api/sistema/reiniciar` | sistema:d | Restaura los datos de demostración (solo Coordinador) |

## Ejemplo

```bash
# iniciar sesión y guardar la cookie
curl -i -c cookies.txt -H 'Content-Type: application/json' \
     -d '{"email":"coordinador@rescata.pe","password":"<clave de demo>"}' http://127.0.0.1:8000/api/auth/login
# consultar con la sesión
curl -b cookies.txt http://127.0.0.1:8000/api/dashboard
# sin cookie → 401
curl -i http://127.0.0.1:8000/api/dashboard
```
