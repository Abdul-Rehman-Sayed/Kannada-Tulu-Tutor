"""
pronunciation.py — speech transcription + fuzzy pronunciation scoring.

Uses faster-whisper ("small") to transcribe a child's spoken word (Kannada,
language="kn"), then scores it against the expected word with a *normalized
Levenshtein similarity* rather than exact string matching.

Why fuzzy, not exact? Automatic speech recognition on children's speech is
unreliable (see Wasnik 2024) — exact ASR string matching would reject correct
attempts constantly. A similarity threshold tolerates the small transcription
errors that dominate child-speech ASR while still catching genuinely wrong words.

Public API:
    prepare_audio(audio_bytes) -> (ok, reason, stats, samples)
    transcribe(path_or_samples) -> str
    transcribe_scored(path_or_samples) -> (str, confidence)
    is_low_confidence(confidence) -> bool
    score_pronunciation(expected_ipa_or_word, whisper_output) -> (score, correct)
    accepted_forms(concept) -> (expected, alternates)
"""

import io
import os
import threading
import unicodedata

# Cross-script phonetic normalization. The faster-whisper "small" model often
# transcribes Kannada speech into a *different* Brahmic script (e.g. it writes
# Devanagari अम्म for the sound "amma"). Comparing raw scripts would score a
# perfect pronunciation as 0. So we romanize any Indic script to a common Latin
# (IAST) form before comparing — matching by sound, not by script. Optional:
# falls back to raw comparison if the library isn't installed.
try:
    from indic_transliteration import sanscript

    _TRANSLIT = True
except ImportError:  # pragma: no cover
    sanscript = None
    _TRANSLIT = False

# First Unicode code point of each Brahmic block we might see, mapped to its
# indic_transliteration scheme name. Used to detect the script of a string.
_INDIC_BLOCKS = [
    (0x0C80, 0x0CFF, "KANNADA"),
    (0x0900, 0x097F, "DEVANAGARI"),
    (0x0C00, 0x0C7F, "TELUGU"),
    (0x0D00, 0x0D7F, "MALAYALAM"),
    (0x0B80, 0x0BFF, "TAMIL"),
]

# Similarity backend.
#
# We use an indel-based, sum-normalized similarity (the "Levenshtein ratio")
# rather than 1 - distance/max_len. The ratio is more forgiving when ASR adds or
# drops a sound — whisper hearing "ammava" for "amma" scores 0.80 (accepted)
# instead of 0.67 (rejected) — while a genuinely wrong word ("appa") still scores
# ~0.50 and is rejected. That matters for noisy child-speech recognition.
#
# LICENCE, NOT PREFERENCE: the obvious package here is `python-Levenshtein`, and
# this project used it — but it is GPL-2.0-or-later, and importing it would drag
# this whole application under the GPL. RapidFuzz is MIT and computes exactly the
# same quantity: Levenshtein.ratio IS Indel.normalized_similarity. Swapping them
# changes no score (test_pronunciation.py asserts the values). Do not "simplify"
# this back to python-Levenshtein.
try:
    from rapidfuzz.distance import Indel

    def _ratio(a, b):
        return Indel.normalized_similarity(a, b)

    _LEV_BACKEND = "rapidfuzz (MIT)"
except ImportError:  # pragma: no cover - exercised only without the wheel
    def _indel_distance(a, b):
        # Edit distance allowing only insertions/deletions (a substitution costs
        # 2 = one delete + one insert). This is what Levenshtein.ratio is built on.
        if a == b:
            return 0
        if not a:
            return len(b)
        if not b:
            return len(a)
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, 1):
            cur = [i]
            for j, cb in enumerate(b, 1):
                if ca == cb:
                    cur.append(prev[j - 1])
                else:
                    cur.append(min(prev[j] + 1, cur[j - 1] + 1))
            prev = cur
        return prev[-1]

    def _ratio(a, b):
        total = len(a) + len(b)
        return 1.0 if total == 0 else (total - _indel_distance(a, b)) / total

    _LEV_BACKEND = "builtin (pure python)"

# Score at/above which a pronunciation is accepted as correct.
#
# MEASURED, not chosen. `python tune_threshold.py` scores all 121 concepts'
# audio against their own accepted forms (121 correct answers) and against other
# concepts' forms (1452 wrong answers), then sweeps the threshold:
#
#     threshold   accepts correct   accepts WRONG
#       0.55            99%             3.8%      <- best Youden's J (0.954)
#       0.65            97%             1.9%      <- chosen (J = 0.948)
#       0.70            94%             0.9%      <- the old guessed value
#
# J peaks at 0.55, but the two are within noise of each other and 0.55 lets
# through nearly twice as many WRONG pronunciations. In a tool that teaches
# children to speak, a false accept is the more expensive error: it silently
# certifies a mispronunciation as correct. 0.65 keeps 97% of correct answers
# while halving that risk. The old 0.70 rejected 6% of correct pronunciations —
# children being told they were wrong when they were right.
PRONUNCIATION_THRESHOLD = 0.65

# Decoding options for a single spoken word. These are not micro-optimizations —
# without them a 1-second clip takes ~70-130s on CPU, because faster-whisper's
# defaults are tuned for long-form audio:
#
#   temperature       Default is a fallback *sweep* [0.0, 0.2 ... 1.0]. When a
#                     decode trips the compression-ratio or log-prob threshold,
#                     the whole clip is re-decoded at each higher temperature —
#                     up to 6 passes. Near-silent child speech trips it almost
#                     every time. Pinning 0.0 means one greedy pass, and makes
#                     scoring deterministic (the same clip always scores alike).
#   max_new_tokens    Whisper answers a near-silent 30s window by hallucinating
#                     a repetition loop ("ರಿತರಿತರಿತ…") until it hits the 448-token
#                     limit. The longest word in vocabulary.csv is 8 tokens, so
#                     24 is ample headroom and caps the runaway.
#   condition_on_previous_text / without_timestamps
#                     Both only earn their cost across many segments; one word
#                     has none, and conditioning primes further repetition.
#
# beam_size=1 (greedy) is faster than a beam search and plenty for one word.
# Measured on this corpus: ~70s -> ~2.9s, with no loss of transcription quality.
# Do NOT add vad_filter here: it measured *slower* (3.8s) and its silence
# trimming can clip a quiet child's word down to nothing.
MAX_NEW_TOKENS = 24

_DECODE_OPTS = dict(
    beam_size=1,
    temperature=0.0,
    max_new_tokens=MAX_NEW_TOKENS,
    condition_on_previous_text=False,
    without_timestamps=True,
)

# Which ASR model to use.
#
# Stock multilingual whisper "small" CANNOT do this task. Measured against this
# project's own (clean, synthetic) TTS audio it scored only 2 of the 8 vocabulary
# words: its Kannada is weak enough that it transcribes into Devanagari ("अम्मः"
# for ಅಮ್ಮ), and on an isolated word — with none of the surrounding speech it was
# trained on — it hallucinates a repetition loop ("ಸಾರಿಕಿಕ" for ಮನೆ). A Kannada
# fine-tune of the *same size* scores 7 of 8 at the same speed and footprint.
#
# Resolution order — the first that loads wins:
#   1. $TUTOR_WHISPER_MODEL — escape hatch; a size name, Hub id, or local path.
#   2. models/whisper-kannada-small-ct2 — built from the authoritative Speech Lab
#      (IIT Madras) weights by `python convert_model.py`. Never touches the
#      network at runtime, so this is what a classroom/offline deploy should ship.
#   3. KANNADA_MODEL — the same fine-tune, already converted, fetched from the
#      Hub once and cached. Keeps a fresh clone working with no build step.
#   4. "small" — stock whisper, so the app still boots on a machine that can
#      reach neither. Scoring is largely broken here; is_kannada_model() reports
#      this so the UI can warn rather than silently mark children wrong.
LOCAL_MODEL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "whisper-kannada-small-ct2"
)
KANNADA_MODEL = "ukta-app/whisper-kannada-ct2"  # int8 CT2 of vasista22/whisper-kannada-small
FALLBACK_MODEL = "small"

_MODEL = None  # lazily loaded, cached across calls (loading is expensive)
_MODEL_NAME = None  # which candidate actually loaded

# What the loader is doing right now, so the UI can SAY so. The first load takes
# ~8-10s (longer if it has to fetch the model), and the app used to spend that
# time looking simply frozen — no spinner, no message, nothing. "It just gets
# stuck and there's no info about what's happening" is a UI bug, not a slow model:
# the wait is unavoidable, being silent about it is not.
IDLE, LOADING, READY, FAILED = "idle", "loading", "ready", "failed"
_LOAD_STATE = IDLE
_LOAD_ERROR = None


def load_state():
    """One of IDLE / LOADING / READY / FAILED — what the recogniser is doing."""
    return _LOAD_STATE


def load_error():
    """Why the model failed to load, or None."""
    return _LOAD_ERROR
# Streamlit runs each browser session in its own thread. These locks stop two
# sessions from double-loading the model or hammering the CPU with concurrent
# inference on a single classroom laptop.
_MODEL_LOCK = threading.Lock()
_INFER_LOCK = threading.Lock()

# Characters stripped before comparison: whitespace, IPA delimiters, punctuation,
# danda marks, and the "~" residue left by anusvara/candrabindu after romanizing.
_STRIP_CHARS = set(" \t\r\n/[]().,!?;:\"'`।॥~")


def is_model_ready():
    """True once the model is loaded in memory (used to show status in the UI)."""
    return _MODEL is not None


def model_name():
    """Identifier of the loaded model, or None before the first load."""
    return _MODEL_NAME


def is_kannada_model():
    """
    False when we fell back to stock whisper, whose Kannada is too weak to score
    a child fairly. The UI warns instead of silently marking correct words wrong.
    """
    return bool(_MODEL_NAME) and "kannada" in _MODEL_NAME.lower()


def _candidates():
    """Model identifiers to try, best first."""
    override = os.environ.get("TUTOR_WHISPER_MODEL")
    if override:
        return [override]
    names = []
    if os.path.isdir(LOCAL_MODEL_DIR):  # else it'd be read as a Hub repo id
        names.append(LOCAL_MODEL_DIR)
    names.append(KANNADA_MODEL)
    names.append(FALLBACK_MODEL)
    return names


def get_model():
    """Load (once) and return the faster-whisper model.

    Thread-safe: concurrent callers block on the lock while the first one loads,
    then all share the same instance.

    IMPORTANT: the first pass is offline-only (local_files_only=True). By default
    faster-whisper contacts the HuggingFace Hub on every construction to validate
    the cache — on a slow or offline network that call can hang for a long time
    (this was the "Scoring… forever" bug). Only once no candidate is cached do we
    allow a single download pass. That ordering also means an already-cached
    *better* model always beats a downloadable one.
    """
    global _MODEL, _MODEL_NAME, _LOAD_STATE, _LOAD_ERROR
    if _MODEL is None:
        with _MODEL_LOCK:
            if _MODEL is None:  # re-check — another thread may have just loaded it
                from faster_whisper import WhisperModel

                _LOAD_STATE = LOADING
                candidates = _candidates()
                last_error = None
                for allow_download in (False, True):
                    for name in candidates:
                        try:
                            # CPU + int8 keeps it runnable on a laptop with no GPU.
                            _MODEL = WhisperModel(
                                name, device="cpu", compute_type="int8",
                                local_files_only=not allow_download,
                            )
                            _MODEL_NAME = name
                            _LOAD_STATE = READY
                            return _MODEL
                        except Exception as e:  # not cached / not downloadable
                            last_error = e
                _LOAD_STATE = FAILED
                _LOAD_ERROR = str(last_error)
                raise RuntimeError(
                    f"could not load any ASR model from {candidates}"
                ) from last_error
    return _MODEL


# Microphone quality control + preprocessing.
#
# Whisper does not fail on a silent clip — it *hallucinates*, confidently (this
# model answers silence with "ಮುಕ್ತಾಯ", "the end"), and the child is then told
# they said the wrong word. A muted mic produces a clip that looks perfectly
# valid. So a recording is inspected BEFORE it reaches the recogniser, and one
# that cannot contain speech is bounced back as "I didn't hear you" — a free
# retry, never a wrong answer.
#
# WHAT THE CHECK MUST ASK. This gate used to reject any clip whose peak fell
# below a fixed level (0.02). That is the wrong question. Peak level is set by
# the mic's input gain and how far the child sits from it — not by whether they
# spoke. Measured on this corpus (scratch/crux, reproduced in test_pronunciation):
#
#   room            raw peak   SNR    whisper           old gate
#   quiet, soft      0.0027     30    ಈರುಳ್ಳಿ  -> 1.00    REJECTED  <- the bug
#   noisy, soft      0.0055    1.7    ಮುಕ್ತಾಯ -> 0.00    rejected
#
# The clip SEVEN TIMES quieter than the old threshold transcribes perfectly,
# while a *louder* one is noise. Absolute level did not merely fail to separate
# these — it ranked them backwards, and children who spoke correctly but softly
# were told "I couldn't hear anything". What actually separates them is whether
# the sound rises above the room: signal-to-noise, and whether ANY frame clears
# the noise floor. Both are scale-free, so mic gain cannot fool them.
#
# A quiet-but-clean clip is then NORMALIZED up rather than refused: the recogniser
# only needs the shape of the sound, and it is a far better speech detector than
# any threshold we can write.
MIN_SNR = 4.0                # speech peak : noise floor. Below ~2 it is room tone.
LOUD_ENOUGH = 0.02           # a peak this high is obviously real sound — accept it
                             # on level alone. Needed because SNR is undefined for a
                             # clip with no silence in it (a pure tone, or a recording
                             # trimmed so tightly that the floor IS the speech).
SILENCE_PEAK = LOUD_ENOUGH   # back-compat alias; no longer used as a veto
MIN_SPEECH_SECONDS = 0.35    # shorter than the shortest real utterance
MAX_SPEECH_SECONDS = 15.0    # a child left the recorder running

_FRAME = 400                 # 25 ms at 16 kHz — one analysis frame
_TARGET_PEAK = 0.95          # normalize a soft voice up to here before recognising
_TRIM_PAD = 0.25             # keep this much silence around the word (s); Whisper
                             # needs a little run-up or it clips the first phoneme

# Reasons audio_quality() can reject a clip; the UI maps these to friendly text.
TOO_SHORT = "too_short"
TOO_QUIET = "too_quiet"
TOO_LONG = "too_long"
UNREADABLE = "unreadable"
NO_SPEECH = "no_speech"
NOT_RECOGNISED = "not_recognised"

# What a scored attempt MEANS — the outcome classify_attempt() returns. These are
# distinct on purpose: only OUTCOME_WRONG is a real wrong answer that gets logged
# and can eventually park a stuck child. The other three never cost a mark.
OUTCOME_CORRECT = "correct"   # matched — logged, mastery updated, child advances
OUTCOME_RETRY = "retry"       # unusable capture (quiet/unrecognised) — free retry
OUTCOME_SOFT = "soft"         # confident non-match, still within grace — free retry
OUTCOME_WRONG = "wrong"       # confident non-match past grace — a logged wrong answer

# Benefit of the doubt before a confident non-match becomes a WRONG mark.
#
# MEASURED, not chosen. The confidence gate (is_low_confidence) rests on the
# premise that a *confident* decode which does not match means the child said a
# different word. On clean TTS that held. On real-world audio it does NOT: the
# recogniser will occasionally, and confidently, mis-transcribe a correctly-spoken
# word — measured on this corpus, ಉ ಉಪ್ಪು degraded with ordinary room noise comes
# back as ಉಕ್ಕು at avg_logprob -0.17 (well inside "confident"), scoring 0.50. The
# old code marked that child wrong. No decode setting removes this: a beam search
# only cut it from 5/60 to 3/60 healthy-signal clips while adding 19% latency and
# a new failure of its own, so the fix cannot live in the recogniser.
#
# What DOES separate "correct word, mis-heard once" from "a different word" is
# repetition: a child saying the right word lands a clean decode within a couple
# of tries, while a child saying the wrong word never does. So a confident
# non-match is a free retry (SOFT) for the first GRACE_MISSES tries on a concept,
# and only a WRONG — logged, counted toward parking — once it keeps happening.
# This never causes a false ACCEPT (nothing below the threshold is accepted) and
# it keeps the parking rule alive: a genuinely stuck child still accumulates WRONG
# marks after the grace window and is moved on. See app.score_recording.
GRACE_MISSES = 2

# The recogniser's OWN certainty that it made out a real word, used to tell a
# genuine wrong answer from a clip we simply could not recognise.
#
# faster-whisper reports two numbers per segment: avg_logprob (the mean per-token
# log-probability — near 0 is confident, more negative is a guess) and
# no_speech_prob. Characterised on this corpus (clean TTS, plus the same audio
# buried in noise): a word the model actually heard — RIGHT or WRONG — sits at
# avg_logprob -0.00..-0.17, while a clip it could not make out drifts to
# -0.25..-0.56, and pure noise reports a high no_speech_prob. That gap is what
# separates "the child said a different word" (confident, low score -> a real
# wrong answer, logged, and eligible for parking) from "we could not make the
# child out" (unconfident -> a capture failure -> a free retry, never a wrong
# mark). Before this, a mis-recognition on a clip with a healthy signal level was
# shown to the child as "wrong, 45%" — the "it can't even hear me" bug.
#
# These are conservative: only a CLEARLY unconfident decode becomes a retry, so a
# genuinely wrong word is still marked wrong. They were set from synthetic audio
# and should be re-checked against real child recordings when a corpus exists.
MIN_CONFIDENT_LOGPROB = -0.45   # below this the recogniser was guessing
MAX_NO_SPEECH_PROB = 0.6        # above this it heard no speech at all


def gate_disabled():
    """
    True when TUTOR_MIC_GATE=off — the microphone gate is bypassed entirely.

    The gate's thresholds are absolute levels, and absolute level is a fact about
    MIC GAIN, not about whether a child spoke. On hardware that captures far below
    the level this corpus was tuned on (measured in the field: a Bluetooth headset
    delivering an absolute peak of 0.011, ~40 dB below a normal laptop mic, while
    the speaker was shouting), a correctly-spoken word can fail BOTH tests — too
    low for LOUD_ENOUGH, and with too little silence in the clip for the SNR test
    to have a floor to measure against. The child is then told "the room was louder
    than your voice" no matter how loudly they speak.

    Rather than guess a new threshold per device, this switch removes the gate and
    lets the recogniser — a far better speech detector than any level rule — decide.
    Read from the environment on every call so it can be flipped without a code
    edit. Default is ON: turning it off costs the protection the gate exists for
    (Whisper answers silence with a confident "ಮುಕ್ತಾಯ"), which is why
    is_silence_filler() catches that specific hallucination as a free retry.

        set TUTOR_MIC_GATE=off        (Windows, cmd)
        $env:TUTOR_MIC_GATE="off"     (PowerShell)
    """
    return os.environ.get("TUTOR_MIC_GATE", "").strip().lower() in ("off", "0", "false", "no")


def _decode(audio_bytes):
    """
    Any browser container -> mono float32 @ 16 kHz.

    Uses faster-whisper's own PyAV decoder, not the `wave` module. `wave` reads
    only integer-PCM WAV: it raises on the 32-bit-float WAV some browsers emit
    ("unknown format: 3") and cannot open WebM/Opus at all — and the old code
    treated every such failure as "unreadable, let it through", silently
    disabling the microphone check on exactly those browsers. PyAV reads them
    all, and resamples, so everything downstream sees one predictable format.
    """
    from faster_whisper.audio import decode_audio

    return decode_audio(io.BytesIO(audio_bytes), sampling_rate=16000)


def _frame_peaks(samples):
    """Peak amplitude of each 25 ms frame — the profile the checks run on."""
    import numpy as np

    n = (len(samples) // _FRAME) * _FRAME
    if n == 0:
        return np.zeros(0, dtype="float32")
    return np.abs(samples[:n].reshape(-1, _FRAME)).max(axis=1)


def analyse(samples):
    """
    Measure a decoded clip: how loud the speech is, how loud the room is, and
    which frames actually contain sound. Returns (stats, speech_frame_indices).
    """
    import numpy as np

    e = _frame_peaks(samples)
    if e.size == 0:
        return {"seconds": 0.0, "peak": 0.0, "floor": 0.0, "snr": 0.0, "frames": 0}, e

    floor = float(np.percentile(e, 10))   # the room, between words
    peak = float(np.percentile(e, 95))    # the word itself
    snr = peak / max(floor, 1e-6)
    # A frame is speech if it clears the room by a clear margin AND carries a
    # real share of the clip's energy. The second half stops a noise-only clip,
    # whose floor is near zero, from calling its own hiss "speech".
    speech = np.where(e > max(floor * 3.0, peak * 0.15))[0]

    stats = {
        "seconds": round(len(samples) / 16000.0, 2),
        "peak": round(float(np.abs(samples).max()), 5),
        "floor": round(floor, 5),
        "snr": round(snr, 1),
        "frames": int(speech.size),
    }
    return stats, speech


def prepare_audio(audio_bytes):
    """
    Decode, check, and CLEAN UP a browser recording in one pass.

    Returns (ok, reason, stats, samples). `ok` False means do not score and do
    not mark the child wrong — ask them to speak again. When ok, `samples` is a
    16 kHz mono float32 array, DC-corrected, trimmed to the spoken word, and
    normalized to a healthy level: a soft voice is amplified rather than refused.

    Trimming matters for speed as well as accuracy — Whisper re-encodes a fresh
    30-second window per seek, so a 5s clip of mostly silence costs several
    encoder passes. Cutting it to the word measured 24.0s -> 3.4s on one clip.
    """
    import numpy as np

    try:
        samples = _decode(audio_bytes)
    except Exception:
        # Undecodable by PyAV: not audio at all. Nothing sane to score.
        return False, UNREADABLE, {"seconds": 0.0, "peak": 0.0, "snr": 0.0}, None

    if samples is None or samples.size == 0:
        return False, TOO_SHORT, {"seconds": 0.0, "peak": 0.0, "snr": 0.0}, None

    samples = samples.astype("float32")
    samples -= float(np.mean(samples))     # a DC offset inflates every peak

    stats, speech = analyse(samples)

    if stats["seconds"] < MIN_SPEECH_SECONDS:
        return False, TOO_SHORT, stats, None
    if stats["seconds"] > MAX_SPEECH_SECONDS:
        return False, TOO_LONG, stats, None

    # The silence test. Loud enough is self-evidently sound. Otherwise it must
    # rise above the room — level alone says nothing (see the note above).
    loud = stats["peak"] >= LOUD_ENOUGH
    audible = stats["snr"] >= MIN_SNR and stats["frames"] >= 1
    if not (loud or audible) and not gate_disabled():
        return False, TOO_QUIET, stats, None

    # Trim to the spoken word, keeping a little air either side.
    if speech.size:
        pad = int(_TRIM_PAD * 16000 / _FRAME)
        lo = max(0, int(speech[0]) - pad) * _FRAME
        hi = min(len(samples), (int(speech[-1]) + 1 + pad) * _FRAME)
        samples = samples[lo:hi]

    # Normalize. This is what actually rescues the softly-spoken child.
    m = float(np.abs(samples).max())
    if m > 1e-6:
        samples = samples * (_TARGET_PEAK / m)

    return True, "", stats, samples


def audio_quality(audio_bytes):
    """(ok, reason, stats) — the check half of prepare_audio(), for callers that
    only want the verdict (the tests, and any caller not doing the transcription)."""
    ok, reason, stats, _ = prepare_audio(audio_bytes)
    return ok, reason, stats


def transcribe_scored(audio, language="kn"):
    """
    Transcribe audio and also report the recogniser's own confidence.

    Returns (text, confidence). `audio` is a path to a file, or a decoded 16 kHz
    mono float32 numpy array (what prepare_audio returns — no temp file needed).
    `confidence` is {"avg_logprob": float|None, "no_speech_prob": float|None},
    aggregated across segments (length-weighted mean log-prob; worst no-speech).
    Both are None when the model returned no segments at all.

    This is the confidence the app uses to tell a wrong answer from a clip it
    could not recognise — see MIN_CONFIDENT_LOGPROB and is_low_confidence().
    """
    if isinstance(audio, str):
        if not os.path.exists(audio):
            raise FileNotFoundError(f"audio file not found: {audio}")

    model = get_model()
    # model.transcribe() returns a LAZY generator — the actual inference happens
    # while it is consumed, so materialising the segments must stay inside the lock.
    with _INFER_LOCK:
        segments, _info = model.transcribe(audio, language=language, **_DECODE_OPTS)
        segments = list(segments)

    text = "".join(segment.text for segment in segments).strip()
    if segments:
        weights = [max(s.end - s.start, 1e-3) for s in segments]
        total = sum(weights)
        avg_logprob = sum(s.avg_logprob * w for s, w in zip(segments, weights)) / total
        no_speech = max(s.no_speech_prob for s in segments)
        confidence = {"avg_logprob": float(avg_logprob), "no_speech_prob": float(no_speech)}
    else:
        confidence = {"avg_logprob": None, "no_speech_prob": None}
    return text, confidence


def transcribe(audio, language="kn"):
    """
    Transcribe audio to text — the plain-string form used by the validators and
    the threshold tuner. Returns the recognized text, possibly empty.
    FileNotFoundError if a path is given and does not exist.
    """
    text, _confidence = transcribe_scored(audio, language)
    return text


def is_low_confidence(confidence):
    """
    True when the recogniser's own certainty says it did not make out a real word.

    A non-match on such a clip is a capture/recognition failure — a free retry —
    not a wrong answer. A confident decode that simply does not match the target
    IS a wrong answer (the child said a different word) and returns False here.
    """
    if not confidence:
        return False
    alp = confidence.get("avg_logprob")
    nsp = confidence.get("no_speech_prob")
    if alp is not None and alp < MIN_CONFIDENT_LOGPROB:
        return True
    if nsp is not None and nsp > MAX_NO_SPEECH_PROB:
        return True
    return False


# What this model says when it is handed no speech.
#
# Whisper does NOT return an empty string on silence — it emits a filler, and this
# fine-tune's is ಮುಕ್ತಾಯ ("the end"). Measured: digital silence decodes to ಮುಕ್ತಾಯ at
# avg_logprob -0.27, faint room tone likewise. That is a disaster for the two
# guards above, because -0.27 reads as CONFIDENT (it clears MIN_CONFIDENT_LOGPROB
# -0.45) and its no_speech_prob of 0.26 sits well under MAX_NO_SPEECH_PROB 0.6. So
# neither catches it, and a child whose microphone captured nothing is told they
# said the wrong word — confirmed from a real session: a 5.6s recording with only
# 0.3s above the noise floor came back as ಮುಕ್ತಾಯ and scored 0.36, "wrong".
#
# None of the 167 concepts contains these forms (checked), so matching them costs
# no real answer. A filler decode means we heard nothing: a free retry, never a mark.
_SILENCE_FILLERS = ("ಮುಕ್ತಾಯ", "ಸಮಾಪ್ತಿ")


def is_silence_filler(text):
    """True when the recogniser returned its no-speech filler instead of a word."""
    if not text:
        return False
    got = _normalize(text)
    return bool(got) and got in {_normalize(t) for t in _SILENCE_FILLERS}


def classify_attempt(correct, snr, confidence, prior_confident_misses):
    """
    Decide what a scored recording MEANS. Pure and side-effect-free so the whole
    "never blame the child" policy sits in one testable place instead of being
    scattered through the Streamlit view.

    Returns one of OUTCOME_CORRECT / OUTCOME_RETRY / OUTCOME_SOFT / OUTCOME_WRONG.
    Only OUTCOME_WRONG is a real wrong answer (logged, counts toward parking); the
    other three never cost the child a mark.

      correct                 did score_pronunciation accept it?
      snr                     stats["snr"] for this clip
      confidence              the dict transcribe_scored() returned
      prior_confident_misses  how many confident non-matches this child has
                              already had on THIS concept (0 on the first try)

    The ordering matters. A HIT is a hit on any signal — if we matched it, they
    said it. Otherwise a non-match is only ever a real wrong answer when the clip
    was audible AND the recogniser was sure of it AND it has kept happening past
    the grace window; every earlier or weaker case is a free retry.
    """
    if correct:
        return OUTCOME_CORRECT
    # Deliberately `snr` ALONE, not "snr or it was loud". The gate's LOUD_ENOUGH
    # escape hatch lets a clip through on level, and loud ROOM NOISE clears it
    # easily (measured: an empty noisy room peaks at 0.14 with no voice in it, and
    # the recogniser answers it at avg_logprob -0.30, i.e. "confident"). This test
    # is the net that catches exactly that. Adding a loudness get-out here was
    # tried and reverted: it routed a no-voice clip to OUTCOME_WRONG — a logged
    # wrong mark against a child who never spoke. See score_recording for the
    # separate question of what to TELL the child, which is where the loud-clip
    # bug actually lived.
    if snr < MIN_SNR:
        return OUTCOME_RETRY          # too quiet to have captured the word
    if is_low_confidence(confidence):
        return OUTCOME_RETRY          # audible, but the recogniser was guessing
    if prior_confident_misses < GRACE_MISSES:
        return OUTCOME_SOFT           # confident non-match, but give it another go
    return OUTCOME_WRONG              # confident, repeated non-match — a real miss


def _detect_scheme(text):
    """Return the indic_transliteration scheme name for the first Indic char, else None."""
    for ch in text:
        o = ord(ch)
        for lo, hi, scheme in _INDIC_BLOCKS:
            if lo <= o <= hi:
                return scheme
    return None


def _romanize(text):
    """
    Convert any Brahmic-script text to a bare Latin phonetic form: transliterate
    to IAST, then decompose and drop combining diacritics (so ā->a, ṃ->m, ṅ->n).
    ASCII/transliteration input passes through unchanged (minus accents).
    """
    if _TRANSLIT:
        scheme = _detect_scheme(text)
        if scheme:
            try:
                text = sanscript.transliterate(text, getattr(sanscript, scheme), sanscript.IAST)
            except Exception:
                pass
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text


def _normalize(text):
    """Romanize, lower-case, and strip whitespace/punctuation for a phonetic key."""
    if not text:
        return ""
    text = _romanize(text).strip().lower()
    return "".join(ch for ch in text if ch not in _STRIP_CHARS)


def _similarity(a, b):
    """Normalized Levenshtein similarity (ratio) in [0, 1]."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return _ratio(a, b)


def score_pronunciation(expected_ipa_or_word, whisper_output, alternates=()):
    """
    Compare what the child was asked to say against what Whisper heard.

    Both strings are normalized (romanized, case/punctuation-insensitive) and
    compared with a normalized Levenshtein similarity. Pass the expected Kannada
    text; IPA or transliteration also work, since everything is romanized first.

    `alternates` are additional forms that also count as correct, and the score
    is the BEST match across all of them. This exists for letter cards. The child
    is asked to say "ಆ ಆನೆ" (the letter, then its anchor word), but the recogniser
    routinely swallows the isolated leading letter and returns just "ಆನೆ" — or
    even "ನೆ". That is an artefact of the recogniser, not a mistake by the child,
    and marking them wrong for it is precisely the bug this app had. So the
    anchor word alone is passed as an alternate and also accepted.

    This widens what counts as correct, so it was checked rather than assumed:
    tune_threshold.py measures both the true-accept and false-accept rate with
    alternates in play, and the threshold below is set from that measurement.

    Returns (score, correct); score in [0, 1]. Empty input scores 0.0 (a miss,
    never an exception).
    """
    got = _normalize(whisper_output)
    if not got:  # Whisper returned empty — a miss, not an error.
        return 0.0, False

    candidates = [expected_ipa_or_word, *alternates]
    best = 0.0
    for cand in candidates:
        norm = _normalize(cand)
        if not norm:
            continue
        best = max(best, _similarity(norm, got))

    score = round(best, 4)
    return score, score >= PRONUNCIATION_THRESHOLD


def accepted_forms(concept):
    """
    The forms that count as a correct spoken answer for a concept.

    A word is just itself. A letter is "letter + anchor word", but the anchor
    word alone is accepted too (see score_pronunciation). Keeping this in one
    place means the app, the validator and the threshold tuner all agree on what
    "correct" means — when they disagreed, the app graded children on rules the
    validator never checked.
    """
    spoken = concept.get("spoken_form") or concept.get("kannada_word", "")
    anchor = (concept.get("anchor_word") or "").strip()
    return spoken, ([anchor] if anchor else [])
