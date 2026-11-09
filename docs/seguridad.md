# Seguridad

Implementado en `backend/auth.py` y `backend/server.py`; verificado por `tests/test_auth.py`, `tests/test_roles.py` y la prueba E2E (`tests/e2e/`).

## Autenticación

| Aspecto | Implementación |
|---|---|
| Credenciales | Correo + contraseña por usuario (tabla `usuario`) |
| Almacenamiento | **PBKDF2-HMAC-SHA256**, 150 000 iteraciones, sal aleatoria de 16 bytes por usuario; formato `pbkdf2_sha256$iter$sal$hash`. Nunca texto plano. Comparación con `hmac.compare_digest`. |
| Política de contraseña | 8–128 caracteres, con letras y números |
| Sesión | Token `secrets.token_urlsafe(32)` en cookie `rescata_sid` (`HttpOnly; SameSite=Strict; Path=/`). En la base solo se guarda su **SHA-256** (`sesion.token_hash`). |
| Caducidad | 120 min de inactividad y 12 h en total; el cierre de sesión la elimina en el servidor |
| Fuerza bruta | Bloqueo de la cuenta 5 min tras 5 intentos fallidos; el coordinador puede desbloquear |
| Enumeración de usuarios | Mensaje único «Correo o contraseña incorrectos.»; para correos inexistentes se calcula un hash ficticio para igualar tiempos |
| Cambio de clave | Exige la actual y cierra las demás sesiones |

## Autorización (RBAC)

El rol y la cuenta se obtienen **siempre de la sesión del servidor**; las cabeceras o parámetros del cliente no se usan para decidirlos. Cada ruta declara `(recurso, acción)` y `need()` la valida antes de ejecutar (`403 ORA-01031`). Además, `Ctx` verifica la **propiedad** del registro (un donante solo toca sus lotes; una organización, sus solicitudes, despachos, vehículos y personal).

| Recurso | Coordinador | Donante | Organización | Auditor |
|---|---|---|---|---|
| dashboard, alertas | r c u d | r | r | r |
| lotes | rcud | rcd (propios) | r | — |
| solicitudes | rud | — | rcd (propias) | — |
| reparto (asignar/sugerir/repartir) | rcud | — | — | — |
| despachos, vehículos, personas | rcud | — | rcud (propios) | — |
| comprobantes | rcud | r (propios) | r (propios) | r |
| donantes, organizaciones, catálogos | rcud | — | organizaciones: r | — |
| perfil | — | ru | ru | — |
| consultas, pruebas, esquema | rcud | — | — | r |
| bitácora | r | — | — | r |
| usuarios, sistema (reiniciar) | rcud | — | — | — |

Fuente: diccionario `PERMISOS` en `backend/server.py`. El coordinador no crea solicitudes (las crea la organización).

**Frontend**: el menú se construye por rol y `route()` devuelve al panel con el aviso «Acceso denegado» si se escribe en la URL una sección no autorizada. Esto es solo comodidad: la barrera real es la del servidor.

## Otras protecciones

* **CSRF**: se rechazan peticiones no-GET cuyo `Origin` no coincide con el `Host`; la cookie es `SameSite=Strict`.
* **Cabeceras**: `Content-Security-Policy` (`default-src 'self'`; sin scripts externos), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`.
* **Entrada**: cuerpo máximo 1 MB; consultas parametrizadas; la consola SQL acepta una sola sentencia `SELECT`, usa un *authorizer* de SQLite y no puede leer `usuario` ni `sesion`.
* **Bitácora**: cada operación (incluidas las rechazadas) se registra con el rol y la cuenta.
* **Servidor local**: escucha solo en `127.0.0.1`.

## Cuentas de demostración y secretos

* Las cuentas de ejemplo se crean con la contraseña de `RESCATA_DEMO_PASSWORD` (valor por defecto de demostración definido en `auth.py`; cámbielo en `.env`). Con `RESCATA_DEMO=0` la pantalla de ingreso no las lista.
* El repositorio **no contiene** archivos `.env`, tokens, claves privadas ni bases de datos. `.gitignore` los excluye; `.env.example` solo documenta las variables.
* Los scripts Oracle incluyen contraseñas de ejemplo `Cambiar#…` que son marcadores para el laboratorio; deben cambiarse antes de cualquier uso real.

## Limitaciones conocidas

* HTTP sin cifrar: la cookie no lleva `Secure`. Para publicar en internet debe ir detrás de HTTPS (proxy inverso).
* El bloqueo es por cuenta, no por IP; no hay límite global de peticiones.
* No hay recuperación de contraseña por correo: la restablece el coordinador.
* No hay autenticación de dos factores.
