import argparse
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
