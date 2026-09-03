import networkx as nx

from tutor import graph_engine, insight

_PITCH_MIN = 13
_PITCH_MAX = 56
_TARGET_WIDTH = 760
_ROW_H = 46
_PAD = 16
_GUTTER = 26
_R_MAX = 6.0
_R_RATIO = 0.36
_SWEEPS = 4

_PAINT = {
    insight.LEARNED: ("#F1F6F1", "#1B5E20"),
    insight.TRYING: ("#FAF6EA", "#7A5A16"),
    insight.STUCK: ("#FBF2F0", "#8E2C1E"),
    insight.NOT_STARTED: ("#FFFFFF", "#CFC9BB"),
}

LEGEND = insight.CHART_LEGEND


def _order_layers(G, layers):
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
