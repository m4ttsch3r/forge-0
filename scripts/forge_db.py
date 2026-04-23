"""forge_db.py — SQLite session + knowledge store for Forge-0.

Public API
----------
get_connection()        -> sqlite3.Connection
init_db()               -> None  (creates schema in current DB_PATH)
register_project(...)   -> int
update_project(...)     -> bool
list_projects(...)      -> list[dict]
log_decision(...)       -> int
get_decisions(...)      -> list[dict]
index_file(...)         -> int
search(...)             -> list[dict]
purge_knowledge(...)    -> int
"""

import hashlib
import pathlib
import sqlite3
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Module-level DB path — tests override this attribute directly.
# ---------------------------------------------------------------------------
DB_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent / "data" / "forge.db"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
_SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sub_projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    path        TEXT,
    description TEXT,
    status      TEXT NOT NULL DEFAULT 'active'
                CHECK(status IN ('bootstrapping','active','archived')),
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS decisions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    agent          TEXT NOT NULL,
    decision       TEXT NOT NULL,
    rationale      TEXT,
    sub_project_id INTEGER REFERENCES sub_projects(id) ON DELETE SET NULL,
    issue_ref      TEXT
);

CREATE TABLE IF NOT EXISTS indexed_files (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    path            TEXT NOT NULL UNIQUE,
    content_hash    TEXT NOT NULL,
    sub_project_id  INTEGER REFERENCES sub_projects(id) ON DELETE SET NULL,
    doc_type        TEXT NOT NULL DEFAULT 'other'
                    CHECK(doc_type IN ('readme','skill','log','doc','code','other')),
    last_indexed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_index USING fts5(
    file_id    UNINDEXED,
    path       UNINDEXED,
    sub_project UNINDEXED,
    doc_type   UNINDEXED,
    content,
    tokenize='porter unicode61'
);
"""


def _init_schema(conn: sqlite3.Connection) -> None:
    """Create all tables if they don't exist."""
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_SCHEMA_SQL)
    conn.commit()


def init_db() -> None:
    """Initialise the schema at the current DB_PATH. Called after tests override DB_PATH."""
    conn = get_connection()
    conn.close()


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------
def get_connection() -> sqlite3.Connection:
    """Open a connection to DB_PATH, initialise the schema, and return it."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    _init_schema(conn)
    return conn


# ---------------------------------------------------------------------------
# sub_projects
# ---------------------------------------------------------------------------
def register_project(
    name: str,
    path: str = None,
    description: str = None,
    status: str = "active",
) -> int:
    """UPSERT a project by name. Returns the project id."""
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO sub_projects (name, path, description, status)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                path        = excluded.path,
                description = excluded.description,
                status      = excluded.status,
                updated_at  = datetime('now')
            """,
            (name, path, description, status),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id FROM sub_projects WHERE name = ?", (name,)
        ).fetchone()
        return row["id"]
    finally:
        conn.close()


def update_project(
    name: str,
    status: str = None,
    description: str = None,
    path: str = None,
) -> bool:
    """Update fields on a named project. Returns True if the project existed."""
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM sub_projects WHERE name = ?", (name,)
        ).fetchone()
        if existing is None:
            return False

        fields = []
        values = []
        if status is not None:
            fields.append("status = ?")
            values.append(status)
        if description is not None:
            fields.append("description = ?")
            values.append(description)
        if path is not None:
            fields.append("path = ?")
            values.append(path)
        fields.append("updated_at = datetime('now')")

        if fields:
            sql = f"UPDATE sub_projects SET {', '.join(fields)} WHERE name = ?"
            values.append(name)
            conn.execute(sql, values)
            conn.commit()
        return True
    finally:
        conn.close()


def list_projects(status: str = None) -> list:
    """Return list of project dicts, optionally filtered by status."""
    conn = get_connection()
    try:
        if status is not None:
            rows = conn.execute(
                "SELECT * FROM sub_projects WHERE status = ?", (status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM sub_projects").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# decisions
# ---------------------------------------------------------------------------
def log_decision(
    agent: str,
    decision: str,
    rationale: str = None,
    sub_project: str = None,
    issue_ref: str = None,
) -> int:
    """Insert a decision record. Resolves sub_project name → id. Returns decision id."""
    conn = get_connection()
    try:
        sub_project_id = None
        if sub_project is not None:
            row = conn.execute(
                "SELECT id FROM sub_projects WHERE name = ?", (sub_project,)
            ).fetchone()
            if row:
                sub_project_id = row["id"]

        cursor = conn.execute(
            """
            INSERT INTO decisions (agent, decision, rationale, sub_project_id, issue_ref)
            VALUES (?, ?, ?, ?, ?)
            """,
            (agent, decision, rationale, sub_project_id, issue_ref),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_decisions(
    agent: str = None,
    sub_project: str = None,
    limit: int = 50,
) -> list:
    """Return list of decision dicts, filtered by agent and/or sub_project name."""
    conn = get_connection()
    try:
        clauses = []
        values = []

        if agent is not None:
            clauses.append("d.agent = ?")
            values.append(agent)

        if sub_project is not None:
            row = conn.execute(
                "SELECT id FROM sub_projects WHERE name = ?", (sub_project,)
            ).fetchone()
            if row:
                clauses.append("d.sub_project_id = ?")
                values.append(row["id"])
            else:
                # No such project — return empty
                return []

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM decisions d {where} ORDER BY d.id DESC LIMIT ?"
        values.append(limit)
        rows = conn.execute(sql, values).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# indexed_files + knowledge_index
# ---------------------------------------------------------------------------
def index_file(
    path: str,
    content: str,
    sub_project: str = None,
    doc_type: str = "other",
) -> int:
    """
    Index a file into indexed_files and knowledge_index (FTS5).
    - Same hash → no-op, returns existing id.
    - Different hash → update indexed_files + refresh knowledge_index.
    - New path → insert both.
    Returns the id from indexed_files.
    """
    content_hash = hashlib.sha256(content.encode()).hexdigest()

    conn = get_connection()
    try:
        # Resolve sub_project name → id
        sub_project_id = None
        sub_project_name = sub_project or ""
        if sub_project is not None:
            row = conn.execute(
                "SELECT id FROM sub_projects WHERE name = ?", (sub_project,)
            ).fetchone()
            if row:
                sub_project_id = row["id"]

        existing = conn.execute(
            "SELECT id, content_hash FROM indexed_files WHERE path = ?", (path,)
        ).fetchone()

        if existing is not None:
            if existing["content_hash"] == content_hash:
                # No-op
                return existing["id"]
            # Updated content — refresh
            file_id = existing["id"]
            conn.execute(
                """
                UPDATE indexed_files
                SET content_hash = ?, last_indexed_at = datetime('now')
                WHERE path = ?
                """,
                (content_hash, path),
            )
            conn.execute(
                "DELETE FROM knowledge_index WHERE file_id = ?", (file_id,)
            )
            conn.execute(
                """
                INSERT INTO knowledge_index (file_id, path, sub_project, doc_type, content)
                VALUES (?, ?, ?, ?, ?)
                """,
                (file_id, path, sub_project_name, doc_type, content),
            )
            conn.commit()
            return file_id

        # New file
        cursor = conn.execute(
            """
            INSERT INTO indexed_files (path, content_hash, sub_project_id, doc_type)
            VALUES (?, ?, ?, ?)
            """,
            (path, content_hash, sub_project_id, doc_type),
        )
        file_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO knowledge_index (file_id, path, sub_project, doc_type, content)
            VALUES (?, ?, ?, ?, ?)
            """,
            (file_id, path, sub_project_name, doc_type, content),
        )
        conn.commit()
        return file_id
    finally:
        conn.close()


def search(
    query: str,
    limit: int = 10,
    sub_project: str = None,
    doc_type: str = None,
) -> list:
    """
    FTS5 full-text search. Returns list of dicts with keys:
    path, sub_project, doc_type, snippet.
    """
    conn = get_connection()
    try:
        clauses = ["knowledge_index MATCH ?"]
        values = [query]

        if sub_project is not None:
            clauses.append("sub_project = ?")
            values.append(sub_project)
        if doc_type is not None:
            clauses.append("doc_type = ?")
            values.append(doc_type)

        where = " AND ".join(clauses)
        sql = f"""
            SELECT
                path,
                sub_project,
                doc_type,
                snippet(knowledge_index, 4, '<b>', '</b>', '...', 10) AS snippet
            FROM knowledge_index
            WHERE {where}
            LIMIT ?
        """
        values.append(limit)
        rows = conn.execute(sql, values).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def purge_knowledge(
    sub_project: str = None,
    older_than_days: int = None,
) -> int:
    """
    Delete from indexed_files (and knowledge_index by file_id).
    Returns count of deleted rows.
    """
    conn = get_connection()
    try:
        clauses = []
        values = []

        if sub_project is not None:
            row = conn.execute(
                "SELECT id FROM sub_projects WHERE name = ?", (sub_project,)
            ).fetchone()
            if row:
                clauses.append("sub_project_id = ?")
                values.append(row["id"])
            else:
                return 0

        if older_than_days is not None:
            cutoff = (datetime.utcnow() - timedelta(days=older_than_days)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            clauses.append("last_indexed_at < ?")
            values.append(cutoff)

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = conn.execute(
            f"SELECT id FROM indexed_files {where}", values
        ).fetchall()
        ids = [r["id"] for r in rows]

        if not ids:
            return 0

        placeholders = ",".join("?" * len(ids))
        conn.execute(
            f"DELETE FROM knowledge_index WHERE file_id IN ({placeholders})", ids
        )
        conn.execute(
            f"DELETE FROM indexed_files WHERE id IN ({placeholders})", ids
        )
        conn.commit()
        return len(ids)
    finally:
        conn.close()
