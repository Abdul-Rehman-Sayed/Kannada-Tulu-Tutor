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

RESPECTFUL_SWAPS = {
    "TW010": {
        "tulu_word": "ಗೆಳೆಯೆ",
        "transliteration": "geḷeye", "ipa": "geḷeye",
        "english_meaning": "friend",
        "spoken_form": "ಗೆಳೆಯೆ",
        "image_query": "two children friends", "icon": "friend",
    },
    "W010": {
        "tulu_word": "ಗೆಳೆಯೆ",
    },
    "W016": {
        "kannada_word": "ಎಮ್ಮೆ",
        "tulu_word": "ಎರ್ಮೆ",
        "transliteration": "emme", "ipa": "emme",
        "english_meaning": "buffalo",
        "spoken_form": "ಎಮ್ಮೆ",
        "image_query": "indian buffalo", "icon": "buffalo",
    },
    "TW016": {
        "kannada_word": "ಎಮ್ಮೆ",
        "tulu_word": "ಎರ್ಮೆ",
        "transliteration": "erme", "ipa": "erme",
        "english_meaning": "buffalo",
        "spoken_form": "ಎರ್ಮೆ",
        "image_query": "indian buffalo", "icon": "buffalo",
    },
    "W089": {
        "kannada_word": "ಕೋತಿ",
        "transliteration": "kōti", "ipa": "kōti",
        "english_meaning": "monkey",
        "spoken_form": "ಕೋತಿ",
        "image_query": "monkey", "icon": "monkey",
    },
    "S023": {
        "kannada_word": "ಕೋತಿ ಮರ "
                        "ಹತ್ತುತ್ತದೆ",
        "transliteration": "kōti mara hattuttade",
        "ipa": "kōti mara hattuttade",
        "spoken_form": "ಕೋತಿ ಮರ "
                       "ಹತ್ತುತ್ತದೆ",
        "english_meaning": "The monkey climbs the tree",
        "icon": "monkey",
    },
    "S015": {
        "kannada_word": "ನನ್ನ ಅಣ್ಣ "
                        "ಶಾಲೆಗೆ "
                        "ಹೋಗುತ್ತಾರೆ",
        "transliteration": "nanna aṇṇa śālege hōguttāre",
        "ipa": "nanna aṇṇa śālege hōguttāre",
        "spoken_form": "ನನ್ನ ಅಣ್ಣ "
                       "ಶಾಲೆಗೆ "
                       "ಹೋಗುತ್ತಾರೆ",
    },
}

COURTESY = [
    ("R001", "kn", "ನಮಸ್ಕಾರ", "",
     "namaskāra", "respectful greetings", "W010", 5, "namaskara"),
    ("R002", "kn", "ದಯವಿಟ್ಟು", "",
     "dayaviṭṭu", "please", "R001", 5, "please"),
    ("R003", "kn", "ಧನ್ಯವಾದ", "",
     "dhanyavāda", "thank you", "R002", 5, "thanks"),
    ("R004", "kn", "ಕ್ಷಮಿಸಿ", "",
     "kṣamisi", "please forgive me", "R003", 5, "sorry"),
    ("R005", "kn", "ದಯೆ", "", "daye", "kindness", "R004", 5, "heart"),
    ("R006", "kn", "ಗೌರವ", "", "gaurava", "respect", "R005", 5,
     "namaskara"),
    ("TR001", "tu", "ನಮಸ್ಕಾರ",
     "ಸೊಲ್ಮೆಲು", "solmelu",
     "respectful greetings", "TW010", 16, "namaskara"),
    ("TR002", "tu", "ನಮಸ್ಕಾರ",
     "ನಮಸ್ಕಾರ", "namaskāra", "greetings",
     "TR001", 16, "namaskara"),
    ("TR003", "tu", "ದಯೆ", "ದಯೆ", "daye",
     "kindness", "TR002", 16, "heart"),
    ("TR004", "tu", "ಗೌರವ", "ಗೌರವ", "gaurava",
     "respect", "TR003", 16, "namaskara"),
]

KN_NUMBERS = {
    11: ("ಹನ್ನೊಂದು", "hannoṁdu"),
    12: ("ಹನ್ನೆರಡು", "hanneraḍu"),
    13: ("ಹದಿಮೂರು", "hadimūru"),
    14: ("ಹದಿನಾಲ್ಕು", "hadinālku"),
    15: ("ಹದಿನೈದು", "hadinaidu"),
    16: ("ಹದಿನಾರು", "hadināru"),
    17: ("ಹದಿನೇಳು", "hadinēḷu"),
    18: ("ಹದಿನೆಂಟು", "hadineṁṭu"),
    19: ("ಹತ್ತೊಂಬತ್ತು",
         "hattoṁbattu"),
    20: ("ಇಪ್ಪತ್ತು", "ippattu"),
    21: ("ಇಪ್ಪತ್ತೊಂದು",
         "ippattoṁdu"),
    22: ("ಇಪ್ಪತ್ತೆರಡು",
         "ippatteraḍu"),
    23: ("ಇಪ್ಪತ್ತಮೂರು",
         "ippattamūru"),
    24: ("ಇಪ್ಪತ್ತನಾಲ್ಕು",
         "ippattanālku"),
    25: ("ಇಪ್ಪತ್ತೈದು", "ippattaidu"),
    26: ("ಇಪ್ಪತ್ತಾರು", "ippattāru"),
    27: ("ಇಪ್ಪತ್ತೇಳು",
         "ippattēḷu"),
    28: ("ಇಪ್ಪತ್ತೆಂಟು",
         "ippatteṁṭu"),
    29: ("ಇಪ್ಪತ್ತೊಂಬತ್ತು",
         "ippattoṁbattu"),
    30: ("ಮೂವತ್ತು", "mūvattu"),
    31: ("ಮೂವತ್ತೊಂದು",
         "mūvattoṁdu"),
    32: ("ಮೂವತ್ತೆರಡು",
         "mūvatteraḍu"),
    33: ("ಮೂವತ್ತಮೂರು",
         "mūvattamūru"),
    34: ("ಮೂವತ್ತನಾಲ್ಕು",
         "mūvattanālku"),
    35: ("ಮೂವತ್ತೈದು", "mūvattaidu"),
    36: ("ಮೂವತ್ತಾರು", "mūvattāru"),
    37: ("ಮೂವತ್ತೇಳು",
         "mūvattēḷu"),
    38: ("ಮೂವತ್ತೆಂಟು",
         "mūvatteṁṭu"),
    39: ("ಮೂವತ್ತೊಂಬತ್ತು",
         "mūvattoṁbattu"),
    40: ("ನಲವತ್ತು", "nalavattu"),
    41: ("ನಲವತ್ತೊಂದು",
         "nalavattoṁdu"),
    42: ("ನಲವತ್ತೆರಡು",
         "nalavatteraḍu"),
    43: ("ನಲವತ್ತಮೂರು",
         "nalavattamūru"),
    44: ("ನಲವತ್ತನಾಲ್ಕು",
         "nalavattanālku"),
    45: ("ನಲವತ್ತೈದು", "nalavattaidu"),
    46: ("ನಲವತ್ತಾರು", "nalavattāru"),
    47: ("ನಲವತ್ತೇಳು",
         "nalavattēḷu"),
    48: ("ನಲವತ್ತೆಂಟು",
         "nalavatteṁṭu"),
    49: ("ನಲವತ್ತೊಂಬತ್ತು",
         "nalavattoṁbattu"),
    50: ("ಐವತ್ತು", "aivattu"),
}

TU_UNITS = {
    1: ("ಒಂಜಿ", "oṁji"),
    2: ("ರಡ್ಡ್", "raḍḍ"),
    3: ("ಮೂಜಿ", "mūji"),
    4: ("ನಾಲ್", "nāl"),
    5: ("ಐನ್", "ain"),
    6: ("ಆಜಿ", "āji"),
    7: ("ಏಳ್", "ēḷ"),
    8: ("ಎಣ್ಮ", "eṇma"),
    9: ("ಒರ್ಂಬ", "orṁba"),
}
TU_TEENS = {
    11: ("ಪದಿನೊಂಜಿ", "padinoṁji"),
    12: ("ಪದ್ರಡ್ಡ್", "padraḍḍ"),
    13: ("ಪದಿಮೂಜಿ", "padimūji"),
    14: ("ಪದಿನಾಲ್", "padināl"),
    15: ("ಪದಿನೈನ್", "padinain"),
    16: ("ಪದಿನಾಜಿ", "padināji"),
    17: ("ಪದಿನೇಳ್", "padinēḷ"),
    18: ("ಪದಿನೆಣ್ಮ", "padineṇma"),
    19: ("ಪದಿನೊರ್ಂಬ", "padinorṁba"),
}
TU_TENS = {
    20: ("ಇರ್ವ", "irva",
         "ಇರ್ವತ್ತ್ ", "irvatt "),
    30: ("ಮುಪ್ಪ", "muppa",
         "ಮುಪ್ಪತ್ತ್ ", "muppatt "),
    40: ("ನಲ್ಪ", "nalpa",
         "ನಲ್ಪತ್ತ್ ", "nalpatt "),
    50: ("ಐವ", "aiva", "", ""),
}

ENGLISH = {
    1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
    8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve",
    13: "thirteen", 14: "fourteen", 15: "fifteen", 16: "sixteen",
    17: "seventeen", 18: "eighteen", 19: "nineteen", 20: "twenty",
    30: "thirty", 40: "forty", 50: "fifty",
}
TENS_EN = {20: "twenty", 30: "thirty", 40: "forty"}
UNITS_EN = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
            7: "seven", 8: "eight", 9: "nine"}


def english_number(n):
    if n in ENGLISH:
        return ENGLISH[n]
    return f"{TENS_EN[n - n % 10]}-{UNITS_EN[n % 10]}"


def tulu_number(n):
    if n in TU_UNITS:
        return TU_UNITS[n]
    if n == 10:
        return ("ಪತ್ತ್", "patt")
    if n in TU_TEENS:
        return TU_TEENS[n]
    if n in TU_TENS:
        word, translit, _, _ = TU_TENS[n]
        return (word, translit)
    tens = n - n % 10
    _, _, stem, stem_translit = TU_TENS[tens]
    unit, unit_translit = TU_UNITS[n % 10]
    return (stem + unit, stem_translit + unit_translit)


def blank_row():
    return {c: "" for c in COLUMNS}


def number_row(cid, language, n, prereq, difficulty):
    row = blank_row()
    kn_word, kn_translit = KN_NUMBERS.get(n, ("", ""))
    tu_word, tu_translit = tulu_number(n)
    shown, translit = ((kn_word, kn_translit) if language == "kn"
                       else (tu_word, tu_translit))
    row.update(
        concept_id=cid, language=language,
        kannada_word=kn_word or tu_word, tulu_word=tu_word,
        transliteration=translit, ipa=translit,
        english_meaning=english_number(n), image_file="",
        category="numbers", prereq_id=prereq, difficulty=str(difficulty),
        level="Numbers", spoken_form=shown, anchor_word="",
        phrase_gloss="", image_query=f"number {english_number(n)}",
        icon=f"count:{n}",
    )
    return row


def courtesy_row(cid, language, kn, tu, translit, english, prereq, difficulty, icon):
    row = blank_row()
    row.update(
        concept_id=cid, language=language, kannada_word=kn, tulu_word=tu,
        transliteration=translit, ipa=translit, english_meaning=english,
        image_file="", category="courtesy", prereq_id=prereq,
        difficulty=str(difficulty), level="Intermediate",
        spoken_form=(kn if language == "kn" else tu), anchor_word="",
        phrase_gloss="", image_query=english, icon=icon,
    )
    return row


def main():
    with open(VOCAB, encoding="utf-8-sig", newline="") as f:
        rows = [dict(r) for r in csv.DictReader(f)]

    for r in rows:
        for c in COLUMNS:
            r.setdefault(c, "")

    by_id = {r["concept_id"]: r for r in rows}

    swapped = 0
    for cid, fields in RESPECTFUL_SWAPS.items():
        row = by_id.get(cid)
        if not row:
            print(f"  [!] {cid} not found - skipped")
            continue
        if any(row.get(k) != v for k, v in fields.items()):
            swapped += 1
        row.update(fields)

    added = []

    if "TN005" not in by_id:
        added.append(number_row("TN005", "tu", 5, "TW049", 15))
        by_id["TW050"]["prereq_id"] = "TN005"
    if "TN007" not in by_id:
        added.append(number_row("TN007", "tu", 7, "TW050", 15))
        by_id["TW051"]["prereq_id"] = "TN007"

    prev = "W066"
    for n in range(11, 51):
        cid = f"N{n:03d}"
        if cid not in by_id:
            added.append(number_row(cid, "kn", n, prev, 5 if n <= 20 else 6))
        prev = cid

    prev = "TW053"
    for n in range(11, 51):
        cid = f"TN{n:03d}"
        if cid not in by_id:
            added.append(number_row(cid, "tu", n, prev, 16 if n <= 20 else 17))
        prev = cid

    for cid, lang, kn, tu, translit, english, prereq, diff, icon in COURTESY:
        if cid not in by_id:
            added.append(courtesy_row(cid, lang, kn, tu, translit, english,
                                      prereq, diff, icon))

    rows.extend(added)

    with open(VOCAB, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    print(f"  respectful swaps applied : {swapped}")
    print(f"  new rows added           : {len(added)}")
    print(f"  total rows               : {len(rows)}")


if __name__ == "__main__":
    main()
