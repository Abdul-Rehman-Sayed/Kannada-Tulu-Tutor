"""
cogmap.py — the cognitive knowledge graph, drawn.

WHY THIS EXISTS, AND WHY IT IS NOT THE MAIN VIEW. The teacher dashboard answers
"how is this child doing?" with the alphabet chart and the findings in
insight.py, because those name the letter a child is stuck on and a diagram of
unlabelled dots cannot. That decision stands and nothing here changes it.

What a diagram *can* show, and the chart cannot, is the shape of the curriculum:
that the vowels are one long chain, that every consonant hangs off the last
vowel, that the words fan out of the consonants. It is a picture of the
prerequisite structure the tutor walks when it chooses the next concept — the
knowledge graph itself, with one child's progress painted onto it. That is a
structural view for someone asking how the tutor decides, not a daily view for a
teacher asking who needs help, so it lives at the bottom of the page behind an
expander.

The layout is the standard layered one for a DAG:

  * rows are `networkx.topological_generations` — every concept sits below all of
    its prerequisites, so depth down the page is depth through the curriculum;
  * order within a row is set by a few barycentre sweeps, the ordering step from
    Sugiyama's method: each node drifts towards the average position of its
    prerequisites, which is what stops the edges between two wide rows from
    turning into a solid smear;
  * pitch adapts to the widest row, so the 85-wide Kannada word tier and the
    11-wide Tulu one both come out at a sensible size.

Every node carries a `title`, so hovering a dot names the letter or word it
stands for. That is the one thing the old diagram could not do, and it is the
reason this one is worth keeping.

Geometry only — no Streamlit, no HTML. `layout()` returns plain numbers and the
caller draws them.
"""

import networkx as nx

from tutor import graph_engine, insight

# Layout constants, all in SVG user units (= CSS px at scale 1).
_PITCH_MIN = 13          # tightest spacing between node centres in a row
_PITCH_MAX = 56          # widest, so a narrow track does not draw four huge dots
_TARGET_WIDTH = 760      # the pitch aims to fill roughly this much, then clamps
_ROW_H = 46              # vertical distance between rows
_PAD = 16                # margin around the drawing
_GUTTER = 26             # left strip holding the row numbers
_R_MAX = 6.0             # node radius cap
_R_RATIO = 0.36          # radius as a fraction of pitch, below the cap
_SWEEPS = 4              # barycentre ordering passes

#: The four progress states, as fill/stroke pairs. Same colours as the alphabet
#: chart — a red dot here and a red cell there mean the same thing.
_PAINT = {
    insight.LEARNED: ("#F1F6F1", "#1B5E20"),
    insight.TRYING: ("#FAF6EA", "#7A5A16"),
    insight.STUCK: ("#FBF2F0", "#8E2C1E"),
    insight.NOT_STARTED: ("#FFFFFF", "#CFC9BB"),
}

LEGEND = insight.CHART_LEGEND


def _order_layers(G, layers):
    """
    Order each row so edges cross as little as possible.

    Starts from curriculum order — (difficulty, concept_id), the same order the
    tables use — then sweeps down the layers repeatedly, sorting each row by the
    mean position of its prerequisites in the row above. Positions are
    normalised to 0..1 so the comparison holds between rows of different widths,
    and a node whose prerequisites are not in the row directly above keeps its
    current place. `sorted` is stable, so ties never churn.
    """
    order = [sorted(layer, key=lambda c: (G.nodes[c]["difficulty"], c))
             for layer in layers]

    for _ in range(_SWEEPS):
        for i in range(1, len(order)):
            above = {c: (j + 0.5) / len(order[i - 1])
                     for j, c in enumerate(order[i - 1])}
            here = {c: (j + 0.5) / len(order[i]) for j, c in enumerate(order[i])}

            def barycentre(cid, _above=above, _here=here):
                parents = [_above[p] for p in G.predecessors(cid) if p in _above]
                return sum(parents) / len(parents) if parents else _here[cid]

            order[i] = sorted(order[i], key=barycentre)

    return order


def _title(row):
    """The hover line for one node: what the concept is, and how the child is on it."""
    state = insight.state(row)
    if state == insight.LEARNED:
        status = "learned"
    elif state == insight.STUCK:
        status = f"stuck after {row['attempts']} tries"
    elif state == insight.TRYING:
        tries = row["attempts"]
        status = f"{tries} try" if tries == 1 else f"{tries} tries"
    else:
        status = "not started"

    roman = row["transliteration"]
    meaning = row["english_meaning"]
    head = f"{row['word']} ({roman})" if roman else row["word"]
    return f"{head} — {meaning}. {status.capitalize()}."


def layout(student_id, language=graph_engine.KANNADA):
    """
    Position the whole curriculum graph for one child.

    Returns ``{"width", "height", "nodes", "edges", "rows"}`` where each node is
    ``{"x", "y", "r", "fill", "stroke", "title"}`` and each edge is
    ``{"x1", "y1", "x2", "y2"}``; `rows` is ``[{"y", "n"}, …]`` for the row
    numbers down the left. Returns None when the track has no concepts, which is
    the caller's cue to draw nothing at all.
    """
    G = graph_engine.load_graph(language)
    if G.number_of_nodes() == 0:
        return None

    rows = {r["concept_id"]: r
            for r in graph_engine.get_student_progress(student_id, language)}

    layers = _order_layers(G, list(nx.topological_generations(G)))
    widest = max(len(layer) for layer in layers)

    pitch = min(_PITCH_MAX, max(_PITCH_MIN, _TARGET_WIDTH / widest))
    radius = min(_R_MAX, pitch * _R_RATIO)
    left = _PAD + _GUTTER

    # A row narrower than the widest is centred against it, so the drawing reads
    # as one shape rather than everything jammed against the left edge.
    span = (widest - 1) * pitch
    pos = {}
    for depth, layer in enumerate(layers):
        row_span = (len(layer) - 1) * pitch
        x0 = left + (span - row_span) / 2
        y = _PAD + depth * _ROW_H
        for i, cid in enumerate(layer):
            pos[cid] = (x0 + i * pitch, y)

    nodes = []
    for cid, (x, y) in pos.items():
        row = rows.get(cid)
        if row is None:
            continue
        fill, stroke = _PAINT[insight.state(row)]
        nodes.append({"x": round(x, 1), "y": round(y, 1), "r": round(radius, 1),
                      "fill": fill, "stroke": stroke, "title": _title(row)})

    edges = []
    for parent, child in G.edges:
        if parent not in pos or child not in pos:
            continue
        x1, y1 = pos[parent]
        x2, y2 = pos[child]
        edges.append({"x1": round(x1, 1), "y1": round(y1 + radius, 1),
                      "x2": round(x2, 1), "y2": round(y2 - radius, 1)})

    return {
        "width": round(left + span + _PAD, 1),
        "height": round(_PAD * 2 + (len(layers) - 1) * _ROW_H, 1),
        "nodes": nodes,
        "edges": edges,
        "rows": [{"y": _PAD + d * _ROW_H, "n": d + 1} for d in range(len(layers))],
    }
