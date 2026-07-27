"""
tune_threshold.py — set the pass mark from evidence instead of from a guess.

PRONUNCIATION_THRESHOLD decides whether a child is told "correct" or "try again".
It was originally 0.7 because 0.7 is a round number. That is the wrong way to
choose it: too high and a child pronouncing the word properly is marked wrong
(the failure this project already had); too low and any noise passes, so the app
teaches nothing and the mastery scores are fiction.

So measure it. For every concept we build two populations:

  POSITIVES — the concept's own audio scored against its own accepted forms.
              This is a child saying the right word. These SHOULD pass.
  NEGATIVES — the concept's audio scored against a DIFFERENT concept's accepted
              forms. This is a child saying the wrong word. These MUST fail.

Then sweep the threshold and report, at each one, the true-accept rate (how many
correct answers are accepted) and the false-accept rate (how many wrong answers
sneak through). The chosen value maximises Youden's J = TPR - FPR, which is the
threshold that best separates the two populations — and, because a false accept
teaches a child the wrong pronunciation, ties are broken towards fewer of those.

Transcriptions are cached in data/asr_transcripts.json, so re-running the sweep
after a dataset change is instant instead of a six-minute re-transcribe.

    python tune_threshold.py                # sweep, using the cache
    python tune_threshold.py --retranscribe # force a fresh ASR pass
"""

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

# Each concept's audio is scored against this many OTHER concepts, to build the
# wrong-answer population. Every concept is a potential confusion for every other
# one, so a decent sample is cheap (scoring is pure string work once transcribed).
NEGATIVES_PER_CONCEPT = 12


def transcripts(concepts, retranscribe=False):
    """{concept_id: what the recogniser heard}, cached on disk."""
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

    rng = random.Random(20260713)  # fixed seed: the report must be reproducible

    positives, negatives = [], []
    for c in concepts:
        got = heard.get(c["concept_id"], "")
        expected, alternates = pronunciation.accepted_forms(c)
        score, _ = pronunciation.score_pronunciation(expected, got, alternates)
        positives.append((c["concept_id"], score))

        others = [o for o in concepts if o["concept_id"] != c["concept_id"]]
        for other in rng.sample(others, min(NEGATIVES_PER_CONCEPT, len(others))):
            # The child said concept `c`, but the card in front of them is
            # `other` — a wrong answer, which must be rejected.
            exp_o, alt_o = pronunciation.accepted_forms(other)
            s, _ = pronunciation.score_pronunciation(exp_o, got, alt_o)
            negatives.append((c["concept_id"], other["concept_id"], s))

    print(f"\n{len(positives)} correct answers, {len(negatives)} wrong answers\n")
    print(f"{'thresh':>7} {'accepts correct':>16} {'accepts WRONG':>15} {'J':>7}")
    print("-" * 50)

    sweep = []
    for i in range(35, 96, 5):
        t = i / 100
        tpr = sum(1 for _, s in positives if s >= t) / len(positives)
        fpr = sum(1 for _, _, s in negatives if s >= t) / len(negatives)
        sweep.append((t, tpr, fpr, tpr - fpr))
        print(f"{t:>7.2f} {tpr*100:>15.0f}% {fpr*100:>14.1f}% {tpr-fpr:>7.3f}")

    # Maximising J alone is not quite the right objective here. The two errors
    # are not symmetric: a false REJECT tells a child who spoke correctly that
    # they were wrong (discouraging, and the bug this project started with),
    # while a false ACCEPT certifies a mispronunciation as correct — it actively
    # teaches the wrong thing, and no one ever finds out. So among the
    # thresholds whose J is within TOLERANCE of the best (i.e. statistically
    # indistinguishable on a sample this size), take the one with the lowest
    # false-accept rate.
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

    # The concepts still rejected at the chosen threshold are dataset bugs:
    # a child saying these perfectly would be marked wrong.
    stuck = sorted([(cid, s) for cid, s in positives if s < t], key=lambda x: x[1])
    if stuck:
        print(f"\n{len(stuck)} concept(s) still unrecognised at {t:.2f}:")
        for cid, s in stuck:
            node = G.nodes[cid]
            print(f"  {cid:5} {node['spoken_form']!r:16} heard {heard.get(cid,'')!r:16} {s:.2f}")


if __name__ == "__main__":
    main()
