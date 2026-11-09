# Registro de avances

Proyecto **RESCATA** — curso Base de Datos 2 (UNMSM, Facultad de Ingeniería de Sistemas e Informática, 2026-II), docente Juan Tapia.

> **Sobre las fechas:** el historial de Git de este repositorio comienza en su publicación; el trabajo previo se desarrolló fuera de Git. Por eso las etapas se ordenan por la secuencia verificable de entregables (carpetas y archivos del repositorio) y **no se atribuyen fechas** que no consten.

## Resumen por etapa

| Etapa | Entregable | Evidencia en el repositorio | Estado |
|---|---|---|---|
| 1. Modelo de datos | Modelo relacional (21 tablas en los scripts Oracle; 22 en la aplicación al añadir `vehiculo`) | `database/oracle/02_base_rescata.sql`, `frontend/assets/modelo_22_*.png` | Completo |
| 2. Scripts Oracle 11g | Usuarios y perfiles, DDL, DDL II, datos DML, consultas y vistas, funciones, excepciones, cursores, records, colecciones, privilegios y pruebas | `database/oracle/01…09_*.sql`, `99_limpieza.sql`; capturas en `docs/evidencia-oracle/` | Completo |
| 3. Aplicación web | Aplicación ejecutable (Python + SQLite + JavaScript) con CRUD validado, reglas de negocio, 10 consultas JOIN, 17 pruebas de reglas, panel «SQL en vivo» y bitácora | `backend/`, `frontend/`, `database/schema.sql`, `seed.sql` | Completo |
| 4. Roles y ciclo completo | Menús y alcance por rol; estado de solicitud derivado; reparto, despacho con hitos y comprobante | `PERMISOS`, `Ctx` en `server.py`; `business.py`; `tests/test_roles.py` | Completo |
| 5. Seguridad e identidad visual | Autenticación con hash, sesiones, bloqueo, RBAC en backend y frontend, gestión de usuarios; ilustraciones SVG propias, animaciones y diseño responsive | `backend/auth.py`, `database/auth.sql`, `tests/test_auth.py`, `frontend/` | Completo |
| 6. Publicación | Documentación técnica, manual con capturas, configuración (`.env.example`), `.gitignore` | `docs/`, `README.md` | Completo |

## Módulos y estado

| Módulo | Roles | Estado | Verificación |
|---|---|---|---|
| Inicio de sesión / cierre / cambio de clave | Todos | Operativo | `test_auth.py`, E2E |
| Paneles con indicadores y gráficos | Todos | Operativo (datos reales por rol) | E2E |
| Lotes de alimentos (publicar, consultar, eliminar, líneas) | Coordinador, Donante, Organización | Operativo | `test_roles.py`, E2E |
| Solicitudes y reparto (asignar, sugerir, repartir equitativo) | Coordinador, Organización | Operativo | `test_rescata.py` |
| Logística (despachos, hitos, flota, personal) | Coordinador, Organización | Operativo | `test_rescata.py`, `test_roles.py` |
| Comprobantes (emisión única, verificación de monto) | Coordinador, Donante, Organización, Auditor | Operativo | `test_rescata.py` |
| Donantes, Organizaciones, Catálogos | Coordinador | Operativo | `test_rescata.py` |
| Usuarios y accesos | Coordinador | Operativo | `test_auth.py`, E2E |
| Consultas JOIN, Pruebas de reglas, Modelo de datos, Bitácora | Coordinador, Auditor | Operativo | `test_rescata.py`, E2E |

## Mejoras del frontend
* Interfaz de página única con menú lateral por rol, tarjetas de indicadores, gráficos SVG/CSS, tablas con búsqueda y orden, formularios con validación en línea y modales.
* Pantalla de ingreso con ilustración, panel de cuentas de demostración, mostrar/ocultar contraseña y mensajes claros.
* Banner ilustrado por rol, ilustración en tablas vacías; todas las imágenes son SVG propios (sin descargas ni CDN).
* Tema claro/oscuro, animaciones sutiles (respetan `prefers-reduced-motion`) y diseño adaptable a escritorio, tableta y celular.
* Aviso «Acceso denegado» al intentar abrir por URL una sección de otro rol.

## Integración con la base de datos
* Todos los módulos leen y escriben en SQLite; no hay datos estáticos simulados. Cada respuesta incluye las sentencias SQL ejecutadas (panel «SQL en vivo»).
* Transacciones manuales con `ROLLBACK` ante cualquier error; las restricciones de la base (PK, FK, UNIQUE, CHECK, disparador de saldo) se aplican aunque se omita la interfaz.
* Migración idempotente: `auth.sql` actualiza bases anteriores sin perder datos.

## Roles y seguridad
Autenticación PBKDF2-SHA256 con sal, sesiones por cookie HttpOnly con caducidad, bloqueo por intentos, RBAC y alcance por cuenta en el servidor, defensa CSRF por `Origin`, cabeceras CSP y consola SQL que no puede leer credenciales. Detalle en [seguridad.md](seguridad.md).

## Errores corregidos durante el desarrollo (verificados en las pruebas)
* Solicitud de ejemplo en estado ASIGNADA sin líneas → corregida en `seed.sql` y reflejada en el estado derivado.
* Los modales de programar/publicar refrescaban una lista desconectada por un re-render del `hash` → se usa `history.replaceState`.
* El panel mostraba el texto «null» en secciones vacías → se filtran los elementos nulos.
* Un `POST /api/sistema/reiniciar` de un rol sin permiso producía una excepción no controlada → ahora devuelve un error limpio.
* Error «cannot commit – no transaction is active» al cerrar sesión → un único `commit` tras resolver la sesión.
* La consola SQL podía leer tablas de credenciales → bloqueada con un *authorizer* de SQLite.
* Desborde horizontal en móvil y botón de menú visible en escritorio → corregidos en `styles.css`.

## Optimizaciones
* 13 índices sobre claves foráneas y campos de consulta; vistas para saldos, lotes disponibles y comprobantes valorizados.
* SQLite en modo WAL.

## Pruebas
* 39 pruebas automáticas (`python -m unittest discover -s tests`): reglas de negocio y flujo completo, permisos por rol y datos propios, autenticación y sesiones.
* Prueba E2E con navegador real (`tests/e2e/e2e_playwright.js`): login de cada rol, recorrido de todos los módulos, URL manipulada, API sin sesión, cierre de sesión, alta de cuenta, cambio de clave, bloqueo, responsive.

## Pendiente / mejoras futuras
* HTTPS y cookie `Secure` para uso en red; límite de peticiones por IP.
* Recuperación de contraseña por correo y autenticación de dos factores.
* Conexión directa a Oracle: hoy la aplicación usa SQLite y los scripts Oracle son independientes (traducción de las reglas a Python).
* Integración continua (CI) para ejecutar las pruebas en cada cambio.
* Reportes exportables (PDF/Excel) y notificaciones.
* Sustituir las ilustraciones vectoriales por fotografías propias si se desea.
* Definir una licencia para el repositorio.
