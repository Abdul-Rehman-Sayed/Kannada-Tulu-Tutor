"""
validate_mic.py — does the microphone gate accept real speech and reject silence?

This exists because the gate got it backwards once already. It vetoed any clip
peaking below 0.02, which is a fact about microphone gain, not about whether a
child spoke: a faint voice in a quiet room was thrown away with "I couldn't hear
anything" while a LOUDER clip of pure room noise sailed through to the recogniser
and came back as a confident, wrong word. Level ranked them backwards.

So the gate now asks whether the sound rises above the room (signal-to-noise),
not whether it is loud — and this script measures that claim against every
concept in the corpus, under the microphone conditions a classroom actually has.

Each concept's reference audio is replayed through a simulated microphone:
scaled to a voice level, dropped into a room with a noise floor, padded with the
hesitation a child leaves either side, and quantized to 16-bit like a browser's.
Then the REAL pipeline runs: prepare_audio() -> transcribe() -> score.

    python validate_mic.py            # all 121 concepts
    python validate_mic.py 25         # a 25-concept sample (faster)

What must hold:
    * a normal voice is accepted and scored           (no regression)
    * a SOFT voice in a quiet room is accepted        (the bug: was 0% accepted)
    * silence / a muted mic is NEVER scored           (whisper hallucinates
                                                       "ಮುಕ್ತಾಯ" — the end — on it)
"""

import csv
import io
import os
import subprocess
import sys
import time
import wave

import numpy as np

from tutor import pronunciation

RATE = 16000
AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "audio")
VOCAB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "vocabulary.csv")

# (label, voice_amplitude, room_noise_floor, must_be_accepted)
#
# The voice levels are the point. 0.30 is a child speaking up. 0.010 is a shy one
# at arm's length from a laptop — SEVENTY times quieter, and 2x below the level
# the old gate demanded. Both are real; both must be scored. The last two rows
# have no voice in them at all and must never reach the recogniser.
CONDITIONS = [
    ("normal voice, quiet room",  0.300, 0.00020, True),
    ("soft voice, quiet room",    0.030, 0.00010, True),
    ("FAINT voice, quiet room",   0.010, 0.00005, True),   # <- the reported bug
    ("no voice, noisy room",      0.000, 0.00200, False),
    ("mic muted (digital zero)",  0.000, 0.00000, False),
]


def load_reference(path):
    """The concept's reference clip as mono 16 kHz float32."""
    out = subprocess.run(
        ["ffmpeg", "-v", "quiet", "-i", path, "-ac", "1", "-ar", str(RATE), "-f", "wav", "pipe:1"],
        capture_output=True, check=True,
    ).stdout
    with wave.open(io.BytesIO(out)) as w:
        pcm = np.frombuffer(w.readframes(w.getnframes()), np.int16)
    return pcm.astype(np.float32) / 32768.0


def simulate_mic(word, amplitude, noise, rng):
    """Replay a clip through a microphone: a voice, a room, hesitation, 16-bit."""
    peak = float(np.abs(word).max()) or 1.0
    voice = word / peak * amplitude
    lead = rng.normal(0, noise, int(1.0 * RATE)) if noise else np.zeros(int(1.0 * RATE))
    tail = rng.normal(0, noise, int(1.5 * RATE)) if noise else np.zeros(int(1.5 * RATE))
    body = voice + (rng.normal(0, noise, len(voice)) if noise else 0.0)
    x = np.concatenate([lead, body, tail]).astype(np.float32)

    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)   # what the browser sends
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    with open(VOCAB, encoding="utf-8-sig") as f:
        vocab = list(csv.DictReader(f))
    audio = {f.split("_")[0]: os.path.join(AUDIO_DIR, f) for f in os.listdir(AUDIO_DIR)}
    concepts = [c for c in vocab if c["concept_id"] in audio]
    if limit:
        step = max(1, len(concepts) // limit)
        concepts = concepts[::step][:limit]

    print(f"Loading the recogniser…")
    pronunciation.get_model()
    print(f"model: {pronunciation.model_name()}")
    print(f"gate : snr >= {pronunciation.MIN_SNR}  or  peak >= {pronunciation.LOUD_ENOUGH}")
    print(f"\nReplaying {len(concepts)} concepts through {len(CONDITIONS)} microphone conditions…\n")

    rng = np.random.default_rng(11)
    results = {}
    t_start = time.time()

    for label, amp, noise, must_accept in CONDITIONS:
        scored = accepted = correct = 0
        times = []
        for c in concepts:
            word = load_reference(audio[c["concept_id"]])
            wav = simulate_mic(word, amp, noise, rng)

            ok, reason, stats, samples = pronunciation.prepare_audio(wav)
            if ok:
                accepted += 1
                t0 = time.time()
                heard = pronunciation.transcribe(samples)
                times.append(time.time() - t0)
                if heard.strip():
                    scored += 1
                    expected, alts = pronunciation.accepted_forms(c)
                    _, is_right = pronunciation.score_pronunciation(expected, heard, alts)
                    correct += bool(is_right)

        n = len(concepts)
        acc_pct = accepted / n * 100
        cor_pct = correct / n * 100
        avg_t = (sum(times) / len(times)) if times else 0.0

        if must_accept:
            verdict = "OK " if cor_pct >= 90 else "FAIL"
            detail = f"accepted {acc_pct:5.1f}%   scored correct {cor_pct:5.1f}%   {avg_t:4.1f}s/clip"
        else:
            verdict = "OK " if accepted == 0 else "FAIL"
            detail = (f"accepted {acc_pct:5.1f}%   (must be 0.0% — anything scored here is "
                      f"a hallucination marked against a child)")
        results[label] = verdict
        print(f"  [{verdict}] {label:<26} {detail}")

    print(f"\n(total {time.time()-t_start:.0f}s)")
    failed = [k for k, v in results.items() if v == "FAIL"]
    print("\n" + ("MIC GATE VALIDATED" if not failed else f"FAILED: {failed}"))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
