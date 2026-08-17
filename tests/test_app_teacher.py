"""
test_app_teacher.py — the access-separation checkpoint (headless, via AppTest).

The teacher dashboard lists every child in the class by name, with how badly each
of them is doing. That is the asset worth guarding. This file assumes an attacker
who is a curious ten-year-old with the app open — the realistic threat here — and
checks that none of the obvious moves work:

  * signing in as a student shows no route to the dashboard at all,
  * a teacher account cannot be created without the deployer's PIN,
  * guessing that PIN is rate-limited,
  * and — the one that matters — the dashboard is gated on the ROLE IN THE
    DATABASE, not on anything the session carries, so tampering with session
    state cannot promote a student.

That last point is why the old shared-PIN gate was replaced. It set
`teacher_authed = True` in the session, and anything that could set that flag
owned the class list. It also asked a teacher to type the PIN in full, in front
of the class, every single visit.

Run:  python test_app_teacher.py
"""

import os
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Isolate from real learner data + skip the whisper warm-up thread. Must be set
# BEFORE the app (and its db import) runs inside AppTest.
_fd, _TMP_DB = tempfile.mkstemp(prefix="tutor_test_teacher_", suffix=".db")
os.close(_fd)
os.environ["TUTOR_DB_PATH"] = _TMP_DB
os.environ["TUTOR_SKIP_WARMUP"] = "1"
os.environ["TUTOR_TEACHER_PIN"] = "teacher-checkpoint-pin"

from streamlit.testing.v1 import AppTest  # noqa: E402

from tutor import auth  # noqa: E402

# Learners and teachers have SEPARATE doors, opened by separate landing buttons.
# Within a door the Sign in tab renders before Create account, and both are in the
# element tree at once, so these indices are stable.
#   landing buttons: 0 = Start learning, 1 = Teacher sign in
#   door text_input: 0,1 = sign-in user/pass; 2,3,4 = name/user/pass; 5 = PIN
#   door buttons   : 0 = Back, 1 = switch door, 2 = Sign in, 3 = Create account
LOGIN_USER, LOGIN_PASS = 0, 1
NEW_NAME, NEW_USER, NEW_PASS, NEW_PIN = 2, 3, 4, 5
BTN_BACK, BTN_SWITCH, BTN_SIGNIN, BTN_CREATE = 0, 1, 2, 3

FAILURES = []


def check(label, condition):
    print(f"  {'PASS' if condition else 'FAIL'}  {label}")
    if not condition:
        FAILURES.append(label)
    return bool(condition)


def _auth_page(teacher=False):
    """Landing -> the learner door, or the teacher door."""
    at = AppTest.from_file("app.py", default_timeout=60)
    at.run()
    at.button[1 if teacher else 0].click().run()
    return at


def _signup(name, user, pw, teacher=False, pin=""):
    at = _auth_page(teacher=teacher)
    at.text_input[NEW_NAME].set_value(name)
    at.text_input[NEW_USER].set_value(user)
    at.text_input[NEW_PASS].set_value(pw)
    if teacher:
        # The PIN exists only on the teacher door — a learner is never shown it.
        at.text_input[NEW_PIN].set_value(pin)
    at.button[BTN_CREATE].click().run()
    return at


def _signin(user, pw, teacher=False):
    at = _auth_page(teacher=teacher)
    at.text_input[LOGIN_USER].set_value(user)
    at.text_input[LOGIN_PASS].set_value(pw)
    at.button[BTN_SIGNIN].click().run()
    return at


def _text(at):
    """Everything the page actually puts in front of a human.

    The dataframes matter as much as the headings: the class list — every child's
    name and score — is rendered as a table, so a leak check that only reads
    markdown would happily pass an app that was printing the whole roster.
    """
    parts = []
    for coll in (at.title, at.header, at.subheader, at.markdown, at.caption):
        parts.extend(str(getattr(e, "value", "")) for e in coll)
    parts.extend(str(b.label) for b in at.button)
    for frame in at.dataframe:
        parts.append(frame.value.to_csv(index=False))
    return " ".join(parts)


def _shows_dashboard(at):
    return "Teacher dashboard" in _text(at)


def run():
    print("A student session:")
    student = _signup("Ravi", "ravi_t", "sunflower22")
    check("a student lands on their flashcard, not the dashboard",
          not _shows_dashboard(student) and "kannada-word" in _text(student))
    check("...and is offered no teacher control of any kind",
          not any("Teacher" in b.label for b in student.button))

    print("\nCreating a teacher account:")
    check("without a PIN, refused",
          not _shows_dashboard(_signup("X", "no_pin", "password1", teacher=True)))
    check("with the wrong PIN, refused",
          not _shows_dashboard(
              _signup("X", "bad_pin", "password1", teacher=True, pin="0000")))

    teacher = _signup("Mrs Rao", "mrs_rao_t", "chalkdust!",
                      teacher=True, pin="teacher-checkpoint-pin")
    check("with the deployer's PIN, the dashboard opens", _shows_dashboard(teacher))
    check("...and the class list is populated with the real students",
          "Ravi" in _text(teacher))
    check("...and no other child's name leaked into the student's own page",
          "Mrs Rao" not in _text(student))

    print("\nSigning back in:")
    # A returning teacher MUST have a sign-in of their own. Before the doors were
    # split there was none: the only route to a teacher account was the Create
    # account form, so this is the regression that split them.
    check("a teacher signing in at the teacher door returns to the dashboard",
          _shows_dashboard(_signin("mrs_rao_t", "chalkdust!", teacher=True)))
    check("a student signing in at the learner door does not",
          not _shows_dashboard(_signin("ravi_t", "sunflower22")))
    check("a wrong password gets nothing",
          not _shows_dashboard(_signin("mrs_rao_t", "not-the-password", teacher=True)))
    # Using the wrong door is refused and explained, rather than silently landing
    # someone in a view that does not match the account they typed.
    check("a student cannot sign in at the teacher door",
          not _shows_dashboard(_signin("ravi_t", "sunflower22", teacher=True)))
    check("a teacher signing in at the learner door is refused, not downgraded",
          not _shows_dashboard(_signin("mrs_rao_t", "chalkdust!")))

    print("\nTampering with the session — the real test:")
    # The old build kept a boolean in the session; anything that could set it
    # owned the class list. The role is now re-read from the DB on every rerun,
    # so the session's copy is advisory and carries no authority.
    forged = _signup("Sneaky", "sneaky_t", "password1")
    forged.session_state["user"]["role"] = auth.TEACHER
    forged.run()
    check("setting role='teacher' in the session does NOT open the dashboard",
          not _shows_dashboard(forged))
    check("...and the forger is still sitting on their own flashcard",
          "kannada-word" in _text(forged))

    print("\nGuessing the teacher PIN is throttled:")
    auth._failures.clear()
    locked = False
    for i in range(auth.MAX_LOGIN_ATTEMPTS + 2):
        at = _signup("Guess", "guesser", "password1", teacher=True, pin=f"{i:04d}")
        errs = " ".join(e.value for e in at.error)
        if "Too many failed attempts" in errs:
            locked = True
            break
    check(f"locked out after repeated wrong PINs (within "
          f"{auth.MAX_LOGIN_ATTEMPTS + 2} tries)", locked)
    check("...and no dashboard was ever reached while guessing",
          not _shows_dashboard(at))

    print()
    if FAILURES:
        print(f"{len(FAILURES)} CHECK(S) FAILED:")
        for f in FAILURES:
            print(f"  - {f}")
        return False
    print("Access separation checkpoint PASSED.")
    return True


if __name__ == "__main__":
    try:
        ok = run()
    finally:
        try:
            os.remove(_TMP_DB)
        except OSError:
            pass
    sys.exit(0 if ok else 1)
