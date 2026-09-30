import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from tutor import graph_engine, tulu_lipi

KA, TA, PA, VA, I = "\U00011392", "\U000113A1", "\U000113A6", "\U000113AE", "\U00011382"
EE, OO = "\U0001138B", "\U00011390"


def main():
    failures = []

    cases = [
        ("ಕ", KA, "a letter maps to its Tulu lipi letter"),
        ("ಪತ್ತ್", PA + TA + tulu_lipi.CONJOINER + TA + tulu_lipi.VIRAMA,
         "a doubled consonant is joined with the conjoiner, and the virama "
         "at the end marks the Tulu u"),
        ("ಇರ್ವ", I + tulu_lipi.REPHA + VA, "ra before a consonant is the repha"),
        ("ಎ", EE, "short e is written with the ee letter"),
        ("ಏ", EE, "long e is written with the ee letter"),
        ("ಒ", OO, "short o is written with the oo letter"),
        ("೧೨", "೧೨", "digits stay Kannada digits"),
        ("ಕ ಕ", KA + " " + KA, "spaces pass through"),
    ]
    for kannada, want, why in cases:
        got = tulu_lipi.convert(kannada)
        if got != want:
            failures.append(f"{kannada!r}: {why} - got "
                            f"{' '.join(f'U+{ord(c):X}' for c in got)}")
    print(f"converter: {len(cases) - len(failures)} of {len(cases)} rules hold")

    letters = graph_engine.letters_in_order(graph_engine.TULU)
    shown = [graph_engine.shown_word(c) for cat in letters.values() for c in cat]
    bad = [s for s in shown
           if len(s) != 1 or not tulu_lipi.is_tulu_lipi(s)]
    if bad:
        failures.append(f"Tulu letters not shown as one Tulu lipi letter: {bad}")
    else:
        print(f"all {len(shown)} Tulu letters are shown in Tulu lipi: "
              f"{' '.join(shown)}")

    for cat in graph_engine.letters_in_order(graph_engine.TULU).values():
        for c in cat:
            if tulu_lipi.is_tulu_lipi(c["spoken_form"] + graph_engine.listen_form(c)):
                failures.append(f"{c['concept_id']} would send Tulu lipi to the "
                                "recogniser or the speech synthesiser")

    kn = [graph_engine.shown_word(c) for cat in
          graph_engine.letters_in_order(graph_engine.KANNADA).values() for c in cat]
    if any(tulu_lipi.is_tulu_lipi(s) for s in kn):
        failures.append("a Kannada letter is being shown in Tulu lipi")

    words = [d for _, d in graph_engine.load_graph(graph_engine.TULU).nodes(data=True)
             if not graph_engine.is_letter(d)]
    wrong = [d["concept_id"] for d in words
             if graph_engine.shown_word(d) != graph_engine.display_word(d)]
    if wrong:
        failures.append(f"Tulu words changed script, but no font can join "
                        f"them yet: {wrong[:5]}")
    else:
        print(f"the {len(words)} Tulu words, numbers and phrases stay in the "
              "Kannada script")

    font = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "static", "fonts", "Mallige-v1.4.ttf")
    if not os.path.exists(font):
        failures.append("the Tulu lipi font is missing from static/fonts")

    if failures:
        print("\nFAIL:")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("\nPASS: the Tulu alphabet is shown in Tulu lipi, while speech still "
          "runs on the Kannada script.")


if __name__ == "__main__":
    main()
