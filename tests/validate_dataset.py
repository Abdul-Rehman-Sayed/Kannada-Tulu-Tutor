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

Reads utf-8-sig so a CSV saved from Excel (BOM-prefixed) validates identically.
"""
import sys, csv, os

def main(path):
    if not os.path.exists(path):
        sys.exit(f"No file: {path}")
    # utf-8-sig: transparently strips the BOM Excel prepends when saving
    # "CSV UTF-8" — with plain utf-8 the first header would silently become
    # "﻿concept_id" and every check here would break. No-op without a BOM.
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    ids = [r["concept_id"].strip() for r in rows if r.get("concept_id","").strip()]
    idset = set(ids)
    problems = []

    # 1. duplicates
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        problems.append(f"Duplicate concept_id: {sorted(dupes)}")

    # 2. dangling prereqs
    for r in rows:
        p = (r.get("prereq_id") or "").strip()
        if p and p not in idset:
            problems.append(f"{r['concept_id']} needs prereq '{p}' which does not exist")

    # 4. missing required fields
    for r in rows:
        for col in ("kannada_word","english_meaning","category"):
            if not (r.get(col) or "").strip():
                problems.append(f"{r.get('concept_id','?')} missing '{col}'")

    # 6. difficulty must be a whole number when present (load_graph int()s it;
    #    a stray "easy" would otherwise pass here and crash the app at boot)
    for r in rows:
        d = (r.get("difficulty") or "").strip()
        if d:
            try:
                int(d)
            except ValueError:
                problems.append(f"{r.get('concept_id','?')} difficulty '{d}' is not a whole number")

    # 3. cycle detection (simple DFS)
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

    # 5. roots
    roots = [cid for cid, p in graph.items() if not p]

    print(f"{len(rows)} rows, {len(roots)} starting concept(s) with no prereq.")
    if problems:
        print("\nFAIL — fix these before running the app:")
        for p in problems: print("  -", p)
        sys.exit(1)
    print("PASS — dataset is structurally sound. App will run cleanly.")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/vocabulary.csv")
