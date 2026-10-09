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
IMAGE_DIR = os.path.join(BASE, "data", "images")

PICTURES = {
    "S005": "S005.jpg", "S006": "S006.jpg", "S007": "S007.jpg",
    "S008": "S008.jpg", "S009": "S009.jpg", "S010": "S010.jpg",
    "S011": "S011.jpg", "S014": "S014.jpg", "S016": "S016.jpg",
    "S017": "S017.jpg", "S018": "S018.jpg", "S019": "S019.jpg",
    "S020": "S020.jpg", "S021": "S021.jpg", "S023": "S023.jpg",
    "S028": "S028.jpg",
    "P005": "W095.jpg", "S030": "W095.jpg", "TP004": "W095.jpg",
    "P006": "", "TP005": "",
    "R001": "R001.jpg", "TR001": "R001.jpg", "TR002": "R001.jpg",
}


def picture(row):
    cid = row["concept_id"]
    category = row["category"]
    if category in ("vowels", "consonants"):
        return "", ""
    if category == "numbers":
        icon = row.get("icon", "")
        if not icon.startswith("count:"):
            raise SystemExit(f"{cid} is a number with no count: icon")
        return icon, ""
    if category == "colours":
        return illustrations.resolve(row["english_meaning"]) or "", ""
    photo = PICTURES.get(cid, row.get("image_file", ""))
    if photo and not os.path.isfile(os.path.join(IMAGE_DIR, photo)):
        photo = ""
    return "", photo


def main():
    with open(VOCAB, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        columns = list(reader.fieldnames)
        rows = [dict(r) for r in reader]
    if "icon" not in columns:
        columns.append("icon")

    changed = 0
    for row in rows:
        icon, photo = picture(row)
        if (row.get("icon", ""), row.get("image_file", "")) != (icon, photo):
            changed += 1
        row["icon"], row["image_file"] = icon, photo

    with open(VOCAB, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    shown = [r for r in rows if r["category"] not in ("vowels", "consonants")]
    photos = sum(1 for r in shown if r["image_file"])
    drawn = sum(1 for r in shown if r["icon"])
    print(f"  rows changed this run : {changed}")
    print(f"  photographs           : {photos}")
    print(f"  numbers and colours   : {drawn}")
    print(f"  no picture            : {len(shown) - photos - drawn} "
          f"(letters take none)")


if __name__ == "__main__":
    main()
