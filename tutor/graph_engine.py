import os
from collections import deque

import pandas as pd
import networkx as nx

from . import db

VOCAB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "vocabulary.csv")
LETTER_WORDS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "letter_words.csv")

_GRAPH = None
_SUBGRAPHS = {}
_LETTER_WORDS = None
_LETTER_RANKS = {}

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
        "blurb": "The full syllabus: the alphabet first, then words, counting, "
                 "phrases and whole sentences.",
        "asr": "kn",
    },
    TULU: {
        "code": TULU,
        "name": "Tulu",
        "native": "ತುಳು",
        "blurb": "Tulu is written in the Kannada script, so it starts with the "
                 "same alphabet — then words, counting and phrases.",
        "asr": "kn",
    },
}

DEFAULT_LANGUAGE = KANNADA


def language_info(code):
    return LANGUAGES.get(code) or LANGUAGES[DEFAULT_LANGUAGE]


def language_name(code):
    return language_info(code)["name"]


def display_word(concept):
    if (concept.get("language") or KANNADA) == TULU:
        return (concept.get("tulu_word") or concept.get("kannada_word") or "").strip()
    return (concept.get("kannada_word") or "").strip()


LETTERS_LEVEL = "Basic"
WORDS_LEVEL = "Intermediate"
NUMBERS_LEVEL = "Numbers"

LEVELS = [LETTERS_LEVEL, WORDS_LEVEL, NUMBERS_LEVEL, "Advanced", "Sentences"]

LEVEL_MEANING = {
    LETTERS_LEVEL: "Letters of the alphabet",
    WORDS_LEVEL: "Whole words",
    NUMBERS_LEVEL: "Numbers",
    "Advanced": "Two-word phrases",
    "Sentences": "Complete sentences",
}

STAGES = [
    {
        "level": LETTERS_LEVEL,
        "number": 1,
        "title": "Letters",
        "one_line": "Single letters, one at a time",
        "blurb": "The alphabet on its own — the shape of each letter and the "
                 "sound it makes. No words yet: they come once every letter "
                 "is done.",
        "unit": "letter",
    },
    {
        "level": WORDS_LEVEL,
        "number": 2,
        "title": "Words",
        "one_line": "Whole words, one letter's family at a time",
        "blurb": "Now the letters make words. The words are taught letter by "
                 "letter, in alphabet order, and the whole family of words "
                 "that grows out of the letter sits beside the card.",
        "unit": "word",
    },
    {
        "level": NUMBERS_LEVEL,
        "number": 3,
        "title": "Numbers",
        "one_line": "Counting, one to fifty",
        "blurb": "Counting from one to fifty, in order.",
        "unit": "number",
    },
    {
        "level": "Advanced",
        "number": 4,
        "title": "Phrases",
        "one_line": "Two words joined together",
        "blurb": "Two words at a time, so the words you know start to work "
                 "together.",
        "unit": "phrase",
    },
    {
        "level": "Sentences",
        "number": 5,
        "title": "Sentences",
        "one_line": "Complete sentences",
        "blurb": "Whole sentences, spoken end to end.",
        "unit": "sentence",
    },
]

STAGE_BY_LEVEL = {s["level"]: s for s in STAGES}

_STAGE_RANK = {s["level"]: i for i, s in enumerate(STAGES)}


def stage_rank(level):
    """Teaching order of a stage. Unknown levels sort last, never first."""
    return _STAGE_RANK.get(level, len(STAGES))


def stage_of(concept):
    """The stage a concept belongs to, as a dict from STAGES."""
    level = (concept or {}).get("level") or "Basic"
    return STAGE_BY_LEVEL.get(level, STAGES[0])


def load_graph(language=None, force_reload=False):
    if language is not None:
        if force_reload:
            _SUBGRAPHS.clear()
            _LETTER_RANKS.clear()
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
    _LETTER_RANKS.clear()

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
        row_language = row["language"].strip() or KANNADA
        G.add_node(
            cid,
            concept_id=cid,
            language=row_language,
            kannada_word=kannada_word,
            tulu_word=tulu_word,
            display_word=display_word(
                {"language": row_language, "kannada_word": kannada_word,
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
            icon=(row["icon"].strip() if "icon" in df.columns else ""),
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
    G = load_graph()
    return dict(G.nodes[concept_id]) if concept_id in G else None


PARK_AFTER_ATTEMPTS = 6


def _progression_sets(student_id, G):
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


def letter_ranks(language=DEFAULT_LANGUAGE):
    """Every concept -> the alphabet position of the letter it grew out of.

    The alphabet itself comes first, in its own order; everything else takes
    the position of the letter it sits behind, so the words of one letter stay
    together instead of being scattered across the stage by topic.  Anything
    with no letter behind it sorts after the whole alphabet.
    """
    cached = _LETTER_RANKS.get(language)
    if cached is not None:
        return cached

    G = load_graph(language)

    index, rank = {}, 0
    for cat in ("vowels", "consonants"):
        for cid in sorted(n for n, d in G.nodes(data=True)
                          if d["category"] == cat):
            index[cid] = rank
            rank += 1
    unplaced = rank

    def resolve(cid, walking):
        if cid in index:
            return index[cid]
        if cid in walking:
            return unplaced
        walking.add(cid)
        value = min((resolve(p, walking) for p in G.predecessors(cid)),
                    default=unplaced)
        walking.discard(cid)
        index[cid] = value
        return value

    for cid in G.nodes:
        resolve(cid, set())

    _LETTER_RANKS[language] = index
    return index


def _teaching_order(node, ranks):
    """Where a concept sits in the syllabus, as a sort key.

    Stage first: the prerequisite graph alone would let a word through as soon
    as its own letter was cleared, which is how a child ended up being asked to
    read kamala with most of the alphabet still unlearned.  Sorting by stage
    holds the whole of the letters back until every letter is cleared.

    Then, in the word stage only, the letter the word grew out of - so a child
    meets all of ka's words together and the panel beside the card stays put
    while they do.  Counting keeps its own order, which is numeric and has
    nothing to do with the alphabet.
    """
    cid = node["concept_id"]
    level = node.get("level")
    group = ranks.get(cid, 0) if level == WORDS_LEVEL else 0
    return (stage_rank(level), group, node["difficulty"], cid)


def get_next_concept(student_id, language=DEFAULT_LANGUAGE):
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

    ranks = letter_ranks(language)
    candidates.sort(key=lambda n: _teaching_order(G.nodes[n], ranks))
    return dict(G.nodes[candidates[0]])


def update_mastery(student_id, concept_id, correct_bool, raw_score=None, heard=None):
    return db.update_mastery(student_id, concept_id, correct_bool, raw_score, heard)


def get_student_progress(student_id, language=DEFAULT_LANGUAGE):
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
    progress = get_student_progress(student_id, language)
    mastered = sum(1 for p in progress if p["mastered"])
    return mastered, len(progress)


def mastery_by_level(student_id, language=DEFAULT_LANGUAGE):
    progress = get_student_progress(student_id, language)
    out = {lv: [0, 0] for lv in LEVELS}
    for p in progress:
        lv = p.get("level") or "Basic"
        out.setdefault(lv, [0, 0])
        out[lv][1] += 1
        if p["mastered"]:
            out[lv][0] += 1
    return {lv: (m, t) for lv, (m, t) in out.items() if t}


def stage_progress(student_id, language=DEFAULT_LANGUAGE):
    """The four stages, in order, with where this learner has got to.

    `mastered` counts only what the learner said correctly; `cleared` also
    counts the concepts they were moved past after too many tries, because
    that is what actually opens the next stage.  A stage with nothing in it
    for this language is left out entirely - Tulu has no sentences stage.
    """
    progress = get_student_progress(student_id, language)

    tally = {}
    for p in progress:
        lv = p.get("level") or "Basic"
        t = tally.setdefault(lv, {"mastered": 0, "cleared": 0, "total": 0})
        t["total"] += 1
        if p["mastered"]:
            t["mastered"] += 1
        if p["mastered"] or p["parked"]:
            t["cleared"] += 1

    out = []
    earlier_open = False
    for stage in STAGES:
        t = tally.get(stage["level"])
        if not t:
            continue
        done = t["cleared"] >= t["total"]
        if done:
            state = "done"
        elif earlier_open:
            state = "locked"
        else:
            state = "current"
            earlier_open = True
        out.append({**stage,
                    "mastered": t["mastered"],
                    "cleared": t["cleared"],
                    "total": t["total"],
                    "state": state})

    if out and all(s["state"] == "done" for s in out):
        out[-1] = {**out[-1], "state": "current"}

    for i, stage in enumerate(out):
        stage["position"] = i + 1
        stage["of"] = len(out)
    return out


def current_stage(student_id, language=DEFAULT_LANGUAGE):
    """The stage the learner is working through right now, or None."""
    for stage in stage_progress(student_id, language):
        if stage["state"] == "current":
            return stage
    return None


def letter_of(concept_id, language=DEFAULT_LANGUAGE):
    """The letter a word grew out of, by walking back up its prerequisites.

    Every word in the syllabus sits behind the letter it begins with, so a
    word card can always point back at the letter that opened it.
    """
    G = load_graph(language)
    if concept_id not in G:
        return None

    seen = set()
    node = concept_id
    while node is not None and node not in seen:
        seen.add(node)
        parents = list(G.predecessors(node))
        if not parents:
            return None
        parent = parents[0]
        if G.nodes[parent]["category"] in ("vowels", "consonants"):
            return dict(G.nodes[parent])
        node = parent
    return None


def available_languages():
    G = load_graph()
    present = {d.get("language", KANNADA) for _, d in G.nodes(data=True)}
    codes = [c for c in LANGUAGES if c in present]
    return codes or [DEFAULT_LANGUAGE]


def normalize_language(code):
    available = available_languages()
    return code if code in available else available[0]


def letters_in_order(language=KANNADA):
    G = load_graph(language)
    out = {}
    for cat in ("vowels", "consonants"):
        nodes = [d for _, d in G.nodes(data=True) if d["category"] == cat]
        nodes.sort(key=lambda d: d["concept_id"])
        if nodes:
            out[cat] = nodes
    return out


def load_letter_words(force_reload=False):
    """(language, letter concept_id) -> extra reading words for that letter.

    A wall chart never shows one word per letter; it shows a column of them, so
    that a child meets ka in kamala and kannu and kage and hears the same sound
    open all three.  These are the words beyond the syllabus itself - reading
    practice, never asked for out loud.
    """
    global _LETTER_WORDS
    if _LETTER_WORDS is not None and not force_reload:
        return _LETTER_WORDS

    words = {}
    if os.path.exists(LETTER_WORDS_PATH):
        df = pd.read_csv(LETTER_WORDS_PATH, dtype=str, encoding="utf-8",
                         keep_default_na=False)
        for _, row in df.iterrows():
            lid = row["letter_id"].strip()
            word = row["word"].strip()
            if not lid or not word:
                continue
            lang = (row["language"].strip() if "language" in df.columns
                    else "") or KANNADA
            words.setdefault((lang, lid), []).append({
                "letter_id": lid,
                "language": lang,
                "letter": row["letter"].strip(),
                "letter_translit": row["letter_translit"].strip(),
                "word": word,
                "transliteration": row["word_translit"].strip(),
                "english_meaning": row["english_meaning"].strip(),
                "icon": row["icon"].strip(),
                "concept_id": "",
                "in_syllabus": False,
            })

    _LETTER_WORDS = words
    return _LETTER_WORDS


def syllabus_words_for_letter(letter_id, language=DEFAULT_LANGUAGE):
    """The words of the word stage that grow out of one letter, in order.

    Every word now sits directly behind the letter it begins with, so this is
    simply that letter's children - the words a child will actually be asked
    to say while they are working through this letter.
    """
    G = load_graph(language)
    if letter_id not in G:
        return []

    kids = [dict(G.nodes[n]) for n in G.successors(letter_id)
            if G.nodes[n].get("level") == WORDS_LEVEL]
    kids.sort(key=lambda d: (d["difficulty"], d["concept_id"]))
    return [{
        "letter_id": letter_id,
        "language": d.get("language", language),
        "letter": G.nodes[letter_id]["kannada_word"],
        "letter_translit": G.nodes[letter_id]["transliteration"],
        "word": d.get("display_word") or d["kannada_word"],
        "transliteration": d["transliteration"],
        "english_meaning": d["english_meaning"],
        "icon": d.get("icon", ""),
        "concept_id": d["concept_id"],
        "in_syllabus": True,
    } for d in kids]


def words_for_letter(letter_id, language=DEFAULT_LANGUAGE, limit=None):
    """One letter's whole family of words, syllabus words first.

    The words the child is going to be asked for come first, in the order they
    will be asked; the extra reading words follow, so the column shows the
    sound doing its work in more places than the syllabus has room for.
    """
    rows = syllabus_words_for_letter(letter_id, language)
    seen = {r["word"].strip() for r in rows}

    extra = [r for r in load_letter_words().get((language, letter_id), [])
             if r["word"].strip() not in seen]

    concept = concept_info(letter_id) or {}
    anchor = concept.get("anchor_word", "").strip()
    if anchor:
        extra.sort(key=lambda r: r["word"].strip() != anchor)

    rows += extra
    return rows[:limit] if limit else rows


def is_letter(concept):
    return (concept or {}).get("category") in ("vowels", "consonants")


def listen_form(concept):
    """The text to synthesise when a child taps Listen.

    A letter is one sound, and one sound synthesised on its own comes back as
    a fifth of a second of audio - too short for a child to catch, and short
    enough that the recogniser hears a word in it that was never there.  So a
    letter is played twice, the way a teacher says it: "a, a".  What the child
    is then asked to say is still the letter, once (see `accepted_forms`).
    """
    spoken = (concept or {}).get("spoken_form", "").strip()
    if is_letter(concept) and spoken:
        return f"{spoken} {spoken}"
    return spoken


def concepts_by_category(language=KANNADA, exclude_letters=True):
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
