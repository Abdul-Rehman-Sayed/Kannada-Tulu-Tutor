"""Stamp an `icon` on every row of data/vocabulary.csv.

Run it after editing the curriculum:  python -m scripts.assign_icons

A letter takes no drawing at all: it is taught on its own, and its card shows
the letter itself.  It used to borrow the drawing of an example word - the ka
card showed a lotus, for kamala - which put a word on a card that is meant to
teach one letter.  A phrase or a sentence takes the drawing of the thing it is
about ("the cow gives milk" shows the cow).  Everything else is looked up from
its English meaning.  Rows already carrying an icon are left alone.
"""
import csv
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tutor import illustrations

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAB = os.path.join(BASE, "data", "vocabulary.csv")

BY_ID = {
    "P001": "mother", "P002": "house", "P003": "school", "P004": "cow",
    "P005": "eye", "P006": "fish", "P007": "flower", "P008": "leaf",
    "P009": "milk", "P010": "sky", "P011": "elephant", "P012": "child",
    "P013": "fruit", "P014": "friend",
    "S001": "house", "S002": "book", "S003": "friend", "S004": "school",
    "S005": "school", "S006": "book", "S007": "milk", "S008": "water",
    "S009": "rice", "S010": "ball", "S011": "school", "S012": "mother",
    "S013": "father", "S014": "grandmother", "S015": "brother",
    "S016": "child", "S017": "cow", "S018": "dog", "S019": "cat",
    "S020": "fish", "S021": "bird", "S022": "elephant", "S023": "monkey",
    "S024": "peacock", "S025": "sun", "S026": "moon", "S027": "rain",
    "S028": "fruit", "S029": "flower", "S030": "eye",
    "TP001": "house", "TP002": "school", "TP003": "cow", "TP004": "eye",
    "TP005": "fish", "TP006": "milk",
}


def main():
    with open(VOCAB, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        columns = list(reader.fieldnames)
        rows = [dict(r) for r in reader]

    if "icon" not in columns:
        columns.append("icon")

    stamped, unresolved = 0, []
    for row in rows:
        cid = row["concept_id"]
        if row.get("icon"):
            continue
        if row["category"] in ("vowels", "consonants"):
            continue

        if cid in BY_ID:
            icon = BY_ID[cid]
        else:
            icon = row["english_meaning"].strip().lower()

        resolved = illustrations.resolve(icon)
        if not resolved:
            unresolved.append((cid, row["category"], icon))
            continue
        row["icon"] = resolved
        stamped += 1

    with open(VOCAB, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    needs = [r for r in rows
             if r["category"] not in ("vowels", "consonants")]
    have = sum(1 for r in needs if r.get("icon"))
    print(f"  stamped this run : {stamped}")
    print(f"  rows with a icon : {have} of {len(needs)} "
          f"(letters take none)")
    if unresolved:
        print(f"  no drawing for   : {len(unresolved)}")
        for cid, cat, icon in unresolved:
            print(f"    {cid:<7} {cat:<11} {icon}")


if __name__ == "__main__":
    main()
