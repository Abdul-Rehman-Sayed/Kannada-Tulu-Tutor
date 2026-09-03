import os
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

_fd, _TMP_DB = tempfile.mkstemp(prefix="tutor_test_graph_", suffix=".db")
os.close(_fd)
os.environ["TUTOR_DB_PATH"] = _TMP_DB

from tutor import db
from tutor import graph_engine


def main():
    db.init_db()

    name = "test_dummy"
    sid = db.create_or_get_student(name)
    db.reset_student(sid)
    print(f"Dummy student '{name}' -> id={sid}\n")

    print("Graph loaded:")
    G = graph_engine.load_graph(graph_engine.KANNADA)
    print(f"  {G.number_of_nodes()} Kannada concepts, "
          f"{G.number_of_edges()} prerequisite edges")
    roots = [n for n in G.nodes if G.in_degree(n) == 0]
    print(f"  root concepts (no prereqs): {roots}\n")

    print("Walking the curriculum (marking each concept CORRECT):\n")
    seen = []
    for step in range(1, 17):
        c = graph_engine.get_next_concept(sid, graph_engine.KANNADA)
        if c is None:
            print("  (nothing left to learn — all reachable concepts mastered)")
            break
        seen.append(c["concept_id"])
        print(
            f"  step {step:2}: {c['concept_id']}  {c['kannada_word']:<4} "
            f"say={c['spoken_form']:<12} diff={c['difficulty']}  — {c['english_meaning']}"
        )
        graph_engine.update_mastery(sid, c["concept_id"], correct_bool=True)

    mastered, total = graph_engine.mastery_summary(sid, graph_engine.KANNADA)
    print(f"\nMastered {mastered} / {total} concepts.")

    failures = []

    vowels = [f"V{i:02d}" for i in range(1, 14)]
    if seen[:13] != vowels:
        failures.append(f"first 13 should be the vowels in order, got {seen[:13]}")

    after = seen[13:16]
    G2 = graph_engine.load_graph(graph_engine.KANNADA)
    for cid in after:
        node = G2.nodes[cid]
        if node["category"] != "consonants":
            failures.append(f"{cid} should be a consonant, is {node['category']}")
        elif node["difficulty"] != 2:
            failures.append(f"{cid} is difficulty {node['difficulty']}, expected a core (2) letter first")

    for cid in G2.nodes:
        node = G2.nodes[cid]
        if node["category"] in ("vowels", "consonants"):
            if node["spoken_form"].strip() == node["kannada_word"].strip():
                failures.append(f"{cid} ({node['kannada_word']}) has no anchor word — unpassable")

    for cid in G2.nodes:
        if G2.nodes[cid]["category"] not in ("vowels", "consonants"):
            if G2.in_degree(cid) == 0:
                failures.append(f"Kannada word {cid} has no prerequisite letter")

    print("\nTrap test: a learner who keeps failing one concept must still progress.")
    trapped_id = db.create_or_get_student("test_always_wrong")
    db.reset_student(trapped_id)

    served, distinct = [], set()
    for _ in range(40):
        c = graph_engine.get_next_concept(trapped_id, graph_engine.KANNADA)
        if c is None:
            break
        served.append(c["concept_id"])
        distinct.add(c["concept_id"])
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
        mastered_n, _ = graph_engine.mastery_summary(
            trapped_id, graph_engine.KANNADA)
        if mastered_n != 0:
            failures.append(f"a learner who never answered correctly shows {mastered_n} mastered")
        parked = [p for p in graph_engine.get_student_progress(
            trapped_id, graph_engine.KANNADA) if p["parked"]]
        print(f"  parked (moved on, NOT counted as mastered): {len(parked)}")
        print(f"  mastered: {mastered_n}  <- must be 0")

    print("\nSeparation test: the two curricula must not touch.")
    full = graph_engine.load_graph()
    for lang in graph_engine.available_languages():
        sub = graph_engine.load_graph(lang)
        wrong = [n for n, d in sub.nodes(data=True) if d["language"] != lang]
        if wrong:
            failures.append(f"{lang} graph contains {len(wrong)} concept(s) of "
                            f"another language: {wrong[:5]}")
    crossing = [(a, b) for a, b in full.edges
                if full.nodes[a]["language"] != full.nodes[b]["language"]]
    if crossing:
        failures.append(f"{len(crossing)} prerequisite edge(s) cross languages: "
                        f"{crossing[:3]}")

    tulu_id = db.create_or_get_student("test_tulu_learner")
    db.reset_student(tulu_id)
    tulu_served = []
    for _ in range(5):
        c = graph_engine.get_next_concept(tulu_id, graph_engine.TULU)
        if c is None:
            break
        tulu_served.append(c)
        graph_engine.update_mastery(tulu_id, c["concept_id"], correct_bool=True)
    print(f"  a Tulu learner was served: "
          f"{[c['display_word'] for c in tulu_served]}")
    if not tulu_served:
        failures.append("a Tulu learner was served nothing at all")
    for c in tulu_served:
        if c["language"] != graph_engine.TULU:
            failures.append(f"a Tulu learner was served {c['concept_id']}, which "
                            f"is {c['language']}")
        if c["display_word"] != c["tulu_word"]:
            failures.append(f"{c['concept_id']} shows {c['display_word']!r} to a "
                            f"Tulu learner, not its Tulu form {c['tulu_word']!r}")
    kn_done, _ = graph_engine.mastery_summary(tulu_id, graph_engine.KANNADA)
    tu_done, tu_total = graph_engine.mastery_summary(tulu_id, graph_engine.TULU)
    print(f"  their progress: Tulu {tu_done}/{tu_total}, Kannada {kn_done}")
    if kn_done != 0:
        failures.append(f"Tulu progress leaked into the Kannada count ({kn_done})")
    if tu_done != len(tulu_served):
        failures.append(f"Tulu learner shows {tu_done} learned, expected "
                        f"{len(tulu_served)}")

    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("\nPASS: vowels in order, core consonants next, every letter has an "
          "anchor, every Kannada word sits behind its letter, a "
          "struggling learner is moved on instead of being trapped, and "
          "the Kannada and Tulu curricula stay entirely separate.")


if __name__ == "__main__":
    try:
        main()
    finally:
        try:
            os.remove(_TMP_DB)
        except OSError:
            pass
