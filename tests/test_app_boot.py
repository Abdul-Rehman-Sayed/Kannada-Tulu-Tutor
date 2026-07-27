"""
test_app_boot.py — headless end-to-end test for the Streamlit app.

Uses Streamlit's AppTest to actually run app.py in a simulated runtime (no
browser, no mic, no audio playback) and drive the real journey: landing page ->
create an account -> the first flashcard. Then it checks the thing that actually
guards children's records — that a student session cannot reach the teacher
dashboard, and a teacher account cannot be created without the PIN.

The live microphone loop still needs a human; everything up to it is here.

Run:  python test_app_boot.py
"""

import os
import sys
import tempfile
import unicodedata

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Isolate from real learner data + skip the whisper warm-up thread. Must be set
# BEFORE the app (and its db import) runs inside AppTest.
_fd, _TMP_DB = tempfile.mkstemp(prefix="tutor_test_boot_", suffix=".db")
os.close(_fd)
os.environ["TUTOR_DB_PATH"] = _TMP_DB
os.environ["TUTOR_SKIP_WARMUP"] = "1"
os.environ["TUTOR_TEACHER_PIN"] = "boot-test-pin"

from streamlit.testing.v1 import AppTest  # noqa: E402

# Field order on the sign-in page: the Sign in tab renders first, then Create
# account. Both tabs exist in the DOM at once, so the indices are stable.
LOGIN_USER, LOGIN_PASS = 0, 1
NEW_NAME, NEW_USER, NEW_PASS, NEW_PIN = 2, 3, 4, 5


def _fresh():
    at = AppTest.from_file("app.py", default_timeout=60)
    at.run()
    return at


def _goto_signup(at):
    """Landing -> 'Start learning' -> the account page."""
    at.button[0].click().run()
    return at


def _signup(at, name, user, pw, teacher=False, pin=""):
    at.text_input[NEW_NAME].set_value(name)
    at.text_input[NEW_USER].set_value(user)
    at.text_input[NEW_PASS].set_value(pw)
    at.text_input[NEW_PIN].set_value(pin)
    if teacher:
        at.checkbox[0].set_value(True)
    # buttons: 0=Back, 1=Sign in, 2=Create account
    at.button[2].click().run()
    return at


def landing_tests():
    print("Landing page:")
    at = _fresh()
    assert not at.exception, f"app raised on first load: {at.exception}"
    blob = " ".join(m.value for m in at.markdown)
    assert "hero" in blob, "landing hero did not render"
    labels = [b.label for b in at.button]
    assert "Start learning" in labels and "I already have an account" in labels, labels
    print(f"  OK  renders with real entry points: {labels}")

    # Nothing on the landing page may be a decorative fake: every call to action
    # has to be a Streamlit button that actually routes somewhere.
    at = _goto_signup(_fresh())
    assert not at.exception, at.exception
    assert any(t.label == "Teacher PIN" for t in at.text_input), "sign-up form missing"
    print("  OK  'Start learning' routes to a real account form")
    return True


def student_journey_tests():
    print("\nStudent journey:")
    at = _signup(_goto_signup(_fresh()), "Ravi", "ravi_b", "sunflower22")
    assert not at.exception, f"raised after sign-up: {at.exception}"

    blob = " ".join(m.value for m in at.markdown)
    assert "kannada-word" in blob, "word card did not render after sign-up"
    assert "ಅ" in blob, "expected first concept ಅ (V01) to be shown"
    print("  OK  account created -> first flashcard rendered (ಅ / V01)")

    # REGRESSION: ಅ on its own cannot be recognised, so a letter card MUST tell
    # the child to say the letter + its anchor word. If this box disappears, the
    # child is being asked for a sound the recogniser will always mark wrong.
    assert "say-box" in blob, "letter card is missing the 'Say this' prompt"
    assert "ಅ ಅಮ್ಮ" in blob, "letter card must ask for the letter + anchor word"
    print("  OK  card asks for 'ಅ ಅಮ್ಮ' (letter + anchor), not a bare ಅ")

    labels = [b.label for b in at.button]
    assert any("Listen" in l for l in labels), f"Listen button missing: {labels}"
    recorders = at.get("audio_input")
    assert len(recorders) >= 1, "microphone recorder (st.audio_input) missing"
    print(f"  OK  real controls present: Listen + {len(recorders)} mic recorder")

    # A student must not be shown any way into the class list.
    assert not any("Teacher" in l for l in labels), f"teacher control on student view: {labels}"
    assert "Teacher dashboard" not in blob
    print("  OK  no teacher control anywhere on the student view")
    return True


def teacher_boundary_tests():
    """The dashboard holds every child's name and score. It is the thing to guard."""
    print("\nTeacher boundary:")

    at = _signup(_goto_signup(_fresh()), "Impostor", "impostor", "password1",
                 teacher=True, pin="wrong-pin")
    assert not at.exception, at.exception
    errs = " ".join(e.value for e in at.error)
    assert "PIN" in errs, f"a wrong teacher PIN was not refused: {errs!r}"
    blob = " ".join(m.value for m in at.markdown)
    assert "Teacher dashboard" not in blob, "the dashboard rendered without a valid PIN"
    print("  OK  a teacher account cannot be created with the wrong PIN")

    at = _signup(_goto_signup(_fresh()), "Mrs Rao", "mrs_rao", "chalkdust!",
                 teacher=True, pin="boot-test-pin")
    assert not at.exception, f"raised after teacher sign-up: {at.exception}"
    heads = " ".join(str(h.value) for h in at.title) + " ".join(
        str(s.value) for s in at.subheader)
    assert "Teacher dashboard" in heads, f"teacher was not shown the dashboard: {heads!r}"
    print("  OK  the correct PIN creates a teacher and opens the dashboard")

    # The role is re-read from the DB every rerun. Forging the session copy must
    # not promote a student: this is the check that the gate is not a session flag.
    at = _signup(_goto_signup(_fresh()), "Sneaky", "sneaky", "password1")
    at.session_state["user"]["role"] = "teacher"
    at.run()
    assert not at.exception, at.exception
    heads = " ".join(str(h.value) for h in at.title)
    assert "Teacher dashboard" not in heads, \
        "a student promoted themselves by editing the session — the role is being trusted"
    blob = " ".join(m.value for m in at.markdown)
    assert "kannada-word" in blob, "the forged student should still be on their flashcard"
    print("  OK  forging role='teacher' in the session does NOT open the dashboard")
    return True


def no_emoji_tests():
    """Icons are Material Symbols. Emoji render differently on every device and
    read as decoration rather than as controls."""
    print("\nInterface:")
    at = _signup(_goto_signup(_fresh()), "Asha", "asha_b", "password1")

    def emoji_in(text):
        return [c for c in str(text)
                if unicodedata.category(c) == "So" or 0x1F000 <= ord(c) <= 0x1FAFF]

    surfaces = [m.value for m in at.markdown]
    surfaces += [b.label for b in at.button]
    surfaces += [getattr(e, "value", "") or "" for e in at.caption]
    found = {e for s in surfaces for e in emoji_in(s)}
    assert not found, f"emoji found in the UI: {found}"
    print("  OK  no emoji anywhere in the rendered interface")
    return True


def run():
    ok = landing_tests()
    ok &= student_journey_tests()
    ok &= teacher_boundary_tests()
    ok &= no_emoji_tests()
    print("\nBoot test PASSED." if ok else "\nBoot test FAILED.")
    return ok


if __name__ == "__main__":
    try:
        good = run()
    finally:
        try:
            os.remove(_TMP_DB)
        except OSError:
            pass
    sys.exit(0 if good else 1)
