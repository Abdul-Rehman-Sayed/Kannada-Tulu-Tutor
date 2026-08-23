"""
validate_dataset.py — catches the dataset problems that silently break the app.
Run this before every app launch. If it prints FAIL, the app will misbehave; fix
the CSV, don't touch app code.

    python validate_dataset.py data/vocabulary.csv

Checks:
  1. Duplicate concept_id (breaks graph nodes)
  2. prereq_id pointing to a concept that doesn't exist (breaks graph edges / traversal)
  3. Cycles in prereqs (get_next_concept would loop forever)
  4. Missing required fields (kannada_word, english_meaning, category)
  5. Orphan roots sanity (how many concepts have no prereq — your starting points)
  6. Non-numeric difficulty (the app int()s it at load — "easy" would crash boot)
  7. Unknown language codes, and prerequisites that cross between languages
     (a Tulu concept behind a Kannada one would stall the Tulu track behind a
     letter nobody on it is ever taught)
  8. A word the child is shown: every row must have something to display in the
     language it belongs to

Reads utf-8-sig so a CSV saved from Excel (BOM-prefixed) validates identically.
"""
import sys, csv, os

def main(path):
    if not os.path.exists(path):
        sys.exit(f"No file: {path}")
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    ids = [r["concept_id"].strip() for r in rows if r.get("concept_id","").strip()]
    idset = set(ids)
    problems = []

    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        problems.append(f"Duplicate concept_id: {sorted(dupes)}")

    for r in rows:
        p = (r.get("prereq_id") or "").strip()
        if p and p not in idset:
            problems.append(f"{r['concept_id']} needs prereq '{p}' which does not exist")

    for r in rows:
        for col in ("english_meaning","category"):
            if not (r.get(col) or "").strip():
                problems.append(f"{r.get('concept_id','?')} missing '{col}'")

    KNOWN_LANGUAGES = {"kn", "tu"}
    language = {}
    for r in rows:
        cid = (r.get("concept_id") or "").strip()
        if not cid:
            continue
        lang = (r.get("language") or "").strip()
        if not lang:
            problems.append(f"{cid} has no language")
            continue
        if lang not in KNOWN_LANGUAGES:
            problems.append(f"{cid} has unknown language '{lang}'")
        language[cid] = lang
    for r in rows:
        cid = (r.get("concept_id") or "").strip()
        p = (r.get("prereq_id") or "").strip()
        if cid and p and p in language and cid in language:
            if language[p] != language[cid]:
                problems.append(
                    f"{cid} ({language[cid]}) has prereq {p} ({language[p]}) — "
                    "prerequisites may not cross languages"
                )

    for r in rows:
        cid = (r.get("concept_id") or "").strip()
        shown = ((r.get("tulu_word") if language.get(cid) == "tu"
                  else r.get("kannada_word")) or "").strip()
        if cid and not shown:
            problems.append(
                f"{cid} has no word to show a learner of "
                f"'{language.get(cid, '?')}'")

    for r in rows:
        d = (r.get("difficulty") or "").strip()
        if d:
            try:
                int(d)
            except ValueError:
                problems.append(f"{r.get('concept_id','?')} difficulty '{d}' is not a whole number")

    graph = {r["concept_id"].strip(): (r.get("prereq_id") or "").strip()
             for r in rows if r.get("concept_id","").strip()}
    def has_cycle(start):
        seen, node = set(), start
        while node:
            if node in seen: return True
            seen.add(node)
            node = graph.get(node, "")
        return False
    for cid in graph:
        if has_cycle(cid):
            problems.append(f"Prerequisite cycle involving {cid}")
            break

    roots = [cid for cid, p in graph.items() if not p]

    per_language = {}
    for r in rows:
        per_language[(r.get("language") or "?").strip()] =             per_language.get((r.get("language") or "?").strip(), 0) + 1
    counts = ", ".join(f"{lang} {n}" for lang, n in sorted(per_language.items()))
    print(f"{len(rows)} rows ({counts}), "
          f"{len(roots)} starting concept(s) with no prereq.")
    if problems:
        print("\nFAIL — fix these before running the app:")
        for p in problems: print("  -", p)
        sys.exit(1)
    print("PASS — dataset is structurally sound. App will run cleanly.")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/vocabulary.csv")
