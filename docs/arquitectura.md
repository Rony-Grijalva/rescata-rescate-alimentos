# Arquitectura

RESCATA es una aplicación web de **tres capas** que se ejecuta con un único proceso Python y sin dependencias externas.

```
┌──────────────────────────┐   HTTP + JSON    ┌───────────────────────────────┐   SQL    ┌──────────────┐
│ Navegador (SPA)          │ ───────────────▶ │ Servidor Python (stdlib)      │ ───────▶ │ SQLite       │
│ HTML + CSS + JS (módulos │ ◀─────────────── │ http.server.ThreadingHTTPServer│ ◀─────── │ data/rescata │
│ ES, sin frameworks)      │  cookie de sesión│ auth · RBAC · reglas · CRUD   │          │ .db (WAL)    │
└──────────────────────────┘                  └───────────────────────────────┘          └──────────────┘
```

## Componentes

| Capa | Ubicación | Responsabilidad |
|---|---|---|
| Presentación | `frontend/` | Página única (`index.html`), módulos ES6 por pantalla (`js/pages/*.js`), menú por rol, gráficos en SVG/CSS, ilustraciones SVG propias (`assets/img/`). No usa CDN ni librerías. |
| API y seguridad | `backend/server.py`, `backend/auth.py` | Enrutado REST (`ROUTES`), autenticación por cookie, matriz de permisos `PERMISOS`, alcance por cuenta (`Ctx`), cabeceras de seguridad, entrega de archivos estáticos. |
| Reglas de negocio | `backend/business.py`, `backend/reglas.py` | Equivalentes en Python de los procedimientos/funciones PL/SQL del proyecto Oracle (`sp_asignar_linea`, `sp_programar_despacho`, `sp_emitir_comprobante`, `fn_saldo_linea`, …) y 17 pruebas de reglas ejecutables con `ROLLBACK`. |
| Acceso a datos | `backend/database.py`, `backend/crud.py`, `backend/services.py`, `backend/queries.py` | Conexión SQLite, transacciones manuales, CRUD genérico con validación, consultas de paneles, 10 consultas JOIN y consola SQL de solo lectura. |
| Base de datos | `database/*.sql` | `schema.sql` (modelo), `seed.sql` (datos de ejemplo), `auth.sql` (usuarios y sesiones). |
| Referencia Oracle | `database/oracle/` | Scripts Oracle 11g originales del curso (DDL, triggers, procedimientos, privilegios, pruebas). |

## Flujo de una petición

1. El navegador envía `fetch('/api/...')` con la cookie `rescata_sid` (HttpOnly).
2. `Handler._api` verifica el `Origin` (defensa CSRF), lee el cuerpo (máx. 1 MB) y llama a `entrada()`.
3. `entrada()` resuelve la sesión (`auth.resolver`) → si no es válida responde `401 SESION`.
4. `dispatch()` busca la ruta, aplica `need(rol, recurso, acción)` (→ `403 ORA-01031` si falta permiso) y construye un `Ctx` con el rol y la cuenta **de la sesión**.
5. El manejador ejecuta la operación dentro de **una transacción**; si ocurre un error de regla o de restricción se hace `ROLLBACK`, se traduce el error a un código estilo Oracle (`ORA-200xx`, `ORA-02290`…) y se registra en la bitácora.
6. La respuesta tiene siempre el formato `{ok, data, mensaje, sql[], error{code,message,fields}}`. El arreglo `sql` alimenta el panel «SQL en vivo» del coordinador.

## Decisiones de diseño

* **Integridad en la base de datos**: PK, FK, UNIQUE, CHECK y un disparador (`trg_det_parcial_saldo`) viven en SQLite y se aplican aunque se evite la interfaz. Las reglas que en Oracle serían PL/SQL están en `business.py`.
* **Estado derivado**: el estado de una solicitud (PENDIENTE → ASIGNADA → ENTREGADA) lo calcula el sistema a partir del reparto y del despacho (`sincronizar_estado_solicitud`); nadie lo cambia a mano.
* **Sin dependencias**: solo biblioteca estándar de Python 3 y JavaScript nativo; instalar = descomprimir.
* **Inicialización idempotente**: `init_db` crea el esquema y datos de ejemplo si la base está vacía y siempre aplica `auth.sql` (migra bases anteriores).
