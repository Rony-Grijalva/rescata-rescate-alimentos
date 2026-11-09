# Manual de usuario

RESCATA conecta a **donantes** (comercios con excedentes), **organizaciones receptoras** (ollas comunes, comedores, albergues) y un **coordinador** que reparte los alimentos y emite las constancias. Un **auditor** revisa todo en modo lectura.

> Las capturas son del sistema real en ejecución con los datos de ejemplo.

## 1. Cómo entrar

1. Abra `http://127.0.0.1:8000` en el navegador.
2. Escriba su **correo** y su **contraseña** y pulse **Ingresar**. El icono del ojo muestra u oculta la contraseña.
3. En modo demostración, la lista «Cuentas de demostración» rellena el formulario con un toque.

![Pantalla de inicio de sesión](img/login.png)

Si se equivoca, aparece un mensaje claro. Tras **5 intentos fallidos** la cuenta se bloquea **5 minutos** (el coordinador puede desbloquearla).

![Error de credenciales](img/login-error.png)

### Menú de usuario, cambio de contraseña y salida
Pulse su nombre (arriba a la derecha): **Cambiar contraseña** (pide la actual y una nueva de 8+ caracteres con letras y números) o **Cerrar sesión**. La sesión también se cierra sola tras 2 horas sin actividad; verá el aviso y volverá al ingreso.

![Menú de usuario](img/menu-usuario.png)

### Qué ve cada rol
Cada persona ve solo su menú. Si escribe en la barra de direcciones una sección que no es de su rol, el sistema lo devuelve a su panel con el aviso **«Acceso denegado»**.

![Acceso denegado](img/acceso-denegado.png)

| Rol | Menú |
|---|---|
| Coordinador | Panel · Lotes de alimentos · Solicitudes y reparto · Logística · Comprobantes · Donantes · Organizaciones · Catálogos · Usuarios y accesos · Consultas JOIN · Pruebas de reglas · Modelo de datos · Bitácora |
| Donante | Inicio · Mis lotes · Mis constancias · Mi perfil |
| Organización | Inicio · Lotes disponibles · Mis solicitudes · Mis despachos · Constancias recibidas · Mi organización |
| Auditor | Panel de auditoría · Comprobantes · Consultas JOIN · Pruebas de reglas · Modelo de datos · Bitácora |

**El ciclo completo:** el donante *publica un lote* → la organización lo *solicita* → el coordinador *asigna alimentos* (la solicitud pasa sola a ASIGNADA) → la organización *programa el recojo* y registra llegada, salida y entrega (pasa sola a ENTREGADA) → el coordinador *emite el comprobante* → donante y organización ven su constancia.

Mensajes: las acciones correctas muestran un aviso verde («Operación exitosa»). Los errores muestran un aviso rojo con un código (p. ej. `ORA-20001`) y la explicación; no se pierde nada porque cada operación se deshace completa si falla.

---

## 2. Donante

### Inicio
Resumen de lo que ha donado: lotes vigentes, kilos ofrecidos y entregados, solicitudes en curso, monto donado con constancia y alimentos por vencer en 24 h.

![Inicio del donante](img/donante-panel.png)

### Mis lotes
Lista **solo sus lotes**, con estado (PUBLICADO, ASIGNADO, CERRADO), saldo y quién los pidió.

![Mis lotes](img/donante-lotes.png)

**Publicar un lote**
1. Pulse **Publicar lote** (la zona y la dirección se proponen desde su perfil; puede cambiarlas).
2. En **Alimentos del lote** elija alimento, cantidad, unidad, peso (kg), costo unitario (S/) y fecha de vencimiento. **Agregar alimento** añade más líneas; el icono de papelera quita una.
3. Pulse **Publicar lote**. El lote y todas sus líneas se guardan juntos o no se guarda nada.

![Publicar lote](img/donante-publicar-lote.png)

**Consultar / eliminar**: el ojo muestra el detalle y las solicitudes; la papelera elimina el lote (solo si ninguna organización lo ha solicitado; si no, `ORA-02292`). Un lote conserva siempre al menos una línea.

### Mis constancias
Constancias de donación emitidas por el coordinador para sus entregas (con el monto). Use el ojo para verla e imprimirla.

![Mis constancias](img/donante-constancias.png)

### Mi perfil
Edite nombre o razón social, zona, dirección, teléfono y correo, y pulse **Guardar cambios**. El RUC y el estado los administra el coordinador.

![Mi perfil](img/donante-perfil.png)

---

## 3. Organización receptora

### Inicio
Qué puede pedir y qué tiene pendiente (tareas con enlace directo).

![Inicio de la organización](img/org-panel.png)

### Lotes disponibles
Lotes publicados con saldo. Use el ojo para ver qué alimentos trae y **Solicitar** para pedirlo (se pide confirmación). Un alimento que requiere frío (❄) solo se le asignará si su organización cuenta con refrigeración.

![Lotes disponibles](img/org-lotes.png)

### Mis solicitudes
Cada pedido con su estado y el **«Siguiente paso»**:
* **PENDIENTE**: espera que el coordinador asigne alimentos (puede cancelarla con la papelera).
* **ASIGNADA**: use **Programar recojo**.
* **ENTREGADA**: ya tiene constancia.

![Mis solicitudes](img/org-solicitudes.png)

### Mis despachos
Tres pestañas: **Mis despachos**, **Mi flota** y **Mi personal de recojo**.

![Mis despachos](img/org-despachos.png)

**Programar un recojo**
1. En *Mis solicitudes* pulse **Programar recojo** (o **Programar despacho** aquí) y elija el vehículo (su capacidad debe alcanzar para la carga; si no, verá `ORA-20008`).
2. En el despacho registre en orden **Llegada al recojo → Salida → Entrega**. Al registrar la entrega la solicitud pasa a ENTREGADA.
3. En el despacho, el botón **Asignar** (junto a «Responsables de recojo») designa personas de su personal autorizado.

**Flota y personal**: en las pestañas *Mi flota* y *Mi personal de recojo* puede **crear, editar y eliminar** sus vehículos (placa única, capacidad en kg) y sus personas (documento único por tipo).

### Constancias recibidas y Mi organización
*Constancias recibidas*: comprobantes de lo recibido. *Mi organización*: edite dirección y zona y marque si **cuenta con refrigeración** (determina si puede recibir alimentos perecibles).

![Constancias recibidas](img/org-constancias.png)
![Mi organización](img/org-perfil.png)

---

## 4. Coordinador

### Panel del coordinador
Tareas que requieren atención (solicitudes por repartir, asignadas sin despacho), indicadores, el **ciclo del rescate** con datos en vivo y alertas de vencimiento.

![Panel del coordinador](img/admin-panel.png)

### Lotes de alimentos
Todos los lotes. Acciones por lote: **ver detalle**, **sugerir receptoras cercanas**, **repartir equitativamente** entre solicitudes pendientes y eliminar.

![Lotes](img/admin-lotes.png)

### Solicitudes y reparto
Pulse la mano (*Gestionar el reparto*) para abrir la solicitud: elija la **línea del lote** y la **cantidad**, y pulse **Asignar**. El sistema propone el saldo disponible y rechaza lo que no se puede (saldo insuficiente `ORA-20001`, alimento con frío para una organización sin refrigeración `ORA-20002`). La papelera de una fila del reparto lo quita.

![Solicitudes](img/admin-solicitudes.png)
![Gestión del reparto](img/admin-reparto.png)

### Logística
Supervisa despachos, vehículos y personas de todas las organizaciones.

![Logística](img/admin-logistica.png)

### Comprobantes
Lista las **entregas pendientes de comprobante** con el botón **Emitir** y los comprobantes emitidos, con verificación de que el **monto emitido coincide con el recalculado**. Solo se emite si la entrega está ENTREGADA y una sola vez (`ORA-20006`, `ORA-20007`).

![Comprobantes](img/admin-comprobantes.png)

### Donantes y Organizaciones
Altas, ediciones y bajas con validación (RUC de 11 dígitos, correo, zona). No se elimina un registro que ya tiene datos asociados (`ORA-02292`).

![Donantes](img/admin-donantes.png)
![Organizaciones](img/admin-organizaciones.png)

### Catálogos
Pestañas para mantener alimentos, categorías, zonas, distritos, unidades y tipos.

### Usuarios y accesos
Gestione las cuentas de ingreso: **Nueva cuenta** (rol, nombre, correo, contraseña inicial y, si es donante u organización, la entidad vinculada), **restablecer contraseña**, **activar/desactivar** y **desbloquear**. No puede desactivar su propia cuenta.

![Usuarios y accesos](img/admin-usuarios.png)
![Nueva cuenta](img/admin-nueva-cuenta.png)

### SQL en vivo y reinicio
El botón **SQL en vivo** abre un panel con los `INSERT/UPDATE/DELETE` reales que ejecuta cada acción. **Reiniciar demo** restaura los datos de ejemplo (pide confirmación; conserva su sesión).

![SQL en vivo](img/admin-sql-en-vivo.png)

---

## 5. Auditor (solo lectura)

Panel de auditoría y **Comprobantes** para verificar montos. No ve botones de escritura.

![Panel del auditor](img/auditor-panel.png)
![Comprobantes del auditor](img/auditor-comprobantes.png)

### Laboratorio de base de datos (Auditor y Coordinador)
* **Consultas JOIN**: 10 consultas (INNER, LEFT, RIGHT, FULL, CROSS, SELF y USING) sobre los datos reales; **Ejecutar consulta** muestra el SQL, el resultado y una consola de solo lectura.
* **Pruebas de reglas**: 17 pruebas de restricciones y reglas de negocio; **Ejecutar las 17 pruebas** (cada una termina en `ROLLBACK`).
* **Modelo de datos**: diagrama de las 22 tablas y explorador de la base real (columnas, claves, filas).
* **Bitácora**: registro de operaciones, incluidas las rechazadas.

![Consultas JOIN](img/lab-consultas.png)
![Pruebas de reglas](img/lab-pruebas.png)
![Modelo de datos](img/lab-modelo.png)
![Bitácora](img/lab-bitacora.png)

---

## 6. Uso en celular y tableta

La interfaz se adapta al ancho de pantalla: en celular el menú se abre con el botón de las tres rayas.

| Panel | Menú |
|---|---|
| ![](img/movil-panel.png) | ![](img/movil-menu.png) |

## 7. Preguntas frecuentes

| Situación | Qué hacer |
|---|---|
| «Su sesión no es válida o expiró» | Inicie sesión de nuevo |
| «Cuenta bloqueada temporalmente» | Espere 5 minutos o pida al coordinador que la desbloquee |
| No veo una opción del menú | Su rol no la incluye (por diseño) |
| `ORA-20001` Saldo insuficiente | Pida o asigne una cantidad menor o igual al saldo |
| `ORA-20008` Capacidad insuficiente | Use un vehículo de mayor capacidad |
| Olvidé mi contraseña | Pida al coordinador que la restablezca en *Usuarios y accesos* |
