"""
validate_asr.py — prove the recogniser can actually HEAR every concept we ship.

A structurally valid dataset (validate_dataset.py) can still contain cards no
child can ever pass, because the speech recogniser cannot resolve the sound. That
is not a hypothetical: the original curriculum opened with a bare "ಅ", which the
recogniser transcribes as ಮಾರ್ಕ್ — the first card in the app was unpassable.

So this walks the whole curriculum, and for each concept:
    1. speaks its `spoken_form` with the same TTS the Listen button uses,
    2. transcribes that audio with the same recogniser that scores the child,
    3. scores it with the same scorer, at the same threshold.

A concept that fails here is a concept a child pronouncing it PERFECTLY would be
marked wrong on — so it is a dataset bug, and the anchor word or the word itself
should be changed. This is a lower bound on quality: clean TTS is easier to
recognise than a six-year-old, so anything failing here is hopeless in the field.

It doubles as the offline warm-up: every clip it generates is cached into
data/audio/, so a classroom deploy with no internet still has all its Listen audio.

    python validate_asr.py              # whole curriculum
    python validate_asr.py --only V     # just the vowels (ids starting with V)

Exit code 0 only if every concept is recognised.
"""

import argparse
import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from tutor import graph_engine
from tutor import media
from tutor import pronunciation


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="only concept ids starting with this prefix")
    ap.add_argument("--quiet", action="store_true", help="print failures only")
    args = ap.parse_args()

    G = graph_engine.load_graph()
    concepts = [dict(G.nodes[n]) for n in sorted(G.nodes)]
    if args.only:
        concepts = [c for c in concepts if c["concept_id"].startswith(args.only)]

    print(f"Loading recogniser…")
    pronunciation.get_model()
    print(f"Model: {pronunciation.model_name()}  (kannada fine-tune: {pronunciation.is_kannada_model()})")
    if not pronunciation.is_kannada_model():
        print("WARNING: not the Kannada model — scores below are not representative.")
    print(f"Checking {len(concepts)} concepts at threshold {pronunciation.PRONUNCIATION_THRESHOLD}\n")

    failures, errors = [], []
    t_start = time.time()

    for i, c in enumerate(concepts, 1):
        cid, spoken = c["concept_id"], c["spoken_form"]
        try:
            audio = media.get_audio(cid, spoken)
        except Exception as e:
            errors.append((cid, spoken, f"TTS failed: {e}"))
            print(f"[{i:3}/{len(concepts)}] {cid:5} TTS ERROR  {e}")
            continue

        heard = pronunciation.transcribe(audio)
        expected, alternates = pronunciation.accepted_forms(c)
        score, correct = pronunciation.score_pronunciation(expected, heard, alternates)

        if not correct:
            failures.append((cid, spoken, heard, score))
        if not args.quiet or not correct:
            mark = "ok  " if correct else "FAIL"
            print(f"[{i:3}/{len(concepts)}] {cid:5} {mark} say={spoken!r:18} heard={heard!r:18} {score:.2f}")

    took = time.time() - t_start
    n = len(concepts)
    passed = n - len(failures) - len(errors)
    print(f"\n{'='*70}")
    print(f"RECOGNISED {passed}/{n} concepts  ({passed/n*100:.0f}%)  in {took:.0f}s")

    if errors:
        print(f"\n{len(errors)} TTS error(s) — audio could not be generated (network?):")
        for cid, spoken, msg in errors:
            print(f"  {cid:5} {spoken!r:18} {msg}")

    if failures:
        print(f"\n{len(failures)} concept(s) the recogniser CANNOT hear — a child saying")
        print("these correctly would be marked wrong. Fix them in build_dataset.py:")
        for cid, spoken, heard, score in failures:
            print(f"  {cid:5} say={spoken!r:18} heard={heard!r:18} {score:.2f}")
        sys.exit(1)

    if errors:
        sys.exit(1)

    print("\nPASS — every concept in the curriculum is recognisable.")


if __name__ == "__main__":
    main()
