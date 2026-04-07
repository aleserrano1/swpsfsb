from database.connection import transaction

_TABLES = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS projects (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id           TEXT    UNIQUE NOT NULL,
    company              TEXT    NOT NULL,
    job_site             TEXT    NOT NULL DEFAULT '',
    tax_rate             REAL    NOT NULL DEFAULT 0,
    down_payment         REAL    NOT NULL DEFAULT 0,
    status               TEXT    NOT NULL DEFAULT 'non_binding',
    color_theme          TEXT    NOT NULL DEFAULT 'blue',
    proposal_description TEXT,
    proposal_note        TEXT,
    master_description   TEXT,
    master_note          TEXT,
    created_at           TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS clients (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS client_names (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    value     TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS client_emails (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    value     TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS client_phones (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    value     TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS client_addresses (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    value     TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS services (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    description TEXT    NOT NULL,
    amount      REAL    NOT NULL DEFAULT 0,
    type        TEXT    NOT NULL DEFAULT 'original_service',
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS payments (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id          INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    amount              REAL    NOT NULL DEFAULT 0,
    payment_type        TEXT    NOT NULL DEFAULT '',
    description         TEXT    NOT NULL DEFAULT '',
    check_number        TEXT,
    status              TEXT    NOT NULL DEFAULT 'unpaid',
    invoice_description TEXT,
    invoice_note        TEXT,
    created_at          TEXT    NOT NULL
);
"""


def initialize() -> None:
    """Create all tables if they don't exist."""
    with transaction() as cur:
        cur.executescript(_TABLES)
