"""
app.py — Interactive Kannada/Tulu literacy tutor (Streamlit).

Landing  : what the tool is, for a teacher deciding whether to use it.
Student  : a flashcard loop — see a letter or word with a picture, hear it, say
           it, get scored, advance — sequenced by the prerequisite graph
           (graph_engine), speech scoring (pronunciation) and media (media).
Teacher  : a dashboard of the class, reachable only by an account whose ROLE says
           teacher. The role is read from the database on every rerun, never from
           a session flag, so a student session has no path to it.

Accounts and password hashing live in auth.py; the visual system in ui.py.

A note on the interface: there are no emoji in it. Icons are Material Symbols,
drawn as vectors at the right size and weight; emoji render differently on every
device, sit at the wrong baseline, and read as decoration rather than as controls.
A child using this in a classroom needs an obvious "speak" button, not a picture
of a microphone in someone else's font.

Run:  streamlit run app.py
"""

import hashlib
import html
import os
import threading

import networkx as nx
import pandas as pd
import streamlit as st

from tutor import (
    auth, config, db, graph_engine, media,
    pronunciation, ui,
)

# Keys wiped on logout. Anything recording-related is prefixed "rec_".
# `confident_misses` is the per-concept benefit-of-the-doubt counter behind the
# grace rule in score_recording (see pronunciation.GRACE_MISSES).
_SESSION_KEYS = ("user", "concept", "last_result", "listen_audio", "scored_sig",
                 "confident_misses")

st.set_page_config(
    page_title="Kannada & Tulu Literacy Tutor",
    page_icon=":material/graphic_eq:",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _esc(value):
    return html.escape(str(value))


def _hide_sidebar():
    """The landing and sign-in pages have no sidebar to show."""
    st.markdown(
        "<style>[data-testid='stSidebar'],"
        "[data-testid='stSidebarCollapsedControl']{display:none !important;}</style>",
        unsafe_allow_html=True,
    )


# Model warm-up: load whisper once in the background at start, so the first Speak
# doesn't stall for the whole model load.
def _warm_model():
    try:
        pronunciation.get_model()
    except Exception:
        pass  # load_state() reports FAILED; the UI surfaces it


@st.cache_resource
def start_model_warmup():
    threading.Thread(target=_warm_model, daemon=True).start()
    return True


# The load is SETTLED once it can no longer change on its own: ready, or failed.
_SETTLED = (pronunciation.READY, pronunciation.FAILED)


def _status_caption():
    """
    Say what the speech recogniser is doing. Out loud, always.

    The first load takes ~8-10 seconds. The app used to show nothing at all
    during it — a child would tap the microphone and the page would simply sit
    there. The wait cannot be removed; the silence about it can.

    Writes to whatever container it is called in, because the polling wrapper
    below is a fragment and a fragment may not address st.sidebar itself — the
    sidebar caller wraps it in `with st.sidebar`.
    """
    state = pronunciation.load_state()

    if state == pronunciation.READY:
        if pronunciation.is_kannada_model():
            st.caption(":material/check_circle: Speech scoring ready")
        else:
            # Stock whisper's Kannada is too weak to grade a child fairly — say
            # so rather than silently marking correct answers wrong.
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
                   "(first time only, about 4-5 minutes)…")


def recogniser_status():
    """
    The status line — and, while the model is still coming up, the WAIT for it.

    This deliberately blocks instead of polling. Two polling designs were tried
    and both broke the page:

      * a plain render is never repainted (Streamlit renders once and stops), so
        the caption froze on "Waking…" while the recogniser was in fact live —
        the page claiming minutes of delay over an 8-second load;
      * an st.fragment(run_every=2) DID repaint, but it reruns while
        st.audio_input holds a live MediaRecorder, remounting the recorder faster
        than it tears down until the browser's main thread died ("Page
        Unresponsive" mid-recording). It is also called from two places in one
        script run (sidebar + student page), which collides.

    get_model() simply joins the warm-up thread's in-flight load via _MODEL_LOCK,
    so this waits exactly as long as the load has left to run — measured 6.6s from
    a cold start, and ZERO once loaded, because get_model() returns the cached
    instance without taking the lock. One spinner, once per server, then never
    again. Nothing to get stuck on.
    """
    if pronunciation.load_state() not in _SETTLED:
        with st.spinner("Waking the speech recogniser (first time only)…"):
            try:
                pronunciation.get_model()
            except Exception:
                pass  # load_state() is now FAILED; the caption below says so
    _status_caption()


# Scoring a recording. What the child is asked to say is `spoken_form`, NOT the
# displayed word. For a letter card those differ: the card shows ಅ, but the child
# says "ಅ ಅಮ್ಮ", because an isolated letter is too short for the recogniser to
# resolve (it comes back as ಮಾರ್ಕ್). See build_dataset.py for the measurements.
def score_recording(sid, concept, wav_bytes):
    """
    Score a browser recording. Sets st.session_state.last_result to one of:
      {"error": msg}                    — the recogniser failed outright
      {"retry": reason, ...}            — unusable audio; NOT a wrong answer
      {"word":…, "score":…, "correct":…}— a real score (mastery recorded)

    A bad recording never costs the child a mark and never advances them. That
    matters: a muted mic produces confident nonsense from Whisper, and the old
    build turned that into "you said it wrong".
    """
    # Decode, check, trim and normalize in one pass. A soft voice is amplified,
    # not refused — see the measurements in pronunciation.py. `samples` goes
    # straight to the recogniser as an array; there is no temp file to write.
    ok, reason, stats, samples = pronunciation.prepare_audio(wav_bytes)
    if not ok:
        st.session_state.last_result = {"retry": reason, "stats": stats}
        return

    msg = ("Listening to what you said…"
           if pronunciation.is_model_ready()
           else "Waking the speech recogniser (first time only)…")
    try:
        with st.spinner(msg):
            heard, confidence = pronunciation.transcribe_scored(samples)
    except Exception as e:
        st.session_state.last_result = {"error": str(e)}
        return

    if not heard.strip() or pronunciation.is_silence_filler(heard):
        # The recogniser produced nothing — either literally empty, or its
        # no-speech filler ("ಮುಕ್ತಾಯ"), which is what a microphone that captured
        # no voice comes back as. A capture problem, not a wrong answer — no
        # attempt is logged and the child stays on this card.
        st.session_state.last_result = {"retry": pronunciation.NO_SPEECH, "stats": stats}
        return

    expected, alternates = pronunciation.accepted_forms(concept)
    score, correct = pronunciation.score_pronunciation(expected, heard, alternates)

    # What does this attempt MEAN? classify_attempt() holds the whole "never blame
    # the child" policy: a HIT counts on any signal; a non-match is only ever a
    # real, logged wrong answer when the clip was audible, the recogniser was sure
    # of it, AND it has kept happening. A weak signal, an unconfident decode, or a
    # first confident non-match are all free retries — because on real-world audio
    # the recogniser will confidently mis-transcribe a correctly-spoken word, and
    # one such miss must never mark a child wrong. See pronunciation.GRACE_MISSES.
    cid = concept["concept_id"]
    misses = st.session_state.setdefault("confident_misses", {})
    outcome = pronunciation.classify_attempt(
        correct, stats.get("snr", 99), confidence, misses.get(cid, 0)
    )

    if outcome == pronunciation.OUTCOME_RETRY:
        # TOO_QUIET tells the child "the room was louder than your voice — move
        # closer". That is a claim about LEVEL, so it may only be made when the
        # clip was actually quiet. A close mic or a noise-cancelling headset (AGC
        # + suppression) lifts the room tone toward the voice, so a plainly loud
        # word measures snr 1.7-3.0 — under MIN_SNR — at an absolute peak of
        # 0.8-0.95. Keying the message on snr alone therefore told children who
        # were loud and clear to speak up: the "it says it can't hear me even
        # though I'm shouting" bug. The retry itself is unchanged and still free;
        # only what we claim about it is now checked against the level.
        reason = (pronunciation.TOO_QUIET
                  if (stats.get("snr", 99) < pronunciation.MIN_SNR
                      and stats.get("peak", 0.0) < pronunciation.LOUD_ENOUGH)
                  else pronunciation.NOT_RECOGNISED)
        st.session_state.last_result = {"retry": reason, "stats": stats}
        return

    if outcome == pronunciation.OUTCOME_SOFT:
        # A confident non-match, but inside the grace window: shown to the child
        # as an ordinary near-miss ("listen and say it once more"), yet NOT logged
        # and NOT counted — so a mis-heard-but-correct answer costs nothing.
        misses[cid] = misses.get(cid, 0) + 1
        st.session_state.last_result = {
            "word": concept["kannada_word"], "expected": expected,
            "translit": concept["transliteration"], "score": score,
            "correct": False, "heard": heard,
        }
        return

    # OUTCOME_CORRECT or OUTCOME_WRONG: a real attempt, logged and mastery-updating.
    if outcome == pronunciation.OUTCOME_WRONG:
        misses[cid] = misses.get(cid, 0) + 1   # keeps the parking count moving
    else:
        misses.pop(cid, None)                  # cleared: they got it

    graph_engine.update_mastery(sid, cid, correct, raw_score=score)
    st.session_state.last_result = {
        "word": concept["kannada_word"],
        "expected": expected,
        "translit": concept["transliteration"],
        "score": score,
        "correct": correct,
        "heard": heard,
    }
    if correct:
        # Only a correct answer moves on; a wrong one stays so the child can
        # hear the word again and retry it immediately.
        st.session_state.concept = None
        st.session_state.pop("listen_audio", None)


_FEATURES = [
    ("record_voice_over",
     "It listens, and it is fair about it",
     "Speech is scored by sound, not by spelling — and a softly-spoken answer is "
     "amplified, never rejected. A recording it cannot hear is a free retry, "
     "never a wrong mark."),
    ("account_tree",
     "It teaches in the right order",
     "121 letters and words in a prerequisite graph. Nothing appears before what "
     "it is built from, and a child stuck on one concept is moved on rather than "
     "left grinding."),
    ("insights",
     "Teachers see who is stuck",
     "Per-child mastery, attempt history and a curriculum map — so the answer to "
     "'who needs me today' takes one glance, not a term."),
]


def landing():
    _hide_sidebar()
    ui.narrow(1040)

    total = graph_engine.load_graph().number_of_nodes()
    ui.card(
        f"""
        <div class="hero">
          <span class="eyebrow">Read &middot; Listen &middot; Speak</span>
          <h1>Learn to read Kannada<br/>by saying it out loud</h1>
          <div class="script kn">ಅ&nbsp;&nbsp;ಆ&nbsp;&nbsp;ಇ&nbsp;&nbsp;ಈ&nbsp;&nbsp;ಉ</div>
          <p class="lede">
            A speaking tutor for Kannada and Tulu. See the letter, hear it, say it —
            and get told honestly whether you got it, by a recogniser that has been
            measured against {total} concepts rather than trusted.
          </p>
        </div>
        """
    )

    ui.spacer(18)
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        if st.button("Start learning", type="primary", width="stretch",
                     icon=":material/arrow_forward:"):
            st.session_state.view = "auth"
            st.session_state.auth_tab = "signup"
            st.rerun()
    with c2:
        if st.button("I already have an account", width="stretch",
                     icon=":material/login:"):
            st.session_state.view = "auth"
            st.session_state.auth_tab = "login"
            st.rerun()

    ui.spacer(26)
    cols = st.columns(3, gap="medium")
    for col, (icon, title, body) in zip(cols, _FEATURES):
        with col:
            ui.card(
                f'<div class="feature">'
                f'<div class="ico">'
                f'<span class="material-symbols-rounded">{icon}</span></div>'
                f"<h3>{title}</h3><p>{body}</p></div>"
            )

    ui.spacer(26)
    concepts = graph_engine.load_graph().number_of_nodes()
    stats = [(str(concepts), "concepts"), ("2", "languages"),
             ("100%", "ASR-validated"), ("0", "cloud calls")]
    scols = st.columns(4, gap="small")
    for col, (n, label) in zip(scols, stats):
        with col:
            ui.card(f'<div class="stat"><div class="n">{n}</div>'
                     f'<div class="l">{label}</div></div>')

    ui.spacer(20)
    st.markdown(
        '<p class="tiny">Speech is recognised on this machine. No recording of a '
        "child's voice is ever sent anywhere.</p>",
        unsafe_allow_html=True,
    )


def _finish_login(user):
    st.session_state.user = user
    st.session_state.concept = None
    st.session_state.last_result = None
    st.session_state.view = "app"
    st.rerun()


def auth_page():
    _hide_sidebar()
    ui.narrow(560)

    ui.card(
        """
        <div class="hero" style="padding:34px 30px 26px">
          <h1 style="font-size:clamp(26px,4vw,38px)">Kannada &amp; Tulu Tutor</h1>
          <p class="lede">Sign in to pick up where you left off.</p>
        </div>
        """
    )
    ui.spacer(16)

    if st.button("Back", icon=":material/arrow_back:"):
        st.session_state.view = "landing"
        st.rerun()

    tab_in, tab_up = st.tabs(["Sign in", "Create an account"])

    with tab_in:
        with st.form("login_form"):
            u = st.text_input("Username", key="li_u")
            p = st.text_input("Password", type="password", key="li_p")
            go = st.form_submit_button("Sign in", type="primary", width="stretch",
                                       icon=":material/login:")
        if go:
            try:
                _finish_login(auth.login(u, p))
            except auth.AuthError as e:
                st.error(str(e), icon=":material/lock:")

    with tab_up:
        with st.form("signup_form"):
            name = st.text_input("Your name", placeholder="Shown on your progress")
            u2 = st.text_input("Username", placeholder="letters and numbers")
            p2 = st.text_input("Password", type="password",
                               help=f"At least {auth.MIN_PASSWORD} characters.")
            is_teacher = st.checkbox("I am a teacher")
            pin = st.text_input(
                "Teacher PIN", type="password",
                help="A teacher account can see every child's name and score, so "
                     "creating one needs the PIN set by whoever deployed this.",
            )
            make = st.form_submit_button("Create account", type="primary",
                                         width="stretch",
                                         icon=":material/person_add:")
        if make:
            try:
                user = auth.register(
                    u2, p2, display_name=name or u2,
                    role=auth.TEACHER if is_teacher else auth.STUDENT,
                    teacher_pin=pin,
                )
                _finish_login(user)
            except auth.AuthError as e:
                st.error(str(e), icon=":material/error:")

        # A shipped default PIN on a public URL is the same as no PIN at all. Say
        # so where the person who can fix it will actually see it.
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
}


def render_word_card(concept):
    """Picture, the letter or word itself, its meaning, and the Tulu form."""
    img_path = media.get_image(concept["image_file"], label=concept["kannada_word"])
    left, mid, right = st.columns([1, 3, 1])
    with mid:
        st.image(img_path, width="stretch")

    tier = concept.get("level") or "Basic"
    is_letter = concept["category"] in ("vowels", "consonants")

    # Tulu is shown only when we actually have it. Tulu is under-documented and
    # has no standard orthography; inventing a form would teach a child a word
    # that does not exist, so a blank column simply renders nothing.
    tulu = concept.get("tulu_word", "").strip()
    tulu_html = (
        f'<div class="tulu"><b>Tulu</b> &nbsp;<span class="kn">{_esc(tulu)}</span></div>'
        if tulu else ""
    )

    # Whenever the thing to SAY is not the thing printed on the card, say so
    # explicitly rather than leaving the child to guess. That happens for every
    # letter ("ಅ" is shown, "ಅ ಅಮ್ಮ" is spoken) and for the few words too short
    # for the recogniser to resolve alone ("ತಲೆ" is shown, "ನನ್ನ ತಲೆ" is spoken).
    spoken = concept["spoken_form"]
    say_html = ""
    if spoken.strip() != concept["kannada_word"].strip():
        if is_letter:
            hint = ("the letter, then a word that starts with it &mdash; "
                    f'<span class="kn">{_esc(concept.get("anchor_word", ""))}</span>')
        else:
            gloss = concept.get("phrase_gloss", "")
            hint = (f"say the whole phrase &mdash; &ldquo;{_esc(gloss)}&rdquo;"
                    if gloss else "say the whole phrase")
        say_html = (
            f'<div class="say-box"><p class="lbl">Say this</p>'
            f'<div class="val kn">{_esc(spoken)}</div>'
            f'<div class="hint">{hint}</div></div>'
        )

    ui.card(
        f'<div class="kannada-word kn">{_esc(concept["kannada_word"])}</div>'
        f'<div class="translit">{_esc(concept["transliteration"])}</div>'
        f'<div class="meaning">{_esc(concept["english_meaning"])}</div>'
        f"{tulu_html}"
        f'<div class="badges">'
        f'<span class="badge badge-cat">{_esc(concept["category"])}</span>'
        f'<span class="badge badge-diff">{_esc(tier)}</span></div>'
        f"{say_html}",
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

    # `heard` is the recogniser's output — user-influenced text going into an
    # unsafe_allow_html block, so it is escaped. Same for the CSV fields.
    word = _esc(res["word"])
    heard = _esc(res.get("heard") or "—")
    pct = int(round(res["score"] * 100))

    if res["correct"]:
        if not res.get("_celebrated"):
            st.balloons()
            res["_celebrated"] = True
        st.markdown(
            f'<div class="fb fb-ok"><div class="hd">Correct &mdash; '
            f'<span class="kn">{word}</span></div>'
            f'<div class="sub">{pct}% match &nbsp;·&nbsp; heard: '
            f'<span class="kn">{heard}</span></div>'
            f'<div class="meter"><i style="width:{pct}%"></i></div></div>',
            unsafe_allow_html=True,
        )
    else:
        # A child is not shown a failing percentage — "45% match" reads as a
        # grade and discourages. Just the encouragement and, quietly, what we
        # heard so a teacher can see why it did not match.
        st.markdown(
            f'<div class="fb fb-no"><div class="hd">Not quite &mdash; listen and '
            f'say <span class="kn">{word}</span> once more</div>'
            f'<div class="sub">heard: <span class="kn">{heard}</span></div></div>',
            unsafe_allow_html=True,
        )


def current_concept(student_id):
    """The concept on screen, fetched lazily and cached for the session."""
    if st.session_state.get("concept") is None:
        st.session_state.concept = graph_engine.get_next_concept(student_id)
    return st.session_state.concept


def _clear_learning_state():
    for k in list(st.session_state.keys()):
        if k in _SESSION_KEYS or k.startswith("rec_"):
            st.session_state.pop(k, None)


def logout():
    _clear_learning_state()
    st.session_state.view = "landing"
    st.rerun()


def app_sidebar(user, mastered=None, total=None, by_level=None):
    st.sidebar.markdown(
        '<div class="sb-brand">Kannada &amp; Tulu Tutor</div>'
        '<div class="sb-sub">Read · Listen · Speak</div>',
        unsafe_allow_html=True,
    )
    st.sidebar.write("")
    role_label = "Teacher" if user["role"] == auth.TEACHER else "Learner"
    st.sidebar.markdown(
        f'<div class="learner"><div class="rl">{role_label}</div>'
        f'<div class="nm">{_esc(user["display_name"])}</div></div>',
        unsafe_allow_html=True,
    )

    if total:
        st.sidebar.progress(mastered / total if total else 0.0)
        pct = int(round(mastered / total * 100)) if total else 0
        st.sidebar.caption(f"{mastered} of {total} mastered  ·  {pct}%")

    # The three tiers, shown as their own small lines so the leveled progression
    # is visible — a child sees the alphabet fill up, then words, then phrases.
    if by_level:
        for lv, (m, t) in by_level.items():
            if t:
                st.sidebar.caption(f"{lv} · {m}/{t}")

    with st.sidebar:  # a fragment cannot address st.sidebar itself
        recogniser_status()
    st.sidebar.write("")
    if st.sidebar.button("Log out", width="stretch", icon=":material/logout:"):
        logout()


def student_view(user):
    sid = user["student_id"]
    mastered, total = graph_engine.mastery_summary(sid)
    app_sidebar(user, mastered, total, graph_engine.mastery_by_level(sid))
    ui.narrow(760)

    render_feedback()

    concept = current_concept(sid)
    if concept is None:
        ui.card(
            f'<div class="hero" style="padding:38px 30px">'
            f"<h1>Every concept mastered</h1>"
            f'<p class="lede">You finished all {total} letters and words. '
            f"Outstanding work.</p></div>"
        )
        ui.spacer()
        if st.button("Practise again from the start", width="stretch",
                     icon=":material/restart_alt:"):
            db.reset_student(sid)
            _clear_learning_state()
            st.session_state.user = user       # stay logged in
            st.session_state.view = "app"
            st.rerun()
        return

    render_word_card(concept)
    ui.spacer()

    # --- Step 1: Listen -------------------------------------------------- #
    # The audio path lives in session_state so the player survives the rerun a
    # button click causes; a bare st.audio inside the click branch would vanish.
    if st.button("Listen to the word", width="stretch", icon=":material/volume_up:"):
        try:
            audio_path = media.get_audio(concept["concept_id"], concept["spoken_form"])
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

    # --- Step 2: Speak ---------------------------------------------------- #
    # st.audio_input records in the BROWSER: the child presses to start and stop,
    # so we never grab silence before they are ready (a fixed-length server-side
    # recorder did exactly that, and was the original "always 0%" bug).
    # The recorder is keyed per concept, so advancing gives a fresh, empty one.
    ui.spacer(6)
    st.markdown("##### Now you say it")

    # Until the model is up, saying so beats a page that looks broken.
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
        # Hash the bytes so the same clip is never scored twice across reruns.
        sig = hashlib.md5(wav_bytes).hexdigest()
        if wav_bytes and st.session_state.get("scored_sig") != sig:
            st.session_state.scored_sig = sig
            score_recording(sid, concept, wav_bytes)
            st.rerun()

    st.caption(
        "The first time, your browser asks for microphone permission — choose Allow."
    )


def _pyplot():
    """pyplot costs ~0.6s to import and only the mastery map needs it, so it
    stays out of the student's cold start."""
    import matplotlib

    matplotlib.use("Agg")  # headless-safe
    import matplotlib.pyplot as plt

    return plt


def _draw_concept_graph(mastery_map):
    """
    The curriculum DAG for one student: green = mastered, amber = attempted but
    weak, grey = not started. Laid out left-to-right by prerequisite depth.
    """
    G = graph_engine.load_graph()

    pos = {}
    for depth, layer in enumerate(nx.topological_generations(G)):
        layer = sorted(layer)
        for i, node in enumerate(layer):
            pos[node] = (depth, -(i - (len(layer) - 1) / 2))

    colors = []
    for n in G.nodes:
        score = mastery_map.get(n, 0.0)
        if score >= db.MASTERY_THRESHOLD:
            colors.append("#2DD4BF")
        elif score > 0:
            colors.append("#FBBF24")
        else:
            colors.append("#D7DBE3")

    plt = _pyplot()
    # 121 concepts: label every node and it becomes an unreadable smear, so the
    # map shows structure and colour, and the table above it carries the detail.
    fig, ax = plt.subplots(figsize=(11, 7))
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#C9CFDE", arrows=False, width=0.7)
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=colors, node_size=140,
                           edgecolors="#FFFFFF", linewidths=0.8)
    ax.set_title("Curriculum map — each dot is a concept, left to right by prerequisite",
                 color="#171A2B", fontsize=11, fontweight="bold")
    ax.axis("off")
    fig.tight_layout()
    return fig


def _class_overview(students):
    concept_total = graph_engine.load_graph().number_of_nodes()
    rows, sum_mastered, sum_total = [], 0, 0
    for s in students:
        mastered, total = graph_engine.mastery_summary(s["id"])
        sum_mastered += mastered
        sum_total += total
        rows.append({
            "Student": s["name"],
            "Mastered": mastered,
            "Concepts": total,
            # 0..100 so ProgressColumn's "%.0f%%" label reads as a percentage.
            "Progress": (mastered / total * 100) if total else 0.0,
        })
    total_attempts = len(db.get_attempts())
    avg_pct = int(round(sum_mastered / sum_total * 100)) if sum_total else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Students", len(students))
    m2.metric("Concepts", concept_total)
    m3.metric("Attempts", total_attempts)
    m4.metric("Avg mastery", f"{avg_pct}%")

    ui.spacer()
    st.subheader("All students")
    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        width="stretch",
        column_config={
            "Progress": st.column_config.ProgressColumn(
                "Progress", min_value=0, max_value=100, format="%.0f%%"
            )
        },
    )


def _student_detail(students):
    name_to_id = {f'{s["name"]} (#{s["id"]})': s["id"] for s in students}
    picked = st.selectbox("Inspect a student", list(name_to_id.keys()))
    sid = name_to_id[picked]

    progress = graph_engine.get_student_progress(sid)
    mastered = sum(1 for p in progress if p["mastered"])
    attempted = sum(1 for p in progress if p["attempts"] > 0)
    struggling = [p for p in progress if p["attempts"] >= 2 and not p["mastered"]]
    parked = [p for p in progress if p["parked"]]

    d1, d2, d3 = st.columns(3)
    d1.metric("Mastered", f"{mastered} / {len(progress)}")
    d2.metric("Attempted", attempted)
    d3.metric("Struggling", len(struggling))

    # The single most useful thing a teacher can see: who is stuck on what.
    if struggling:
        ui.spacer()
        st.subheader("Needs help")
        st.caption(
            f"Tried at least twice and still below the mastery threshold. After "
            f"{graph_engine.PARK_AFTER_ATTEMPTS} tries the tutor moves the child "
            f"on rather than leaving them stuck — those are marked 'moved on', "
            f"and are the ones to sit down with."
        )
        st.dataframe(
            pd.DataFrame([{
                "Concept": p["concept_id"],
                "Kannada": p["kannada_word"],
                "Roman": p["transliteration"],
                "Meaning": p["english_meaning"],
                "Tries": p["attempts"],
                "Mastery": p["mastery_score"],
                "Moved on": p["parked"],
            } for p in sorted(struggling, key=lambda p: (-p["parked"], -p["attempts"]))]),
            hide_index=True, width="stretch",
            column_config={
                "Mastery": st.column_config.ProgressColumn(
                    "Mastery", min_value=0.0, max_value=1.0, format="%.2f"),
                "Moved on": st.column_config.CheckboxColumn("Moved on"),
            },
        )
        if parked:
            st.info(
                f"{len(parked)} concept(s) were tried "
                f"{graph_engine.PARK_AFTER_ATTEMPTS}+ times without success. The "
                f"child has been moved on so they are not stuck, but these are "
                f"not counted as mastered.",
                icon=":material/info:",
            )

    df = pd.DataFrame(progress)[[
        "concept_id", "kannada_word", "transliteration", "english_meaning",
        "category", "level", "mastery_score", "attempts", "mastered",
    ]]

    ui.spacer()
    st.subheader("Every concept")
    st.dataframe(
        df,
        hide_index=True,
        width="stretch",
        column_config={
            "concept_id": "ID",
            "kannada_word": "Kannada",
            "transliteration": "Roman",
            "english_meaning": "Meaning",
            "category": "Category",
            "level": "Tier",
            "mastery_score": st.column_config.ProgressColumn(
                "Mastery", min_value=0.0, max_value=1.0, format="%.2f"
            ),
            "attempts": "Tries",
            "mastered": st.column_config.CheckboxColumn("Mastered"),
        },
    )

    ui.spacer()
    st.subheader("Curriculum map")
    st.caption("Teal — mastered.  Amber — attempted but still weak.  Grey — not started.")
    mastery_map = {p["concept_id"]: p["mastery_score"] for p in progress}
    fig = _draw_concept_graph(mastery_map)
    st.pyplot(fig)
    _pyplot().close(fig)

    ui.spacer()
    st.subheader("Session history")
    attempts_log = db.get_attempts(sid)
    if attempts_log:
        hist = pd.DataFrame(attempts_log)[["timestamp", "concept_id", "score", "correct"]]
        hist["correct"] = hist["correct"].map({1: "Correct", 0: "Wrong"})
        st.dataframe(
            hist, hide_index=True, width="stretch",
            column_config={
                "timestamp": "When",
                "concept_id": "Concept",
                "score": st.column_config.NumberColumn("Match", format="%.2f"),
                "correct": "Result",
            },
        )
    else:
        st.caption("No attempts recorded yet for this student.")

    # utf-8-sig BOM so Excel renders the Kannada column instead of mojibake.
    csv = df.to_csv(index=False).encode("utf-8-sig")
    # Student names are free text — keep only filename-safe characters.
    raw_name = picked.split(" (")[0]
    safe_name = "".join(c if (c.isalnum() or c in "-_") else "_" for c in raw_name) or "student"
    ui.spacer()
    st.download_button(
        "Export this student's progress (CSV)",
        data=csv,
        file_name=f"{safe_name}_progress.csv",
        mime="text/csv",
        width="stretch",
        icon=":material/download:",
    )


def teacher_view(user):
    app_sidebar(user)
    st.title("Teacher dashboard")

    students = db.get_all_students()
    if not students:
        st.info("No students yet — ask a learner to create an account and begin.",
                icon=":material/school:")
        return

    tab_overview, tab_detail = st.tabs(["Class overview", "Student detail"])
    with tab_overview:
        _class_overview(students)
    with tab_detail:
        _student_detail(students)


# Main — the router. The teacher dashboard is reached by ROLE, read from the
# database on every rerun. There is no "I am a teacher" selector: a student
# session cannot select its way into the class list, because nothing it can set
# is consulted.
def main():
    db.init_db()
    auth.init_auth()
    ui.inject()
    if not os.environ.get("TUTOR_SKIP_WARMUP"):
        start_model_warmup()  # cached: the thread starts once per server

    user = st.session_state.get("user")
    if user:
        # Re-read the role from the DB rather than trusting the session copy.
        fresh = auth.get_user(user["id"])
        if not fresh:
            logout()
            return
        if fresh["role"] == auth.TEACHER:
            teacher_view(fresh)
        else:
            student_view(fresh)
        return

    if st.session_state.get("view") == "auth":
        auth_page()
    else:
        landing()


if __name__ == "__main__":
    main()
