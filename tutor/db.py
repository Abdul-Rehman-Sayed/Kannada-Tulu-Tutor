"""
db.py — SQLite persistence for the Kannada/Tulu literacy tutor.

Two core tables (as specified for Slice 1):
    students(id, name, pin_optional)
    mastery(student_id, concept_id, mastery_score, attempts, last_seen)

Plus one forward-looking table used by the teacher dashboard (Slice 5):
    attempts(id, student_id, concept_id, score, correct, timestamp)  -- session history

Mastery scoring uses a recent-performance-weighted moving average (EMA). A single
confident correct answer crosses the mastery threshold; wrong answers pull it back
down quickly. This keeps short tutoring sessions responsive.

The DB path can be overridden with the TUTOR_DB_PATH environment variable —
the test scripts point it at a temp file so checkpoint runs never touch real
learner data.
"""

import os
import sqlite3
import datetime
from contextlib import closing

_DEFAULT_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tutor.db")
DB_PATH = os.environ.get("TUTOR_DB_PATH") or _DEFAULT_DB

# A concept counts as "mastered" at or above this score.
MASTERY_THRESHOLD = 0.7
# Weight given to the latest attempt in the moving average (0..1). Higher = more
# reactive to the most recent answer. 0.75 means one correct answer from zero -> 0.75.
EMA_ALPHA = 0.75

_initialized = False


def get_connection():
    """Low-level connection helper. Ensures the data/ directory exists.

    timeout=10 makes concurrent Streamlit sessions wait for a write lock
    instead of instantly raising "database is locked" (extra important here
    because the DB lives in a OneDrive-synced folder).
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they do not exist. Safe to call repeatedly."""
    with closing(get_connection()) as conn, conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS students (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL UNIQUE,
                pin_optional  TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS mastery (
                student_id     INTEGER NOT NULL,
                concept_id     TEXT NOT NULL,
                mastery_score  REAL NOT NULL DEFAULT 0,
                attempts       INTEGER NOT NULL DEFAULT 0,
                last_seen      TEXT,
                PRIMARY KEY (student_id, concept_id),
                FOREIGN KEY (student_id) REFERENCES students(id)
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS attempts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id  INTEGER NOT NULL,
                concept_id  TEXT NOT NULL,
                score       REAL NOT NULL,
                correct     INTEGER NOT NULL,
                timestamp   TEXT NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students(id)
            )"""
        )
    global _initialized
    _initialized = True


def _ensure_init():
    if not _initialized:
        init_db()


def create_or_get_student(name, pin=None):
    """Return the id of the student with this name, creating them if needed."""
    _ensure_init()
    name = (name or "").strip()
    if not name:
        raise ValueError("student name cannot be empty")
    with closing(get_connection()) as conn, conn:
        # INSERT OR IGNORE + re-select is race-safe: if two sessions submit the
        # same new name simultaneously, the UNIQUE constraint makes one insert a
        # no-op and both then read the same row.
        conn.execute(
            "INSERT OR IGNORE INTO students (name, pin_optional) VALUES (?, ?)",
            (name, pin),
        )
        row = conn.execute("SELECT id FROM students WHERE name = ?", (name,)).fetchone()
        return row["id"]


def get_student(student_id):
    _ensure_init()
    with closing(get_connection()) as conn:
        row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        return dict(row) if row else None


def get_all_students():
    _ensure_init()
    with closing(get_connection()) as conn:
        rows = conn.execute("SELECT * FROM students ORDER BY name").fetchall()
        return [dict(r) for r in rows]


def get_mastery_map(student_id):
    """Return {concept_id: mastery_score} for a student."""
    _ensure_init()
    with closing(get_connection()) as conn:
        rows = conn.execute(
            "SELECT concept_id, mastery_score FROM mastery WHERE student_id = ?",
            (student_id,),
        ).fetchall()
        return {r["concept_id"]: r["mastery_score"] for r in rows}


def update_mastery(student_id, concept_id, correct_bool, raw_score=None):
    """
    Update the student's mastery of a concept given a correct/incorrect attempt.
    Returns the new mastery score. Also appends a row to the session history.

    `raw_score` is the actual pronunciation similarity (0..1) for this attempt;
    when given it is what gets logged in the history table, so teachers see how
    close each attempt was — not the smoothed mastery average. Falls back to
    1/0 for callers that only know correct/incorrect.
    """
    _ensure_init()
    target = 1.0 if correct_bool else 0.0
    logged = round(float(raw_score), 4) if raw_score is not None else target
    correct = 1 if correct_bool else 0
    now = datetime.datetime.now().isoformat(timespec="seconds")
    with closing(get_connection()) as conn, conn:
        row = conn.execute(
            "SELECT mastery_score, attempts FROM mastery WHERE student_id=? AND concept_id=?",
            (student_id, concept_id),
        ).fetchone()
        old_score = row["mastery_score"] if row else 0.0
        attempts = (row["attempts"] if row else 0) + 1
        new_score = round((1 - EMA_ALPHA) * old_score + EMA_ALPHA * target, 4)

        if row:
            conn.execute(
                "UPDATE mastery SET mastery_score=?, attempts=?, last_seen=? "
                "WHERE student_id=? AND concept_id=?",
                (new_score, attempts, now, student_id, concept_id),
            )
        else:
            conn.execute(
                "INSERT INTO mastery (student_id, concept_id, mastery_score, attempts, last_seen) "
                "VALUES (?, ?, ?, ?, ?)",
                (student_id, concept_id, new_score, attempts, now),
            )
        conn.execute(
            "INSERT INTO attempts (student_id, concept_id, score, correct, timestamp) "
            "VALUES (?, ?, ?, ?, ?)",
            (student_id, concept_id, logged, correct, now),
        )
    return new_score


def get_mastery_rows(student_id):
    """Raw mastery rows for a student (concept_id, mastery_score, attempts, last_seen)."""
    _ensure_init()
    with closing(get_connection()) as conn:
        rows = conn.execute(
            "SELECT concept_id, mastery_score, attempts, last_seen "
            "FROM mastery WHERE student_id=? ORDER BY concept_id",
            (student_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_attempts(student_id=None):
    """Session history, newest first. All students if student_id is None."""
    _ensure_init()
    with closing(get_connection()) as conn:
        if student_id is None:
            rows = conn.execute(
                "SELECT a.*, s.name AS student_name FROM attempts a "
                "JOIN students s ON s.id = a.student_id ORDER BY a.timestamp DESC, a.id DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT a.*, s.name AS student_name FROM attempts a "
                "JOIN students s ON s.id = a.student_id "
                "WHERE a.student_id=? ORDER BY a.timestamp DESC, a.id DESC",
                (student_id,),
            ).fetchall()
        return [dict(r) for r in rows]


def reset_student(student_id):
    """Clear all mastery + history for a student (used by tests / retry)."""
    _ensure_init()
    with closing(get_connection()) as conn, conn:
        conn.execute("DELETE FROM mastery WHERE student_id=?", (student_id,))
        conn.execute("DELETE FROM attempts WHERE student_id=?", (student_id,))
