-- Elderly Wellbeing Monitor — Progress-1 schema (SQLite)

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    hashed_password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'caregiver',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS elderly_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    elderly_code TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    age INTEGER,
    notes TEXT,
    caregiver_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (caregiver_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS monitoring_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL UNIQUE,
    elderly_id INTEGER NOT NULL,
    caregiver_id INTEGER NOT NULL,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    FOREIGN KEY (elderly_id) REFERENCES elderly_profiles(id),
    FOREIGN KEY (caregiver_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS expression_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    elderly_id INTEGER NOT NULL,
    caregiver_id INTEGER NOT NULL,
    expression TEXT NOT NULL,
    confidence REAL NOT NULL,
    attention_indicator TEXT NOT NULL DEFAULT 'normal_observation',
    observed_at TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (elderly_id) REFERENCES elderly_profiles(id),
    FOREIGN KEY (caregiver_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    elderly_id INTEGER NOT NULL,
    caregiver_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    period_start TEXT,
    period_end TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (elderly_id) REFERENCES elderly_profiles(id),
    FOREIGN KEY (caregiver_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    detail TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_observations_session ON expression_observations(session_id);
CREATE INDEX IF NOT EXISTS idx_observations_elderly ON expression_observations(elderly_id);
CREATE INDEX IF NOT EXISTS idx_sessions_elderly ON monitoring_sessions(elderly_id);
