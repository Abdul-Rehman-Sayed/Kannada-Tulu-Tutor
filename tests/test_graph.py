"""
test_graph.py — Slice 1 checkpoint.

Proves the concept graph traversal + SQLite mastery tracking work end to end.
NO Streamlit, NO audio, NO whisper. Creates a dummy student and prints the
concepts get_next_concept() serves as we mark each one correct — it should walk
from the first vowel through the prerequisite chain in sensible order.

Run:  python test_graph.py
"""

import os
import sys
import tempfile

# Kannada script won't render on a cp1252 Windows console; force UTF-8 output.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Isolate this checkpoint from real learner data: point the DB at a temp file.
# Must happen BEFORE importing db (db reads TUTOR_DB_PATH at import time).
_fd, _TMP_DB = tempfile.mkstemp(prefix="tutor_test_graph_", suffix=".db")
os.close(_fd)
os.environ["TUTOR_DB_PATH"] = _TMP_DB

from tutor import db
from tutor import graph_engine


def main():
    db.init_db()

    name = "test_dummy"
    sid = db.create_or_get_student(name)
    db.reset_student(sid)  # clean slate so re-runs are deterministic
    print(f"Dummy student '{name}' -> id={sid}\n")

    print("Graph loaded:")
    G = graph_engine.load_graph()
    print(f"  {G.number_of_nodes()} concepts, {G.number_of_edges()} prerequisite edges")
    roots = [n for n in G.nodes if G.in_degree(n) == 0]
    print(f"  root concepts (no prereqs): {roots}\n")

    print("Walking the curriculum (marking each concept CORRECT):\n")
    seen = []
    # Walk far enough to cross a tier boundary: 13 vowels, then the core
    # consonants. If the ordering is broken this is where it shows.
    for step in range(1, 17):
        c = graph_engine.get_next_concept(sid)
        if c is None:
            print("  (nothing left to learn — all reachable concepts mastered)")
            break
        seen.append(c["concept_id"])
        print(
            f"  step {step:2}: {c['concept_id']}  {c['kannada_word']:<4} "
            f"say={c['spoken_form']:<12} diff={c['difficulty']}  — {c['english_meaning']}"
        )
        graph_engine.update_mastery(sid, c["concept_id"], correct_bool=True)

    mastered, total = graph_engine.mastery_summary(sid)
    print(f"\nMastered {mastered} / {total} concepts.")

    failures = []

    # 1. The 13 vowels are a chain, so they must be served in varnamale order.
    vowels = [f"V{i:02d}" for i in range(1, 14)]
    if seen[:13] != vowels:
        failures.append(f"first 13 should be the vowels in order, got {seen[:13]}")

    # 2. Only after the vowels do consonants unlock — and the CORE ones (the
    #    high-frequency letters, difficulty 2) must come before the rare ones
    #    (difficulty 4). If difficulty were ignored, a child would meet ಝ before ಕ.
    after = seen[13:16]
    G2 = graph_engine.load_graph()
    for cid in after:
        node = G2.nodes[cid]
        if node["category"] != "consonants":
            failures.append(f"{cid} should be a consonant, is {node['category']}")
        elif node["difficulty"] != 2:
            failures.append(f"{cid} is difficulty {node['difficulty']}, expected a core (2) letter first")

    # 3. Every letter must be speakable: an isolated letter cannot be recognised,
    #    so spoken_form has to carry an anchor word. A letter whose spoken_form is
    #    just itself is the exact bug that made the first card unpassable.
    for cid in G2.nodes:
        node = G2.nodes[cid]
        if node["category"] in ("vowels", "consonants"):
            if node["spoken_form"].strip() == node["kannada_word"].strip():
                failures.append(f"{cid} ({node['kannada_word']}) has no anchor word — unpassable")

    # 4. A word must never be served before the letter it starts with.
    for cid in G2.nodes:
        if G2.nodes[cid]["category"] not in ("vowels", "consonants"):
            if G2.in_degree(cid) == 0:
                failures.append(f"word {cid} has no prerequisite letter")

    # 5. THE TRAP TEST. A child who can never master one concept must not be
    #    served it forever. Before the parking rule existed, get_next_concept()
    #    returned the lowest ready-and-unmastered concept — so a concept the
    #    recogniser could not hear was returned again, and again, and the rest of
    #    the curriculum was permanently unreachable.
    print("\nTrap test: a learner who keeps failing one concept must still progress.")
    trapped_id = db.create_or_get_student("test_always_wrong")
    db.reset_student(trapped_id)

    served, distinct = [], set()
    for _ in range(40):
        c = graph_engine.get_next_concept(trapped_id)
        if c is None:
            break
        served.append(c["concept_id"])
        distinct.add(c["concept_id"])
        # This learner NEVER gets anything right.
        graph_engine.update_mastery(trapped_id, c["concept_id"], correct_bool=False,
                                    raw_score=0.1)

    print(f"  concepts served over 40 always-wrong attempts: {len(distinct)} distinct")
    print(f"  first few: {served[:8]}")
    if len(distinct) < 3:
        failures.append(
            f"a learner who always fails is stuck on {distinct} — they can never "
            f"reach the rest of the curriculum (parking is broken)"
        )
    else:
        mastered_n, _ = graph_engine.mastery_summary(trapped_id)
        if mastered_n != 0:
            failures.append(f"a learner who never answered correctly shows {mastered_n} mastered")
        parked = [p for p in graph_engine.get_student_progress(trapped_id) if p["parked"]]
        print(f"  parked (moved on, NOT counted as mastered): {len(parked)}")
        print(f"  mastered: {mastered_n}  <- must be 0")

    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("\nPASS: vowels in order, core consonants next, every letter has an "
          "anchor, every word sits behind its letter, and a struggling learner "
          "is moved on instead of being trapped.")


if __name__ == "__main__":
    try:
        main()
    finally:
        try:
            os.remove(_TMP_DB)
        except OSError:
            pass
