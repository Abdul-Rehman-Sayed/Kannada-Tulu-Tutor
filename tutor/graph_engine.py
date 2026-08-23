"""
graph_engine.py — concept graph + adaptive sequencing for the literacy tutor.

Loads data/vocabulary.csv and builds a directed NetworkX graph where each
concept_id is a node and prereq_id defines a directed edge (prereq -> concept).
The graph drives an adaptive curriculum: a student is always shown the easiest
concept they are *ready* for (all prerequisites mastered) but have not mastered.

Public API (used by app.py):
    load_graph()
    get_next_concept(student_id)
    update_mastery(student_id, concept_id, correct_bool)
    get_student_progress(student_id)
"""

import os
from collections import deque

import pandas as pd
import networkx as nx

from . import db

VOCAB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "vocabulary.csv")

_GRAPH = None
_SUBGRAPHS = {}

_REQUIRED_COLUMNS = [
    "concept_id", "language", "kannada_word", "tulu_word", "transliteration",
    "ipa", "english_meaning", "image_file", "category", "prereq_id",
    "difficulty", "level", "spoken_form", "anchor_word", "phrase_gloss",
]

KANNADA = "kn"
TULU = "tu"

LANGUAGES = {
    KANNADA: {
        "code": KANNADA,
        "name": "Kannada",
        "native": "ಕನ್ನಡ",
        "blurb": "The full syllabus: the alphabet, then words, then phrases and "
                 "whole sentences.",
        "asr": "kn",
    },
    TULU: {
        "code": TULU,
        "name": "Tulu",
        "native": "ತುಳು",
        "blurb": "Everyday Tulu words and phrases, written in Kannada script, "
                 "grouped by topic.",
        "asr": "kn",
    },
}

DEFAULT_LANGUAGE = KANNADA


def language_info(code):
    """The metadata block for a language code, falling back to Kannada."""
    return LANGUAGES.get(code) or LANGUAGES[DEFAULT_LANGUAGE]


def language_name(code):
    return language_info(code)["name"]


def display_word(concept):
    """
    The word a learner is shown and scored on — Tulu on the Tulu track, Kannada
    on the Kannada track.

    Every row carries both scripts, because the Kannada-word/Tulu-equivalent
    pairing is the dataset this project contributes and the teacher dashboard
    reads it. Only one of the two is ever put in front of a child, and this is
    the single place that decides which. build_dataset.py derives the CSV's
    transliteration column through the identical rule, so the romanization on a
    card always belongs to the word printed above it.
    """
    if (concept.get("language") or KANNADA) == TULU:
        return (concept.get("tulu_word") or concept.get("kannada_word") or "").strip()
    return (concept.get("kannada_word") or "").strip()

LEVELS = ["Basic", "Intermediate", "Advanced", "Sentences"]

LEVEL_MEANING = {
    "Basic": "Letters of the alphabet",
    "Intermediate": "Whole words",
    "Advanced": "Two-word phrases",
    "Sentences": "Complete sentences",
}


def load_graph(language=None, force_reload=False):
    """
    The concept DiGraph from vocabulary.csv (cached).

    With no `language` this is the whole dataset — both curricula, as two
    disconnected components. With one, it is that language's curriculum alone,
    which is what every learner-facing call wants: the Tulu track must not be
    able to see, count, or serve a Kannada concept.

    The subgraph is a real filtered copy rather than a view, so callers can treat
    it as an ordinary graph, and it is cached per language because it is rebuilt
    on every Streamlit rerun otherwise.
    """
    if language is not None:
        if force_reload:
            _SUBGRAPHS.clear()
        if language not in _SUBGRAPHS:
            full = load_graph(force_reload=force_reload)
            _SUBGRAPHS[language] = full.subgraph(
                [n for n, d in full.nodes(data=True)
                 if d.get("language", KANNADA) == language]
            ).copy()
        return _SUBGRAPHS[language]

    global _GRAPH
    if _GRAPH is not None and not force_reload:
        return _GRAPH
    _SUBGRAPHS.clear()

    if not os.path.exists(VOCAB_PATH):
        raise FileNotFoundError(f"vocabulary CSV not found at {VOCAB_PATH}")

    df = pd.read_csv(VOCAB_PATH, dtype=str, encoding="utf-8", keep_default_na=False)

    missing = [c for c in _REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"vocabulary.csv is missing columns: {missing}")

    G = nx.DiGraph()

    for _, row in df.iterrows():
        cid = row["concept_id"].strip()
        if not cid:
            continue
        if cid in G:
            raise ValueError(f"duplicate concept_id in vocabulary.csv: {cid}")
        difficulty = row["difficulty"].strip()
        try:
            difficulty = int(difficulty) if difficulty else 99
        except ValueError:
            raise ValueError(
                f"concept '{cid}' has a non-numeric difficulty: {difficulty!r} "
                "(fix vocabulary.csv — run validate_dataset.py)"
            ) from None
        kannada_word = row["kannada_word"].strip()
        tulu_word = row["tulu_word"].strip()
        language = row["language"].strip() or KANNADA
        G.add_node(
            cid,
            concept_id=cid,
            language=language,
            kannada_word=kannada_word,
            tulu_word=tulu_word,
            display_word=display_word(
                {"language": language, "kannada_word": kannada_word,
                 "tulu_word": tulu_word}
            ),
            transliteration=row["transliteration"].strip(),
            ipa=row["ipa"].strip(),
            english_meaning=row["english_meaning"].strip(),
            image_file=row["image_file"].strip(),
            category=row["category"].strip(),
            difficulty=difficulty,
            level=row["level"].strip() or "Basic",
            spoken_form=row["spoken_form"].strip() or kannada_word,
            anchor_word=row["anchor_word"].strip(),
            phrase_gloss=row["phrase_gloss"].strip(),
        )

    for _, row in df.iterrows():
        cid = row["concept_id"].strip()
        prereq = row["prereq_id"].strip()
        if not cid or not prereq:
            continue
        if prereq not in G:
            raise ValueError(
                f"prereq_id '{prereq}' (for concept '{cid}') is not a known concept_id"
            )
        if G.nodes[prereq]["language"] != G.nodes[cid]["language"]:
            raise ValueError(
                f"concept '{cid}' ({G.nodes[cid]['language']}) has prereq "
                f"'{prereq}' ({G.nodes[prereq]['language']}) — prerequisites may "
                "not cross languages"
            )
        G.add_edge(prereq, cid)

    if not nx.is_directed_acyclic_graph(G):
        cycle = nx.find_cycle(G)
        raise ValueError(f"vocabulary prerequisites contain a cycle: {cycle}")

    _GRAPH = G
    return G


def concept_info(concept_id):
    """Return the attribute dict for one concept, or None if unknown.

    Deliberately searches the FULL graph, not one language: this is how the
    teacher dashboard resolves a concept id out of the attempt history, and a
    class contains children on both tracks.
    """
    G = load_graph()
    return dict(G.nodes[concept_id]) if concept_id in G else None


PARK_AFTER_ATTEMPTS = 6


def _progression_sets(student_id, G):
    """(mastered, parked) — parked = tried hard, still failing, moved past."""
    mastered, parked = set(), set()
    for row in db.get_mastery_rows(student_id):
        cid = row["concept_id"]
        if cid not in G:
            continue
        if row["mastery_score"] >= db.MASTERY_THRESHOLD:
            mastered.add(cid)
        elif row["attempts"] >= PARK_AFTER_ATTEMPTS:
            parked.add(cid)
    return mastered, parked


def get_next_concept(student_id, language=DEFAULT_LANGUAGE):
    """
    The concept the student should learn next *in the language they chose*: the
    lowest-difficulty concept that is not yet mastered, not parked, and whose
    prerequisites are all cleared. Returns None when nothing is left on that
    track.

    `language` is not optional in spirit — a call without it would serve a child
    the whole dataset and hand a Tulu learner Kannada consonants.
    """
    G = load_graph(language)
    mastered, parked = _progression_sets(student_id, G)
    cleared = mastered | parked

    visited = set()
    queue = deque()

    for n in G.nodes:
        if G.in_degree(n) == 0:
            queue.append(n)
    for n in cleared:
        queue.extend(G.successors(n))

    candidates = []
    while queue:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)

        if node in cleared:
            queue.extend(G.successors(node))
            continue

        if all(p in cleared for p in G.predecessors(node)):
            candidates.append(node)

    if not candidates:
        return None

    candidates.sort(key=lambda n: (G.nodes[n]["difficulty"], n))
    return dict(G.nodes[candidates[0]])


def update_mastery(student_id, concept_id, correct_bool, raw_score=None, heard=None):
    """Record an attempt and return the updated mastery score.

    `raw_score` (optional, 0..1) is the pronunciation similarity for this
    attempt; it is logged in the session history for the teacher view.
    `heard` (optional) is what the recogniser transcribed, logged so the teacher
    can see the child's actual error rather than only its score.
    """
    return db.update_mastery(student_id, concept_id, correct_bool, raw_score, heard)


def get_student_progress(student_id, language=DEFAULT_LANGUAGE):
    """
    Full progress view for ONE track: every concept in `language`, enriched with
    the student's mastery. Concepts never attempted appear with score 0 /
    attempts 0. Sorted by (difficulty, concept_id) so it reads as a curriculum.

    Pass language=None for every concept across both tracks — the teacher
    dashboard's whole-class exports want that; a learner's own progress never
    does, because "12 of 273" would count a curriculum they are not studying.
    """
    G = load_graph(language)
    rows = {r["concept_id"]: r for r in db.get_mastery_rows(student_id)}

    progress = []
    for cid in G.nodes:
        node = G.nodes[cid]
        r = rows.get(cid)
        score = r["mastery_score"] if r else 0.0
        attempts = r["attempts"] if r else 0
        mastered = score >= db.MASTERY_THRESHOLD
        progress.append(
            {
                "concept_id": cid,
                "language": node.get("language", KANNADA),
                "word": node.get("display_word") or node["kannada_word"],
                "kannada_word": node["kannada_word"],
                "tulu_word": node["tulu_word"],
                "transliteration": node["transliteration"],
                "english_meaning": node["english_meaning"],
                "category": node["category"],
                "difficulty": node["difficulty"],
                "level": node.get("level", "Basic"),
                "mastery_score": round(score, 4),
                "attempts": attempts,
                "mastered": mastered,
                "parked": (not mastered) and attempts >= PARK_AFTER_ATTEMPTS,
                "last_seen": r["last_seen"] if r else None,
            }
        )
    progress.sort(key=lambda p: (p["difficulty"], p["concept_id"]))
    return progress


def mastery_summary(student_id, language=DEFAULT_LANGUAGE):
    """Return (mastered_count, total_count) for one track's progress display."""
    progress = get_student_progress(student_id, language)
    mastered = sum(1 for p in progress if p["mastered"])
    return mastered, len(progress)


def mastery_by_level(student_id, language=DEFAULT_LANGUAGE):
    """
    Per-tier progress for one track: {level: (mastered, total)} in
    Basic -> Intermediate -> Advanced -> Sentences order. Lets the UI show the
    leveled progression explicitly rather than as one flat bar.

    Tiers with no concepts on this track are dropped — the Tulu track has no
    alphabet and no sentences, and an empty "Basic 0/0" line would read as a
    child who has learned no letters rather than a tier that does not exist.
    """
    progress = get_student_progress(student_id, language)
    out = {lv: [0, 0] for lv in LEVELS}
    for p in progress:
        lv = p.get("level") or "Basic"
        out.setdefault(lv, [0, 0])
        out[lv][1] += 1
        if p["mastered"]:
            out[lv][0] += 1
    return {lv: (m, t) for lv, (m, t) in out.items() if t}


def available_languages():
    """
    The language codes that actually have concepts in the dataset, in the order
    LANGUAGES declares them.

    Read from the data rather than hard-coded, so a deployment that ships a CSV
    with only one track shows one door instead of offering an empty curriculum.
    """
    G = load_graph()
    present = {d.get("language", KANNADA) for _, d in G.nodes(data=True)}
    codes = [c for c in LANGUAGES if c in present]
    return codes or [DEFAULT_LANGUAGE]


def normalize_language(code):
    """Coerce anything (None, a stale session value, a dropped track) to a code
    the dataset actually has."""
    available = available_languages()
    return code if code in available else available[0]


def letters_in_order(language=KANNADA):
    """
    The alphabet as a teacher would write it out: vowels first, then consonants,
    each in curriculum order.

    This is what the teacher dashboard's varnamale chart is drawn from. It is a
    list, not a graph, because that is what the thing on screen actually is — a
    chart of letters, in the order children learn them.
    """
    G = load_graph(language)
    out = {}
    for cat in ("vowels", "consonants"):
        nodes = [d for _, d in G.nodes(data=True) if d["category"] == cat]
        nodes.sort(key=lambda d: d["concept_id"])
        if nodes:
            out[cat] = nodes
    return out


def concepts_by_category(language=KANNADA, exclude_letters=True):
    """
    Concepts grouped by topic ({category: [node dicts]}), in the order they are
    taught. The teacher dashboard shows words this way because "animals 3/18" is
    a fact a teacher can act on; a node in a network diagram is not.
    """
    G = load_graph(language)
    out = {}
    for _, d in G.nodes(data=True):
        if exclude_letters and d["category"] in ("vowels", "consonants"):
            continue
        out.setdefault(d["category"], []).append(d)
    for nodes in out.values():
        nodes.sort(key=lambda d: (d["difficulty"], d["concept_id"]))
    return dict(sorted(out.items(),
                       key=lambda kv: (min(d["difficulty"] for d in kv[1]), kv[0])))
