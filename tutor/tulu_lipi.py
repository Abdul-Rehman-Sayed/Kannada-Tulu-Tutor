import unicodedata

VIRAMA = "\U000113CE"
CONJOINER = "\U000113D0"
REPHA = "\U000113D1"

_KN_VIRAMA = "್"
_KN_RA = "ರ"

_LETTERS = {
    "ಅ": "\U00011380", "ಆ": "\U00011381", "ಇ": "\U00011382", "ಈ": "\U00011383",
    "ಉ": "\U00011384", "ಊ": "\U00011385", "ಋ": "\U00011386", "ೠ": "\U00011387",
    "ಌ": "\U00011388", "ೡ": "\U00011389",
    "ಎ": "\U0001138B", "ಏ": "\U0001138B", "ಐ": "\U0001138E",
    "ಒ": "\U00011390", "ಓ": "\U00011390", "ಔ": "\U00011391",
}

_CONSONANTS = {
    "ಕ": "\U00011392", "ಖ": "\U00011393", "ಗ": "\U00011394", "ಘ": "\U00011395",
    "ಙ": "\U00011396", "ಚ": "\U00011397", "ಛ": "\U00011398", "ಜ": "\U00011399",
    "ಝ": "\U0001139A", "ಞ": "\U0001139B", "ಟ": "\U0001139C", "ಠ": "\U0001139D",
    "ಡ": "\U0001139E", "ಢ": "\U0001139F", "ಣ": "\U000113A0", "ತ": "\U000113A1",
    "ಥ": "\U000113A2", "ದ": "\U000113A3", "ಧ": "\U000113A4", "ನ": "\U000113A5",
    "ಪ": "\U000113A6", "ಫ": "\U000113A7", "ಬ": "\U000113A8", "ಭ": "\U000113A9",
    "ಮ": "\U000113AA", "ಯ": "\U000113AB", "ರ": "\U000113AC", "ಲ": "\U000113AD",
    "ವ": "\U000113AE", "ಶ": "\U000113AF", "ಷ": "\U000113B0", "ಸ": "\U000113B1",
    "ಹ": "\U000113B2", "ಳ": "\U000113B3", "ಱ": "\U000113B4", "ೞ": "\U000113B5",
}

_SIGNS = {
    "ಾ": "\U000113B8", "ಿ": "\U000113B9", "ೀ": "\U000113BA", "ು": "\U000113BB",
    "ೂ": "\U000113BC", "ೃ": "\U000113BD", "ೄ": "\U000113BE", "ೢ": "\U000113BF",
    "ೣ": "\U000113C0",
    "ೆ": "\U000113C2", "ೇ": "\U000113C2", "ೈ": "\U000113C5",
    "ೊ": "\U000113C7", "ೋ": "\U000113C7", "ೌ": "\U000113C8",
    "ಁ": "\U000113CA", "ಂ": "\U000113CC", "ಃ": "\U000113CD", "ಽ": "\U000113B7",
}

_DROP = {"‌", "‍", "಼"}


def convert(text):
    s = unicodedata.normalize("NFC", text or "")
    out = []
    i = 0
    while i < len(s):
        ch = s[i]
        nxt = s[i + 1] if i + 1 < len(s) else ""
        after = s[i + 2] if i + 2 < len(s) else ""
        if ch == _KN_RA and nxt == _KN_VIRAMA and after in _CONSONANTS:
            out.append(REPHA)
            i += 2
            continue
        if ch == _KN_VIRAMA:
            out.append(CONJOINER if nxt in _CONSONANTS else VIRAMA)
        elif ch in _CONSONANTS:
            out.append(_CONSONANTS[ch])
        elif ch in _LETTERS:
            out.append(_LETTERS[ch])
        elif ch in _SIGNS:
            out.append(_SIGNS[ch])
        elif ch not in _DROP:
            out.append(ch)
        i += 1
    return "".join(out)


def is_tulu_lipi(text):
    return any("\U00011380" <= ch <= "\U000113FF" for ch in text or "")
