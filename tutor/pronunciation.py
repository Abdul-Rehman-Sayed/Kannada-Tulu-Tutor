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

try:
    from indic_transliteration import sanscript

    _TRANSLIT = True
except ImportError:  # pragma: no cover
    sanscript = None
    _TRANSLIT = False

_INDIC_BLOCKS = [
    (0x0C80, 0x0CFF, "KANNADA"),
    (0x0900, 0x097F, "DEVANAGARI"),
    (0x0C00, 0x0C7F, "TELUGU"),
    (0x0D00, 0x0D7F, "MALAYALAM"),
    (0x0B80, 0x0BFF, "TAMIL"),
]

try:
    from rapidfuzz.distance import Indel

    def _ratio(a, b):
        return Indel.normalized_similarity(a, b)

    _LEV_BACKEND = "rapidfuzz (MIT)"
except ImportError:  # pragma: no cover
    def _indel_distance(a, b):
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

PRONUNCIATION_THRESHOLD = 0.65

MAX_NEW_TOKENS = 96


def estimate_tokens(text):
    """
    A deliberately generous upper bound on the tokens a Kannada string decodes to.

    Used to check MAX_NEW_TOKENS still covers the curriculum WITHOUT loading the
    model — the tokenizer lives inside the model directory, which a fresh clone
    may not have yet, and this check has to run in the fast test suite where the
    truncation bug would have been caught in the first place.

    Calibrated against the shipped tokenizer: the worst ratio measured across all
    273 concepts is 1.9 tokens per character, so 2.2 plus a constant for the
    decoder's own prompt tokens stays above every real value.
    """
    return int(len(text or "") * 2.2) + 8

_DECODE_OPTS = dict(
    beam_size=1,
    temperature=0.0,
    max_new_tokens=MAX_NEW_TOKENS,
    condition_on_previous_text=False,
    without_timestamps=True,
)

LOCAL_MODEL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "whisper-kannada-small-ct2"
)
KANNADA_MODEL = "ukta-app/whisper-kannada-ct2"
FALLBACK_MODEL = "small"

_MODEL = None
_MODEL_NAME = None

IDLE, LOADING, READY, FAILED = "idle", "loading", "ready", "failed"
_LOAD_STATE = IDLE
_LOAD_ERROR = None


def load_state():
    """One of IDLE / LOADING / READY / FAILED — what the recogniser is doing."""
    return _LOAD_STATE


def load_error():
    """Why the model failed to load, or None."""
    return _LOAD_ERROR
_MODEL_LOCK = threading.Lock()
_INFER_LOCK = threading.Lock()

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
    if os.path.isdir(LOCAL_MODEL_DIR):
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
            if _MODEL is None:
                from faster_whisper import WhisperModel

                _LOAD_STATE = LOADING
                candidates = _candidates()
                last_error = None
                for allow_download in (False, True):
                    for name in candidates:
                        try:
                            _MODEL = WhisperModel(
                                name, device="cpu", compute_type="int8",
                                local_files_only=not allow_download,
                            )
                            _MODEL_NAME = name
                            _LOAD_STATE = READY
                            return _MODEL
                        except Exception as e:
                            last_error = e
                _LOAD_STATE = FAILED
                _LOAD_ERROR = str(last_error)
                raise RuntimeError(
                    f"could not load any ASR model from {candidates}"
                ) from last_error
    return _MODEL


MIN_SNR = 4.0
LOUD_ENOUGH = 0.02
SILENCE_PEAK = LOUD_ENOUGH
MIN_SPEECH_SECONDS = 0.35
MAX_SPEECH_SECONDS = 15.0

_FRAME = 400
_TARGET_PEAK = 0.95
_TRIM_PAD = 0.25

TOO_SHORT = "too_short"
TOO_QUIET = "too_quiet"
TOO_LONG = "too_long"
UNREADABLE = "unreadable"
NO_SPEECH = "no_speech"
NOT_RECOGNISED = "not_recognised"

OUTCOME_CORRECT = "correct"
OUTCOME_RETRY = "retry"
OUTCOME_SOFT = "soft"
OUTCOME_WRONG = "wrong"

GRACE_MISSES = 2

MIN_CONFIDENT_LOGPROB = -0.45
MAX_NO_SPEECH_PROB = 0.6


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

    floor = float(np.percentile(e, 10))
    peak = float(np.percentile(e, 95))
    snr = peak / max(floor, 1e-6)
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
        return False, UNREADABLE, {"seconds": 0.0, "peak": 0.0, "snr": 0.0}, None

    if samples is None or samples.size == 0:
        return False, TOO_SHORT, {"seconds": 0.0, "peak": 0.0, "snr": 0.0}, None

    samples = samples.astype("float32")
    samples -= float(np.mean(samples))

    stats, speech = analyse(samples)

    if stats["seconds"] < MIN_SPEECH_SECONDS:
        return False, TOO_SHORT, stats, None
    if stats["seconds"] > MAX_SPEECH_SECONDS:
        return False, TOO_LONG, stats, None

    loud = stats["peak"] >= LOUD_ENOUGH
    audible = stats["snr"] >= MIN_SNR and stats["frames"] >= 1
    if not (loud or audible) and not gate_disabled():
        return False, TOO_QUIET, stats, None

    if speech.size:
        pad = int(_TRIM_PAD * 16000 / _FRAME)
        lo = max(0, int(speech[0]) - pad) * _FRAME
        hi = min(len(samples), (int(speech[-1]) + 1 + pad) * _FRAME)
        samples = samples[lo:hi]

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
    if snr < MIN_SNR:
        return OUTCOME_RETRY
    if is_low_confidence(confidence):
        return OUTCOME_RETRY
    if prior_confident_misses < GRACE_MISSES:
        return OUTCOME_SOFT
    return OUTCOME_WRONG


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
    if not got:
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
