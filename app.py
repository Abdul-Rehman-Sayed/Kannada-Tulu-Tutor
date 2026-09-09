import contextlib
import datetime
import hashlib
import html
import os
import threading

import pandas as pd
import streamlit as st

from tutor import (
    auth, cogmap, config, db, graph_engine, illustrations, insight, media,
    pronunciation, ui,
)

_SESSION_KEYS = ("user", "concept", "last_result", "listen_audio", "scored_sig",
                 "confident_misses", "language", "last_level")

st.set_page_config(
    page_title="Kannada & Tulu Literacy Tutor",
    page_icon=":material/graphic_eq:",
    layout="wide",
    initial_sidebar_state="auto",
)


def _esc(value):
    return html.escape(str(value))


def _hide_sidebar():
    st.markdown(
        "<style>[data-testid='stSidebar'],"
        "[data-testid='stSidebarCollapsedControl']{display:none !important;}</style>",
        unsafe_allow_html=True,
    )


def _warm_model():
    try:
        pronunciation.get_model()
    except Exception:
        pass


@st.cache_resource
def start_model_warmup():
    threading.Thread(target=_warm_model, daemon=True).start()
    return True


_SETTLED = (pronunciation.READY, pronunciation.FAILED)


def _status_caption():
    state = pronunciation.load_state()

    if state == pronunciation.READY:
        if pronunciation.is_kannada_model():
            st.caption(":material/check_circle: Speech scoring ready")
        else:
            st.warning(
                "The Kannada speech model could not be loaded, so scoring is "
                "unreliable. Listening still works.",
                icon=":material/warning:",
            )
    elif state == pronunciation.FAILED:
        st.error(
            "The speech recogniser could not start, so nothing will be marked. "
            "Listening and reading still work.",
            icon=":material/error:",
        )
    else:
        st.caption(":material/hourglass_top: Waking the speech recogniser "
                   "(first time only)…")


def recogniser_status():
    if pronunciation.load_state() not in _SETTLED:
        with st.spinner("Waking the speech recogniser (first time only)…"):
            try:
                pronunciation.get_model()
            except Exception:
                pass
    _status_caption()


def score_recording(sid, concept, wav_bytes):
    ok, reason, stats, samples = pronunciation.prepare_audio(wav_bytes)
    if not ok:
        st.session_state.last_result = {"retry": reason, "stats": stats}
        return

    msg = ("Listening to what you said…"
           if pronunciation.is_model_ready()
           else "Waking the speech recogniser (first time only)…")
    asr_lang = graph_engine.language_info(concept.get("language"))["asr"]
    try:
        with st.spinner(msg):
            heard, confidence = pronunciation.transcribe_scored(samples, language=asr_lang)
    except Exception as e:
        st.session_state.last_result = {"error": str(e)}
        return

    if not heard.strip() or pronunciation.is_silence_filler(heard):
        st.session_state.last_result = {"retry": pronunciation.NO_SPEECH, "stats": stats}
        return

    expected, alternates = pronunciation.accepted_forms(concept)
    score, correct = pronunciation.score_pronunciation(expected, heard, alternates)

    cid = concept["concept_id"]
    misses = st.session_state.setdefault("confident_misses", {})
    outcome = pronunciation.classify_attempt(
        correct, stats.get("snr", 99), confidence, misses.get(cid, 0),
        scoreable=pronunciation.is_scoreable(concept),
    )

    if outcome == pronunciation.OUTCOME_RETRY:
        if not pronunciation.is_scoreable(concept):
            reason = pronunciation.UNSCOREABLE
        elif (stats.get("snr", 99) < pronunciation.MIN_SNR
                and stats.get("peak", 0.0) < pronunciation.LOUD_ENOUGH):
            reason = pronunciation.TOO_QUIET
        else:
            reason = pronunciation.NOT_RECOGNISED
        st.session_state.last_result = {"retry": reason, "stats": stats}
        return

    if outcome == pronunciation.OUTCOME_SOFT:
        misses[cid] = misses.get(cid, 0) + 1
        st.session_state.last_result = {
            "word": graph_engine.display_word(concept), "expected": expected,
            "translit": concept["transliteration"], "score": score,
            "correct": False, "heard": heard,
        }
        return

    if outcome == pronunciation.OUTCOME_WRONG:
        misses[cid] = misses.get(cid, 0) + 1
    else:
        misses.pop(cid, None)

    graph_engine.update_mastery(sid, cid, correct, raw_score=score, heard=heard)
    st.session_state.last_result = {
        "word": graph_engine.display_word(concept),
        "expected": expected,
        "translit": concept["transliteration"],
        "score": score,
        "correct": correct,
        "heard": heard,
    }
    if correct:
        st.session_state.concept = None
        st.session_state.pop("listen_audio", None)


_POINTS = [
    ("It listens, and it is fair about it",
     "Speech is scored by sound, not by spelling — and a softly-spoken answer is "
     "amplified, never rejected. A recording it cannot hear is a free retry, "
     "never a wrong mark."),
    ("It teaches in the right order",
     "Every letter, word, phrase and sentence sits behind what it is built from. "
     "Nothing appears too early, and a child stuck on one thing is moved on "
     "rather than left grinding."),
    ("Two separate curricula",
     "Kannada and Tulu are taught as two syllabuses, not one mixed together. A "
     "child picks the language they came to learn and sees only that."),
    ("Teachers see who is stuck, in words",
     "An alphabet chart with each child's letters coloured in, and plain "
     "sentences: who has not practised, what they keep missing, what to do about "
     "it today."),
]


def landing():
    _hide_sidebar()
    ui.narrow(920)

    total = graph_engine.load_graph().number_of_nodes()
    langs = graph_engine.available_languages()
    ui.card(
        """
        <div class="masthead">
          <div class="rule"></div>
          <h1>Learn to read Kannada and Tulu<br/>by saying it out loud</h1>
          <p class="lede">
            A speaking tutor for children who are learning to read. See the
            letter, hear it, say it — and be told honestly whether you got it.
          </p>
          <div class="script kn">ಅ&nbsp;&nbsp;ಆ&nbsp;&nbsp;ಇ&nbsp;&nbsp;ಈ&nbsp;&nbsp;ಉ</div>
        </div>
        """
    )
    st.markdown(
        f'<div class="facts"><b>{total}</b> concepts across '
        f'<b>{len(langs)}</b> separate curricula &nbsp;·&nbsp; speech is '
        f"recognised <b>on this machine</b> &nbsp;·&nbsp; no recording of a "
        f"child's voice is ever sent anywhere</div>",
        unsafe_allow_html=True,
    )

    ui.spacer(20)
    c1, c2 = st.columns(2, gap="small")
    with c1:
        if st.button("Start learning", type="primary", width="stretch",
                     icon=":material/arrow_forward:"):
            _goto_auth(auth.STUDENT, "signup")
    with c2:
        if st.button("Teacher sign in", width="stretch",
                     icon=":material/shield_person:"):
            _goto_auth(auth.TEACHER, "login")

    ui.spacer(26)
    points = "".join(
        f'<div class="point"><div class="num">{n}</div>'
        f"<div><h3>{title}</h3><p>{body}</p></div></div>"
        for n, (title, body) in enumerate(_POINTS, start=1)
    )
    ui.card(f'<div class="points">{points}</div>')


def _language_card(code):
    info = graph_engine.language_info(code)
    total = graph_engine.load_graph(code).number_of_nodes()
    tiers = ", ".join(
        graph_engine.LEVEL_MEANING.get(lv, lv).lower()
        for lv in graph_engine.LEVELS
        if any(d["level"] == lv
               for _, d in graph_engine.load_graph(code).nodes(data=True))
    )
    ui.card(
        f'<div class="panel"><div class="word kn" style="font-size:clamp(30px,6vw,44px);'
        f'margin:0 0 6px;text-align:left">{ui.esc(info["native"])}</div>'
        f'<h3 style="margin:0 0 8px">{ui.esc(info["name"])}</h3>'
        f'<p class="section-note" style="margin:0 0 6px">{ui.esc(info["blurb"])}</p>'
        f'<p class="tiny">{total} concepts &nbsp;·&nbsp; {tiers}</p></div>',
        extra="lang-card",
    )


def language_page(user):
    _hide_sidebar()
    ui.narrow(760)
    ui.card(
        f'<div class="masthead"><div class="rule"></div>'
        f"<h1>What would you like to learn?</h1>"
        f'<p class="lede">Pick one. You can change it at any time from the menu, '
        f"and your progress in each language is kept separately.</p></div>"
    )
    ui.spacer(20)

    codes = graph_engine.available_languages()
    cols = st.columns(len(codes), gap="small")
    for col, code in zip(cols, codes):
        with col:
            _language_card(code)
            info = graph_engine.language_info(code)
            if st.button(f"Learn {info['name']}", key=f"pick_{code}",
                         type="primary", width="stretch",
                         icon=":material/arrow_forward:"):
                _set_language(user, code)

    ui.spacer(16)
    if st.button("Log out", icon=":material/logout:"):
        logout()


def _set_language(user, code):
    code = graph_engine.normalize_language(code)
    db.set_student_language(user["student_id"], code)
    st.session_state.language = code
    st.session_state.concept = None
    st.session_state.last_result = None
    st.session_state.pop("listen_audio", None)
    st.session_state.pop("confident_misses", None)
    for key in [k for k in list(st.session_state.keys()) if k.startswith("rec_")]:
        st.session_state.pop(key, None)
    st.session_state.view = "app"
    st.rerun()


def current_language(user):
    code = st.session_state.get("language") or db.get_student_language(
        user["student_id"])
    if not code:
        return None
    code = graph_engine.normalize_language(code)
    st.session_state.language = code
    return code


def _finish_login(user):
    st.session_state.user = user
    st.session_state.concept = None
    st.session_state.last_result = None
    st.session_state.pop("language", None)
    if user.get("student_id"):
        stored = db.get_student_language(user["student_id"])
        if stored:
            st.session_state.language = graph_engine.normalize_language(stored)
    st.session_state.view = "app"
    st.rerun()


def _goto_auth(role, tab):
    st.session_state.view = "auth"
    st.session_state.auth_role = role
    st.session_state.auth_tab = tab
    st.rerun()


def _login_as(username, password, expected_role):
    user = auth.login(username, password)
    if user["role"] != expected_role:
        actual = "teacher" if user["role"] == auth.TEACHER else "learner"
        raise auth.AuthError(
            f"That is a {actual} account. Go back and use the "
            f"{actual} entrance to sign in."
        )
    _finish_login(user)


def auth_page():
    _hide_sidebar()
    ui.narrow(560)
    role = st.session_state.get("auth_role")
    if role == auth.TEACHER:
        _teacher_auth()
    elif role == auth.STUDENT:
        _student_auth()
    else:
        _auth_chooser()


def _auth_chooser():
    ui.card(
        """
        <div class="hero" style="padding:34px 30px 26px">
          <h1 style="font-size:clamp(26px,4vw,38px)">Kannada &amp; Tulu Tutor</h1>
          <p class="lede">Who is signing in?</p>
        </div>
        """
    )
    ui.spacer(16)
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        if st.button("I am a learner", type="primary", width="stretch",
                     icon=":material/school:"):
            _goto_auth(auth.STUDENT, "login")
    with c2:
        if st.button("I am a teacher", width="stretch",
                     icon=":material/shield_person:"):
            _goto_auth(auth.TEACHER, "login")
    ui.spacer(8)
    if st.button("Back", icon=":material/arrow_back:"):
        st.session_state.view = "landing"
        st.rerun()


def _auth_header(title, lede):
    ui.card(
        f"""
        <div class="hero" style="padding:34px 30px 26px">
          <h1 style="font-size:clamp(26px,4vw,38px)">{title}</h1>
          <p class="lede">{lede}</p>
        </div>
        """
    )
    ui.spacer(16)


def _student_auth():
    _auth_header("Learner sign in", "Sign in to pick up where you left off.")

    b1, b2 = st.columns(2)
    with b1:
        if st.button("Back", width="stretch", icon=":material/arrow_back:"):
            st.session_state.view = "landing"
            st.rerun()
    with b2:
        if st.button("I am a teacher", width="stretch",
                     icon=":material/shield_person:"):
            _goto_auth(auth.TEACHER, "login")

    tab_in, tab_up = st.tabs(["Sign in", "Create an account"])

    with tab_in:
        with st.form("login_form"):
            u = st.text_input("Username", key="li_u")
            p = st.text_input("Password", type="password", key="li_p")
            go = st.form_submit_button("Sign in", type="primary", width="stretch",
                                       icon=":material/login:")
        if go:
            try:
                _login_as(u, p, auth.STUDENT)
            except auth.AuthError as e:
                st.error(str(e), icon=":material/lock:")

    with tab_up:
        with st.form("signup_form"):
            name = st.text_input("Your name", placeholder="Shown on your progress")
            u2 = st.text_input("Username", placeholder="letters and numbers")
            p2 = st.text_input("Password", type="password",
                               help=f"At least {auth.MIN_PASSWORD} characters.")
            make = st.form_submit_button("Create account", type="primary",
                                         width="stretch",
                                         icon=":material/person_add:")
        if make:
            try:
                _finish_login(auth.register(
                    u2, p2, display_name=name or u2, role=auth.STUDENT))
            except auth.AuthError as e:
                st.error(str(e), icon=":material/error:")


def _teacher_auth():
    _auth_header("Teacher sign in",
                 "Sign in to see your class, or create a teacher account.")

    b1, b2 = st.columns(2)
    with b1:
        if st.button("Back", width="stretch", icon=":material/arrow_back:"):
            st.session_state.view = "landing"
            st.rerun()
    with b2:
        if st.button("I am a learner", width="stretch", icon=":material/school:"):
            _goto_auth(auth.STUDENT, "login")

    tab_in, tab_up = st.tabs(["Sign in", "Create a teacher account"])

    with tab_in:
        with st.form("t_login_form"):
            u = st.text_input("Username", key="tli_u")
            p = st.text_input("Password", type="password", key="tli_p")
            go = st.form_submit_button("Sign in", type="primary", width="stretch",
                                       icon=":material/login:")
        if go:
            try:
                _login_as(u, p, auth.TEACHER)
            except auth.AuthError as e:
                st.error(str(e), icon=":material/lock:")
        st.caption("Signing in needs only your username and password. The teacher "
                   "PIN is required once, when the account is first created.")

    with tab_up:
        with st.form("t_signup_form"):
            name = st.text_input("Your name", placeholder="Shown on the dashboard")
            u2 = st.text_input("Username", placeholder="letters and numbers")
            p2 = st.text_input("Password", type="password",
                               help=f"At least {auth.MIN_PASSWORD} characters.")
            pin = st.text_input(
                "Teacher PIN", type="password",
                help="A teacher account can see every child's name and score, so "
                     "creating one needs the PIN set by whoever deployed this.",
            )
            make = st.form_submit_button("Create teacher account", type="primary",
                                         width="stretch",
                                         icon=":material/person_add:")
        if make:
            try:
                _finish_login(auth.register(
                    u2, p2, display_name=name or u2,
                    role=auth.TEACHER, teacher_pin=pin))
            except auth.AuthError as e:
                st.error(str(e), icon=":material/error:")

        if not auth.teacher_exists():
            st.info("No teacher account exists yet. The first one is created with "
                    "the PIN set by whoever deployed this app.",
                    icon=":material/info:")

        if config.IS_DEFAULT_PIN:
            st.warning(
                "This deployment is still using the default teacher PIN. Set "
                "`TUTOR_TEACHER_PIN` (environment variable, or Streamlit secrets) "
                "before letting students near it.",
                icon=":material/warning:",
            )


_RETRY_TEXT = {
    pronunciation.TOO_QUIET: (
        "The room was louder than your voice.",
        "Move closer to the microphone and say it once more.",
    ),
    pronunciation.TOO_SHORT: (
        "That was too short to hear.",
        "Hold the mic on while you say the whole word.",
    ),
    pronunciation.TOO_LONG: (
        "That recording was very long.",
        "Tap the mic, say just the word, then tap again to stop.",
    ),
    pronunciation.NO_SPEECH: (
        "I couldn't make out a word.",
        "Try once more, a little slower and clearer.",
    ),
    pronunciation.NOT_RECOGNISED: (
        "I couldn't quite catch that word.",
        "Say it once more, clearly — this does not count against you.",
    ),
    pronunciation.UNREADABLE: (
        "That recording didn't come through.",
        "Tap the microphone and try again.",
    ),
    pronunciation.UNSCOREABLE: (
        "This letter is one the app cannot hear on its own.",
        "Say it for your teacher instead — you will move on after a few tries.",
    ),
}


def render_stages(stages):
    """The strip across the top saying which stage the learner is in.

    Letters, then words, then phrases, then sentences - and the learner can
    see at a glance which one they are on and what is still shut.
    """
    if not stages:
        return
    cells = []
    for s in stages:
        cls = {"done": "stg stg-done", "current": "stg stg-now"}.get(
            s["state"], "stg stg-locked")
        pct = (s["mastered"] / s["total"] * 100) if s["total"] else 0
        caption = {"locked": "locked",
                   "done": f"all {s['total']} done"}.get(
            s["state"], f"{s['mastered']} of {s['total']}")
        cells.append(
            f'<div class="{cls}"><div class="n">Stage {s["position"]}</div>'
            f'<div class="t">{_esc(s["title"])}</div>'
            f'<div class="c">{_esc(caption)}</div>'
            f'<div class="m"><i style="width:{pct:.0f}%"></i></div></div>')
    st.markdown(f'<div class="stages">{"".join(cells)}</div>',
                unsafe_allow_html=True)

    now = next((s for s in stages if s["state"] == "current"), None)
    if now:
        ui.card(
            f'<div class="stage-now"><h4>Stage {now["position"]} of {now["of"]} '
            f'&mdash; {_esc(now["title"])}</h4>'
            f'<p>{_esc(now["blurb"])}</p></div>')
        ui.spacer(10)


def render_stage_change(stages, concept):
    """Mark the moment a learner crosses from one stage into the next.

    Finishing the alphabet is the biggest thing that happens in this app, and
    it used to pass without a word: the card simply stopped being a letter and
    started being a word.
    """
    level = concept.get("level")
    previous = st.session_state.get("last_level")
    st.session_state.last_level = level
    if previous is None or previous == level:
        return

    done = next((s for s in stages if s["level"] == previous), None)
    now = next((s for s in stages if s["level"] == level), None)
    if not done or not now or done["state"] != "done":
        return

    st.markdown(
        f'<div class="fb fb-ok"><div class="hd">Stage {done["position"]} '
        f'finished &mdash; {_esc(done["title"].lower())} done</div>'
        f'<div class="sub">{_esc(now["blurb"])}</div></div>',
        unsafe_allow_html=True,
    )


def render_picture(concept):
    """The drawing above the word.

    Always a drawing from our own library, never a photograph.  The cards used
    to fall back to photographs fetched off the web for anything not drawn yet,
    and what came back was not fit to put in front of a child - the bell
    arrived as a labelled engineering diagram on a black ground.  Nothing
    reaches a card now that has not been drawn here on purpose; where there is
    no drawing the library sets the word itself, which is plain but safe.

    A letter never gets here at all: a letter is taught on its own, and the
    picture it used to show was borrowed from an example word.
    """
    if graph_engine.is_letter(concept):
        return
    word = graph_engine.display_word(concept)
    icon = concept.get("icon") or concept.get("english_meaning", "")
    st.markdown(
        f'<div class="pic">{illustrations.render(icon, label=word)}</div>',
        unsafe_allow_html=True,
    )


def render_letter_family(concept, language):
    """The words that grow out of this word's letter, beside the card.

    A child working through ka meets kamala, then kannu, then kage, and the
    whole family stays on screen the whole time - so the sound is seen opening
    word after word, not met once and gone.  The list scrolls, so a long
    family never pushes the microphone off the screen.
    """
    letter = graph_engine.letter_of(concept["concept_id"], language)
    if not letter:
        return

    rows = graph_engine.words_for_letter(letter["concept_id"], language)
    if not rows:
        return

    here = concept["concept_id"]
    taught = [r for r in rows if r["in_syllabus"]]
    reading = [r for r in rows if not r["in_syllabus"]]

    def item(row, number):
        classes = "lw-item"
        mark = ""
        if row["concept_id"] == here:
            classes += " lw-now"
            mark = '<span class="lw-mark">you are here</span>'
        return (
            f'<li class="{classes}"><span class="lw-n">{number}</span>'
            f'<span class="w kn">{_esc(row["word"])}</span>'
            f'<span class="t">{_esc(row["transliteration"])}</span>'
            f'<span class="m">{_esc(row["english_meaning"])}{mark}</span></li>'
        )

    body = "".join(item(r, i) for i, r in enumerate(taught, 1))
    if reading:
        body += ('<li class="lw-split">more words with this letter, to read '
                 "only</li>")
        body += "".join(item(r, i) for i, r in enumerate(reading, len(taught) + 1))

    foot = (f"You are asked for the first {len(taught)}; the rest are to read."
            if reading else
            f"All {len(taught)} are yours to say, one after another.")

    st.markdown(
        f'<div class="lw"><div class="lw-hd">'
        f'<span class="kn">{_esc(letter["kannada_word"])}</span> '
        f'words from this letter'
        f'<span class="n">{len(rows)}</span></div>'
        f'<ul class="lw-list">{body}</ul>'
        f'<p class="lw-ft">{foot}</p>'
        f"</div>",
        unsafe_allow_html=True,
    )


def render_letter_card(concept):
    """A letter, on its own.

    The card used to read "a is for amma" and ask the child to say both, which
    put whole words in front of a child who could not yet read one letter.  A
    letter card now carries the letter, the sound it makes, and nothing else -
    no example word, and no picture borrowed from one.  The words come later,
    once the whole alphabet is done.
    """
    letter = graph_engine.display_word(concept)
    kind = "vowel" if concept["category"] == "vowels" else "consonant"

    ui.card(
        f'<div class="letter-tile"><span class="kn">{_esc(letter)}</span></div>'
        f'<div class="translit">{_esc(concept["transliteration"])}</div>'
        f'<div class="meaning">A single {kind} &mdash; learn the sound it '
        f"makes.</div>"
        f'<div class="tags"><span>{_esc(concept["category"])}</span>'
        f'<span>Stage 1 &middot; Letters</span></div>'
        f'<div class="isfor"><p class="lead">Say this</p>'
        f'<div class="line"><span class="l">{_esc(letter)}</span></div>'
        f'<div class="gloss">Just the letter, on its own &mdash; '
        f'<b>{_esc(concept["transliteration"])}</b></div></div>',
        extra="word-card",
    )


def render_word_card(concept, language=None, stage=None):
    """A word, a phrase or a sentence, with the letter it grew out of."""
    if graph_engine.is_letter(concept):
        render_letter_card(concept)
        return

    render_picture(concept)

    word = graph_engine.display_word(concept)
    stage_info = stage or graph_engine.stage_of(concept)
    long_form = len(word) > 12 or " " in word.strip()

    spoken = concept["spoken_form"]
    say_html = ""
    if spoken.strip() != word.strip():
        gloss = concept.get("phrase_gloss", "")
        hint = (f"say the whole line &mdash; &ldquo;{_esc(gloss)}&rdquo;"
                if gloss else "say the whole line")
        say_html = (
            f'<div class="say"><p class="lbl">Say this</p>'
            f'<div class="val">{_esc(spoken)}</div>'
            f'<div class="hint">{hint}</div></div>'
        )

    grew_html = ""
    if language:
        parent = graph_engine.letter_of(concept["concept_id"], language)
        if parent and word.startswith(parent["kannada_word"]):
            grew_html = (
                f'<div class="isfor"><p class="lead">The letter it grew from'
                f'</p><div class="line">'
                f'<span class="l">{_esc(parent["kannada_word"])}</span>'
                f'<span class="j">is for</span>'
                f'<span class="a">{_esc(word)}</span></div>'
                f'<div class="gloss">You have already learned '
                f'<b>{_esc(parent["transliteration"])}</b>.</div></div>'
            )

    ui.card(
        f'<div class="word{" long" if long_form else ""}">{_esc(word)}</div>'
        f'<div class="translit">{_esc(concept["transliteration"])}</div>'
        f'<div class="meaning">{_esc(concept["english_meaning"])}</div>'
        f'<div class="tags"><span>{_esc(concept["category"])}</span>'
        f'<span>Stage {stage_info.get("position") or stage_info["number"]} '
        f'&middot; {_esc(stage_info["title"])}</span></div>'
        f"{say_html}{grew_html}",
        extra="word-card",
    )


def render_feedback():
    res = st.session_state.get("last_result")
    if not res:
        return

    if res.get("error"):
        st.error(
            "The speech recogniser isn't available right now, so nothing was "
            f"marked. You can keep practising with Listen. ({_esc(res['error'])})",
            icon=":material/error:",
        )
        return

    if res.get("retry"):
        head, hint = _RETRY_TEXT.get(
            res["retry"], ("I didn't catch that.", "Please try again.")
        )
        st.markdown(
            f'<div class="fb fb-warn"><div class="hd">{_esc(head)}</div>'
            f'<div class="sub">{_esc(hint)} This does not count as a wrong answer.</div></div>',
            unsafe_allow_html=True,
        )
        return

    word = _esc(res["word"])
    heard = _esc(res.get("heard") or "—")
    pct = int(round(res["score"] * 100))

    if res["correct"]:
        st.markdown(
            f'<div class="fb fb-ok"><div class="hd">Correct &mdash; '
            f'<span class="kn">{word}</span></div>'
            f'<div class="sub">{pct}% match &nbsp;·&nbsp; heard: '
            f'<span class="kn">{heard}</span></div>'
            f'<div class="meter"><i style="width:{pct}%"></i></div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="fb fb-no"><div class="hd">Not quite &mdash; listen and '
            f'say <span class="kn">{word}</span> once more</div>'
            f'<div class="sub">heard: <span class="kn">{heard}</span></div></div>',
            unsafe_allow_html=True,
        )


def current_concept(student_id, language):
    if st.session_state.get("concept") is None:
        st.session_state.concept = graph_engine.get_next_concept(student_id, language)
    return st.session_state.concept


def _clear_learning_state():
    for k in list(st.session_state.keys()):
        if k in _SESSION_KEYS or k.startswith("rec_"):
            st.session_state.pop(k, None)


def logout():
    _clear_learning_state()
    st.session_state.pop("auth_role", None)
    st.session_state.pop("auth_tab", None)
    st.session_state.pop("language", None)
    st.session_state.view = "landing"
    st.rerun()


def app_sidebar(user, language=None, mastered=None, total=None, by_level=None):
    st.sidebar.markdown(
        '<div class="sb-brand">Kannada &amp; Tulu Tutor</div>'
        '<div class="sb-sub">Read · Listen · Speak</div>',
        unsafe_allow_html=True,
    )
    role_label = "Teacher" if user["role"] == auth.TEACHER else "Learner"
    lang_line = ""
    if language:
        info = graph_engine.language_info(language)
        lang_line = (f'<div class="lang">Learning {_esc(info["name"])} '
                     f'<span class="kn">{_esc(info["native"])}</span></div>')
    st.sidebar.markdown(
        f'<div class="learner"><div class="rl">{role_label}</div>'
        f'<div class="nm">{_esc(user["display_name"])}</div>{lang_line}</div>',
        unsafe_allow_html=True,
    )

    if total:
        st.sidebar.progress(mastered / total if total else 0.0)
        pct = int(round(mastered / total * 100)) if total else 0
        st.sidebar.caption(f"{mastered} of {total} learned  ·  {pct}%")

    if by_level:
        for stage in by_level:
            tail = {"locked": "locked",
                    "done": f"{stage['total']}/{stage['total']} done"}.get(
                stage["state"],
                f"{stage['mastered']}/{stage['total']} · now")
            st.sidebar.caption(
                f"Stage {stage['position']} · {stage['title']} · {tail}")

    if language and len(graph_engine.available_languages()) > 1:
        st.sidebar.write("")
        if st.sidebar.button("Change language", width="stretch",
                             icon=":material/translate:"):
            st.session_state.view = "language"
            st.rerun()

    with st.sidebar:
        recogniser_status()
    st.sidebar.write("")
    if st.sidebar.button("Log out", width="stretch", icon=":material/logout:"):
        logout()


def student_view(user, language):
    sid = user["student_id"]
    mastered, total = graph_engine.mastery_summary(sid, language)
    stages = graph_engine.stage_progress(sid, language)
    app_sidebar(user, language, mastered, total, stages)

    concept = current_concept(sid, language)
    beside = bool(concept) and concept.get("level") == graph_engine.WORDS_LEVEL
    ui.narrow(1080 if beside else 720)

    render_stages(stages)
    render_feedback()

    if concept is None:
        name = graph_engine.language_name(language)
        ui.card(
            f'<div class="masthead centred"><h1>Every {_esc(name)} concept '
            f"learned</h1>"
            f'<p class="lede" style="margin:0 auto">You finished all {total} of '
            f"them. Outstanding work.</p></div>"
        )
        ui.spacer()
        others = [c for c in graph_engine.available_languages() if c != language]
        if others:
            other = graph_engine.language_info(others[0])
            if st.button(f"Start learning {other['name']}", type="primary",
                         width="stretch", icon=":material/arrow_forward:"):
                _set_language(user, other["code"])
        if st.button(f"Practise {name} again from the start",
                     width="stretch", icon=":material/restart_alt:"):
            db.reset_student(sid)
            _clear_learning_state()
            st.session_state.user = user
            st.session_state.language = language
            st.session_state.view = "app"
            st.rerun()
        return

    render_stage_change(stages, concept)
    stage = next((s for s in stages if s["level"] == concept.get("level")), None)

    if beside:
        left, right = st.columns([1.5, 1], gap="medium")
        with right:
            render_letter_family(concept, language)
        target = left
    else:
        target = contextlib.nullcontext()

    with target:
        render_word_card(concept, language=language, stage=stage)
        ui.spacer()
        render_lesson_controls(sid, concept, language)


def render_lesson_controls(sid, concept, language):
    """Listen, then say it - the part of the card the child actually works."""
    label = ("Listen to the letter" if graph_engine.is_letter(concept)
             else "Listen to the word")
    if st.button(label, width="stretch", icon=":material/volume_up:"):
        try:
            audio_path = media.get_audio(
                concept["concept_id"], graph_engine.listen_form(concept),
                lang=graph_engine.language_info(language)["asr"])
            st.session_state.listen_audio = (concept["concept_id"], audio_path)
        except Exception as e:
            st.error(
                "Couldn't play the word. The first play of each word needs "
                f"internet; after that it works offline. ({_esc(e)})",
                icon=":material/volume_off:",
            )

    la = st.session_state.get("listen_audio")
    if la and la[0] == concept["concept_id"] and os.path.exists(la[1]):
        st.audio(la[1])

    ui.spacer(6)
    st.markdown("##### Now you say it")

    if pronunciation.load_state() != pronunciation.READY:
        recogniser_status()

    rec_key = f"rec_{concept['concept_id']}"
    for stale in [k for k in list(st.session_state.keys())
                  if k.startswith("rec_") and k != rec_key]:
        st.session_state.pop(stale, None)

    recording = st.audio_input(
        "Tap the microphone, say the word, then tap again to stop", key=rec_key
    )
    if recording is not None:
        wav_bytes = recording.getvalue()
        sig = hashlib.md5(wav_bytes).hexdigest()
        if wav_bytes and st.session_state.get("scored_sig") != sig:
            st.session_state.scored_sig = sig
            score_recording(sid, concept, wav_bytes)
            st.rerun()

    st.caption(
        "The first time, your browser asks for microphone permission — choose Allow."
    )


def _findings(items):
    if not items:
        return
    rows = []
    for item in items:
        mark = "→" if item["do"] else "·"
        cls = "finding finding-do" if item["do"] else "finding"
        rows.append(f'<div class="{cls}"><span class="mk">{mark}</span>'
                    f"<span>{item['text']}</span></div>")
    ui.card(f'<div class="findings">{"".join(rows)}</div>')


def _alphabet_chart(student_id, language):
    chart = insight.alphabet_chart(student_id, language)
    if not chart:
        return

    st.subheader("Alphabet chart")
    ui.note(
        "The same chart as on the classroom wall. Each letter is coloured by how "
        "this child is doing on it."
    )
    titles = {"vowels": "Vowels — ಸ್ವರಗಳು", "consonants": "Consonants — ವ್ಯಂಜನಗಳು"}
    for cat, cells in chart.items():
        st.markdown(
            f'<p class="tiny" style="margin:14px 0 6px;text-transform:uppercase;'
            f'letter-spacing:.1em;font-weight:600">{titles.get(cat, cat)}</p>',
            unsafe_allow_html=True,
        )
        grid = "".join(
            f'<div class="cell {c["state"]}" title="{_esc(c["title"])}">'
            f'<div class="g">{_esc(c["glyph"])}</div>'
            f'<div class="r">{_esc(c["roman"])}</div></div>'
            for c in cells
        )
        st.markdown(f'<div class="chart">{grid}</div>', unsafe_allow_html=True)
    ui.legend(insight.CHART_LEGEND)


def _cognitive_map(student_id, language, display_name):
    try:
        plan = cogmap.layout(student_id, language)
    except Exception:
        return
    if not plan:
        return

    ui.spacer(16)
    with st.expander(f"How the tutor plans {display_name}'s lessons "
                     f"({len(plan['nodes'])} concepts)"):
        ui.note(
            "The cognitive knowledge graph: every concept in this track, each "
            "one sitting below the concepts it needs first. The tutor walks it "
            "downward to choose what to teach next. Colours are the same as the "
            "alphabet chart — hover a dot to see which concept it is."
        )
        edges = "".join(
            f'<line class="edge" x1="{e["x1"]}" y1="{e["y1"]}" '
            f'x2="{e["x2"]}" y2="{e["y2"]}"/>'
            for e in plan["edges"]
        )
        tiers = "".join(
            f'<text class="tier" x="4" y="{r["y"] + 3}">{r["n"]}</text>'
            for r in plan["rows"]
        )
        nodes = "".join(
            f'<circle class="node" cx="{n["x"]}" cy="{n["y"]}" r="{n["r"]}" '
            f'fill="{n["fill"]}" stroke="{n["stroke"]}">'
            f'<title>{_esc(n["title"])}</title></circle>'
            for n in plan["nodes"]
        )
        st.markdown(
            f'<div class="cogmap"><svg width="{plan["width"]}" '
            f'height="{plan["height"]}" viewBox="0 0 {plan["width"]} '
            f'{plan["height"]}" role="img" aria-label="Prerequisite graph of '
            f'{_esc(display_name)}\'s curriculum">'
            f"{edges}{tiers}{nodes}</svg></div>",
            unsafe_allow_html=True,
        )
        ui.legend(cogmap.LEGEND)


def _days_since(iso_ts):
    if not iso_ts:
        return None
    try:
        return max(0, (datetime.datetime.now() - datetime.datetime.fromisoformat(iso_ts)).days)
    except ValueError:
        return None


def _student_language(student):
    return graph_engine.normalize_language(
        student.get("language") or graph_engine.DEFAULT_LANGUAGE)


def _class_rows(students):
    activity = {a["student_id"]: a for a in db.get_student_activity()}
    rows = []
    for s in students:
        language = _student_language(s)
        progress = graph_engine.get_student_progress(s["id"], language)
        mastered = sum(1 for p in progress if p["mastered"])
        total = len(progress)
        needs = sum(1 for p in progress
                    if p["attempts"] >= insight.STRUGGLE_ATTEMPTS and not p["mastered"])
        parked = sum(1 for p in progress if p["parked"])
        act = activity.get(s["id"], {})
        rows.append({
            "Student": s["name"],
            "Learning": graph_engine.language_name(language),
            "_language": language,
            "_id": s["id"],
            "Learned": mastered,
            "Concepts": total,
            "Progress": (mastered / total * 100) if total else 0.0,
            "Needs help": needs,
            "Moved on": parked,
            "Attempts": act.get("attempts", 0),
            "Idle (days)": _days_since(act.get("last_active")),
            "Last active": (act.get("last_active") or "never").replace("T", " "),
        })
    return rows


def _class_overview(students):
    rows = _class_rows(students)

    st.subheader("What needs you today")
    ui.note(
        "Read this first. Everything below is the same information as numbers, "
        "for when you want to check it."
    )
    safe = [dict(r, Student=_esc(r["Student"])) for r in rows]
    _findings(insight.class_findings(safe))

    ui.spacer(20)
    all_attempts = db.get_attempts()
    sum_learned = sum(r["Learned"] for r in rows)
    sum_total = sum(r["Concepts"] for r in rows)
    avg_pct = int(round(sum_learned / sum_total * 100)) if sum_total else 0
    inactive = sum(1 for r in rows if r["Idle (days)"] is None
                   or r["Idle (days)"] >= insight.IDLE_DAYS)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Children", len(students))
    m2.metric("Things practised", len(all_attempts))
    m3.metric("Average progress", f"{avg_pct}%")
    m4.metric("Not seen in a week", inactive)

    ui.spacer()
    st.subheader("Every child")
    ui.note(
        "‘Needs help’ — tried something twice or more and still not got it. "
        f"‘Moved on’ — tried {graph_engine.PARK_AFTER_ATTEMPTS}+ times without "
        "success, so the tutor advanced the child rather than leaving them stuck. "
        "Each child is counted out of the curriculum they are actually learning."
    )
    table = pd.DataFrame(
        [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    ).sort_values(["Moved on", "Needs help"], ascending=False, kind="stable")
    st.dataframe(
        table,
        hide_index=True,
        width="stretch",
        column_config={
            "Progress": st.column_config.ProgressColumn(
                "Progress", min_value=0, max_value=100, format="%.0f%%"
            ),
            "Idle (days)": st.column_config.NumberColumn("Idle (days)", format="%d"),
        },
    )

    _hardest_concepts()
    _class_trend(all_attempts)
    _class_export(table)


def _hardest_concepts():
    stats = db.get_concept_stats()
    if not stats:
        return

    rows = []
    for s in stats:
        info = graph_engine.concept_info(s["concept_id"])
        if not info:
            continue
        tries = s["tries"] or 0
        rows.append({
            "Word": info.get("display_word") or info["kannada_word"],
            "Roman": info["transliteration"],
            "Meaning": info["english_meaning"],
            "Language": graph_engine.language_name(info.get("language")),
            "Topic": info["category"],
            "Children": s["students"],
            "Tries": tries,
            "Got it %": (s["correct"] or 0) / tries * 100 if tries else 0.0,
            "Avg match": round(s["mean_score"] or 0.0, 3),
        })
    if not rows:
        return

    ui.spacer()
    st.subheader("What the class finds hardest")
    ui.note(
        "Lowest success rate first, counting only things at least one child has "
        "tried. A low rate across several children points at the lesson or at the "
        "recogniser — not at one child."
    )
    df = pd.DataFrame(rows).sort_values(["Got it %", "Tries"], ascending=[True, False])
    only_multi = st.checkbox(
        "Only show things 2 or more children have tried", value=False,
        help="Filters out words a single child happened to hit, so what is left "
             "is a class-wide pattern.",
    )
    if only_multi:
        df = df[df["Children"] >= 2]
    st.dataframe(
        df, hide_index=True, width="stretch",
        column_config={
            "Got it %": st.column_config.ProgressColumn(
                "Got it %", min_value=0, max_value=100, format="%.0f%%"),
            "Avg match": st.column_config.NumberColumn("Avg match", format="%.2f"),
        },
    )


def _class_trend(all_attempts):
    if not all_attempts:
        return
    df = pd.DataFrame(all_attempts)
    df["day"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.date
    df = df.dropna(subset=["day"])
    if df.empty:
        return

    daily = df.groupby("day").agg(
        Attempts=("id", "count"), Correct=("correct", "sum")).reset_index()
    daily["Accuracy %"] = daily["Correct"] / daily["Attempts"] * 100
    first = (df[df["correct"] == 1]
             .sort_values("timestamp")
             .drop_duplicates(subset=["student_id", "concept_id"]))
    if not first.empty:
        learned = first.groupby("day").size().reset_index(name="Learned")
        daily = daily.merge(learned, on="day", how="left")
        daily["Learned"] = daily["Learned"].fillna(0).cumsum()
    daily = daily.set_index("day")

    ui.spacer()
    st.subheader("The class over time")
    c1, c2 = st.columns(2)
    with c1:
        st.caption("How much they practised each day")
        st.bar_chart(daily[["Attempts"]])
    with c2:
        st.caption("How often they got it right (%)")
        st.line_chart(daily[["Accuracy %"]])
    if "Learned" in daily:
        st.caption("Things learned, running total across the class")
        st.area_chart(daily[["Learned"]])


def _class_export(table):
    ui.spacer()
    st.download_button(
        "Download the whole class (CSV)",
        data=table.to_csv(index=False).encode("utf-8-sig"),
        file_name="class_progress.csv",
        mime="text/csv",
        width="stretch",
        icon=":material/download:",
    )


def _student_detail(students):
    name_to_id = {f'{s["name"]} (#{s["id"]})': s["id"] for s in students}
    picked = st.selectbox("Choose a child", list(name_to_id.keys()))
    sid = name_to_id[picked]
    student = next(s for s in students if s["id"] == sid)
    display_name = student["name"]

    languages = graph_engine.available_languages()
    default = _student_language(student)
    language = default
    if len(languages) > 1:
        labels = {graph_engine.language_name(c): c for c in languages}
        chosen = st.radio(
            "Curriculum", list(labels.keys()),
            index=list(labels.values()).index(default),
            horizontal=True,
            help="This child is signed up for "
                 f"{graph_engine.language_name(default)}.",
        )
        language = labels[chosen]

    progress = graph_engine.get_student_progress(sid, language)
    learned = sum(1 for p in progress if p["mastered"])
    attempted = sum(1 for p in progress if p["attempts"] > 0)
    struggling = [p for p in progress
                  if p["attempts"] >= insight.STRUGGLE_ATTEMPTS and not p["mastered"]]

    ui.spacer(8)
    st.subheader(f"What {display_name} needs")
    _findings(insight.student_findings(sid, language, _esc(display_name)))

    ui.spacer(20)
    d1, d2, d3 = st.columns(3)
    d1.metric("Learned", f"{learned} / {len(progress)}")
    d2.metric("Tried", attempted)
    d3.metric("Stuck on", len(struggling))

    ui.spacer(20)
    _alphabet_chart(sid, language)

    topics = insight.topic_rows(sid, language)
    if topics:
        ui.spacer(24)
        st.subheader("Words, by topic")
        ui.note("Topics they have started, least finished first. Topics they "
                "have not reached yet come last.")
        ui.bars(topics)

    if struggling:
        ui.spacer(24)
        st.subheader("Stuck on these")
        ui.note(
            f"Tried at least {insight.STRUGGLE_ATTEMPTS} times and still not "
            f"got it. After {graph_engine.PARK_AFTER_ATTEMPTS} tries the tutor "
            f"moves the child on rather than leaving them stuck — those are "
            f"marked ‘moved on’, and are the ones to sit down with."
        )
        st.dataframe(
            pd.DataFrame([{
                "Word": p["word"],
                "Roman": p["transliteration"],
                "Meaning": p["english_meaning"],
                "Tries": p["attempts"],
                "How close": p["mastery_score"],
                "Moved on": p["parked"],
            } for p in sorted(struggling, key=lambda p: (-p["parked"], -p["attempts"]))]),
            hide_index=True, width="stretch",
            column_config={
                "How close": st.column_config.ProgressColumn(
                    "How close", min_value=0.0, max_value=1.0, format="%.2f"),
                "Moved on": st.column_config.CheckboxColumn("Moved on"),
            },
        )

    mishears = db.get_mishearings(sid)
    rows = []
    for m in mishears:
        info = graph_engine.concept_info(m["concept_id"])
        if not info or info.get("language", graph_engine.KANNADA) != language:
            continue
        expected, _alts = pronunciation.accepted_forms(info)
        rows.append({
            "Asked for": expected,
            "Child said": m["heard"],
            "Times": m["times"],
            "Avg match": round(m["mean_score"] or 0.0, 3),
        })
    if rows:
        ui.spacer(24)
        st.subheader("What they actually said")
        ui.note(
            "Attempts that did not match, most repeated first. The same wrong "
            "form coming back for one word is the thing to correct directly."
        )
        st.dataframe(
            pd.DataFrame(rows), hide_index=True, width="stretch",
            column_config={"Avg match": st.column_config.NumberColumn(
                "Avg match", format="%.2f")},
        )

    df = pd.DataFrame(progress)[[
        "concept_id", "word", "transliteration", "english_meaning",
        "category", "level", "mastery_score", "attempts", "mastered",
    ]]
    ui.spacer(24)
    with st.expander(f"Every {graph_engine.language_name(language)} concept "
                     f"({len(progress)})"):
        st.dataframe(
            df,
            hide_index=True,
            width="stretch",
            column_config={
                "concept_id": "ID",
                "word": "Word",
                "transliteration": "Roman",
                "english_meaning": "Meaning",
                "category": "Topic",
                "level": "Tier",
                "mastery_score": st.column_config.ProgressColumn(
                    "How close", min_value=0.0, max_value=1.0, format="%.2f"
                ),
                "attempts": "Tries",
                "mastered": st.column_config.CheckboxColumn("Learned"),
            },
        )

    log = db.get_attempts(sid)
    ui.spacer(16)
    with st.expander(f"Everything {display_name} has tried ({len(log)})"):
        if log:
            hist = pd.DataFrame(log)[
                ["timestamp", "concept_id", "heard", "score", "correct"]]
            hist["correct"] = hist["correct"].map({1: "Got it", 0: "Missed"})
            hist["heard"] = hist["heard"].fillna("—")
            st.dataframe(
                hist, hide_index=True, width="stretch",
                column_config={
                    "timestamp": "When",
                    "concept_id": "Concept",
                    "heard": "Heard",
                    "score": st.column_config.NumberColumn("Match", format="%.2f"),
                    "correct": "Result",
                },
            )
        else:
            st.caption("Nothing recorded yet for this child.")

    csv = df.to_csv(index=False).encode("utf-8-sig")
    safe_name = "".join(c if (c.isalnum() or c in "-_") else "_"
                        for c in display_name) or "student"
    ui.spacer()
    st.download_button(
        f"Download {display_name}'s progress (CSV)",
        data=csv,
        file_name=f"{safe_name}_progress.csv",
        mime="text/csv",
        width="stretch",
        icon=":material/download:",
    )

    _cognitive_map(sid, language, display_name)


def teacher_view(user):
    app_sidebar(user)
    st.title("Teacher dashboard")

    students = db.get_all_students()
    if not students:
        st.info("No children yet — ask a learner to create an account and begin.",
                icon=":material/school:")
        return

    tab_overview, tab_detail = st.tabs(["The class", "One child"])
    with tab_overview:
        _class_overview(students)
    with tab_detail:
        _student_detail(students)


def main():
    db.init_db()
    auth.init_auth()
    ui.inject()
    if not os.environ.get("TUTOR_SKIP_WARMUP"):
        start_model_warmup()

    user = st.session_state.get("user")
    if user:
        fresh = auth.get_user(user["id"])
        if not fresh:
            logout()
            return
        if fresh["role"] == auth.TEACHER:
            teacher_view(fresh)
            return
        language = current_language(fresh)
        if language is None or st.session_state.get("view") == "language":
            language_page(fresh)
            return
        student_view(fresh, language)
        return

    if st.session_state.get("view") == "auth":
        auth_page()
    else:
        landing()


if __name__ == "__main__":
    main()
