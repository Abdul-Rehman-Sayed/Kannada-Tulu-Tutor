import os
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

_fd, _TMP_DB = tempfile.mkstemp(prefix="tutor_test_teacher_", suffix=".db")
os.close(_fd)
os.environ["TUTOR_DB_PATH"] = _TMP_DB
os.environ["TUTOR_SKIP_WARMUP"] = "1"
os.environ["TUTOR_TEACHER_PIN"] = "teacher-checkpoint-pin"

from streamlit.testing.v1 import AppTest

CARD = 'class="card word-card"'

from tutor import auth

LOGIN_USER, LOGIN_PASS = 0, 1
NEW_NAME, NEW_USER, NEW_PASS = 2, 3, 4
NEW_PIN = NEW_CODE = 5
BTN_BACK, BTN_SWITCH, BTN_SIGNIN, BTN_CREATE = 0, 1, 2, 3

FAILURES = []


def check(label, condition):
    print(f"  {'PASS' if condition else 'FAIL'}  {label}")
    if not condition:
        FAILURES.append(label)
    return bool(condition)


def _auth_page(teacher=False):
    at = AppTest.from_file("app.py", default_timeout=60)
    at.run()
    at.button[1 if teacher else 0].click().run()
    return at


def _signup(name, user, pw, teacher=False, pin="", code=""):
    at = _auth_page(teacher=teacher)
    at.text_input[NEW_NAME].set_value(name)
    at.text_input[NEW_USER].set_value(user)
    at.text_input[NEW_PASS].set_value(pw)
    if teacher:
        at.text_input[NEW_PIN].set_value(pin)
    elif code:
        at.text_input[NEW_CODE].set_value(code)
    at.button[BTN_CREATE].click().run()
    return at


def _code_of(at):
    user = auth.get_user(at.session_state["user"]["id"])
    return (user or {}).get("join_code")


def _join_class(at, code):
    boxes = [t for t in at.text_input if t.label == "Class code"]
    assert boxes, f"no class-code box on the learner's screen: "                   f"{[t.label for t in at.text_input]}"
    boxes[0].set_value(auth.format_join_code(code))
    labels = [b.label for b in at.button]
    assert "Join class" in labels, f"no Join class button: {labels}"
    at.button[labels.index("Join class")].click().run()
    return at


def _tables(at):
    return " ".join(f.value.to_csv(index=False) for f in at.dataframe)


def _informs(at, phrase):
    return any(phrase in str(getattr(i, "value", "")) for i in at.info)


def _choose_language(at, name="Kannada"):
    labels = [b.label for b in at.button]
    want = f"Learn {name}"
    if want in labels:
        at.button[labels.index(want)].click().run()
    return at


def _signin(user, pw, teacher=False):
    at = _auth_page(teacher=teacher)
    at.text_input[LOGIN_USER].set_value(user)
    at.text_input[LOGIN_PASS].set_value(pw)
    at.button[BTN_SIGNIN].click().run()
    return at


def _text(at):
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
    student = _choose_language(_signup("Ravi", "ravi_t", "sunflower22"))
    check("a student lands on their flashcard, not the dashboard",
          not _shows_dashboard(student) and CARD in _text(student))
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

    rao_code = _code_of(teacher)
    check("...and the teacher is given a class code to read out",
          bool(rao_code) and auth.format_join_code(rao_code) in _text(teacher))
    check("...and a child who has joined no class is not on the class list",
          "Ravi" not in _tables(teacher))
    check("...but the dashboard says that child exists, rather than losing them",
          _informs(teacher, "not in any class"))
    check("...and no other child's name leaked into the student's own page",
          "Mrs Rao" not in _text(student))

    print("\nA child joining a class with the code:")
    ravi = _join_class(_choose_language(_signin("ravi_t", "sunflower22")), rao_code)
    check("the code is accepted and the class shown to the child",
          "Mrs Rao" in _text(ravi))
    check("...and the child is not told any other class code",
          not _informs(ravi, "not in a class"))

    after = _signin("mrs_rao_t", "chalkdust!", teacher=True)
    check("...and the child now appears on that teacher's class list",
          "Ravi" in _tables(after))

    print("\nTwo teachers, two classes:")
    other = _signup("Mr Shetty", "mr_shetty_t", "blackboard!",
                    teacher=True, pin="teacher-checkpoint-pin")
    shetty_code = _code_of(other)
    check("a second teacher gets a different code",
          bool(shetty_code) and shetty_code != rao_code)

    asha = _join_class(
        _choose_language(_signup("Asha", "asha_t", "password1")), shetty_code)
    check("a second child joins the second teacher's class",
          "Mr Shetty" in _text(asha))

    rao = _signin("mrs_rao_t", "chalkdust!", teacher=True)
    shetty = _signin("mr_shetty_t", "blackboard!", teacher=True)
    check("the first teacher sees their own child",
          "Ravi" in _tables(rao))
    check("...and NOT the other teacher's child",
          "Asha" not in _tables(rao))
    check("the second teacher sees their own child",
          "Asha" in _tables(shetty))
    check("...and NOT the first teacher's child",
          "Ravi" not in _tables(shetty))
    check("...and neither teacher is shown the other's class code",
          auth.format_join_code(shetty_code) not in _text(rao)
          and auth.format_join_code(rao_code) not in _text(shetty))

    print("\nSigning back in:")
    check("a teacher signing in at the teacher door returns to the dashboard",
          _shows_dashboard(_signin("mrs_rao_t", "chalkdust!", teacher=True)))
    check("a student signing in at the learner door does not",
          not _shows_dashboard(_signin("ravi_t", "sunflower22")))
    check("a wrong password gets nothing",
          not _shows_dashboard(_signin("mrs_rao_t", "not-the-password", teacher=True)))
    check("a student cannot sign in at the teacher door",
          not _shows_dashboard(_signin("ravi_t", "sunflower22", teacher=True)))
    check("a teacher signing in at the learner door is refused, not downgraded",
          not _shows_dashboard(_signin("mrs_rao_t", "chalkdust!")))

    print("\nTampering with the session — the real test:")
    forged = _choose_language(_signup("Sneaky", "sneaky_t", "password1"))
    forged.session_state["user"]["role"] = auth.TEACHER
    forged.run()
    check("setting role='teacher' in the session does NOT open the dashboard",
          not _shows_dashboard(forged))
    check("...and the forger is still sitting on their own flashcard",
          CARD in _text(forged))

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
