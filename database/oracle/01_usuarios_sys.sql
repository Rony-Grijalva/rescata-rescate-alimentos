-- =====================================================================
-- RESCATA - 3.er avance | Archivo 01: gestion de usuarios (parte A)
-- Ejecutar como SYS o SYSTEM. En Oracle XE 21c se trabaja en la PDB
-- XEPDB1, por eso los usuarios locales no llevan el prefijo C##.
-- Las contrasenas son marcadores: cambiarlas antes de ejecutar.
-- =====================================================================
ALTER SESSION SET CONTAINER = XEPDB1;

-- 1) Perfil: reglas de contrasena y de sesion para todos los usuarios
CREATE PROFILE perfil_rescata LIMIT
  FAILED_LOGIN_ATTEMPTS 5      -- bloquea la cuenta al quinto intento fallido
  PASSWORD_LOCK_TIME    1      -- dias de bloqueo
  PASSWORD_LIFE_TIME    90     -- la contrasena vence a los 90 dias
  SESSIONS_PER_USER     3
  IDLE_TIME             30;    -- minutos de inactividad

-- 2) Esquema propietario: es dueno de las 21 tablas
CREATE USER rescata IDENTIFIED BY "Cambiar#Owner26"
  DEFAULT TABLESPACE users
  TEMPORARY TABLESPACE temp
  QUOTA 200M ON users
  PROFILE perfil_rescata;

GRANT CREATE SESSION, CREATE TABLE, CREATE VIEW,
      CREATE PROCEDURE, CREATE SEQUENCE TO rescata;

-- 3) Roles por actor del sistema (los privilegios sobre objetos se
--    otorgan despues, en el archivo 08, cuando las tablas ya existen)
CREATE ROLE rol_rescata_admin;
CREATE ROLE rol_rescata_donante;
CREATE ROLE rol_rescata_organizacion;
CREATE ROLE rol_rescata_auditor;

GRANT CREATE SESSION TO rol_rescata_admin;
GRANT CREATE SESSION TO rol_rescata_donante;
GRANT CREATE SESSION TO rol_rescata_organizacion;
GRANT CREATE SESSION TO rol_rescata_auditor;

-- 4) Usuarios de demostracion (uno por rol)
CREATE USER usr_admin_demo IDENTIFIED BY "Cambiar#Adm26"
  DEFAULT TABLESPACE users QUOTA 0 ON users PROFILE perfil_rescata;
CREATE USER usr_donante_demo IDENTIFIED BY "Cambiar#Don26"
  DEFAULT TABLESPACE users QUOTA 0 ON users PROFILE perfil_rescata;
CREATE USER usr_org_demo IDENTIFIED BY "Cambiar#Org26"
  DEFAULT TABLESPACE users QUOTA 0 ON users PROFILE perfil_rescata;
CREATE USER usr_auditor_demo IDENTIFIED BY "Cambiar#Aud26"
  DEFAULT TABLESPACE users QUOTA 0 ON users PROFILE perfil_rescata;

GRANT rol_rescata_admin        TO usr_admin_demo;
GRANT rol_rescata_donante      TO usr_donante_demo;
GRANT rol_rescata_organizacion TO usr_org_demo;
GRANT rol_rescata_auditor      TO usr_auditor_demo;

-- 5) Administracion posterior (ALTER USER, como en la sesion de DDL
--    avanzado): cambio de clave, bloqueo, desbloqueo y expiracion
ALTER USER usr_auditor_demo ACCOUNT LOCK;
ALTER USER usr_auditor_demo ACCOUNT UNLOCK;
ALTER USER usr_org_demo     PASSWORD EXPIRE;   -- obliga a cambiarla al ingresar

-- 6) Consulta de control
SELECT username, account_status, profile
  FROM dba_users
 WHERE username IN ('RESCATA','USR_ADMIN_DEMO','USR_DONANTE_DEMO',
                    'USR_ORG_DEMO','USR_AUDITOR_DEMO')
 ORDER BY username;
