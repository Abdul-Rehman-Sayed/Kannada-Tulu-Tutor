"""
test_pronunciation.py — the speech scorer, including regressions for the bugs
that made this app mark correct children wrong.

Runs entirely offline (no whisper, no network) unless you hand it an audio file:

    python test_pronunciation.py                    # scorer unit tests
    python test_pronunciation.py my_recording.wav ಅಮ್ಮ   # + real transcription
"""

import csv
import io
import os
import sys
import wave

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from tutor import pronunciation


def _check(label, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    if not ok:
        print(f"        expected {want!r}, got {got!r}")
    return ok


def scorer_tests():
    print(f"backend: {pronunciation._LEV_BACKEND}   "
          f"transliteration: {pronunciation._TRANSLIT}   "
          f"threshold: {pronunciation.PRONUNCIATION_THRESHOLD}\n")
    ok = True

    print("Cross-script matching (whisper writes Kannada in Devanagari):")
    score, correct = pronunciation.score_pronunciation("ಅಮ್ಮ", "अम्मँ")
    ok &= _check("ಅಮ್ಮ vs Devanagari अम्मँ is accepted", correct, True)

    print("\nWrong words are still rejected:")
    for expected, heard, label in [
        ("ಅಮ್ಮ", "ಅಪ್ಪ", "appa is not amma"),
        ("ನೀರು", "ಹಸು", "hasu is not neeru"),
        ("ಅ", "ಇ", "i is not a"),
    ]:
        _, correct = pronunciation.score_pronunciation(expected, heard)
        ok &= _check(label, correct, False)

    print("\nNoisy-but-correct speech is accepted (why the ratio, not exact match):")
    score, correct = pronunciation.score_pronunciation("ಅಮ್ಮ", "ಅಮ್ಮಾ")
    ok &= _check("ಅಮ್ಮಾ (extra vowel sign) accepted", correct, True)

    print("\nLetter cards accept the anchor word alone:")
    letter = {"spoken_form": "ಆ ಆನೆ", "anchor_word": "ಆನೆ", "kannada_word": "ಆ"}
    expected, alternates = pronunciation.accepted_forms(letter)
    for heard, label in [("ಆ ಆನೆ", "full form"), ("ಆನೆ", "anchor only"), ("ನೆ", "clipped anchor")]:
        _, correct = pronunciation.score_pronunciation(expected, heard, alternates)
        ok &= _check(f"{label}: {heard!r} accepted for ಆ", correct, True)
    _, correct = pronunciation.score_pronunciation(expected, "ಹಸು", alternates)
    ok &= _check("saying ಹಸು on the ಆ card is rejected", correct, False)

    print("\nA word card has no anchor (nothing extra is accepted):")
    word = {"spoken_form": "ಹಸು", "anchor_word": "", "kannada_word": "ಹಸು"}
    expected, alternates = pronunciation.accepted_forms(word)
    ok &= _check("no alternates for a word", alternates, [])

    print("\nEmpty / silent input never crashes and never passes:")
    score, correct = pronunciation.score_pronunciation("ಅಮ್ಮ", "")
    ok &= _check("empty transcription scores 0.0", score, 0.0)
    ok &= _check("empty transcription is not correct", correct, False)

    return ok


def _wav(seconds, amplitude, rate=16000):
    """A synthetic WAV clip, for the microphone quality gate."""
    import io

    n = int(seconds * rate)
    tone = (amplitude * 32767 * np.sin(2 * np.pi * 220 * np.arange(n) / rate)).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(tone.tobytes())
    return buf.getvalue()


def mic_tests():
    """
    The microphone gate. Whisper does not fail on a silent clip — it hallucinates
    a word, confidently, and the child is then told they said the wrong thing. A
    muted or unplugged mic must be caught BEFORE it reaches the recogniser.
    """
    print("\nMicrophone quality gate:")
    ok = True

    good, reason, stats = pronunciation.audio_quality(_wav(1.0, 0.5))
    ok &= _check(f"a normal 1.0s clip is scored (peak={stats['peak']})", good, True)

    silent, reason, _ = pronunciation.audio_quality(_wav(1.0, 0.0))
    ok &= _check("a silent clip (muted mic) is rejected", silent, False)
    ok &= _check("  ...and the reason is TOO_QUIET", reason, pronunciation.TOO_QUIET)

    short, reason, _ = pronunciation.audio_quality(_wav(0.1, 0.5))
    ok &= _check("a 0.1s clip is rejected as too short", short, False)
    ok &= _check("  ...and the reason is TOO_SHORT", reason, pronunciation.TOO_SHORT)

    long_, reason, _ = pronunciation.audio_quality(_wav(20.0, 0.5))
    ok &= _check("a 20s clip is rejected as too long", long_, False)
    ok &= _check("  ...and the reason is TOO_LONG", reason, pronunciation.TOO_LONG)

    junk, reason, _ = pronunciation.audio_quality(b"not a wav file at all")
    ok &= _check("undecodable audio is rejected", junk, False)
    ok &= _check("  ...and the reason is UNREADABLE", reason, pronunciation.UNREADABLE)

    quiet_ok, _, stats = pronunciation.audio_quality(_wav(0.8, 0.06))
    ok &= _check(f"a softly-spoken answer is still scored (peak={stats['peak']})", quiet_ok, True)

    return ok


def _clip(seconds, amplitude, noise, rate=16000):
    """A word-shaped burst inside a quiet lead/tail, as a real recording arrives.

    `amplitude` is the voice, `noise` the room. A real mic never returns a bare
    tone: there is always a floor, and the ratio between the two is the whole
    question the gate has to answer. Quantized to 16-bit, like the browser's.
    """
    import io

    rng = np.random.default_rng(7)
    n = int(seconds * rate)
    t = np.arange(n) / rate
    env = np.sin(np.pi * np.arange(n) / n) ** 2
    voice = amplitude * env * (np.sin(2 * np.pi * 150 * t) + 0.5 * np.sin(2 * np.pi * 430 * t)) / 1.5
    lead = rng.normal(0, noise, int(1.0 * rate))
    tail = rng.normal(0, noise, int(1.2 * rate))
    body = voice + rng.normal(0, noise, n)
    x = np.concatenate([lead, body, tail])

    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def soft_voice_tests():
    """
    REGRESSION — "I said the exact word and it says it couldn't hear anything."

    The gate used to veto any clip peaking below 0.02, which is a statement about
    microphone gain, not about whether a child spoke. Measured against the real
    recogniser: a clip peaking at 0.0027 in a quiet room transcribes at 1.00,
    while a LOUDER one (0.0055) in a noisy room is pure hallucination. Level
    ranked them backwards. What separates them is signal-to-noise.

    So: a soft voice in a quiet room must be ACCEPTED however faint it is, and a
    noisy room with no voice in it must still be REJECTED.
    """
    print("\nSoft-voice regression (the 'couldn't hear anything' bug):")
    ok = True

    faint, reason, stats = pronunciation.audio_quality(_clip(0.9, 0.010, 0.00005))
    ok &= _check(
        f"a faint voice in a quiet room is ACCEPTED "
        f"(peak={stats['peak']} — far below the old {pronunciation.LOUD_ENOUGH} veto; "
        f"snr={stats['snr']})",
        faint, True,
    )

    drowned, reason, stats = pronunciation.audio_quality(_clip(0.9, 0.004, 0.004))
    ok &= _check(f"a voice drowned by room noise is rejected (snr={stats['snr']})",
                 drowned, False)
    ok &= _check("  ...and the reason is TOO_QUIET", reason, pronunciation.TOO_QUIET)

    empty, reason, stats = pronunciation.audio_quality(_clip(0.9, 0.0, 0.002))
    ok &= _check(f"an empty room (no voice at all) is rejected (snr={stats['snr']})",
                 empty, False)

    good, _, stats, samples = pronunciation.prepare_audio(_clip(0.9, 0.010, 0.00005))
    if good and samples is not None:
        peak = float(np.abs(samples).max())
        ok &= _check(f"the faint clip is normalized up for the recogniser (peak={peak:.2f})",
                     peak > 0.9, True)
        ok &= _check(f"...and trimmed to the word ({len(samples)/16000:.2f}s of a 3.1s recording)",
                     len(samples) / 16000 < 2.0, True)
    else:
        ok &= _check("the faint clip survives preprocessing", False, True)

    return ok


def confidence_tests():
    """
    REGRESSION — "it says 45% match when it can't even hear me."

    A non-match on a clip the recogniser could not make out must be a free retry,
    not a wrong mark. is_low_confidence() reads the model's own certainty to tell
    a genuine wrong answer (a confident decode of a different word) from a clip we
    simply failed to recognise. Characterised in pronunciation.py: a word the
    model actually heard sits near avg_logprob 0, a clip it guessed at drifts well
    below MIN_CONFIDENT_LOGPROB, and noise reports a high no_speech_prob.
    """
    print("\nRecogniser-confidence gate (the 'says 45% when it can't hear me' bug):")
    ok = True

    ok &= _check("a confident decode is NOT low-confidence (a real wrong answer)",
                 pronunciation.is_low_confidence(
                     {"avg_logprob": -0.05, "no_speech_prob": 0.0}), False)
    ok &= _check("an unconfident decode IS low-confidence (a free retry)",
                 pronunciation.is_low_confidence(
                     {"avg_logprob": -0.9, "no_speech_prob": 0.0}), True)
    ok &= _check("a high no-speech probability IS low-confidence",
                 pronunciation.is_low_confidence(
                     {"avg_logprob": -0.1, "no_speech_prob": 0.95}), True)
    ok &= _check("no confidence at all is treated as confident (never masks a wrong)",
                 pronunciation.is_low_confidence(None), False)
    ok &= _check("empty segment stats do not crash and read as confident",
                 pronunciation.is_low_confidence(
                     {"avg_logprob": None, "no_speech_prob": None}), False)
    return ok


def grace_tests():
    """
    REGRESSION — "I said it right and it marked me wrong."

    On real-world (noisy) audio the recogniser confidently mis-transcribes a
    correctly-spoken word — measured: ಉ ಉಪ್ಪು -> ಉಕ್ಕು at avg_logprob -0.17,
    scoring 0.50. The confidence gate cannot catch this (the decode IS confident),
    so a single confident non-match must be a free retry, not a wrong mark. It
    only becomes a real, logged wrong answer once it keeps happening — which is
    what still lets the parking rule move a genuinely stuck child on.
    """
    print("\nGrace rule (the 'said it right, marked wrong' bug):")
    ok = True
    confident = {"avg_logprob": -0.17, "no_speech_prob": 0.0}
    healthy_snr = pronunciation.MIN_SNR + 10

    ok &= _check("a match is CORRECT however weak the signal",
                 pronunciation.classify_attempt(True, 0.0, confident, 0),
                 pronunciation.OUTCOME_CORRECT)
    ok &= _check("a non-match on a quiet clip is a free RETRY",
                 pronunciation.classify_attempt(False, 0.0, confident, 0),
                 pronunciation.OUTCOME_RETRY)
    ok &= _check("a non-match the recogniser was unsure of is a free RETRY",
                 pronunciation.classify_attempt(
                     False, healthy_snr, {"avg_logprob": -0.9, "no_speech_prob": 0.0}, 0),
                 pronunciation.OUTCOME_RETRY)

    for prior in range(pronunciation.GRACE_MISSES):
        ok &= _check(f"confident non-match #{prior + 1} (within grace) is SOFT, never wrong",
                     pronunciation.classify_attempt(False, healthy_snr, confident, prior),
                     pronunciation.OUTCOME_SOFT)
    ok &= _check("a confident non-match PAST the grace window is a real WRONG answer",
                 pronunciation.classify_attempt(
                     False, healthy_snr, confident, pronunciation.GRACE_MISSES),
                 pronunciation.OUTCOME_WRONG)

    ok &= _check("a persistently wrong child still produces WRONG marks (parking survives)",
                 pronunciation.classify_attempt(False, healthy_snr, confident, 99),
                 pronunciation.OUTCOME_WRONG)
    return ok


def decode_budget_tests():
    """
    The decode cap must cover the longest thing the curriculum asks a child to say.

    THE BUG THIS CATCHES. max_new_tokens was 24, set when the longest item in the
    curriculum was a single 8-token word. Nothing failed loudly when longer items
    were added — the recogniser simply stopped decoding part-way and returned a
    PREFIX. "ನಾನು ಶಾಲೆಗೆ ಹೋಗುತ್ತೇನೆ" came back as "ನಾನು ಶಾಲ", scored 0.52, and a
    child who read the sentence perfectly was marked wrong. Every two-word phrase
    was being clipped by it as well.

    It is checked here, in the fast suite, against the CSV and a calibrated
    upper-bound estimate — not against the real tokenizer — because the tokenizer
    ships inside the model directory, and the whole point is that this must fail
    on a laptop with no model, before anyone runs the slow ASR pass.
    """
    print("\nDecode budget (the cap must fit the longest spoken form):")
    ok = True

    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "vocabulary.csv")
    with io.open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    worst, worst_row = 0, None
    for row in rows:
        spoken = (row.get("spoken_form") or row.get("kannada_word") or "").strip()
        need = pronunciation.estimate_tokens(spoken)
        if need > worst:
            worst, worst_row = need, row

    label = f"{worst_row['concept_id']} {worst_row['spoken_form']!r}" if worst_row else "?"
    ok &= _check(
        f"the longest spoken form ({label}) fits in max_new_tokens",
        worst <= pronunciation.MAX_NEW_TOKENS,
        True,
    )
    print(f"    longest needs ~{worst} tokens, cap is "
          f"{pronunciation.MAX_NEW_TOKENS}")

    ok &= _check("the cap still bounds a runaway decode",
                 pronunciation.MAX_NEW_TOKENS < 200, True)
    return ok


def main():
    passed = scorer_tests()
    passed &= mic_tests()
    passed &= soft_voice_tests()
    passed &= confidence_tests()
    passed &= grace_tests()
    passed &= decode_budget_tests()

    if len(sys.argv) > 1:
        audio_path = sys.argv[1]
        expected = sys.argv[2] if len(sys.argv) > 2 else "ಅಮ್ಮ"
        print(f"\nTranscribing {audio_path!r}…")
        text = pronunciation.transcribe(audio_path)
        score, correct = pronunciation.score_pronunciation(expected, text)
        print(f"  model    : {pronunciation.model_name()}")
        print(f"  heard    : {text!r}")
        print(f"  expected : {expected!r}")
        print(f"  score    : {score}  -> {'CORRECT' if correct else 'INCORRECT'}")

    print("\n" + ("ALL PRONUNCIATION TESTS PASSED" if passed else "SOME TESTS FAILED"))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
