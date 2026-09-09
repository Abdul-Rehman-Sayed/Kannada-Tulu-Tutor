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
            if node["spoken_form"].strip() != node["kannada_word"].strip():
                failures.append(
                    f"{cid} asks for {node['spoken_form']!r}, but a letter card "
                    f"asks for the letter alone: {node['kannada_word']!r}")

    for cid in G2.nodes:
        if G2.nodes[cid]["category"] not in ("vowels", "consonants"):
            if G2.in_degree(cid) == 0:
                failures.append(f"Kannada word {cid} has no prerequisite letter")

    print("\nStage test: letters, then words, then counting, then phrases, "
          "then sentences.")
    staged_id = db.create_or_get_student("test_stage_order")
    db.reset_student(staged_id)

    walked = []
    for _ in range(400):
        c = graph_engine.get_next_concept(staged_id, graph_engine.KANNADA)
        if c is None:
            break
        walked.append(c)
        graph_engine.update_mastery(staged_id, c["concept_id"], correct_bool=True)

    order = [graph_engine.stage_rank(c.get("level")) for c in walked]
    if order != sorted(order):
        bad = next(i for i in range(1, len(order)) if order[i] < order[i - 1])
        failures.append(
            f"stages are interleaved: {walked[bad]['concept_id']} "
            f"({walked[bad]['level']}) was served after "
            f"{walked[bad - 1]['concept_id']} ({walked[bad - 1]['level']})")
    else:
        runs = []
        for c in walked:
            if not runs or runs[-1][0] != c["level"]:
                runs.append([c["level"], 0])
            runs[-1][1] += 1
        print("  served in stage blocks: "
              + ", ".join(f"{lv} x{n}" for lv, n in runs))

    letters_seen = sum(1 for c in walked if graph_engine.is_letter(c))
    first_word = next((i for i, c in enumerate(walked)
                       if not graph_engine.is_letter(c)), None)
    if first_word is not None and first_word < letters_seen:
        failures.append(
            f"a whole word was served at step {first_word + 1}, with only "
            f"{first_word} of {letters_seen} letters done")
    else:
        print(f"  all {letters_seen} letters came before the first whole word")

    stages = graph_engine.stage_progress(staged_id, graph_engine.KANNADA)
    levels = [st["level"] for st in stages]
    if levels != ["Basic", "Intermediate", "Numbers", "Advanced", "Sentences"]:
        failures.append(f"stage_progress lost or reordered a stage: {levels}")
    for st in stages:
        if not 1 <= st["position"] <= len(stages) or st["of"] != len(stages):
            failures.append(f"stage {st['level']} is numbered {st['position']} "
                            f"of {st['of']}, expected 1..{len(stages)}")

    for c in walked:
        if c["level"] == graph_engine.WORDS_LEVEL:
            if graph_engine.letter_of(c["concept_id"], graph_engine.KANNADA) is None:
                failures.append(
                    f"{c['concept_id']} cannot name the letter it grew out of")
                break

    tu_stages = graph_engine.stage_progress(staged_id, graph_engine.TULU)
    if tu_stages and (tu_stages[0]["position"] != 1
                      or tu_stages[0]["of"] != len(tu_stages)):
        failures.append(
            f"Tulu stage numbering starts at {tu_stages[0]['position']} of "
            f"{tu_stages[0]['of']}, expected 1 of {len(tu_stages)}")

    print("\nAlphabet-first test: both syllabuses start at the letters, and "
          "the words come one letter's family at a time.")
    for lang in graph_engine.available_languages():
        name = graph_engine.language_name(lang)
        lang_id = db.create_or_get_student(f"test_alphabet_first_{lang}")
        db.reset_student(lang_id)

        served = []
        for _ in range(500):
            c = graph_engine.get_next_concept(lang_id, lang)
            if c is None:
                break
            served.append(c)
            graph_engine.update_mastery(lang_id, c["concept_id"], correct_bool=True)

        first_stage = graph_engine.stage_progress(lang_id, lang)
        if not first_stage or first_stage[0]["level"] != "Basic":
            failures.append(f"{name} does not start at the alphabet")
            continue

        letters = [c for c in served if graph_engine.is_letter(c)]
        words = [c for c in served if c["level"] == graph_engine.WORDS_LEVEL]
        numbers = [c for c in served if c["level"] == graph_engine.NUMBERS_LEVEL]
        print(f"  {name}: {len(letters)} letters, then {len(words)} words, "
              f"then {len(numbers)} numbers")

        if not letters:
            failures.append(f"{name} has no alphabet stage at all")
        if words and served.index(words[0]) < len(letters):
            failures.append(
                f"a {name} word was served before the alphabet was finished")
        if numbers and words and served.index(numbers[0]) < served.index(words[-1]):
            failures.append(
                f"{name} counting was served before the words were finished")

        ranks = graph_engine.letter_ranks(lang)
        seen_letters, previous, revisited = set(), None, []
        for c in words:
            group = ranks.get(c["concept_id"])
            if group != previous:
                if group in seen_letters:
                    revisited.append(c["concept_id"])
                seen_letters.add(group)
                previous = group
        if revisited:
            failures.append(
                f"{name} words jump back to a letter it had already left: "
                f"{revisited[:3]}")
        else:
            print(f"    words came in {len(seen_letters)} unbroken letter "
                  f"families, in alphabet order")

        for c in words:
            letter = graph_engine.letter_of(c["concept_id"], lang)
            if not letter:
                failures.append(f"{c['concept_id']} has no letter behind it")
                break
            family = graph_engine.words_for_letter(letter["concept_id"], lang)
            if c["concept_id"] not in [r["concept_id"] for r in family]:
                failures.append(
                    f"{c['concept_id']} is missing from the family of words "
                    f"shown beside it ({letter['concept_id']})")
                break

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
    print("\nPASS: vowels in order, core consonants next, every letter asked "
          "for on its own, the five stages served strictly in order with the "
          "whole alphabet before the first word and every word before the "
          "first number, both syllabuses starting at the letters and teaching "
          "the words one letter's family at a time, a struggling learner "
          "moved on instead of trapped, and the Kannada and Tulu curricula "
          "entirely separate.")


if __name__ == "__main__":
    try:
        main()
    finally:
        try:
            os.remove(_TMP_DB)
        except OSError:
            pass
