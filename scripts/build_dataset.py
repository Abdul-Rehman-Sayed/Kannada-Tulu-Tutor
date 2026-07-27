"""
build_dataset.py — author data/vocabulary.csv, the tutor's whole curriculum.

The curriculum is written HERE, in code, and generated into the CSV rather than
hand-edited, because three of the CSV's columns must not be typed by a human:

  * transliteration / ipa  are derived from the Kannada with `indic-transliteration`
    (ISO-15919). Hand-typed romanization is where earlier versions went wrong.
  * prereq_id             is computed: a word's prerequisite is the LETTER it
    starts with, so the graph unlocks words as the alphabet is learned.
  * spoken_form           is what the child is asked to say and what the speech
    scorer compares against (see below).

Run:  python build_dataset.py          (then: python validate_dataset.py)

--------------------------------------------------------------------------- #
Why letters carry an "anchor word"
--------------------------------------------------------------------------- #
A bare vowel is the one thing the speech recogniser cannot hear. Measured on
this project's own audio, an isolated "ಅ" (0.55 s) is transcribed as ಮಾರ್ಕ್ —
there is simply not enough acoustic evidence in a 1-phoneme utterance, and no
decoding option recovers it (prompting, hotwords, padding, repetition and a
temperature sweep were all tried and all failed). Because ಅ is the FIRST card in
the curriculum, a child could say it perfectly, be marked wrong, and never
advance. That was the "voice input doesn't work" bug.

So every letter is taught the way a Kannada varnamale chart teaches it — the
letter followed by a word that carries it ("ಅ… ಅಮ್ಮ", exactly like "A for
Apple"). The child says both; the extra syllables give the recogniser the
context it needs. Measured: 6/7 letters recognised this way, and a child saying
the WRONG letter is still rejected (0.22), so scoring keeps its teeth.

--------------------------------------------------------------------------- #
Why ಙ and ಞ are not in the curriculum
--------------------------------------------------------------------------- #
The varnamale lists 34 consonants, but ಙ (ṅa) and ಞ (ña) do not occur
independently in modern written Kannada — the anusvara ಂ took their place. They
cannot be spoken in isolation, cannot anchor a word, and could never be scored.
Including them would only manufacture cards no child can pass, so the speaking
curriculum uses 13 vowels + 32 consonants. This is a deliberate curriculum
decision, not an omission.

Tulu: filled in only where there is a reliable source. Tulu has no standardised
orthography and is under-documented; a blank tulu_word renders as "no Tulu form
recorded" rather than a guess, because a wrong word in a teaching tool is worse
than a missing one.
"""

import csv
import os
import sys

try:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate
except ImportError:
    sys.exit("Run: pip install indic-transliteration")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "vocabulary.csv")

COLS = [
    "concept_id", "kannada_word", "tulu_word", "transliteration", "ipa",
    "english_meaning", "image_file", "category", "prereq_id", "difficulty",
    "level", "spoken_form", "anchor_word", "phrase_gloss", "image_query",
]

# The syllabus has three explicit tiers, Basic -> Intermediate -> Advanced. A
# concept's tier follows from what KIND of thing it is: the letters are the
# foundation, words are built out of letters, phrases are built out of words. The
# tier is written into the CSV as its own column so the progression is explicit
# data a teacher can see, not something implied by a difficulty number. The
# difficulty values assigned in main() keep the SERVING order strictly tier by
# tier — every letter before any word, every word before any phrase — so a child
# finishes the alphabet, then reads words, then reads phrases.
LEVEL_BASIC = "Basic"          # the alphabet: vowels + consonants
LEVEL_INTERMEDIATE = "Intermediate"  # whole words
LEVEL_ADVANCED = "Advanced"    # short phrases — reading words together

# 1. Vowels — swaragalu. (letter, anchor word, anchor meaning, image query)
VOWELS = [
    ("ಅ", "ಅಮ್ಮ",   "mother",     "indian mother baby"),
    ("ಆ", "ಆನೆ",    "elephant",   "Indian elephant"),
    ("ಇ", "ಇಲಿ",    "mouse",      "house mouse"),
    # ಈಜು ("swimming") was the natural anchor, but the recogniser hears it as
    # ಇಲ್ಲ (0.29) — unpassable. ಈರುಳ್ಳಿ is recognised perfectly. Anchors are
    # chosen to be *hearable*, not just correct; validate_asr.py proves it.
    ("ಈ", "ಈರುಳ್ಳಿ", "onion",     "onion"),
    ("ಉ", "ಉಪ್ಪು",  "salt",       "salt"),
    ("ಊ", "ಊಟ",     "meal",       "Indian meal thali"),
    ("ಋ", "ಋಷಿ",    "sage",       "hindu sage statue"),
    ("ಎ", "ಎಲೆ",    "leaf",       "leaf"),
    ("ಏ", "ಏಣಿ",    "ladder",     "ladder"),
    ("ಐ", "ಐದು",    "five",       "number five"),
    ("ಒ", "ಒಂಟೆ",   "camel",      "camel"),
    ("ಓ", "ಓದು",    "reading",    "child reading book"),
    ("ಔ", "ಔಷಧಿ",   "medicine",   "medicine tablets"),
]

# 2. Consonants — vyanjanagalu (ಙ, ಞ excluded; see module docstring).
#    `core=True` letters are the high-frequency ones taught first; the rest come
#    after the child has read some real words.
#    Where a letter cannot begin a word (ಣ, ಥ, ಷ, ಳ) the anchor word CONTAINS it.
CONSONANTS = [
    # letter, anchor, anchor meaning, image query, core?
    ("ಕ", "ಕಮಲ",     "lotus",       "lotus flower",        True),
    ("ಖ", "ಖರ್ಜೂರ",  "dates",       "date fruit",          False),
    ("ಗ", "ಗಿಡ",     "plant",       "young plant",         True),
    ("ಘ", "ಘಂಟೆ",    "bell",        "temple bell",         False),
    ("ಚ", "ಚಂದ್ರ",   "moon",        "moon",                True),
    ("ಛ", "ಛತ್ರಿ",   "umbrella",    "umbrella",            False),
    ("ಜ", "ಜಿಂಕೆ",   "deer",        "spotted deer",        True),
    ("ಝ", "ಝರಿ",     "stream",      "mountain stream",     False),
    ("ಟ", "ಟೋಪಿ",    "cap",         "cap hat",             False),
    ("ಠ", "ಠಾಣೆ",    "police station", "police station",   False),
    ("ಡ", "ಡಬ್ಬಿ",   "box",         "tin box",             False),
    ("ಢ", "ಢಮರು",    "damaru drum", "damaru drum",         False),
    ("ಣ", "ಬಾಣ",     "arrow",       "arrow",               False),
    ("ತ", "ತಲೆ",     "head",        "child face portrait",          True),
    # ಕಥೆ ("story") is the natural anchor but the recogniser drops the ಥ and
    # hears just ಕೆ (0.57). ಗ್ರಂಥ is recognised perfectly.
    ("ಥ", "ಗ್ರಂಥ",   "scripture",   "old manuscript book", False),
    ("ದ", "ದೀಪ",     "lamp",        "oil lamp diya",       True),
    ("ಧ", "ಧ್ವಜ",    "flag",        "flag of India",       False),
    ("ನ", "ನಾಯಿ",    "dog",         "dog",                 True),
    ("ಪ", "ಪುಸ್ತಕ",  "book",        "book",                True),
    ("ಫ", "ಫಲ",      "fruit",       "assorted fruit",      False),
    ("ಬ", "ಬಾಗಿಲು",  "door",        "wooden door",         False),
    ("ಭ", "ಭೂಮಿ",    "earth",       "planet Earth",        False),
    ("ಮ", "ಮನೆ",     "house",       "village house",       True),
    ("ಯ", "ಯಂತ್ರ",   "machine",     "industrial machine",  False),
    ("ರ", "ರೈಲು",    "train",       "train",               False),
    ("ಲ", "ಲಿಂಬೆ",   "lemon",       "lemon",               False),
    ("ವ", "ವಿಮಾನ",   "aeroplane",   "airplane",            False),
    ("ಶ", "ಶಾಲೆ",    "school",      "school building",     False),
    ("ಷ", "ಪುಷ್ಪ",   "flower",      "flower",              False),
    ("ಸ", "ಸೂರ್ಯ",   "sun",         "sun",                 False),
    ("ಹ", "ಹಸು",     "cow",         "cow",                 True),
    ("ಳ", "ಮಳೆ",     "rain",        "rain",                False),
]

# 3. Vocabulary. (kannada, tulu, english, category, image query, core?)
#    tulu = "" where no reliable form is known — never a guess.
#    Tulu forms follow tulubuzz.in / tuludictionary.in and common Tulu usage.
WORDS = [
    # --- family -----------------------------------------------------------
    ("ಅಮ್ಮ",     "ಅಪ್ಪೆ",   "mother",          "family", "indian mother baby",     True),
    ("ಅಪ್ಪ",     "ಅಮ್ಮೆ",   "father",          "family", "father child playing",     True),
    ("ಅಣ್ಣ",     "ಪಳಯೆ",   "elder brother",   "family", "indian school boys",             True),
    ("ಅಕ್ಕ",     "ಪಳ್ದಿ",   "elder sister",    "family", "indian school girls",              True),
    ("ತಮ್ಮ",     "ಮೆಗ್ಯೆ",  "younger brother", "family", "boy portrait child",            False),
    ("ತಂಗಿ",     "ಮೆಗ್ದಿ",  "younger sister",  "family", "girl portrait child",           False),
    ("ಮಗು",      "ಬಾಲೆ",    "child",           "family", "smiling baby infant",                 True),
    ("ಅಜ್ಜ",     "ಅಜ್ಜೆ",   "grandfather",     "family", "elderly indian man portrait",   False),
    ("ಅಜ್ಜಿ",    "ಅಜ್ಜಿ",   "grandmother",     "family", "elderly indian woman portrait", False),
    ("ಸ್ನೇಹಿತ",  "ದೋಸ್ತಿ",  "friend",          "family", "children playing together",              False),

    # --- animals ----------------------------------------------------------
    ("ಹಸು",      "ಪೆತ್ತ",   "cow",             "animals", "cow",                 True),
    ("ನಾಯಿ",     "ನಾಯಿ",    "dog",             "animals", "dog",                 True),
    ("ಬೆಕ್ಕು",   "ಪುಚ್ಚೆ",  "cat",             "animals", "cat",                 True),
    ("ಆನೆ",      "ಆನೆ",     "elephant",        "animals", "Indian elephant",     True),
    ("ಕುದುರೆ",   "ಕುದುರೆ",  "horse",           "animals", "horse",               False),
    ("ಹಂದಿ",     "ಪಂಜಿ",    "pig",             "animals", "pig",                 False),
    ("ಕುರಿ",     "ಕುರಿ",    "sheep",           "animals", "sheep",               False),
    ("ಇಲಿ",      "ಇಲಿ",     "mouse",           "animals", "house mouse",         False),
    ("ಮೀನು",     "ಮೀನ್",    "fish",            "animals", "fish",                True),
    ("ಹಕ್ಕಿ",    "ಪಕ್ಕಿ",   "bird",            "animals", "bird",                True),
    ("ಕೋಳಿ",     "ಕೋರಿ",    "hen",             "animals", "hen",                 False),
    ("ಹುಲಿ",     "ಪಿಲಿ",    "tiger",           "animals", "tiger",               False),

    # --- nature -----------------------------------------------------------
    ("ನೀರು",     "ನೀರ್",    "water",           "nature", "glass of water",       True),
    ("ಗಾಳಿ",     "ಗಾಳಿ",    "wind",            "nature", "windmill wind",        False),
    ("ಬೆಂಕಿ",    "ತೂ",      "fire",            "nature", "fire",                 False),
    ("ಮಳೆ",      "ಬರ್ಸ",    "rain",            "nature", "rain",                 True),
    ("ಸೂರ್ಯ",    "ಸೂರ್ಯೆ",  "sun",             "nature", "sun",                  True),
    ("ಚಂದ್ರ",    "ಚಂದ್ರೆ",  "moon",            "nature", "moon",                 True),
    ("ನಕ್ಷತ್ರ",  "ಬೊಳ್ಳಿ",  "star",            "nature", "star night sky",       False),
    ("ಮರ",       "ಮರ",      "tree",            "nature", "tree",                 True),
    ("ಹೂವು",     "ಪೂ",      "flower",          "nature", "flower",               True),
    ("ಎಲೆ",      "ಎಲೆ",     "leaf",            "nature", "leaf",                 False),
    ("ಬೆಟ್ಟ",    "ಬೆಟ್ಟು",  "hill",            "nature", "hill",                 False),
    ("ಕಡಲು",     "ಕಡಲ್",    "sea",             "nature", "sea",                  False),

    # --- food -------------------------------------------------------------
    ("ಅನ್ನ",     "ಅನ್ನ",    "cooked rice",     "food", "cooked rice",            True),
    ("ಹಾಲು",     "ಪೇರ್",    "milk",            "food", "glass of milk",          True),
    ("ಉಪ್ಪು",    "ಉಪ್ಪು",   "salt",            "food", "salt",                   False),
    ("ಹಣ್ಣು",    "ಪರ್ಂದ್",  "fruit",           "food", "assorted fruit",         True),
    ("ಬಾಳೆಹಣ್ಣು", "",       "banana",          "food", "banana",                 False),
    ("ಮೊಸರು",    "ಮೊಸರು",   "curd",            "food", "curd yogurt",            False),
    ("ಸಕ್ಕರೆ",   "",        "sugar",           "food", "sugar",                  False),
    ("ರೊಟ್ಟಿ",   "",        "flatbread",       "food", "roti flatbread",         False),

    # --- body -------------------------------------------------------------
    ("ತಲೆ",      "ತರೆ",     "head",            "body", "child face portrait",             True),
    ("ಕಣ್ಣು",    "ಕಣ್ಣ್",   "eye",             "body", "human eye closeup",              True),
    ("ಕಿವಿ",     "ಕೆಬಿ",    "ear",             "body", "human ear closeup",              True),
    ("ಮೂಗು",     "ಮೂಕು",    "nose",            "body", "human nose closeup",             True),
    ("ಬಾಯಿ",     "ಬಾಯಿ",    "mouth",           "body", "human lips closeup",            False),
    ("ಕೈ",       "ಕೈ",      "hand",            "body", "open human hand",             True),
    ("ಕಾಲು",     "ಕಾರ್",    "leg",             "body", "human legs walking",              False),
    ("ಹಲ್ಲು",    "ಪಲ್ಲ್",   "tooth",           "body", "tooth",                  False),

    # --- colours ----------------------------------------------------------
    ("ಕೆಂಪು",    "ಕೆಂಪು",   "red",             "colours", "red colour",          True),
    ("ಹಸಿರು",    "ಪಚ್ಚೆ",   "green",           "colours", "green colour",        True),
    ("ಹಳದಿ",     "ಮಂಜಲ್",   "yellow",          "colours", "yellow colour",       True),
    ("ನೀಲಿ",     "ನೀಲಿ",    "blue",            "colours", "blue colour",         True),
    ("ಕಪ್ಪು",    "ಕಪ್ಪು",   "black",           "colours", "black colour",        False),
    ("ಬಿಳಿ",     "ಬೊಲ್ದು",  "white",           "colours", "white colour",        False),

    # --- numbers ----------------------------------------------------------
    ("ಒಂದು",     "ಒಂಜಿ",    "one",             "numbers", "number one",          True),
    ("ಎರಡು",     "ರಡ್ಡ್",   "two",             "numbers", "number two",          True),
    ("ಮೂರು",     "ಮೂಜಿ",    "three",           "numbers", "number three",        True),
    ("ನಾಲ್ಕು",   "ನಾಲ್",    "four",            "numbers", "number four",         True),
    ("ಐದು",      "ಐನ್",     "five",            "numbers", "number five",         True),
    ("ಆರು",      "ಆಜಿ",     "six",             "numbers", "number six",          False),
    ("ಏಳು",      "ಏಳ್",     "seven",           "numbers", "number seven",        False),
    ("ಎಂಟು",     "ಎಣ್ಮ",    "eight",           "numbers", "number eight",        False),
    ("ಒಂಬತ್ತು",  "ಒರ್ಂಬ",   "nine",            "numbers", "number nine",         False),
    ("ಹತ್ತು",    "ಪತ್ತ್",   "ten",             "numbers", "number ten",          False),

    # --- home & school ----------------------------------------------------
    ("ಮನೆ",      "ಇಲ್ಲ್",   "house",           "home", "village house",          True),
    ("ಬಾಗಿಲು",   "ಬಾಕಿಲ್",  "door",            "home", "wooden door",            False),
    ("ಕುರ್ಚಿ",   "ಕುರ್ಚಿ",  "chair",           "home", "chair",                  False),
    ("ದೀಪ",      "",        "lamp",            "home", "oil lamp diya",          False),
    ("ಪುಸ್ತಕ",   "ಪುಸ್ತಕ",  "book",            "school", "book",                 True),
    ("ಶಾಲೆ",     "ಶಾಲೆ",    "school",          "school", "school building",      True),
    ("ಪೆನ್ಸಿಲ್", "",        "pencil",          "school", "pencil",               False),
    ("ರೈಲು",     "",        "train",           "travel", "train",                False),
    ("ಬಸ್ಸು",    "",        "bus",             "travel", "bus",                  False),
    ("ವಿಮಾನ",    "",        "aeroplane",       "travel", "airplane",             False),

    # ===================================================================== #
    # Expansion (added 2026-07-19). Common, concrete, child-safe vocabulary
    # only — nothing frightening, and every entry is checked by validate_asr
    # so a child saying it correctly is actually recognised. Tulu is left ""
    # rather than guessed: a wrong Tulu word would teach a child something that
    # does not exist, which is worse than a blank (see the module docstring).
    # ===================================================================== #

    # --- fruits -----------------------------------------------------------
    ("ಮಾವು",      "",        "mango",           "fruits", "mango fruit",         True),
    ("ಸೇಬು",      "",        "apple",           "fruits", "red apple",           True),
    ("ಕಿತ್ತಳೆ",   "",        "orange",          "fruits", "orange fruit",        True),
    ("ದ್ರಾಕ್ಷಿ",  "",        "grapes",          "fruits", "bunch of grapes",     False),
    ("ಕಲ್ಲಂಗಡಿ",  "",        "watermelon",      "fruits", "watermelon",          False),

    # --- vegetables -------------------------------------------------------
    ("ಆಲೂಗಡ್ಡೆ",  "",        "potato",          "vegetables", "potato",          True),
    ("ಬದನೆಕಾಯಿ",  "",        "brinjal",         "vegetables", "brinjal eggplant", False),
    ("ಬೆಂಡೆಕಾಯಿ", "",        "okra",            "vegetables", "okra ladyfinger", False),

    # --- food (more) ------------------------------------------------------
    ("ದೋಸೆ",      "",        "dosa",            "food", "dosa south indian",     True),
    ("ಇಡ್ಲಿ",     "",        "idli",            "food", "idli steamed cake",     True),
    ("ಜೇನು",      "",        "honey",           "food", "honey jar",             False),
    ("ಬೆಣ್ಣೆ",    "",        "butter",          "food", "butter block",          False),

    # --- animals (more, all friendly) -------------------------------------
    ("ಮಂಗ",       "",        "monkey",          "animals", "monkey",             True),
    ("ಗಿಳಿ",      "",        "parrot",          "animals", "green parrot",       True),
    ("ಕಾಗೆ",      "",        "crow",            "animals", "crow bird",          False),
    ("ನವಿಲು",     "",        "peacock",         "animals", "peacock",            True),
    ("ಮೊಲ",       "",        "rabbit",          "animals", "rabbit",             False),
    ("ಅಳಿಲು",     "",        "squirrel",        "animals", "squirrel",           False),

    # --- body (more) ------------------------------------------------------
    ("ಮುಖ",       "",        "face",            "body", "child smiling face",    True),
    ("ಕೂದಲು",     "",        "hair",            "body", "hair",                  True),
    ("ಬೆರಳು",     "",        "finger",          "body", "finger pointing",       False),

    # --- nature (more) ----------------------------------------------------
    ("ಮೋಡ",       "",        "cloud",           "nature", "white cloud sky",     True),
    ("ನದಿ",       "",        "river",           "nature", "river",               True),
    ("ಆಕಾಶ",      "",        "sky",             "nature", "blue sky",            True),
    ("ಕಲ್ಲು",     "",        "stone",           "nature", "stone rock",          False),

    # --- home & objects ---------------------------------------------------
    # ಮೇಜು ("table") was the natural pick but the recogniser hears it as ನೀಜು
    # (0.50) — unpassable, so it is replaced by ಹಾಸಿಗೆ, which is recognised.
    ("ಹಾಸಿಗೆ",    "",        "bed",             "home", "bed",                   True),
    ("ಕಿಟಕಿ",     "",        "window",          "home", "window",                False),
    ("ಗಡಿಯಾರ",    "",        "clock",           "home", "wall clock",            False),
    ("ಚೆಂಡು",     "",        "ball",            "home", "colourful ball",        True),

    # --- clothes ----------------------------------------------------------
    ("ಅಂಗಿ",      "",        "shirt",           "clothes", "shirt",              True),
    ("ಸೀರೆ",      "",        "saree",           "clothes", "indian saree",       False),

    # --- travel (more) ----------------------------------------------------
    ("ಕಾರು",      "",        "car",             "travel", "car",                 True),
]

# 4. Words too short for the recogniser to resolve on their own.
#
# The same problem as a bare letter, and the same fix. ತಲೆ (tale, "head") is only
# three phonemes, and the recogniser maps it onto a far more frequent word —
# it hears ಅಲ್ಲಿ ("there"). Likewise ಎಲೆ -> ಎಲ್ಲಿ ("where") and ಕೈ -> ತಾಯಿ
# ("mother"). Measured: all three fail in isolation no matter how they are
# spoken, so a child pronouncing them perfectly would always be marked wrong.
#
# Spoken inside a two-word phrase they are all recognised (1.00). The card still
# TEACHES the single word — this only changes what the child is asked to say, and
# saying a body part as "my head" is natural language anyway.
SPOKEN_PHRASE = {
    "ಎಲೆ": ("ಮರದ ಎಲೆ", "the leaf of a tree"),
    "ತಲೆ": ("ನನ್ನ ತಲೆ", "my head"),
    "ಕೈ":  ("ನನ್ನ ಕೈ", "my hand"),
}

# 5. Phrases — the Advanced tier of the syllabus.
#
# Once a child can read whole words, the next step is reading them TOGETHER. These
# are short, natural two-word phrases made entirely from words the curriculum has
# already taught, so nothing here is new vocabulary — the skill being practised is
# joining known words into meaning. They are spoken as the whole phrase, which the
# recogniser handles comfortably (a multi-word utterance is far easier to hear than
# a lone short word), and validate_asr checks every one.
#
# Each phrase sits in the graph behind ONE of its content words (`prereq`, given as
# the Kannada word), so it only appears after that word has been learned. The few
# function words they introduce (ನನ್ನ "my", ದೊಡ್ಡ "big", ಚಿಕ್ಕ "small") are read
# in context, the way a first reader meets them.
#     (kannada_phrase, english, prereq_word_kannada)
PHRASES = [
    ("ನನ್ನ ಅಮ್ಮ",       "my mother",     "ಅಮ್ಮ"),
    ("ನನ್ನ ಮನೆ",        "my house",      "ಮನೆ"),
    ("ನನ್ನ ಶಾಲೆ",       "my school",     "ಶಾಲೆ"),
    ("ಒಂದು ಹಸು",        "one cow",       "ಹಸು"),
    ("ಎರಡು ಕಣ್ಣು",      "two eyes",      "ಕಣ್ಣು"),
    ("ಮೂರು ಮೀನು",       "three fish",    "ಮೀನು"),
    ("ಕೆಂಪು ಹೂವು",      "a red flower",  "ಹೂವು"),
    ("ಹಸಿರು ಎಲೆ",       "a green leaf",  "ಎಲೆ"),
    ("ಬಿಳಿ ಹಾಲು",       "white milk",    "ಹಾಲು"),
    ("ನೀಲಿ ಆಕಾಶ",       "the blue sky",  "ಆಕಾಶ"),
    ("ದೊಡ್ಡ ಆನೆ",       "a big elephant", "ಆನೆ"),
    # ಚಿಕ್ಕ ("small") was misheard as ಚಿತ್ರ (0.63); ಪುಟ್ಟ is recognised cleanly.
    ("ಪುಟ್ಟ ಮಗು",       "a little child", "ಮಗು"),
    ("ಸಿಹಿ ಹಣ್ಣು",      "a sweet fruit", "ಹಣ್ಣು"),
    ("ಒಳ್ಳೆಯ ಸ್ನೇಹಿತ",  "a good friend", "ಸ್ನೇಹಿತ"),
]

# Kannada vowel signs (matras) and the virama, used to strip a word down to the
# base letter it *starts* with, so a word can be attached to that letter's card.
_SIGNS = set("ಾಿೀುೂೃೄೆೇೈೊೋೌ್ಂಃ")


def iso(word):
    """ISO-15919 romanization — the app's scorer romanizes the same way."""
    return transliterate(word.strip(), sanscript.KANNADA, sanscript.ISO)


def base_letter(word):
    """The first *base* letter of a Kannada word (skipping any vowel sign)."""
    for ch in word:
        if ch not in _SIGNS:
            return ch
    return ""


def main():
    rows = []
    letter_concept = {}  # Kannada letter -> concept_id, for wiring word prereqs

    # ---- vowels: a single chain, so they are learned in varnamale order ----
    prev = ""
    for i, (letter, anchor, anchor_en, query) in enumerate(VOWELS, start=1):
        cid = f"V{i:02d}"
        letter_concept[letter] = cid
        rows.append({
            "concept_id": cid,
            "kannada_word": letter,
            "tulu_word": "",
            "english_meaning": f"vowel {iso(letter)} — as in {anchor} ({anchor_en})",
            "image_file": f"{cid}.jpg",
            "category": "vowels",
            "prereq_id": prev,
            "difficulty": 1,
            "level": LEVEL_BASIC,
            "spoken_form": f"{letter} {anchor}",
            "anchor_word": anchor,
            "phrase_gloss": "",
            "image_query": query,
        })
        prev = cid

    last_vowel = prev

    # ---- consonants: all unlock once the vowels are done, so the ORDER they
    #      are taught in is decided by difficulty (core, high-frequency letters
    #      first). Both bands sit ABOVE the vowels (1) and BELOW the words (4+),
    #      so the whole alphabet — the Basic tier — is finished before the first
    #      word is served. Core = 2, the rest = 3.
    for i, (letter, anchor, anchor_en, query, core) in enumerate(CONSONANTS, start=1):
        cid = f"C{i:02d}"
        letter_concept[letter] = cid
        rows.append({
            "concept_id": cid,
            "kannada_word": letter,
            "tulu_word": "",
            "english_meaning": f"consonant {iso(letter)} — as in {anchor} ({anchor_en})",
            "image_file": f"{cid}.jpg",
            "category": "consonants",
            "prereq_id": last_vowel,
            "difficulty": 2 if core else 3,
            "level": LEVEL_BASIC,
            "spoken_form": f"{letter} {anchor}",
            "anchor_word": anchor,
            "phrase_gloss": "",
            "image_query": query,
        })

    # ---- words: the Intermediate tier. Prerequisite is the LETTER the word
    #      starts with, so vocabulary unlocks as the alphabet is mastered.
    #      Difficulty 4 (core) / 5 sits above every letter (<=3), so all words
    #      are served after the whole alphabet — Basic finishes, then Intermediate.
    word_concept = {}  # Kannada word -> concept_id, for wiring phrase prereqs
    for i, (kn, tulu, en, cat, query, core) in enumerate(WORDS, start=1):
        cid = f"W{i:03d}"
        word_concept[kn] = cid
        first = base_letter(kn)
        prereq = letter_concept.get(first, "")
        if not prereq:
            raise SystemExit(
                f"{cid} {kn!r} starts with {first!r}, which is not a letter in the "
                "curriculum — add the letter or change the word."
            )
        # A word is normally spoken as itself. The few that are too short for the
        # recogniser to resolve are said inside a short phrase instead.
        spoken, phrase_gloss = SPOKEN_PHRASE.get(kn, (kn, ""))
        rows.append({
            "concept_id": cid,
            "kannada_word": kn,
            "tulu_word": tulu,
            "english_meaning": en,
            "image_file": f"{cid}.jpg",
            "category": cat,
            "prereq_id": prereq,
            "difficulty": 4 if core else 5,
            "level": LEVEL_INTERMEDIATE,
            "spoken_form": spoken,
            # anchor_word doubles as the hint shown under "Say this", and as the
            # alternate accepted form; for a phrase there is no alternate, so it
            # carries the English gloss of the phrase for the UI.
            "anchor_word": "",
            "phrase_gloss": phrase_gloss,
            "image_query": query,
        })

    # ---- phrases: the Advanced tier. Each sits behind one of its content words
    #      (difficulty 6, above every word), so phrases are served last — after
    #      the child can already read the words they are built from.
    for i, (phrase, en, prereq_word) in enumerate(PHRASES, start=1):
        cid = f"P{i:03d}"
        prereq = word_concept.get(prereq_word, "")
        if not prereq:
            raise SystemExit(
                f"{cid} {phrase!r} needs prereq word {prereq_word!r}, which is not "
                "in the curriculum — add the word or change the phrase."
            )
        rows.append({
            "concept_id": cid,
            "kannada_word": phrase,
            "tulu_word": "",
            "english_meaning": en,
            "image_file": f"{cid}.jpg",
            "category": "phrases",
            "prereq_id": prereq,
            "difficulty": 6,
            "level": LEVEL_ADVANCED,
            "spoken_form": phrase,
            "anchor_word": "",
            # The gloss carries the English so the card can show what the phrase
            # means without a separate image of an abstract idea.
            "phrase_gloss": en,
            "image_query": "",
        })

    # ---- derived columns: never hand-typed --------------------------------
    for r in rows:
        source = r["spoken_form"]        # romanize what is actually SAID
        r["transliteration"] = iso(r["kannada_word"])
        r["ipa"] = iso(source)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    # utf-8-sig: Excel needs the BOM to detect UTF-8, so a teacher can open and
    # edit the Kannada columns without mojibake. Every reader here handles it.
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)

    letters = sum(1 for r in rows if r["category"] in ("vowels", "consonants"))
    phrases = sum(1 for r in rows if r["category"] == "phrases")
    words = len(rows) - letters - phrases
    tulu = sum(1 for r in rows if r["tulu_word"])
    by_level = {lv: sum(1 for r in rows if r["level"] == lv)
                for lv in (LEVEL_BASIC, LEVEL_INTERMEDIATE, LEVEL_ADVANCED)}
    print(f"Wrote {len(rows)} concepts to {OUT}")
    print(f"  {len(VOWELS)} vowels + {len(CONSONANTS)} consonants = {letters} letters")
    print(f"  {words} vocabulary words ({tulu} with a Tulu form)")
    print(f"  {phrases} phrases")
    print(f"  tiers: " + ", ".join(f"{lv} {n}" for lv, n in by_level.items()))
    print(f"  categories: {sorted({r['category'] for r in rows})}")


if __name__ == "__main__":
    main()
