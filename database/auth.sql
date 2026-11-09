-- Autenticacion: cuentas y sesiones (se ejecuta siempre; es idempotente)
CREATE TABLE IF NOT EXISTS usuario (
  id_usuario        INTEGER PRIMARY KEY AUTOINCREMENT,
  email             TEXT NOT NULL UNIQUE COLLATE NOCASE,
  nombre            TEXT NOT NULL,
  password_hash     TEXT NOT NULL,                      -- PBKDF2-HMAC-SHA256 con sal propia; nunca texto plano
  rol               TEXT NOT NULL CHECK (rol IN ('admin','donante','organizacion','auditor')),
  id_donante        INTEGER REFERENCES donante(id_donante) ON DELETE CASCADE,
  id_organizacion   INTEGER REFERENCES organizacion(id_organizacion) ON DELETE CASCADE,
  activo            INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
  intentos_fallidos INTEGER NOT NULL DEFAULT 0,
  bloqueado_hasta   TEXT,
  ultimo_acceso     TEXT,
  creado            TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  CHECK ((rol='donante' AND id_donante IS NOT NULL AND id_organizacion IS NULL)
      OR (rol='organizacion' AND id_organizacion IS NOT NULL AND id_donante IS NULL)
      OR (rol IN ('admin','auditor') AND id_donante IS NULL AND id_organizacion IS NULL))
);
CREATE TABLE IF NOT EXISTS sesion (
  token_hash       TEXT PRIMARY KEY,                    -- SHA-256 del token; el token real solo vive en la cookie
  id_usuario       INTEGER NOT NULL REFERENCES usuario(id_usuario) ON DELETE CASCADE,
  creada           TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  ultima_actividad TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  expira           TEXT NOT NULL
);
