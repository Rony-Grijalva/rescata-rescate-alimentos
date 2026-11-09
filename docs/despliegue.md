# Despliegue

RESCATA está pensado para **demostración y uso local**. Esta guía cubre el despliegue en una máquina propia y las medidas mínimas si se quisiera exponer en una red.

## 1. Despliegue local (recomendado para la presentación)

1. Instale Python 3.9+ y clone el repositorio ([instalacion.md](instalacion.md)).
2. Copie `.env.example` a `.env` y defina `RESCATA_DEMO_PASSWORD` (clave de demostración propia).
3. Ejecute `python3 backend/server.py` (o `run.bat` / `run.sh`).
4. Entre como Coordinador, abra **Usuarios y accesos** y verifique las cuentas.

Los datos viven en `data/rescata.db`. Para respaldarlos basta copiar ese archivo con el servidor detenido (modo WAL: copie también `rescata.db-wal` si existe).

## 2. Actualizar una instalación existente

Reemplace las carpetas `backend/`, `frontend/`, `database/` conservando `data/`. Al arrancar, `auth.sql` se aplica de forma idempotente y migra bases creadas con versiones anteriores (crea `usuario` y `sesion` y las cuentas de demostración si faltan).

## 3. Exposición en una red (no recomendado sin estas medidas)

El servidor escucha solo en `127.0.0.1`. Si se necesitara acceso remoto:

* Colóquelo detrás de un **proxy inverso con HTTPS** (Nginx, Caddy…) y añada el atributo `Secure` a la cookie de sesión.
* Defina `RESCATA_DEMO=0` y cambie todas las contraseñas de demostración desde la aplicación.
* Añada límite de peticiones (el bloqueo actual es por cuenta, no por IP).
* Ejecute el proceso con un usuario sin privilegios y haga copias de seguridad de `data/`.
* Considere migrar a un motor cliente-servidor (el modelo original está en `database/oracle/`) si se esperan muchos usuarios simultáneos.

## 4. Lista de comprobación previa

- [ ] `python3 -m unittest discover -s tests` termina en `OK`
- [ ] `.env` no está versionado (`git status` no lo muestra)
- [ ] `RESCATA_DEMO` y contraseñas definidos según el entorno
- [ ] `data/` respaldada o ignorada según corresponda
