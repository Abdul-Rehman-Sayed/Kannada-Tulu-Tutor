import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from contextlib import closing

from . import config
from . import db

SCRYPT_N = 16384
SCRYPT_R = 8
SCRYPT_P = 1
KEY_LEN = 32

STUDENT = "student"
TEACHER = "teacher"

MIN_PASSWORD = 6
MAX_LOGIN_ATTEMPTS = 6
LOCKOUT_SECONDS = 60

_USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,32}$")

_failures = {}


class AuthError(Exception):
    pass


def init_auth():
    db._ensure_init()
    with closing(db.get_connection()) as conn, conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
                display_name  TEXT NOT NULL,
                password_hash BLOB NOT NULL,
                salt          BLOB NOT NULL,
                kdf           TEXT NOT NULL,
                role          TEXT NOT NULL,
                student_id    INTEGER,
                created_at    TEXT NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students(id)
            )"""
        )


def _hash(password, salt):
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt,
        n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=KEY_LEN,
        maxmem=64 * 1024 * 1024,
    )
    return digest, f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}"


def _verify_hash(password, salt, expected, kdf):
    try:
        n, r, p = (int(x) for x in kdf.split("$")[1:4])
    except (ValueError, IndexError):
        return False
    try:
        candidate = hashlib.scrypt(
            password.encode("utf-8"), salt=salt,
            n=n, r=r, p=p, dklen=len(expected), maxmem=64 * 1024 * 1024,
        )
    except ValueError:
        return False
    return hmac.compare_digest(candidate, expected)


def _clean_username(username):
    username = (username or "").strip()
    if not _USERNAME_RE.match(username):
        raise AuthError(
            "Usernames are 3-32 characters, letters and numbers only "
            "(dot, dash and underscore allowed)."
        )
    return username


def _check_password(password):
    if len(password or "") < MIN_PASSWORD:
        raise AuthError(f"Passwords must be at least {MIN_PASSWORD} characters.")
    return password


def register(username, password, display_name=None, role=STUDENT, teacher_pin=None):
    init_auth()
    username = _clean_username(username)
    _check_password(password)
    display_name = (display_name or username).strip()[:40]

    if role not in (STUDENT, TEACHER):
        raise AuthError("Unknown account type.")

    if role == TEACHER:
        _guard_rate_limit(f"register:{username}")
        given = str(teacher_pin or "").encode("utf-8")
        actual = str(config.TEACHER_PIN).encode("utf-8")
        if not hmac.compare_digest(given, actual):
            _record_failure(f"register:{username}")
            raise AuthError("That teacher PIN is not correct.")
        _clear_failures(f"register:{username}")

    salt = secrets.token_bytes(16)
    digest, kdf = _hash(password, salt)

    student_id = db.create_student(display_name, hint=username) if role == STUDENT else None

    with closing(db.get_connection()) as conn, conn:
        try:
            cur = conn.execute(
                "INSERT INTO users (username, display_name, password_hash, salt, kdf, "
                "role, student_id, created_at) VALUES (?,?,?,?,?,?,?,datetime('now'))",
                (username, display_name, digest, salt, kdf, role, student_id),
            )
        except sqlite3.IntegrityError:
            raise AuthError("That username is already taken.") from None
        new_id = cur.lastrowid

    return get_user(new_id)


def _guard_rate_limit(key):
    entry = _failures.get(key)
    if not entry:
        return
    count, first = entry
    if count >= MAX_LOGIN_ATTEMPTS:
        elapsed = time.time() - first
        if elapsed < LOCKOUT_SECONDS:
            raise AuthError(
                f"Too many failed attempts. Try again in "
                f"{int(LOCKOUT_SECONDS - elapsed)} seconds."
            )
        _failures.pop(key, None)


def _record_failure(key):
    count, first = _failures.get(key, (0, time.time()))
    _failures[key] = (count + 1, first)


def _clear_failures(key):
    _failures.pop(key, None)


def login(username, password):
    init_auth()
    username = (username or "").strip()
    key = f"login:{username.lower()}"
    _guard_rate_limit(key)

    with closing(db.get_connection()) as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,)
        ).fetchone()

    if row is None:
        _hash(password or "x", b"\x00" * 16)
        _record_failure(key)
        raise AuthError("Incorrect username or password.")

    if not _verify_hash(password or "", row["salt"], row["password_hash"], row["kdf"]):
        _record_failure(key)
        raise AuthError("Incorrect username or password.")

    _clear_failures(key)
    return _row_to_user(row)


def _row_to_user(row):
    return {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "role": row["role"],
        "student_id": row["student_id"],
    }


def get_user(user_id):
    init_auth()
    with closing(db.get_connection()) as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _row_to_user(row) if row else None


def user_count():
    init_auth()
    with closing(db.get_connection()) as conn:
        return conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]


def teacher_exists():
    init_auth()
    with closing(db.get_connection()) as conn:
        return conn.execute(
            "SELECT 1 FROM users WHERE role = ? LIMIT 1", (TEACHER,)
        ).fetchone() is not None
