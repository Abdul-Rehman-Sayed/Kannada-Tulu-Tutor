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
    "concept_id", "language", "kannada_word", "tulu_word", "transliteration",
    "ipa", "english_meaning", "image_file", "category", "prereq_id",
    "difficulty", "level", "spoken_form", "anchor_word", "phrase_gloss",
    "image_query",
]

LANG_KANNADA = "kn"
LANG_TULU = "tu"

LEVEL_BASIC = "Basic"
LEVEL_INTERMEDIATE = "Intermediate"
LEVEL_ADVANCED = "Advanced"
LEVEL_SENTENCES = "Sentences"

VOWELS = [
    ("ಅ", "ಅಮ್ಮ",   "mother",     "indian mother baby"),
    ("ಆ", "ಆನೆ",    "elephant",   "Indian elephant"),
    ("ಇ", "ಇಲಿ",    "mouse",      "house mouse"),
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

CONSONANTS = [
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

WORDS = [
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

    ("ಅನ್ನ",     "ಅನ್ನ",    "cooked rice",     "food", "cooked rice",            True),
    ("ಹಾಲು",     "ಪೇರ್",    "milk",            "food", "glass of milk",          True),
    ("ಉಪ್ಪು",    "ಉಪ್ಪು",   "salt",            "food", "salt",                   False),
    ("ಹಣ್ಣು",    "ಪರ್ಂದ್",  "fruit",           "food", "assorted fruit",         True),
    ("ಬಾಳೆಹಣ್ಣು", "",       "banana",          "food", "banana",                 False),
    ("ಮೊಸರು",    "ಮೊಸರು",   "curd",            "food", "curd yogurt",            False),
    ("ಸಕ್ಕರೆ",   "",        "sugar",           "food", "sugar",                  False),
    ("ರೊಟ್ಟಿ",   "",        "flatbread",       "food", "roti flatbread",         False),

    ("ತಲೆ",      "ತರೆ",     "head",            "body", "child face portrait",             True),
    ("ಕಣ್ಣು",    "ಕಣ್ಣ್",   "eye",             "body", "human eye closeup",              True),
    ("ಕಿವಿ",     "ಕೆಬಿ",    "ear",             "body", "human ear closeup",              True),
    ("ಮೂಗು",     "ಮೂಕು",    "nose",            "body", "human nose closeup",             True),
    ("ಬಾಯಿ",     "ಬಾಯಿ",    "mouth",           "body", "human lips closeup",            False),
    ("ಕೈ",       "ಕೈ",      "hand",            "body", "open human hand",             True),
    ("ಕಾಲು",     "ಕಾರ್",    "leg",             "body", "human legs walking",              False),
    ("ಹಲ್ಲು",    "ಪಲ್ಲ್",   "tooth",           "body", "tooth",                  False),

    ("ಕೆಂಪು",    "ಕೆಂಪು",   "red",             "colours", "red colour",          True),
    ("ಹಸಿರು",    "ಪಚ್ಚೆ",   "green",           "colours", "green colour",        True),
    ("ಹಳದಿ",     "ಮಂಜಲ್",   "yellow",          "colours", "yellow colour",       True),
    ("ನೀಲಿ",     "ನೀಲಿ",    "blue",            "colours", "blue colour",         True),
    ("ಕಪ್ಪು",    "ಕಪ್ಪು",   "black",           "colours", "black colour",        False),
    ("ಬಿಳಿ",     "ಬೊಲ್ದು",  "white",           "colours", "white colour",        False),

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

    ("ಮಾವು",      "",        "mango",           "fruits", "mango fruit",         True),
    ("ಸೇಬು",      "",        "apple",           "fruits", "red apple",           True),
    ("ಕಿತ್ತಳೆ",   "",        "orange",          "fruits", "orange fruit",        True),
    ("ದ್ರಾಕ್ಷಿ",  "",        "grapes",          "fruits", "bunch of grapes",     False),
    ("ಕಲ್ಲಂಗಡಿ",  "",        "watermelon",      "fruits", "watermelon",          False),

    ("ಆಲೂಗಡ್ಡೆ",  "",        "potato",          "vegetables", "potato",          True),
    ("ಬದನೆಕಾಯಿ",  "",        "brinjal",         "vegetables", "brinjal eggplant", False),
    ("ಬೆಂಡೆಕಾಯಿ", "",        "okra",            "vegetables", "okra ladyfinger", False),

    ("ದೋಸೆ",      "",        "dosa",            "food", "dosa south indian",     True),
    ("ಇಡ್ಲಿ",     "",        "idli",            "food", "idli steamed cake",     True),
    ("ಜೇನು",      "",        "honey",           "food", "honey jar",             False),
    ("ಬೆಣ್ಣೆ",    "",        "butter",          "food", "butter block",          False),

    ("ಮಂಗ",       "",        "monkey",          "animals", "monkey",             True),
    ("ಗಿಳಿ",      "",        "parrot",          "animals", "green parrot",       True),
    ("ಕಾಗೆ",      "",        "crow",            "animals", "crow bird",          False),
    ("ನವಿಲು",     "",        "peacock",         "animals", "peacock",            True),
    ("ಮೊಲ",       "",        "rabbit",          "animals", "rabbit",             False),
    ("ಅಳಿಲು",     "",        "squirrel",        "animals", "squirrel",           False),

    ("ಮುಖ",       "",        "face",            "body", "child smiling face",    True),
    ("ಕೂದಲು",     "",        "hair",            "body", "hair",                  True),
    ("ಬೆರಳು",     "",        "finger",          "body", "finger pointing",       False),

    ("ಮೋಡ",       "",        "cloud",           "nature", "white cloud sky",     True),
    ("ನದಿ",       "",        "river",           "nature", "river",               True),
    ("ಆಕಾಶ",      "",        "sky",             "nature", "blue sky",            True),
    ("ಕಲ್ಲು",     "",        "stone",           "nature", "stone rock",          False),

    ("ಹಾಸಿಗೆ",    "",        "bed",             "home", "bed",                   True),
    ("ಕಿಟಕಿ",     "",        "window",          "home", "window",                False),
    ("ಗಡಿಯಾರ",    "",        "clock",           "home", "wall clock",            False),
    ("ಚೆಂಡು",     "",        "ball",            "home", "colourful ball",        True),

    ("ಅಂಗಿ",      "",        "shirt",           "clothes", "shirt",              True),
    ("ಸೀರೆ",      "",        "saree",           "clothes", "indian saree",       False),

    ("ಕಾರು",      "",        "car",             "travel", "car",                 True),
]

SPOKEN_PHRASE = {
    "ಎಲೆ": ("ಮರದ ಎಲೆ", "the leaf of a tree"),
    "ತಲೆ": ("ನನ್ನ ತಲೆ", "my head"),
    "ಕೈ":  ("ನನ್ನ ಕೈ", "my hand"),
}

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
    ("ಪುಟ್ಟ ಮಗು",       "a little child", "ಮಗು"),
    ("ಸಿಹಿ ಹಣ್ಣು",      "a sweet fruit", "ಹಣ್ಣು"),
    ("ಒಳ್ಳೆಯ ಸ್ನೇಹಿತ",  "a good friend", "ಸ್ನೇಹಿತ"),
]

SENTENCES = [
    ("ಇದು ನನ್ನ ಮನೆ",                "This is my house",            "ಮನೆ"),
    ("ಇದು ನನ್ನ ಪುಸ್ತಕ",             "This is my book",             "ಪುಸ್ತಕ"),
    ("ಇದು ನನ್ನ ಸ್ನೇಹಿತ",            "This is my friend",           "ಸ್ನೇಹಿತ"),
    ("ನನ್ನ ಶಾಲೆ ದೊಡ್ಡದು",           "My school is big",            "ಶಾಲೆ"),
    ("ನಾನು ಶಾಲೆಗೆ ಹೋಗುತ್ತೇನೆ",      "I go to school",              "ಶಾಲೆ"),
    ("ನಾನು ಪುಸ್ತಕ ಓದುತ್ತೇನೆ",       "I read a book",               "ಪುಸ್ತಕ"),
    ("ನಾನು ಹಾಲು ಕುಡಿಯುತ್ತೇನೆ",      "I drink milk",                "ಹಾಲು"),
    ("ನಾನು ನೀರು ಕುಡಿಯುತ್ತೇನೆ",      "I drink water",               "ನೀರು"),
    ("ನಾನು ಅನ್ನ ತಿನ್ನುತ್ತೇನೆ",       "I eat rice",                  "ಅನ್ನ"),
    ("ನಾನು ಚೆಂಡು ಆಡುತ್ತೇನೆ",        "I play with the ball",        "ಚೆಂಡು"),
    ("ನಾವು ಶಾಲೆಗೆ ಹೋಗುತ್ತೇವೆ",      "We go to school",             "ಶಾಲೆ"),
    ("ಅಮ್ಮ ಮನೆಯಲ್ಲಿ ಇದ್ದಾರೆ",       "Mother is at home",           "ಅಮ್ಮ"),
    ("ಅಪ್ಪ ಕೆಲಸಕ್ಕೆ ಹೋಗುತ್ತಾರೆ",     "Father goes to work",         "ಅಪ್ಪ"),
    ("ಅಜ್ಜಿ ಕಥೆ ಹೇಳುತ್ತಾರೆ",         "Grandmother tells a story",   "ಅಜ್ಜಿ"),
    ("ನನ್ನ ಅಣ್ಣ ಶಾಲೆಗೆ ಹೋಗುತ್ತಾನೆ",  "My elder brother goes to school", "ಅಣ್ಣ"),
    ("ಮಗು ಆಟ ಆಡುತ್ತದೆ",             "The child plays",             "ಮಗು"),
    ("ಹಸು ಹಾಲು ಕೊಡುತ್ತದೆ",          "The cow gives milk",          "ಹಸು"),
    ("ನಾಯಿ ಮನೆಯಲ್ಲಿ ಇದೆ",           "The dog is in the house",     "ನಾಯಿ"),
    ("ಬೆಕ್ಕು ಹಾಲು ಕುಡಿಯುತ್ತದೆ",     "The cat drinks milk",         "ಬೆಕ್ಕು"),
    ("ಮೀನು ನೀರಿನಲ್ಲಿ ಇದೆ",          "The fish is in the water",    "ಮೀನು"),
    ("ಹಕ್ಕಿ ಆಕಾಶದಲ್ಲಿ ಹಾರುತ್ತದೆ",   "The bird flies in the sky",   "ಹಕ್ಕಿ"),
    ("ಆನೆ ತುಂಬಾ ದೊಡ್ಡದು",           "The elephant is very big",    "ಆನೆ"),
    ("ಮಂಗ ಮರ ಹತ್ತುತ್ತದೆ",           "The monkey climbs the tree",  "ಮಂಗ"),
    ("ನವಿಲು ಚೆನ್ನಾಗಿ ಕುಣಿಯುತ್ತದೆ",  "The peacock dances beautifully", "ನವಿಲು"),
    ("ಸೂರ್ಯ ಆಕಾಶದಲ್ಲಿ ಇದ್ದಾನೆ",     "The sun is in the sky",       "ಸೂರ್ಯ"),
    ("ಚಂದ್ರ ರಾತ್ರಿ ಕಾಣುತ್ತಾನೆ",     "The moon is seen at night",   "ಚಂದ್ರ"),
    ("ಇವತ್ತು ಮಳೆ ಬರುತ್ತಿದೆ",        "It is raining today",         "ಮಳೆ"),
    ("ಮರದಲ್ಲಿ ಹಣ್ಣು ಇದೆ",           "There is fruit on the tree",  "ಮರ"),
    ("ಈ ಹೂವು ಕೆಂಪಾಗಿದೆ",            "This flower is red",          "ಹೂವು"),
    ("ನನಗೆ ಎರಡು ಕಣ್ಣು ಇವೆ",         "I have two eyes",             "ಕಣ್ಣು"),
]

TULU_CATEGORY_ORDER = [
    "family", "animals", "body", "food", "nature",
    "numbers", "colours", "home", "school", "travel",
]

TULU_SPOKEN_PHRASE = {
    "ಅಪ್ಪೆ":  ("ಅಪ್ಪೆ ಬತ್ತೆರ್", "mother came"),
    "ಪಳ್ದಿ":  ("ಎನ್ನ ಪಳ್ದಿ", "my elder sister"),
    "ಪೆತ್ತ":  ("ಎನ್ನ ಪೆತ್ತ", "my cow"),
    "ಪಕ್ಕಿ":  ("ಎನ್ನ ಪಕ್ಕಿ", "my bird"),
    "ಕಣ್ಣ್":  ("ಎನ್ನ ಕಣ್ಣ್", "my eye"),
    "ಕೈ":     ("ಎನ್ನ ಕೈ", "my hand"),
    "ತೂ":     ("ತೂ ಉಂಡು", "there is fire"),
    "ರಡ್ಡ್":  ("ಒಂಜಿ ರಡ್ಡ್ ಮೂಜಿ", "one, two, three"),
}

TULU_UNHEARABLE = {"ಎಲೆ", "ಪೂ", "ಏಳ್", "ಐನ್"}

TULU_PHRASES = [
    ("ಎನ್ನ ಇಲ್ಲ್",   "my house",     "ಇಲ್ಲ್", "ಉಂದು ಎನ್ನ ಇಲ್ಲ್"),
    ("ಎನ್ನ ಶಾಲೆ",    "my school",    "ಶಾಲೆ",  ""),
    ("ಒಂಜಿ ಪೆತ್ತ",   "one cow",      "ಪೆತ್ತ", ""),
    ("ರಡ್ಡ್ ಕಣ್ಣ್",  "two eyes",     "ಕಣ್ಣ್", "ರಡ್ಡ್ ಕಣ್ಣ್ ಉಂಡು"),
    ("ಮೂಜಿ ಮೀನ್",    "three fish",   "ಮೀನ್",  ""),
    ("ಬೊಲ್ದು ಪೇರ್",  "white milk",   "ಪೇರ್",  ""),
]

_SIGNS = set("ಾಿೀುೂೃೄೆೇೈೊೋೌ್ಂಃ")


def iso(word):
    return transliterate(word.strip(), sanscript.KANNADA, sanscript.ISO)


def base_letter(word):
    for ch in word:
        if ch not in _SIGNS:
            return ch
    return ""


def display_word(row):
    if row.get("language") == LANG_TULU:
        return (row.get("tulu_word") or row.get("kannada_word") or "").strip()
    return (row.get("kannada_word") or "").strip()


def main():
    rows = []
    letter_concept = {}

    prev = ""
    for i, (letter, anchor, anchor_en, query) in enumerate(VOWELS, start=1):
        cid = f"V{i:02d}"
        letter_concept[letter] = cid
        rows.append({
            "concept_id": cid,
            "language": LANG_KANNADA,
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

    for i, (letter, anchor, anchor_en, query, core) in enumerate(CONSONANTS, start=1):
        cid = f"C{i:02d}"
        letter_concept[letter] = cid
        rows.append({
            "concept_id": cid,
            "language": LANG_KANNADA,
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

    word_concept = {}
    kn_image = {}
    for i, (kn, tulu, en, cat, query, core) in enumerate(WORDS, start=1):
        cid = f"W{i:03d}"
        word_concept[kn] = cid
        kn_image[kn] = cid
        first = base_letter(kn)
        prereq = letter_concept.get(first, "")
        if not prereq:
            raise SystemExit(
                f"{cid} {kn!r} starts with {first!r}, which is not a letter in the "
                "curriculum — add the letter or change the word."
            )
        spoken, phrase_gloss = SPOKEN_PHRASE.get(kn, (kn, ""))
        rows.append({
            "concept_id": cid,
            "language": LANG_KANNADA,
            "kannada_word": kn,
            "tulu_word": tulu,
            "english_meaning": en,
            "image_file": f"{cid}.jpg",
            "category": cat,
            "prereq_id": prereq,
            "difficulty": 4 if core else 5,
            "level": LEVEL_INTERMEDIATE,
            "spoken_form": spoken,
            "anchor_word": "",
            "phrase_gloss": phrase_gloss,
            "image_query": query,
        })

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
            "language": LANG_KANNADA,
            "kannada_word": phrase,
            "tulu_word": "",
            "english_meaning": en,
            "image_file": f"{prereq}.jpg",
            "category": "phrases",
            "prereq_id": prereq,
            "difficulty": 6,
            "level": LEVEL_ADVANCED,
            "spoken_form": phrase,
            "anchor_word": "",
            "phrase_gloss": en,
            "image_query": "",
        })

    for i, (sentence, en, prereq_word) in enumerate(SENTENCES, start=1):
        cid = f"S{i:03d}"
        prereq = word_concept.get(prereq_word, "")
        if not prereq:
            raise SystemExit(
                f"{cid} {sentence!r} needs prereq word {prereq_word!r}, which is "
                "not in the curriculum — add the word or change the sentence."
            )
        rows.append({
            "concept_id": cid,
            "language": LANG_KANNADA,
            "kannada_word": sentence,
            "tulu_word": "",
            "english_meaning": en,
            "image_file": f"{prereq}.jpg",
            "category": "sentences",
            "prereq_id": prereq,
            "difficulty": 7,
            "level": LEVEL_SENTENCES,
            "spoken_form": sentence,
            "anchor_word": "",
            "phrase_gloss": en,
            "image_query": "",
        })

    tulu_by_cat = {}
    for kn, tulu, en, cat, query, core in WORDS:
        tulu = tulu.strip()
        if tulu and tulu not in TULU_UNHEARABLE:
            tulu_by_cat.setdefault(cat, []).append((tulu, kn, en, query, core))

    cats = [c for c in TULU_CATEGORY_ORDER if c in tulu_by_cat]
    cats += [c for c in sorted(tulu_by_cat) if c not in cats]

    tulu_concept = {}
    tulu_image = {}
    n = 0
    for cat_rank, cat in enumerate(cats):
        prev = ""
        for tulu, kn, en, query, core in tulu_by_cat[cat]:
            n += 1
            cid = f"TW{n:03d}"
            tulu_concept.setdefault(tulu, cid)
            tulu_image[cid] = f"{kn_image.get(kn, cid)}.jpg"
            spoken, gloss = TULU_SPOKEN_PHRASE.get(tulu, (tulu, ""))
            rows.append({
                "concept_id": cid,
                "language": LANG_TULU,
                "kannada_word": kn,
                "tulu_word": tulu,
                "english_meaning": en,
                "image_file": f"{kn_image.get(kn, cid)}.jpg",
                "category": cat,
                "prereq_id": prev,
                "difficulty": 4 + cat_rank * 2 + (0 if core else 1),
                "level": LEVEL_INTERMEDIATE,
                "spoken_form": spoken,
                "anchor_word": "",
                "phrase_gloss": gloss,
                "image_query": query,
            })
            prev = cid

    max_word_difficulty = 4 + max(len(cats) - 1, 0) * 2 + 1
    for i, (phrase, en, prereq_word, spoken) in enumerate(TULU_PHRASES, start=1):
        cid = f"TP{i:03d}"
        prereq = tulu_concept.get(prereq_word, "")
        if not prereq:
            raise SystemExit(
                f"{cid} {phrase!r} needs Tulu word {prereq_word!r}, which is not in "
                "the Tulu track — add it to WORDS with a tulu form, or change the "
                "phrase."
            )
        rows.append({
            "concept_id": cid,
            "language": LANG_TULU,
            "kannada_word": "",
            "tulu_word": phrase,
            "english_meaning": en,
            "image_file": tulu_image.get(prereq, f"{cid}.jpg"),
            "category": "phrases",
            "prereq_id": prereq,
            "difficulty": max_word_difficulty + 1,
            "level": LEVEL_ADVANCED,
            "spoken_form": spoken or phrase,
            "anchor_word": "",
            "phrase_gloss": en,
            "image_query": "",
        })

    for r in rows:
        r["transliteration"] = iso(display_word(r))
        r["ipa"] = iso(r["spoken_form"])

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)

    kn_rows = [r for r in rows if r["language"] == LANG_KANNADA]
    tu_rows = [r for r in rows if r["language"] == LANG_TULU]
    letters = sum(1 for r in kn_rows if r["category"] in ("vowels", "consonants"))
    kn_phrases = sum(1 for r in kn_rows if r["category"] == "phrases")
    sentences = sum(1 for r in kn_rows if r["category"] == "sentences")
    kn_words = len(kn_rows) - letters - kn_phrases - sentences
    paired = sum(1 for r in rows if r["kannada_word"] and r["tulu_word"])
    by_level = {lv: sum(1 for r in rows if r["level"] == lv)
                for lv in (LEVEL_BASIC, LEVEL_INTERMEDIATE, LEVEL_ADVANCED,
                           LEVEL_SENTENCES)}
    print(f"Wrote {len(rows)} concepts to {OUT}")
    print(f"  Kannada track — {len(kn_rows)} concepts")
    print(f"    {len(VOWELS)} vowels + {len(CONSONANTS)} consonants = {letters} letters")
    print(f"    {kn_words} words, {kn_phrases} phrases, {sentences} sentences")
    print(f"  Tulu track — {len(tu_rows)} concepts")
    print(f"    {len(tu_rows) - len(TULU_PHRASES)} words, {len(TULU_PHRASES)} phrases")
    print(f"  {paired} rows pair a Kannada word with its Tulu equivalent")
    print("  tiers: " + ", ".join(f"{lv} {n}" for lv, n in by_level.items()))
    print(f"  categories: {sorted({r['category'] for r in rows})}")


if __name__ == "__main__":
    main()
