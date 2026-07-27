"""
enrich_dataset.py — SUPERSEDED. Do not run this against data/vocabulary.csv.

This script used to fill blank transliteration/ipa cells in a hand-written CSV.
`build_dataset.py` now generates the whole curriculum, including those columns,
from the authoritative source data — so this is redundant.

It is also DANGEROUS to run as it was written. It rewrote the CSV using a
hardcoded list of ten columns, and the curriculum now has fourteen. Running the
old version would silently drop:

    spoken_form    what the child is asked to SAY. Without it every letter card
                   reverts to asking for a bare "ಅ", which the recogniser cannot
                   hear — a child would be marked wrong for a perfect answer, and
                   the very first card in the app would become unpassable again.
                   This is the exact bug the project was fixed to remove.
    anchor_word    the anchor shown and accepted for letter cards
    phrase_gloss   the English gloss of the phrase for short words
    image_query    which picture each concept fetches

Nothing is deleted here, because you may still want the file. It simply refuses
to run rather than quietly corrupting the dataset.

To change the curriculum, edit build_dataset.py and run:

    python build_dataset.py
    python validate_dataset.py data/vocabulary.csv
    python validate_asr.py            # proves every card is still passable
"""

import sys

sys.exit(
    "enrich_dataset.py is superseded by build_dataset.py and will not run.\n"
    "Running it would drop the spoken_form / anchor_word / phrase_gloss /\n"
    "image_query columns and make every letter card unpassable again.\n\n"
    "Edit the curriculum in build_dataset.py, then:\n"
    "    python build_dataset.py\n"
    "    python validate_dataset.py data/vocabulary.csv\n"
    "    python validate_asr.py\n"
)
