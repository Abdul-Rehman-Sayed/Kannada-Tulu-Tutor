import argparse
import json
import os
import random
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from tutor import graph_engine
from tutor import media
from tutor import pronunciation

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(BASE, "data", "asr_transcripts.json")

NEGATIVES_PER_CONCEPT = 12


def transcripts(concepts, retranscribe=False):
    cache = {}
    if os.path.exists(CACHE) and not retranscribe:
        with open(CACHE, encoding="utf-8") as f:
            cache = json.load(f)

    missing = [c for c in concepts if c["concept_id"] not in cache]
    if missing:
        print(f"Transcribing {len(missing)} concept(s)… (cached: {len(cache)})")
        pronunciation.get_model()
        for i, c in enumerate(missing, 1):
            audio = media.get_audio(c["concept_id"], c["spoken_form"])
            cache[c["concept_id"]] = pronunciation.transcribe(audio)
            print(f"  [{i}/{len(missing)}] {c['concept_id']}: {cache[c['concept_id']]!r}")
        with open(CACHE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=1)
    return cache


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--retranscribe", action="store_true")
    args = ap.parse_args()

    G = graph_engine.load_graph()
    concepts = [dict(G.nodes[n]) for n in sorted(G.nodes)]
    heard = transcripts(concepts, args.retranscribe)

    rng = random.Random(20260713)

    positives, negatives = [], []
    for c in concepts:
        got = heard.get(c["concept_id"], "")
        expected, alternates = pronunciation.accepted_forms(c)
        score, ok = pronunciation.score_pronunciation(
            expected, got, alternates, rivals=graph_engine.rivals(c))
        positives.append((c["concept_id"], score, ok))

        others = [o for o in concepts if o["concept_id"] != c["concept_id"]]
        for other in rng.sample(others, min(NEGATIVES_PER_CONCEPT, len(others))):
            exp_o, alt_o = pronunciation.accepted_forms(other)
            s, ok_o = pronunciation.score_pronunciation(
                exp_o, got, alt_o, rivals=graph_engine.rivals(other))
            negatives.append((c["concept_id"], other["concept_id"], s, ok_o))

    print(f"\n{len(positives)} correct answers, {len(negatives)} wrong answers\n")
    print(f"{'thresh':>7} {'accepts correct':>16} {'accepts WRONG':>15} {'J':>7}")
    print("-" * 50)

    sweep = []
    for i in range(35, 96, 5):
        t = i / 100
        tpr = sum(1 for _, s, _ in positives if s >= t) / len(positives)
        fpr = sum(1 for _, _, s, _ in negatives if s >= t) / len(negatives)
        sweep.append((t, tpr, fpr, tpr - fpr))
        print(f"{t:>7.2f} {tpr*100:>15.0f}% {fpr*100:>14.1f}% {tpr-fpr:>7.3f}")

    TOLERANCE = 0.02
    best_j = max(s[3] for s in sweep)
    viable = [s for s in sweep if s[3] >= best_j - TOLERANCE]
    t, tpr, fpr, j = min(viable, key=lambda s: (s[2], -s[0]))
    print("-" * 50)
    print(f"\nBEST THRESHOLD  {t:.2f}   (Youden's J = {j:.3f})")
    print(f"  accepts {tpr*100:.0f}% of correct pronunciations")
    print(f"  accepts {fpr*100:.1f}% of wrong ones")
    print(f"\nCurrently in pronunciation.py: PRONUNCIATION_THRESHOLD = "
          f"{pronunciation.PRONUNCIATION_THRESHOLD}")

    shipped_tpr = sum(1 for *_, ok in positives if ok) / len(positives)
    shipped_fpr = sum(1 for *_, ok in negatives if ok) / len(negatives)
    print(f"\nAS SHIPPED (ratio, and no closer word in the course or look-alikes)")
    print(f"  accepts {shipped_tpr*100:.0f}% of correct pronunciations")
    print(f"  accepts {shipped_fpr*100:.1f}% of wrong ones")

    stuck = sorted([(cid, s) for cid, s, ok in positives if not ok], key=lambda x: x[1])
    if stuck:
        print(f"\n{len(stuck)} concept(s) the shipped scorer does not accept:")
        for cid, s in stuck:
            node = G.nodes[cid]
            print(f"  {cid:5} {node['spoken_form']!r:16} heard {heard.get(cid,'')!r:16} {s:.2f}")


if __name__ == "__main__":
    main()
