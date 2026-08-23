"""
test_auth.py — accounts, password hashing, and the teacher boundary.

The thing being guarded here is a list of real children's names and how badly
each of them is doing. So these tests care about more than "login works": they
check that the password is not recoverable from the database, that a student
cannot promote themselves to teacher, and that guessing is throttled.

    python test_auth.py
"""

import os
import sys
import tempfile

_fd, _path = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["TUTOR_DB_PATH"] = _path
os.environ["TUTOR_TEACHER_PIN"] = "test-pin-9271"

from tutor import auth  # noqa: E402
from tutor import db  # noqa: E402


def _check(label, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    if not ok:
        print(f"        expected {want!r}, got {got!r}")
    return ok


def _raises(label, fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except auth.AuthError as e:
        print(f"  PASS  {label}  ({e})")
        return True
    print(f"  FAIL  {label}  — no AuthError raised")
    return False


def account_tests():
    print("Accounts:")
    ok = True

    u = auth.register("ravi", "sunflower22", display_name="Ravi")
    ok &= _check("a student can register", u["role"], auth.STUDENT)
    ok &= _check("...and gets a students row for mastery to hang off",
                 isinstance(u["student_id"], int), True)

    back = auth.login("ravi", "sunflower22")
    ok &= _check("...and can log in", back["id"], u["id"])
    ok &= _check("...case-insensitively", auth.login("RAVI", "sunflower22")["id"], u["id"])

    ok &= _raises("the wrong password is refused", auth.login, "ravi", "sunflower23")
    ok &= _raises("an unknown user is refused", auth.login, "nobody", "sunflower22")
    ok &= _raises("a duplicate username is refused", auth.register, "ravi", "another1")
    ok &= _raises("a short password is refused", auth.register, "meera", "abc")
    ok &= _raises("a bad username is refused", auth.register, "a b!", "goodpassword")
    return ok


def hashing_tests():
    """The database is the thing that gets stolen. It must not contain passwords."""
    print("\nPassword storage:")
    ok = True
    from contextlib import closing

    auth.register("asha", "correct-horse")
    with closing(db.get_connection()) as conn:
        row = conn.execute("SELECT * FROM users WHERE username='asha'").fetchone()

    blob = bytes(row["password_hash"])
    ok &= _check("the password is not stored", b"correct-horse" in blob, False)
    ok &= _check("...nor anywhere on the row",
                 b"correct-horse" in b"".join(bytes(str(v), "utf-8") if not isinstance(v, bytes)
                                              else v for v in tuple(row)), False)
    ok &= _check("a scrypt hash is stored", row["kdf"].startswith("scrypt$"), True)
    ok &= _check("...with a 32-byte digest", len(blob), 32)
    ok &= _check("...and a per-user random salt", len(bytes(row["salt"])), 16)

    auth.register("asha2", "correct-horse")
    with closing(db.get_connection()) as conn:
        a = conn.execute("SELECT password_hash FROM users WHERE username='asha'").fetchone()[0]
        b = conn.execute("SELECT password_hash FROM users WHERE username='asha2'").fetchone()[0]
    ok &= _check("the same password hashes differently for two users", bytes(a) == bytes(b), False)
    return ok


def teacher_tests():
    """A student session must have no path to the class list."""
    print("\nThe teacher boundary:")
    ok = True

    ok &= _raises("a teacher account cannot be made without the PIN",
                  auth.register, "fake_teacher", "password1", role=auth.TEACHER)
    ok &= _raises("...nor with the wrong PIN",
                  auth.register, "fake_teacher", "password1",
                  role=auth.TEACHER, teacher_pin="0000")

    t = auth.register("mrs_rao", "chalkdust!", display_name="Mrs Rao",
                      role=auth.TEACHER, teacher_pin="test-pin-9271")
    ok &= _check("the right PIN creates a teacher", t["role"], auth.TEACHER)
    ok &= _check("...who is NOT listed as a learner", t["student_id"], None)

    names = [s["name"] for s in db.get_all_students()]
    ok &= _check("...and does not appear in the class list", "Mrs Rao" in names, False)
    ok &= _check("...while the students do", "Ravi" in names, True)

    ok &= _check("the role is whatever the DB says", auth.get_user(t["id"])["role"], auth.TEACHER)
    return ok


def ratelimit_tests():
    print("\nGuessing is throttled:")
    ok = True
    auth.register("target", "realpassword")
    auth._failures.clear()

    for _ in range(auth.MAX_LOGIN_ATTEMPTS):
        try:
            auth.login("target", "wrong")
        except auth.AuthError:
            pass

    ok &= _raises(f"locked out after {auth.MAX_LOGIN_ATTEMPTS} wrong passwords",
                  auth.login, "target", "wrong")
    ok &= _raises("...the lockout holds even for the CORRECT password",
                  auth.login, "target", "realpassword")

    auth._failures.clear()
    ok &= _check("...and clears after the window", auth.login("target", "realpassword")["username"], "target")
    return ok


def main():
    passed = account_tests()
    passed &= hashing_tests()
    passed &= teacher_tests()
    passed &= ratelimit_tests()
    try:
        os.remove(_path)
    except OSError:
        pass
    print("\n" + ("ALL AUTH TESTS PASSED" if passed else "SOME TESTS FAILED"))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
