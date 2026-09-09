import os
import sys
import tempfile
import unicodedata

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

_fd, _TMP_DB = tempfile.mkstemp(prefix="tutor_test_boot_", suffix=".db")
os.close(_fd)
os.environ["TUTOR_DB_PATH"] = _TMP_DB
os.environ["TUTOR_SKIP_WARMUP"] = "1"
os.environ["TUTOR_TEACHER_PIN"] = "boot-test-pin"

from streamlit.testing.v1 import AppTest

CARD = 'class="card word-card"'

LOGIN_USER, LOGIN_PASS = 0, 1
NEW_NAME, NEW_USER, NEW_PASS, NEW_PIN = 2, 3, 4, 5
BTN_SIGN_IN, BTN_CREATE = 2, 3


def _fresh():
    at = AppTest.from_file("app.py", default_timeout=60)
    at.run()
    return at


def _goto_signup(at, teacher=False):
    at.button[1 if teacher else 0].click().run()
    return at


def _signup(at, name, user, pw, teacher=False, pin=""):
    at.text_input[NEW_NAME].set_value(name)
    at.text_input[NEW_USER].set_value(user)
    at.text_input[NEW_PASS].set_value(pw)
    if teacher:
        at.text_input[NEW_PIN].set_value(pin)
    at.button[BTN_CREATE].click().run()
    return at


def _choose_language(at, name="Kannada"):
    labels = [b.label for b in at.button]
    want = f"Learn {name}"
    assert want in labels, f"language chooser has no {want!r} button: {labels}"
    at.button[labels.index(want)].click().run()
    return at


def _login(at, user, pw, teacher=False):
    at.text_input[LOGIN_USER].set_value(user)
    at.text_input[LOGIN_PASS].set_value(pw)
    at.button[BTN_SIGN_IN].click().run()
    return at


def landing_tests():
    print("Landing page:")
    at = _fresh()
    assert not at.exception, f"app raised on first load: {at.exception}"
    blob = " ".join(m.value for m in at.markdown)
    assert 'class="masthead"' in blob, "landing masthead did not render"
    labels = [b.label for b in at.button]
    for want in ("Start learning", "Teacher sign in"):
        assert want in labels, f"missing landing entry point {want!r}: {labels}"
    print(f"  OK  renders with real entry points: {labels}")

    at = _goto_signup(_fresh())
    assert not at.exception, at.exception
    assert any(t.label == "Your name" for t in at.text_input), "learner form missing"
    print("  OK  'Start learning' routes to a real account form")

    assert not any(t.label == "Teacher PIN" for t in at.text_input), \
        "the teacher PIN is being shown on the learner door"
    assert not any("teacher" in (c.label or "").lower() for c in at.checkbox), \
        "an 'I am a teacher' control is still on the learner door"
    print("  OK  learner door shows no teacher PIN and no teacher checkbox")

    at = _goto_signup(_fresh(), teacher=True)
    assert not at.exception, at.exception
    assert any(t.label == "Teacher PIN" for t in at.text_input), \
        "the teacher door has no PIN field"
    labels = [b.label for b in at.button]
    assert "Sign in" in labels, f"teacher door has no way to SIGN IN: {labels}"
    print(f"  OK  teacher door has both a sign-in and a PIN-gated sign-up: {labels}")
    return True


def student_journey_tests():
    print("\nStudent journey:")
    at = _signup(_goto_signup(_fresh()), "Ravi", "ravi_b", "sunflower22")
    assert not at.exception, f"raised after sign-up: {at.exception}"

    blob = " ".join(m.value for m in at.markdown)
    assert "What would you like to learn" in blob, \
        "a new learner was not asked which language they came to learn"
    labels = [b.label for b in at.button]
    for want in ("Learn Kannada", "Learn Tulu"):
        assert want in labels, f"language chooser is missing {want!r}: {labels}"
    print(f"  OK  account created -> asked which curriculum: {labels}")

    at = _choose_language(at, "Kannada")
    assert not at.exception, f"raised after choosing a language: {at.exception}"

    blob = " ".join(m.value for m in at.markdown)
    assert CARD in blob, "word card did not render after choosing Kannada"
    assert "ಅ" in blob, "expected first concept ಅ (V01) to be shown"
    print("  OK  chose Kannada -> first flashcard rendered (ಅ / V01)")

    assert "Say this" in blob, "letter card is missing the 'Say this' prompt"
    assert "ಅಮ್ಮ" not in blob, \
        "letter card is still showing an example word alongside the letter"
    assert "Just the letter" in blob, \
        "letter card does not tell the child to say the letter on its own"
    print("  OK  card asks for a bare ಅ — no example word beside it")

    labels = [b.label for b in at.button]
    assert any("Listen" in l for l in labels), f"Listen button missing: {labels}"
    recorders = at.get("audio_input")
    assert len(recorders) >= 1, "microphone recorder (st.audio_input) missing"
    print(f"  OK  real controls present: Listen + {len(recorders)} mic recorder")

    assert not any("Teacher" in l for l in labels), f"teacher control on student view: {labels}"
    assert "Teacher dashboard" not in blob
    print("  OK  no teacher control anywhere on the student view")
    return True


def teacher_boundary_tests():
    print("\nTeacher boundary:")

    at = _signup(_goto_signup(_fresh(), teacher=True), "Impostor", "impostor",
                 "password1", teacher=True, pin="wrong-pin")
    assert not at.exception, at.exception
    errs = " ".join(e.value for e in at.error)
    assert "PIN" in errs, f"a wrong teacher PIN was not refused: {errs!r}"
    blob = " ".join(m.value for m in at.markdown)
    assert "Teacher dashboard" not in blob, "the dashboard rendered without a valid PIN"
    print("  OK  a teacher account cannot be created with the wrong PIN")

    at = _signup(_goto_signup(_fresh(), teacher=True), "Mrs Rao", "mrs_rao",
                 "chalkdust!", teacher=True, pin="boot-test-pin")
    assert not at.exception, f"raised after teacher sign-up: {at.exception}"
    heads = " ".join(str(h.value) for h in at.title) + " ".join(
        str(s.value) for s in at.subheader)
    assert "Teacher dashboard" in heads, f"teacher was not shown the dashboard: {heads!r}"
    print("  OK  the correct PIN creates a teacher and opens the dashboard")

    at = _choose_language(
        _signup(_goto_signup(_fresh()), "Sneaky", "sneaky", "password1"))
    at.session_state["user"]["role"] = "teacher"
    at.run()
    assert not at.exception, at.exception
    heads = " ".join(str(h.value) for h in at.title)
    assert "Teacher dashboard" not in heads, \
        "a student promoted themselves by editing the session — the role is being trusted"
    blob = " ".join(m.value for m in at.markdown)
    assert CARD in blob, "the forged student should still be on their flashcard"
    print("  OK  forging role='teacher' in the session does NOT open the dashboard")
    return True


def no_emoji_tests():
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


def word_stage_tests():
    """The word stage, once the whole alphabet is behind the learner.

    Two things have to be true of it: the letter's family of words is on the
    screen beside the card, and the card names the letter the word grew out of.
    """
    from tutor import db, graph_engine

    print("\nWord stage:")
    at = _choose_language(
        _signup(_goto_signup(_fresh()), "Nita", "nita_w", "sunflower23"))
    assert not at.exception, at.exception

    sid = at.session_state["user"]["student_id"]
    letters = [cid for cid, d in
               graph_engine.load_graph(graph_engine.KANNADA).nodes(data=True)
               if d["category"] in ("vowels", "consonants")]
    for cid in letters:
        db.update_mastery(sid, cid, correct_bool=True)
    at.session_state["concept"] = None
    at.run()
    assert not at.exception, f"raised on the first word card: {at.exception}"

    concept = at.session_state["concept"]
    assert concept["level"] == graph_engine.WORDS_LEVEL, \
        f"after all {len(letters)} letters the learner got {concept['level']}"

    blob = " ".join(m.value for m in at.markdown)
    assert 'class="lw"' in blob, \
        "the family of words for this letter is not beside the card"

    letter = graph_engine.letter_of(concept["concept_id"], graph_engine.KANNADA)
    family = graph_engine.words_for_letter(letter["concept_id"],
                                           graph_engine.KANNADA)
    for row in family[:3]:
        assert row["word"] in blob, \
            f"{row['word']} is missing from the panel beside the card"
    assert "lw-now" in blob, "the panel does not mark the word being taught"
    assert "is for" in blob, "the word card does not name the letter it grew from"
    print(f"  OK  {concept['kannada_word']} is taught beside all "
          f"{len(family)} words of {letter['kannada_word']}, "
          f"and the card reads '{letter['kannada_word']} is for "
          f"{concept['kannada_word']}'")
    return True


def run():
    ok = landing_tests()
    ok &= student_journey_tests()
    ok &= word_stage_tests()
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
