import os
import sqlite3
import datetime
from contextlib import closing

_DEFAULT_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tutor.db")
DB_PATH = os.environ.get("TUTOR_DB_PATH") or _DEFAULT_DB

MASTERY_THRESHOLD = 0.7
EMA_ALPHA = 0.75

_initialized = False


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with closing(get_connection()) as conn, conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS students (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL UNIQUE,
                pin_optional  TEXT,
                language      TEXT
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
                heard       TEXT,
                FOREIGN KEY (student_id) REFERENCES students(id)
            )"""
        )
        have = {r["name"] for r in conn.execute("PRAGMA table_info(attempts)")}
        if "heard" not in have:
            conn.execute("ALTER TABLE attempts ADD COLUMN heard TEXT")

        have = {r["name"] for r in conn.execute("PRAGMA table_info(students)")}
        if "language" not in have:
            conn.execute("ALTER TABLE students ADD COLUMN language TEXT")
        if "teacher_user_id" not in have:
            conn.execute(
                "ALTER TABLE students ADD COLUMN teacher_user_id INTEGER"
            )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_students_teacher "
            "ON students(teacher_user_id)"
        )
    global _initialized
    _initialized = True


def _ensure_init():
    if not _initialized:
        init_db()


def create_or_get_student(name, pin=None):
    _ensure_init()
    name = (name or "").strip()
    if not name:
        raise ValueError("student name cannot be empty")
    with closing(get_connection()) as conn, conn:
        conn.execute(
            "INSERT OR IGNORE INTO students (name, pin_optional) VALUES (?, ?)",
            (name, pin),
        )
        row = conn.execute("SELECT id FROM students WHERE name = ?", (name,)).fetchone()
        return row["id"]


def _student_name_candidates(base, hint):
    yield base
    if hint:
        yield f"{base} ({hint})"
    for n in range(2, 1000):
        yield f"{base} ({n})"


def create_student(name, hint=None):
    _ensure_init()
    base = (name or "").strip()
    if not base:
        raise ValueError("student name cannot be empty")
    with closing(get_connection()) as conn, conn:
        for candidate in _student_name_candidates(base, hint):
            try:
                cur = conn.execute(
                    "INSERT INTO students (name, pin_optional) VALUES (?, NULL)",
                    (candidate,),
                )
                return cur.lastrowid
            except sqlite3.IntegrityError:
                continue
    raise ValueError(f"could not allocate a student row for {base!r}")


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
    _ensure_init()
    with closing(get_connection()) as conn:
        rows = conn.execute(
            "SELECT concept_id, mastery_score FROM mastery WHERE student_id = ?",
            (student_id,),
        ).fetchall()
        return {r["concept_id"]: r["mastery_score"] for r in rows}


def update_mastery(student_id, concept_id, correct_bool, raw_score=None, heard=None):
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
            "INSERT INTO attempts (student_id, concept_id, score, correct, timestamp, heard) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (student_id, concept_id, logged, correct, now, (heard or "").strip() or None),
        )
    return new_score


def get_mastery_rows(student_id):
    _ensure_init()
    with closing(get_connection()) as conn:
        rows = conn.execute(
            "SELECT concept_id, mastery_score, attempts, last_seen "
            "FROM mastery WHERE student_id=? ORDER BY concept_id",
            (student_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def _class_clause(student_ids, column="student_id"):
    if student_ids is None:
        return "", []
    ids = [int(i) for i in student_ids]
    if not ids:
        return " AND 1=0", []
    return f" AND {column} IN ({','.join('?' for _ in ids)})", ids


def get_attempts(student_id=None, student_ids=None):
    _ensure_init()
    where, params = ["1=1"], []
    if student_id is not None:
        where.append("a.student_id = ?")
        params.append(student_id)
    clause, extra = _class_clause(student_ids, "a.student_id")
    params += extra
    with closing(get_connection()) as conn:
        rows = conn.execute(
            "SELECT a.*, s.name AS student_name FROM attempts a "
            "JOIN students s ON s.id = a.student_id "
            f"WHERE {' AND '.join(where)}{clause} "
            "ORDER BY a.timestamp DESC, a.id DESC",
            params,
        ).fetchall()
        return [dict(r) for r in rows]


def get_concept_stats(student_ids=None):
    _ensure_init()
    clause, params = _class_clause(student_ids)
    with closing(get_connection()) as conn:
        rows = conn.execute(
            "SELECT concept_id, COUNT(*) AS tries, "
            "       COUNT(DISTINCT student_id) AS students, "
            "       SUM(correct) AS correct, AVG(score) AS mean_score "
            f"FROM attempts WHERE 1=1{clause} GROUP BY concept_id",
            params,
        ).fetchall()
        return [dict(r) for r in rows]


def get_student_activity():
    _ensure_init()
    with closing(get_connection()) as conn:
        rows = conn.execute(
            "SELECT s.id AS student_id, s.name AS name, "
            "       COUNT(a.id) AS attempts, "
            "       COALESCE(SUM(a.correct), 0) AS correct, "
            "       MAX(a.timestamp) AS last_active "
            "FROM students s LEFT JOIN attempts a ON a.student_id = s.id "
            "GROUP BY s.id, s.name ORDER BY s.name"
        ).fetchall()
        return [dict(r) for r in rows]


def get_mishearings(student_id=None, only_wrong=True):
    _ensure_init()
    where = ["heard IS NOT NULL", "TRIM(heard) <> ''"]
    params = []
    if only_wrong:
        where.append("correct = 0")
    if student_id is not None:
        where.append("student_id = ?")
        params.append(student_id)
    with closing(get_connection()) as conn:
        rows = conn.execute(
            "SELECT concept_id, heard, COUNT(*) AS times, AVG(score) AS mean_score "
            f"FROM attempts WHERE {' AND '.join(where)} "
            "GROUP BY concept_id, heard ORDER BY times DESC, concept_id",
            params,
        ).fetchall()
        return [dict(r) for r in rows]


def reset_student(student_id):
    _ensure_init()
    with closing(get_connection()) as conn, conn:
        conn.execute("DELETE FROM mastery WHERE student_id=?", (student_id,))
        conn.execute("DELETE FROM attempts WHERE student_id=?", (student_id,))


def get_student_language(student_id):
    _ensure_init()
    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT language FROM students WHERE id=?", (student_id,)
        ).fetchone()
        return (row["language"] or None) if row else None


def set_student_language(student_id, language):
    _ensure_init()
    with closing(get_connection()) as conn, conn:
        conn.execute(
            "UPDATE students SET language=? WHERE id=?", (language, student_id)
        )


def set_student_teacher(student_id, teacher_user_id):
    _ensure_init()
    with closing(get_connection()) as conn, conn:
        conn.execute(
            "UPDATE students SET teacher_user_id=? WHERE id=?",
            (teacher_user_id, student_id),
        )


def get_student_teacher(student_id):
    _ensure_init()
    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT teacher_user_id FROM students WHERE id=?", (student_id,)
        ).fetchone()
        return (row["teacher_user_id"] if row else None) or None


def get_students_for_teacher(teacher_user_id):
    _ensure_init()
    with closing(get_connection()) as conn:
        rows = conn.execute(
            "SELECT * FROM students WHERE teacher_user_id=? ORDER BY name",
            (teacher_user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_unassigned_students():
    _ensure_init()
    with closing(get_connection()) as conn:
        rows = conn.execute(
            "SELECT * FROM students WHERE teacher_user_id IS NULL ORDER BY name"
        ).fetchall()
        return [dict(r) for r in rows]
