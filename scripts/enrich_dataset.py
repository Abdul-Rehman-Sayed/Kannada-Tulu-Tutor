import sys

sys.exit(
    "enrich_dataset.py is superseded by build_dataset.py and will not run.\n"
    "Running it would drop the spoken_form / anchor_word / phrase_gloss /\n"
    "image_query columns and make every letter card unpassable again.\n\n"
    "Edit the curriculum in scripts/build_dataset.py, then, from the project root:\n"
    "    python -m scripts.build_dataset\n"
    "    python -m tests.validate_dataset data/vocabulary.csv\n"
    "    python -m tests.validate_asr\n"
)
