# Instalación

## Requisitos

| Requisito | Detalle |
|---|---|
| Python | **3.9 o superior** (probado con 3.10 y 3.13). Solo se usa la biblioteca estándar: **no hay que instalar paquetes**. |
| SQLite | Incluido con Python. `RIGHT JOIN` / `FULL OUTER JOIN` requieren SQLite ≥ 3.39; con una versión anterior la aplicación ejecuta la forma equivalente con `LEFT JOIN` y lo avisa en pantalla. |
| Navegador | Chrome, Edge o Firefox actuales |
| Opcional (solo prueba E2E) | Node.js 18+ y `playwright` |

## Pasos

```bash
git clone https://github.com/Rony-Grijalva/rescata-rescate-alimentos.git
cd rescata-rescate-alimentos
cp .env.example .env        # opcional: personalizar puerto, modo demo y clave de demostración
python3 backend/server.py   # Windows: py -3 backend\server.py  (o doble clic en run.bat)
```

Se abre el navegador en `http://127.0.0.1:8000`. En el primer arranque se crea `data/rescata.db` con el esquema, datos de ejemplo y cuentas de demostración.

Atajos: `./run.sh` (Linux/macOS) y `run.bat` (Windows). Para otro puerto: `python3 backend/server.py 8080`. Para no abrir el navegador: `--no-browser`.

## Variables de entorno

Se leen del entorno o de un archivo `.env` en la raíz (las variables ya definidas en el entorno tienen prioridad). Ver `.env.example`.

| Variable | Defecto | Descripción |
|---|---|---|
| `PORT` | `8000` | Puerto HTTP (si el puerto está ocupado, el servidor prueba el siguiente) |
| `RESCATA_DB` | `./data/rescata.db` | Ruta del archivo SQLite |
| `RESCATA_DEMO` | `1` | `0` oculta en el login la lista de cuentas de demostración |
| `RESCATA_DEMO_PASSWORD` | valor de demostración de `auth.py` | Contraseña inicial de las cuentas de ejemplo (solo al crearlas) |
| `RESCATA_VERBOSE` | vacío | Muestra las peticiones HTTP en consola |

## Verificación

```bash
python3 -m unittest discover -s tests -v     # 39 pruebas: reglas, roles y autenticación
```

Prueba E2E opcional con navegador real (login de cada rol, permisos, URL manipulada, bloqueo, responsive):

```bash
npm install playwright && npx playwright install chromium
RESCATA_DB=/tmp/e2e.db python3 backend/server.py 8123 --no-browser &
BASE_URL=http://localhost:8123 SHOTS=/tmp/shots node tests/e2e/e2e_playwright.js
```

## Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| «No se encontró Python 3» (Windows) | Instale Python desde python.org marcando *Add python.exe to PATH* |
| El navegador no abre | Visite manualmente `http://127.0.0.1:8000` |
| «No se pudo conectar con el servidor» en la página | El servidor se cerró; vuelva a ejecutarlo |
| Quiero empezar de cero | Cierre el servidor y borre `data/rescata.db`, o use **Reiniciar demo** como Coordinador |
