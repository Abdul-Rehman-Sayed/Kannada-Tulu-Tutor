import csv
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAB = os.path.join(BASE, "data", "vocabulary.csv")

COLUMNS = [
    "concept_id", "language", "kannada_word", "tulu_word", "transliteration",
    "ipa", "english_meaning", "image_file", "category", "prereq_id",
    "difficulty", "level", "spoken_form", "anchor_word", "phrase_gloss",
    "image_query", "icon",
]

LETTER_CATEGORIES = ("vowels", "consonants")

WORDS_LEVEL = "Intermediate"
NUMBERS_LEVEL = "Numbers"


def blank_row():
    return {c: "" for c in COLUMNS}


def is_letter(row):
    return row.get("category", "") in LETTER_CATEGORIES


def letter_meaning(row):
    kind = "vowel" if row["category"] == "vowels" else "consonant"
    return f"the {kind} {row['transliteration']}"


def teach_letters_alone(rows):
    changed = 0
    for row in rows:
        if not is_letter(row):
            continue
        letter = row["kannada_word"].strip()
        before = (row["spoken_form"], row["ipa"], row["english_meaning"],
                  row["icon"], row["image_query"])
        row["spoken_form"] = letter
        row["ipa"] = row["transliteration"].strip()
        row["english_meaning"] = letter_meaning(row)
        row["icon"] = ""
        row["image_query"] = ""
        if before != (row["spoken_form"], row["ipa"], row["english_meaning"],
                      row["icon"], row["image_query"]):
            changed += 1
    return changed


def add_tulu_alphabet(rows, by_id):
    kn_letters = [r for r in rows if r["language"] == "kn" and is_letter(r)]
    kn_letters.sort(key=lambda r: (r["category"] != "vowels", r["concept_id"]))

    added = []
    previous_vowel = ""
    last_vowel = ""
    for kn in kn_letters:
        tu_id = "T" + kn["concept_id"]
        if kn["category"] == "vowels":
            prereq, previous_vowel = previous_vowel, tu_id
            last_vowel = tu_id
        else:
            prereq = last_vowel
        if tu_id in by_id:
            continue
        glyph = kn["kannada_word"].strip()
        row = blank_row()
        row.update(
            concept_id=tu_id, language="tu",
            kannada_word=glyph, tulu_word=glyph,
            transliteration=kn["transliteration"].strip(),
            ipa=kn["transliteration"].strip(),
            english_meaning=letter_meaning(kn),
            image_file="", category=kn["category"], prereq_id=prereq,
            difficulty=kn["difficulty"], level="Basic",
            spoken_form=glyph, anchor_word="", phrase_gloss="",
            image_query="", icon="",
        )
        added.append(row)
        by_id[tu_id] = row
    return added


def letter_index(rows):
    index = {}
    for row in rows:
        if is_letter(row):
            index[(row["language"], row["kannada_word"].strip())] = \
                row["concept_id"]
    return index


def shown_word(row):
    if row["language"] == "tu":
        return (row["tulu_word"] or row["kannada_word"]).strip()
    return row["kannada_word"].strip()


def first_letter_id(row, index):
    word = shown_word(row)
    if not word:
        return None
    return index.get((row["language"], word[0]))


def reparent_words(rows, index):
    number_roots = {}
    for row in rows:
        if row["category"] == "numbers" and not row["prereq_id"]:
            number_roots[row["language"]] = row["concept_id"]

    moved, orphans = 0, []
    for row in rows:
        if is_letter(row) or row["level"] not in (WORDS_LEVEL, NUMBERS_LEVEL):
            continue
        if (row["category"] == "numbers"
                and row["concept_id"] != number_roots.get(row["language"])):
            continue
        lid = first_letter_id(row, index)
        if lid is None:
            orphans.append((row["concept_id"], shown_word(row)))
            continue
        if row["prereq_id"] != lid:
            row["prereq_id"] = lid
            moved += 1
    return moved, orphans


def split_out_numbers(rows):
    changed = 0
    for row in rows:
        if row["category"] == "numbers" and row["level"] != NUMBERS_LEVEL:
            row["level"] = NUMBERS_LEVEL
            changed += 1
    return changed


def main():
    with open(VOCAB, encoding="utf-8-sig", newline="") as f:
        rows = [dict(r) for r in csv.DictReader(f)]
    for r in rows:
        for c in COLUMNS:
            r.setdefault(c, "")

    by_id = {r["concept_id"]: r for r in rows}

    letters_fixed = teach_letters_alone(rows)
    tulu_letters = add_tulu_alphabet(rows, by_id)
    rows.extend(tulu_letters)

    numbers_moved = split_out_numbers(rows)
    reparented, orphans = reparent_words(rows, letter_index(rows))

    with open(VOCAB, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    print(f"  letters taught alone            : {letters_fixed}")
    print(f"  Tulu letters added              : {len(tulu_letters)}")
    print(f"  words moved behind their letter : {reparented}")
    print(f"  rows moved to the counting stage: {numbers_moved}")
    print(f"  total rows                      : {len(rows)}")
    if orphans:
        print(f"  [!] no letter found for         : {len(orphans)}")
        for cid, word in orphans:
            print(f"      {cid:<7} {word}")


if __name__ == "__main__":
    main()
