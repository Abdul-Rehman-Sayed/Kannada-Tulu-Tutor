import datetime

from . import db
from . import graph_engine
from . import pronunciation

STRUGGLE_ATTEMPTS = 2

IDLE_DAYS = 7

LEARNED = "cell-ok"
TRYING = "cell-try"
STUCK = "cell-stuck"
NOT_SCORED = "cell-mute"
NOT_STARTED = ""

CHART_LEGEND = [
    (LEARNED, "Learned it"),
    (TRYING, "Practising"),
    (STUCK, "Stuck — needs you"),
    (NOT_SCORED, "The app can't hear this one — you judge it"),
    ("", "Not started yet"),
]


def state(row):
    if row["mastered"]:
        return LEARNED
    if row["attempts"] >= STRUGGLE_ATTEMPTS:
        return STUCK
    if row["attempts"] > 0:
        return TRYING
    return NOT_STARTED


def _days_since(iso_ts):
    if not iso_ts:
        return None
    try:
        stamp = datetime.datetime.fromisoformat(iso_ts)
    except (ValueError, TypeError):
        return None
    return max(0, (datetime.datetime.now() - stamp).days)


def _finding(text, do=False):
    return {"text": text, "do": do}


def alphabet_chart(student_id, language=graph_engine.KANNADA):
    rows = {r["concept_id"]: r for r in
            graph_engine.get_student_progress(student_id, language)}
    chart = {}
    for cat, nodes in graph_engine.letters_in_order(language).items():
        cells = []
        for node in nodes:
            row = rows.get(node["concept_id"])
            if not row:
                continue
            cell_state = state(row)
            tries = row["attempts"]
            if not pronunciation.is_scoreable(node):
                if cell_state != LEARNED:
                    cell_state = NOT_SCORED
                status = "the app cannot hear this letter on its own — " \
                         "listen to this one yourself"
            elif cell_state == LEARNED:
                status = "learned"
            elif cell_state == STUCK:
                status = f"stuck after {tries} tries"
            elif cell_state == TRYING:
                status = f"{tries} try" + ("" if tries == 1 else "s")
            else:
                status = "not started"
            cells.append({
                "glyph": graph_engine.shown_word(node),
                "script": "tu" if graph_engine.in_tulu_lipi(node) else "kn",
                "roman": node["transliteration"],
                "state": cell_state,
                "title": f"{graph_engine.shown_word(node)} "
                         f"({node['kannada_word']}, {node['transliteration']}) — "
                         f"{status}.",
            })
        if cells:
            chart[cat] = cells
    return chart


def topic_rows(student_id, language=graph_engine.KANNADA):
    progress = graph_engine.get_student_progress(student_id, language)
    by_cat = {}
    for row in progress:
        if row["category"] in ("vowels", "consonants"):
            continue
        done, total = by_cat.get(row["category"], (0, 0))
        by_cat[row["category"]] = (done + (1 if row["mastered"] else 0), total + 1)

    rows = [(cat.replace("_", " ").capitalize(), done, total, f"{done} of {total}")
            for cat, (done, total) in by_cat.items()]
    rows.sort(key=lambda r: (r[1] == 0, r[1] / r[2] if r[2] else 0, r[0]))
    return rows


def _tier_sentence(name, by_level):
    tiers = [(lv, m, t) for lv, (m, t) in by_level.items() if t]
    if not tiers:
        return None

    shown = []
    for lv, done, total in tiers:
        shown.append((lv, done, total))
        if done < total:
            break

    parts = [f"{done} of {total} "
             f"{graph_engine.LEVEL_MEANING.get(lv, lv).lower()}"
             for lv, done, total in shown]
    if len(parts) > 1:
        body = ", ".join(parts[:-1]) + " and " + parts[-1]
    else:
        body = parts[0]

    remaining = len(tiers) - len(shown)
    tail = (f" There {'is' if remaining == 1 else 'are'} {remaining} more "
            f"{'stage' if remaining == 1 else 'stages'} after that."
            if remaining else "")
    return f"{name} has learned {body}.{tail}"


def student_findings(student_id, language=graph_engine.KANNADA, name="This child"):
    progress = graph_engine.get_student_progress(student_id, language)
    if not progress:
        return [_finding(f"{name} is not studying this language.")]

    by_level = graph_engine.mastery_by_level(student_id, language)
    attempted = [row for row in progress if row["attempts"] > 0]
    out = []

    if not attempted:
        out.append(_finding(f"{name} has not practised anything yet."))
        nxt = graph_engine.get_next_concept(student_id, language)
        if nxt:
            out.append(_finding(
                f"Their first lesson will be <b class='kn'>{graph_engine.shown_word(nxt)}</b> "
                f"({nxt['transliteration']}).", do=True))
        return out

    sentence = _tier_sentence(name, by_level)
    if sentence:
        out.append(_finding(sentence))

    stuck = [row for row in progress
             if not row["mastered"] and row["attempts"] >= STRUGGLE_ATTEMPTS]
    stuck.sort(key=lambda row: (-row["attempts"], row["concept_id"]))
    if stuck:
        worst = stuck[0]
        info = graph_engine.concept_info(worst["concept_id"]) or {}
        as_in = ""
        anchor = (info.get("anchor_word") or "").strip()
        if anchor:
            as_in = f" (as in <span class='kn'>{anchor}</span>)"
        elif worst["english_meaning"]:
            as_in = f" (‘{worst['english_meaning']}’)"
        out.append(_finding(
            f"{name} has tried <b class='kn'>{worst['word']}</b>"
            f"{as_in} {worst['attempts']} times and still not got it."))
        if len(stuck) > 1:
            others = ", ".join(f"<span class='kn'>{row['word']}</span>"
                               for row in stuck[1:6])
            more = f" and {len(stuck) - 6} more" if len(stuck) > 6 else ""
            out.append(_finding(
                f"{len(stuck)} things are giving them trouble: {others}{more}."))
        out.append(_finding(
            f"Sit with {name} on <b class='kn'>{worst['word']}</b> — say it "
            f"together a few times, then let them try the microphone again.",
            do=True))

    parked = [row for row in progress if row["parked"]]
    if parked:
        words = ", ".join(f"<span class='kn'>{row['word']}</span>"
                          for row in parked[:5])
        more = f" and {len(parked) - 5} more" if len(parked) > 5 else ""
        out.append(_finding(
            f"The tutor moved {name} past {len(parked)} thing(s) they could not "
            f"get — {words}{more}. These are not counted as learned, and they are "
            f"the ones to teach by hand."))

    log = db.get_attempts(student_id)
    log = [a for a in log
           if (graph_engine.concept_info(a["concept_id"]) or {}).get(
               "language", graph_engine.KANNADA) == language]
    if len(log) >= 4:
        window = max(3, min(5, len(log) // 2))
        recent = sum(a["score"] for a in log[:window]) / window
        earliest = sum(a["score"] for a in log[-window:]) / window
        delta = recent - earliest
        if delta >= 0.08:
            out.append(_finding(
                f"{name} is getting clearer — their pronunciation has improved "
                f"over their last {window} tries."))
        elif delta <= -0.08:
            out.append(_finding(
                f"{name}'s pronunciation has slipped over their last {window} "
                f"tries. Worth listening to them in person."))

    nxt = graph_engine.get_next_concept(student_id, language)
    if nxt is None:
        out.append(_finding(f"{name} has finished this whole curriculum."))
    else:
        out.append(_finding(
            f"Next lesson: <b class='kn'>{graph_engine.shown_word(nxt)}</b> "
            f"({nxt['transliteration']} — {nxt['english_meaning']})."))

    last = max((row["last_seen"] for row in attempted if row["last_seen"]),
               default=None)
    idle = _days_since(last)
    if idle is None:
        pass
    elif idle == 0:
        out.append(_finding(f"{name} practised today."))
    elif idle >= IDLE_DAYS:
        out.append(_finding(
            f"{name} has not practised for {idle} days.", do=True))
    else:
        out.append(_finding(
            f"{name} last practised {idle} day" + ("" if idle == 1 else "s")
            + " ago."))
    return out


def class_findings(rows):
    out = []
    if not rows:
        return [_finding("No children have signed up yet.")]

    total = len(rows)
    never = [r for r in rows if r["Attempts"] == 0]
    idle = [r for r in rows
            if r["Idle (days)"] is not None and r["Idle (days)"] >= IDLE_DAYS]
    needs = sorted((r for r in rows if r["Needs help"] > 0),
                   key=lambda r: -r["Needs help"])

    if never:
        names = ", ".join(r["Student"] for r in never[:5])
        more = f" and {len(never) - 5} more" if len(never) > 5 else ""
        out.append(_finding(
            f"{len(never)} of {total} children have not started at all: "
            f"{names}{more}.", do=True))
    if idle:
        names = ", ".join(r["Student"] for r in idle[:5])
        more = f" and {len(idle) - 5} more" if len(idle) > 5 else ""
        out.append(_finding(
            f"{len(idle)} child(ren) have not practised in over a week: "
            f"{names}{more}.", do=True))
    if needs:
        worst = needs[0]
        out.append(_finding(
            f"<b>{worst['Student']}</b> is stuck on {worst['Needs help']} things "
            f"— the most in the class. Start there."
            if worst["Needs help"] > 1 else
            f"<b>{worst['Student']}</b> is stuck on one thing.", do=True))

    ahead = max(rows, key=lambda r: r["Learned"])
    if ahead["Learned"] > 0:
        out.append(_finding(
            f"<b>{ahead['Student']}</b> is furthest along, with "
            f"{ahead['Learned']} of {ahead['Concepts']} learned."))

    hard = hardest_for_class()
    if hard:
        words = ", ".join(f"<span class='kn'>{h['word']}</span>" for h in hard[:3])
        out.append(_finding(
            f"The class as a whole finds {words} hardest. When several children "
            f"miss the same thing it is usually the lesson, not the child — worth "
            f"teaching to the whole room.", do=True))

    if not out:
        out.append(_finding("Nothing needs your attention today."))
    return out


def hardest_for_class(min_students=2, min_tries=3):
    out = []
    for stat in db.get_concept_stats():
        tries = stat["tries"] or 0
        if stat["students"] < min_students or tries < min_tries:
            continue
        info = graph_engine.concept_info(stat["concept_id"])
        if not info:
            continue
        rate = (stat["correct"] or 0) / tries
        if rate >= 0.6:
            continue
        out.append({
            "concept_id": stat["concept_id"],
            "word": graph_engine.shown_word(info),
            "roman": info["transliteration"],
            "meaning": info["english_meaning"],
            "language": info.get("language", graph_engine.KANNADA),
            "students": stat["students"],
            "tries": tries,
            "rate": rate,
        })
    out.sort(key=lambda h: (h["rate"], -h["tries"]))
    return out
