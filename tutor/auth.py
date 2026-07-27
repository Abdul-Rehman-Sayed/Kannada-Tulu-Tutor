"""
auth.py — real accounts for the literacy tutor.

WHAT THIS REPLACES. The app used to "log in" a student by asking for a name and
trusting it: typing "Ravi" gave you Ravi's progress, and typing it again from any
browser gave it to anyone else. The teacher dashboard — every child's name and
score — sat behind one shared PIN, typed in full on every visit, with the default
still shipped in config.py. Neither is authentication; both are an honour system.

WHAT IT DOES INSTEAD.
  * Every user has a password, stored as a scrypt hash with a per-user random
    salt. The password itself is never written anywhere.
  * scrypt (RFC 7914) is used, not a bare SHA-256. A plain hash is checked at
    billions of guesses/second on a GPU; scrypt is deliberately slow AND
    memory-hard (n=16384, r=8 -> ~16 MB per guess), which is what makes a stolen
    tutor.db worth little. It is in hashlib — no new dependency.
  * Hashes are compared with hmac.compare_digest, so a wrong password leaks
    nothing through timing.
  * A teacher account cannot simply be claimed: creating one requires the
    TUTOR_TEACHER_PIN. The PIN is now a REGISTRATION secret, used once, instead
    of a session password typed in front of a classroom of children — so it stops
    being something a child can watch a teacher type and reuse.
  * Failed logins are rate-limited per username.

The role lives on the user row, so a student session has no path to the teacher
view: `require_teacher()` reads the DB, not a session flag the client can set.
"""

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from contextlib import closing

from . import config
from . import db

# scrypt work factors. n is the memory/CPU cost; 2**14 with r=8 needs ~16 MB and
# ~50-100 ms per hash on a classroom laptop — unnoticeable on a login, brutal
# across a stolen database. Stored per-hash so these can be raised later without
# locking out anyone who registered under the old cost.
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

# username -> [failure_count, first_failure_time]. In-process: this is a single
# Streamlit server, and a lockout that survives a restart would lock a classroom
# out of its own tutor with no way back in.
_failures = {}


class AuthError(Exception):
    """Registration or login refused. The message is safe to show a user."""


def init_auth():
    """Create the users table. Safe to call repeatedly."""
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
    """scrypt(password, salt) -> (digest, kdf_descriptor)."""
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt,
        n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=KEY_LEN,
        maxmem=64 * 1024 * 1024,   # scrypt raises if it cannot get its memory
    )
    return digest, f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}"


def _verify_hash(password, salt, expected, kdf):
    """Constant-time check of a password against a stored hash."""
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
    """
    Create an account. Returns the user dict.

    A TEACHER account requires the teacher PIN — otherwise anyone who can reach
    the sign-up form could grant themselves every child's records. The PIN is
    compared in constant time, and the caller is rate-limited like a login.
    """
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

    # A learner needs a row in `students` for mastery to hang off. A teacher does
    # not — they are not a learner, and giving them one would put them in the
    # class list as a child with 0% progress.
    student_id = db.create_or_get_student(display_name) if role == STUDENT else None

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

    # Read the row back only after the transaction above has COMMITTED — get_user
    # opens its own connection and would not see an insert still in flight.
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
    """Return the user dict, or raise AuthError. Never says WHICH half was wrong."""
    init_auth()
    username = (username or "").strip()
    key = f"login:{username.lower()}"
    _guard_rate_limit(key)

    with closing(db.get_connection()) as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,)
        ).fetchone()

    # Hash even when the user does not exist, so the response time does not
    # reveal which usernames are real.
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
    """Used by the UI to explain what the teacher PIN is for on first run."""
    init_auth()
    with closing(db.get_connection()) as conn:
        return conn.execute(
            "SELECT 1 FROM users WHERE role = ? LIMIT 1", (TEACHER,)
        ).fetchone() is not None
