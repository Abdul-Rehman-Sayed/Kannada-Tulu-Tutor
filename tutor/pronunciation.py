import io
import os
import threading
import unicodedata

try:
    from indic_transliteration import sanscript

    _TRANSLIT = True
except ImportError:
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
except ImportError:
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
    return _LOAD_STATE


def load_error():
    return _LOAD_ERROR


_MODEL_LOCK = threading.Lock()
_INFER_LOCK = threading.Lock()

_STRIP_CHARS = set(" \t\r\n/[]().,!?;:\"'`।॥~")


def is_model_ready():
    return _MODEL is not None


def model_name():
    return _MODEL_NAME


def is_kannada_model():
    return bool(_MODEL_NAME) and "kannada" in _MODEL_NAME.lower()


def _candidates():
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
UNSCOREABLE = "unscoreable"

OUTCOME_CORRECT = "correct"
OUTCOME_RETRY = "retry"
OUTCOME_SOFT = "soft"
OUTCOME_WRONG = "wrong"

GRACE_MISSES = 2

MIN_CONFIDENT_LOGPROB = -0.45
MAX_NO_SPEECH_PROB = 0.6


def gate_disabled():
    return os.environ.get("TUTOR_MIC_GATE", "").strip().lower() in ("off", "0", "false", "no")


def _decode(audio_bytes):
    from faster_whisper.audio import decode_audio

    return decode_audio(io.BytesIO(audio_bytes), sampling_rate=16000)


def _frame_peaks(samples):
    import numpy as np

    n = (len(samples) // _FRAME) * _FRAME
    if n == 0:
        return np.zeros(0, dtype="float32")
    return np.abs(samples[:n].reshape(-1, _FRAME)).max(axis=1)


def analyse(samples):
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
    ok, reason, stats, _ = prepare_audio(audio_bytes)
    return ok, reason, stats


def transcribe_scored(audio, language="kn"):
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
    text, _confidence = transcribe_scored(audio, language)
    return text


def is_low_confidence(confidence):
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
    if not text:
        return False
    got = _normalize(text)
    return bool(got) and got in {_normalize(t) for t in _SILENCE_FILLERS}


UNSCOREABLE_ALONE = {"ಘ", "ಛ", "ಠ", "ಢ", "ಧ"}


def is_scoreable(concept):
    """Can the recogniser judge this concept at all?

    Everything except a handful of letters that only exist inside words.
    """
    if (concept or {}).get("category") not in ("vowels", "consonants"):
        return True
    return (concept or {}).get("kannada_word", "").strip() not in UNSCOREABLE_ALONE


def classify_attempt(correct, snr, confidence, prior_confident_misses,
                     scoreable=True):
    if correct:
        return OUTCOME_CORRECT
    if not scoreable:
        return OUTCOME_RETRY
    if snr < MIN_SNR:
        return OUTCOME_RETRY
    if is_low_confidence(confidence):
        return OUTCOME_RETRY
    if prior_confident_misses < GRACE_MISSES:
        return OUTCOME_SOFT
    return OUTCOME_WRONG


def _detect_scheme(text):
    for ch in text:
        o = ord(ch)
        for lo, hi, scheme in _INDIC_BLOCKS:
            if lo <= o <= hi:
                return scheme
    return None


def _romanize(text):
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
    if not text:
        return ""
    text = _romanize(text).strip().lower()
    return "".join(ch for ch in text if ch not in _STRIP_CHARS)


def _similarity(a, b):
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return _ratio(a, b)


def score_pronunciation(expected_ipa_or_word, whisper_output, alternates=()):
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
    """What counts as having said this concept.

    A letter is accepted as itself, or repeated - "a", or "a, a", which is how
    a child answers a card that plays the sound twice.  It is not accepted as
    its example word: the card used to ask for "a amma" and take either, which
    would now let a child pass the card for a by saying amma without ever
    saying the letter.
    """
    spoken = concept.get("spoken_form") or concept.get("kannada_word", "")
    if (concept.get("category") or "") in ("vowels", "consonants"):
        letter = spoken.strip()
        return spoken, ([f"{letter} {letter}"] if letter else [])
    anchor = (concept.get("anchor_word") or "").strip()
    return spoken, ([anchor] if anchor else [])
