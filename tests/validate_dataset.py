import sys, csv, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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

    try:
        from tutor import illustrations
    except Exception as e:
        problems.append(f"could not import the drawings: {e}")
        illustrations = None

    letters = [r for r in rows
               if (r.get("category") or "").strip() in ("vowels", "consonants")]

    if illustrations is not None:
        for r in rows:
            cid = r["concept_id"].strip()
            icon = (r.get("icon") or "").strip()
            is_letter = (r.get("category") or "").strip() in ("vowels",
                                                              "consonants")
            if is_letter:
                if icon:
                    problems.append(
                        f"{cid} is a letter but carries the picture '{icon}' — "
                        "a letter is taught on its own, with no picture of a "
                        "word")
            elif not icon:
                problems.append(f"{cid} has no icon")
            elif not illustrations.has(icon):
                problems.append(f"{cid} icon '{icon}' has no drawing")

    for r in letters:
        cid = r["concept_id"].strip()
        letter = (r.get("kannada_word") or "").strip()
        spoken = (r.get("spoken_form") or "").strip()
        if spoken != letter:
            problems.append(
                f"{cid} asks a child to say '{spoken}', but a letter card asks "
                f"for the letter alone: '{letter}'")

    by_id = {r["concept_id"].strip(): r for r in rows}
    letter_glyph = {r["concept_id"].strip(): (r.get("kannada_word") or "").strip()
                    for r in letters}
    languages_with_letters = {(r.get("language") or "").strip() for r in letters}
    for lang in sorted({(r.get("language") or "").strip() for r in rows}):
        if lang and lang not in languages_with_letters:
            problems.append(f"'{lang}' has no alphabet — every syllabus starts "
                            "at the letters")

    for r in rows:
        if (r.get("level") or "").strip() != "Intermediate":
            continue
        cid = r["concept_id"].strip()
        lang = (r.get("language") or "").strip()
        word = ((r.get("tulu_word") if lang == "tu"
                 else r.get("kannada_word")) or "").strip()
        parent = (r.get("prereq_id") or "").strip()
        if parent not in letter_glyph:
            problems.append(
                f"{cid} ({word}) sits behind "
                f"{parent or 'nothing'}, not behind a letter")
        elif word and not word.startswith(letter_glyph[parent]):
            problems.append(
                f"{cid} ({word}) sits behind the letter "
                f"{letter_glyph[parent]}, which is not the letter it begins "
                "with")
        elif by_id[parent].get("language", "").strip() != lang:
            problems.append(f"{cid} ({lang}) sits behind a {lang} letter")

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
