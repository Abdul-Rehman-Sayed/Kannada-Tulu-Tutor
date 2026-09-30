"""The two pictures a card draws for itself: counting beads and colour swatches.

Every other card shows a real photograph, chosen by hand (see
scripts/fetch_images.py), or no picture at all.  Numbers and colours are the
exceptions because the thing itself can be drawn exactly: seven beads are
seven, and a red swatch is red, where a photograph of seven mangoes or of a
red car would teach mango, or car.

    svg = illustrations.render("count:7")   # ೭ over seven counting beads
    svg = illustrations.render("red")       # a red swatch
"""
import html

W, H = 200, 150

INK = "#2E2A21"

RED = "#D2564B"
ORANGE = "#E4873F"
YELLOW = "#EFC04A"
GOLD = "#D9A227"
GREEN = "#5C9A57"
BLUE = "#4E86BE"
PLUM = "#8B6DA4"
WHITE = "#FFFFFF"
COAL = "#3B3730"

GROUNDS = {
    "numbers": "#EFF2EA",
    "plain": "#F2F0E9",
}


def _svg(body, ground="plain"):
    fill = GROUNDS.get(ground, GROUNDS["plain"])
    return (
        f'<svg class="ill" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
        f'role="img" preserveAspectRatio="xMidYMid meet">'
        f'<rect width="{W}" height="{H}" rx="10" fill="{fill}"/>'
        f'<g stroke="{INK}" stroke-width="3" stroke-linejoin="round" '
        f'stroke-linecap="round">{body}</g></svg>'
    )


def _c(cx, cy, r, fill):
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"/>'


def _e(cx, cy, rx, ry, fill, extra=""):
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}"{extra}/>'


def _r(x, y, w, h, fill, rx=0):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"/>'


def _p(d, fill="none", extra=""):
    return f'<path d="{d}" fill="{fill}"{extra}/>'


def _text(s, x=100, y=92, size=54, fill=INK, weight="700"):
    return (f'<text x="{x}" y="{y}" text-anchor="middle" font-size="{size}" '
            f"font-family=\"'Noto Sans Kannada','Nirmala UI',sans-serif\" "
            f'font-weight="{weight}" fill="{fill}" stroke="none">'
            f"{html.escape(s)}</text>")


_COLOURS = {}
for _name, _hex in [("red", RED), ("green", GREEN), ("yellow", YELLOW),
                    ("blue", BLUE), ("black", COAL), ("white", WHITE)]:
    _COLOURS[_name] = (
        _r(34, 26, 132, 98, _hex, 12)
        + _p("M34 92 h132", extra=' stroke-width="2" opacity=".28"')
        + _e(62, 50, 18, 11, WHITE, ' opacity=".22" stroke="none"')
    )

_BEAD_COLOURS = [RED, BLUE, GREEN, ORANGE, PLUM, GOLD]

_KN_DIGITS = "೦೧೨೩೪೫೬೭೮೯"


def numeral(n):
    """`n` in Kannada digits: 24 -> ೨೪.

    The Tulu track uses the same digits.  It is written in the Kannada script,
    and Unicode has no Tulu digits of its own (none in Tulu-Tigalari, as of
    Unicode 18), so a Tulu card pairs these with the Tulu number word.
    """
    return "".join(_KN_DIGITS[int(d)] for d in str(int(n)))


def _counting(n):
    """N counting beads under the number, laid out like a number chart.

    Up to 10 they are big enough to count one by one.  Past that they are
    grouped in rows of ten, so the shape of the number is what you read - which
    is exactly how a wall chart teaches twenty-four.
    """
    n = max(1, min(50, int(n)))
    body = [_text(numeral(n), 100, 44, 40, INK, "600")]

    if n <= 10:
        per_row = 5 if n > 5 else n
        rows = [min(per_row, n - i * per_row) for i in range((n - 1) // per_row + 1)]
        r = 15
        y0 = 84 if len(rows) > 1 else 92
        for ri, count in enumerate(rows):
            y = y0 + ri * 34
            span = (count - 1) * 34
            x0 = 100 - span / 2
            for i in range(count):
                body.append(_c(round(x0 + i * 34), y, r,
                                _BEAD_COLOURS[(ri * per_row + i) % len(_BEAD_COLOURS)]))
        return "".join(body)

    full, rest = divmod(n, 10)
    rows = [10] * full + ([rest] if rest else [])
    r, step = 6.5, 15
    gap = 20 if len(rows) <= 3 else 16
    y0 = 92 - (len(rows) - 1) * gap / 2
    x0 = 100 - 9 * step / 2
    for ri, count in enumerate(rows):
        y = round(y0 + ri * gap)
        for i in range(count):
            body.append(_c(round(x0 + i * step), y, r,
                            _BEAD_COLOURS[ri % len(_BEAD_COLOURS)]))
    return "".join(body)


def _clean(name):
    return (name or "").strip().lower()


def resolve(name):
    """The drawing key for `name` ("count:7", "red"), or None if it has none."""
    name = _clean(name)
    if name.startswith("count:"):
        try:
            n = int(name.split(":", 1)[1])
        except ValueError:
            return None
        return f"count:{n}" if 1 <= n <= 50 else None
    return name if name in _COLOURS else None


def has(name):
    """Does a card with this icon draw its own picture?"""
    return resolve(name) is not None


def render(name):
    """SVG markup for a counting card or a colour swatch; "" for anything else."""
    key = resolve(name)
    if key is None:
        return ""
    if key.startswith("count:"):
        return _svg(_counting(int(key.split(":", 1)[1])), "numbers")
    return _svg(_COLOURS[key], "plain")
