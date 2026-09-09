"""Flat picture-book drawings for the flashcards.

The old cards pulled photographs off Wikimedia Commons.  A photograph of a
cherry orchard is a poor way to teach a five-year-old that ga is for gida, and
some of what came back was worse than poor - the bell for gha arrived as a
labelled engineering diagram on a black ground.

So the cards draw themselves instead.  Every picture here is flat vector art in
the shape of the wall charts children actually learn from: one object, bold
outline, bright fill, nothing else in the frame.  They are SVG, so they cost a
couple of kilobytes, stay sharp at any size and need no network.

    svg = illustrations.render("cow")          # one drawing
    svg = illustrations.render("count:7")      # seven counting beads
    svg = illustrations.render("?", label="ಅ")  # typographic fallback

`has(name)` reports whether a real drawing exists, so callers can fall back to
the photograph library for anything not drawn yet.
"""
import html

W, H = 200, 150

INK = "#2E2A21"

RED = "#D2564B"
ORANGE = "#E4873F"
YELLOW = "#EFC04A"
GOLD = "#D9A227"
GREEN = "#5C9A57"
LEAF = "#7CAF5A"
MINT = "#A8CE96"
BLUE = "#4E86BE"
SKY = "#93C2E4"
DEEP = "#33608C"
BROWN = "#9A6B43"
BARK = "#6E4A2E"
SAND = "#D9BE8E"
GREY = "#9AA1A8"
SLATE = "#5E656D"
PINK = "#E2A0A6"
PLUM = "#8B6DA4"
CREAM = "#F5E9D2"
WHITE = "#FFFFFF"
COAL = "#3B3730"
SKIN = "#DFA97A"
SKIN_D = "#BE8550"

GROUNDS = {
    "animals": "#F3EEE1",
    "nature": "#EAF1F4",
    "food": "#F6EDE2",
    "body": "#F4EDEE",
    "home": "#F1EFE6",
    "school": "#EDF0F3",
    "people": "#F5EEE8",
    "numbers": "#EFF2EA",
    "courtesy": "#F4F0F6",
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


def _poly(points, fill):
    return f'<polygon points="{points}" fill="{fill}"/>'


def _line(x1, y1, x2, y2):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>'


def _dot(cx, cy, r=3, fill=INK):
    """An eye or a seed - drawn without the heavy outline."""
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="none"/>'


def _text(s, x=100, y=92, size=54, fill=INK, weight="700", family="serif"):
    fam = ("'Noto Sans Kannada','Nirmala UI',sans-serif" if family == "kn"
           else "Georgia,'Times New Roman',serif")
    return (f'<text x="{x}" y="{y}" text-anchor="middle" font-size="{size}" '
            f'font-family="{fam}" font-weight="{weight}" fill="{fill}" '
            f'stroke="none">{html.escape(s)}</text>')


def _legs(xs, y0, y1, ):
    return "".join(_line(x, y0, x, y1) for x in xs)


_A = {}

_LEG_TOP, _LEG_BOT, _LEG_W = 92, 128, 14


def _leg(x, fill, top=_LEG_TOP, bottom=_LEG_BOT, w=_LEG_W):
    return _r(x - w / 2, top, w, bottom - top, fill, w / 2)


def _legs4(xs, fill, **kw):
    return "".join(_leg(x, fill, **kw) for x in xs)


def _tail(d, fill, width=8):
    return (_p(d, "none", f' stroke-width="{width}" stroke="{fill}"')
            + _p(d, "none", ' stroke-width="2.5"'))


_A["cow"] = (
    _legs4((80, 102, 128, 148), WHITE)
    + _e(108, 72, 44, 27, WHITE)
    + _tail("M150 62 q22 8 14 34", WHITE, 7)
    + _e(56, 62, 25, 22, WHITE)
    + _p("M36 44 q-8 -16 4 -20 q10 6 6 20 Z", CREAM)
    + _p("M76 44 q8 -16 -4 -20 q-10 6 -6 20 Z", CREAM)
    + _e(32, 68, 12, 9, WHITE)
    + _e(56, 74, 13, 10, PINK)
    + _dot(48, 56, 3) + _dot(66, 56, 3)
    + _dot(51, 74, 2.2) + _dot(61, 74, 2.2)
    + _c(124, 64, 13, COAL) + _c(96, 82, 9, COAL)
)


_A["dog"] = (
    _legs4((80, 102, 128, 146), SAND)
    + _e(108, 76, 42, 25, SAND)
    + _tail("M148 64 q20 -12 14 -28", SAND, 7)
    + _c(58, 68, 24, SAND)
    + _p("M34 56 q-8 -26 8 -24 q8 12 6 26 Z", BROWN)
    + _p("M82 56 q8 -26 -8 -24 q-8 12 -6 26 Z", BROWN)
    + _e(58, 80, 13, 10, CREAM)
    + _c(58, 74, 6, COAL)
    + _dot(48, 62, 3) + _dot(68, 62, 3)
    + _p("M58 80 v6", extra=' stroke-width="2"')
)

_A["cat"] = (
    _legs4((84, 104, 126, 144), GREY)
    + _e(108, 78, 40, 24, GREY)
    + _tail("M146 68 q26 -6 18 -34", GREY, 7)
    + _c(58, 66, 24, GREY)
    + _poly("38,50 40,26 60,44", GREY) + _poly("78,50 76,26 56,44", GREY)
    + _poly("43,47 45,33 56,44", PINK) + _poly("73,47 71,33 60,44", PINK)
    + _e(50, 62, 5, 7, GREEN) + _e(66, 62, 5, 7, GREEN)
    + _dot(50, 62, 2.4) + _dot(66, 62, 2.4)
    + _c(58, 74, 4, PINK)
    + _p("M58 78 q-5 5 -10 3 M58 78 q5 5 10 3", extra=' stroke-width="2"')
    + _p("M36 72 h-16 M36 78 h-16 M80 72 h16 M80 78 h16",
         extra=' stroke-width="2"')
)

_A["elephant"] = (
    _legs4((80, 106, 132, 154), GREY, top=84, w=20)
    + _e(112, 66, 46, 34, GREY)
    + _c(58, 62, 30, GREY)
    + _e(32, 56, 22, 26, "#8A9199")
    + _p("M52 88 q-12 26 4 38 q14 8 18 -8", "none",
         f' stroke-width="14" stroke="{GREY}" stroke-linecap="round"')
    + _p("M52 88 q-12 26 4 38 q14 8 18 -8", "none", ' stroke-width="2.5"')
    + _dot(66, 54, 3.4)
    + _p("M76 76 q10 -6 18 0", "none", ' stroke-width="4" stroke="#F5E9D2"')
    + _tail("M156 56 q16 8 10 26", GREY, 5)
)


_A["sheep"] = (
    _legs4((84, 104, 126, 144), COAL, w=11)
    + _c(112, 70, 30, WHITE) + _c(86, 62, 22, WHITE) + _c(136, 62, 22, WHITE)
    + _c(104, 48, 20, WHITE) + _c(130, 46, 17, WHITE)
    + _c(64, 74, 21, COAL)
    + _e(40, 68, 12, 8, COAL) + _e(88, 68, 12, 8, COAL)
    + _c(60, 50, 17, WHITE)
    + _dot(56, 72, 3, WHITE) + _dot(72, 72, 3, WHITE)
    + _e(58, 84, 8, 6, "#5A554D")
)


_A["deer"] = (
    _legs4((84, 104, 128, 148), SAND, w=11)
    + _e(112, 78, 40, 24, SAND)
    + _p("M70 90 q-8 -40 8 -50 q20 6 14 30 Z", SAND)
    + _c(72, 34, 18, SAND)
    + _p("M62 20 q-8 -18 -22 -16 M62 20 q-2 -14 -14 -18 "
         "M84 20 q8 -18 22 -16 M84 20 q2 -14 14 -18", "none",
         f' stroke-width="4" stroke="{BROWN}"')
    + _e(50, 36, 10, 7, SAND) + _e(94, 36, 10, 7, SAND)
    + _dot(64, 32, 3) + _dot(80, 32, 3)
    + _e(72, 44, 8, 6, COAL)
    + _dot(104, 68, 4, WHITE) + _dot(122, 78, 4, WHITE)
    + _dot(136, 66, 4, WHITE)
)


_A["tiger"] = (
    _legs4((80, 102, 128, 148), ORANGE)
    + _e(108, 74, 44, 26, ORANGE)
    + _tail("M150 62 q24 6 16 34", ORANGE, 8)
    + _c(58, 66, 26, ORANGE)
    + _c(40, 46, 9, ORANGE) + _c(76, 46, 9, ORANGE)
    + _e(58, 76, 15, 11, CREAM)
    + _dot(49, 60, 3.2) + _dot(67, 60, 3.2)
    + _c(58, 70, 5, COAL)
    + _p("M58 76 q-6 6 -12 4 M58 76 q6 6 12 4", extra=' stroke-width="2"')
    + _p("M92 58 v20 M112 56 v22 M132 58 v20", "none",
         f' stroke-width="5" stroke="{COAL}"')
    + _p("M46 50 l4 10 M70 50 l-4 10", extra=' stroke-width="3"')
)


_A["monkey"] = (
    _legs4((92, 116), BROWN, top=96, w=13)
    + _e(112, 84, 32, 26, BROWN)
    + _tail("M140 86 q30 4 20 -30", BROWN, 6)
    + _c(70, 60, 26, BROWN)
    + _c(46, 56, 11, SAND) + _c(94, 56, 11, SAND)
    + _e(70, 68, 18, 15, SAND)
    + _dot(62, 56, 3.2) + _dot(78, 56, 3.2)
    + _dot(66, 66, 2.2) + _dot(74, 66, 2.2)
    + _p("M62 76 q8 7 16 0", extra=' stroke-width="2.5"')
    + _p("M88 92 q18 4 20 18", "none", f' stroke-width="11" stroke="{BROWN}"')
)

_A["mouse"] = (
    _e(106, 88, 36, 24, GREY)
    + _tail("M140 96 q28 8 20 28", GREY, 5)
    + _c(72, 78, 20, GREY)
    + _c(58, 56, 14, PINK) + _c(90, 54, 13, PINK)
    + _c(58, 56, 8, "#EFC6CB") + _c(90, 54, 7, "#EFC6CB")
    + _dot(64, 76, 3) + _dot(80, 76, 3)
    + _c(56, 86, 4, PINK)
    + _p("M54 88 h-18 M54 94 h-18", extra=' stroke-width="2"')
    + _legs4((94, 118), GREY, top=104, bottom=118, w=9)
)

_A["rabbit"] = (
    _e(108, 92, 34, 24, WHITE)
    + _c(150, 88, 13, WHITE)
    + _c(74, 78, 22, WHITE)
    + _e(60, 42, 9, 26, WHITE) + _e(88, 40, 9, 26, WHITE)
    + _e(60, 42, 4, 17, PINK) + _e(88, 40, 4, 17, PINK)
    + _dot(66, 76, 3.2) + _dot(82, 76, 3.2)
    + _c(74, 86, 4, PINK)
    + _p("M74 90 q-5 5 -10 3 M74 90 q5 5 10 3", extra=' stroke-width="2"')
    + _legs4((96, 120), WHITE, top=108, bottom=124, w=12)
)

_A["squirrel"] = (
    _p("M124 112 q46 -10 26 -60 q-10 -22 -26 -8 q20 22 6 50 Z", SAND)
    + _e(96, 94, 28, 24, BROWN)
    + _c(76, 62, 20, BROWN)
    + _poly("64,46 66,28 80,44", BROWN)
    + _poly("88,46 86,28 74,44", BROWN)
    + _dot(70, 60, 3) + _dot(84, 60, 3)
    + _c(77, 70, 3.5, COAL)
    + _e(96, 108, 12, 9, CREAM)
    + _legs4((88, 110), BROWN, top=108, bottom=124, w=11)
)

_A["bird"] = (
    _e(104, 84, 32, 24, SKY)
    + _c(76, 64, 18, SKY)
    + _poly("58,64 36,70 58,76", ORANGE)
    + _dot(72, 60, 3.2)
    + _p("M100 76 q20 -16 34 2 q-18 12 -34 -2 Z", DEEP)
    + _poly("132,90 164,78 136,102", SKY)
    + _p("M92 106 v14 M112 106 v14", "none",
         ' stroke-width="4" stroke="#E4873F"')
)

_A["crow"] = (
    _e(104, 84, 32, 24, COAL)
    + _c(76, 64, 18, COAL)
    + _poly("58,62 32,70 58,78", GREY)
    + _dot(72, 60, 3, WHITE)
    + _p("M98 76 q20 -14 32 2 q-16 12 -32 -2 Z", "#4A453D")
    + _poly("132,90 166,80 136,102", COAL)
    + _p("M92 106 v14 M112 106 v14", "none",
         ' stroke-width="4" stroke="#9AA1A8"')
)

_A["parrot"] = (
    _e(106, 86, 30, 26, GREEN)
    + _c(80, 60, 20, GREEN)
    + _p("M62 54 q-18 4 -12 18 q12 8 16 -8 Z", RED)
    + _dot(76, 54, 3.2, WHITE)
    + _c(76, 54, 5, COAL)
    + _p("M102 80 q18 -14 28 4 q-16 10 -28 -4 Z", MINT)
    + _poly("130,100 164,118 132,114", YELLOW)
    + _p("M96 110 v12 M114 110 v12", "none",
         ' stroke-width="4" stroke="#9AA1A8"')
)

_A["hen"] = (
    _e(104, 92, 34, 26, CREAM)
    + _c(78, 62, 20, CREAM)
    + _p("M68 42 q-6 -12 6 -12 q2 -10 12 -2 q12 -2 8 14 Z", RED)
    + _poly("58,62 34,68 58,74", GOLD)
    + _p("M76 78 q-4 12 4 14", RED)
    + _dot(74, 58, 3.2)
    + _p("M128 78 q26 -16 24 -32 q-16 12 -24 14 Z", BROWN)
    + _p("M94 116 v14 M114 116 v14", "none",
         ' stroke-width="4" stroke="#EFC04A"')
    + _p("M88 130 h12 M108 130 h12", "none",
         ' stroke-width="3" stroke="#EFC04A"')
)

_A["peacock"] = (
    _p("M100 112 q-62 -8 -56 -54 q6 -38 56 -38 q50 0 56 38 q6 46 -56 54 Z",
      "#2E6E7E")
    + "".join(_c(x, y, 9, GREEN) + _c(x, y, 4, DEEP)
              for x, y in [(58, 62), (78, 40), (100, 32), (122, 40), (142, 62),
                           (62, 90), (138, 90)])
    + _e(100, 96, 17, 26, BLUE)
    + _c(100, 66, 15, BLUE)
    + _p("M100 48 v-12", extra=' stroke-width="2.5"')
    + _c(100, 32, 5, GOLD)
    + _dot(94, 63, 3, WHITE) + _dot(106, 63, 3, WHITE)
    + _dot(94, 63, 1.6) + _dot(106, 63, 1.6)
    + _poly("100,72 88,80 100,84", GOLD)
    + _p("M92 122 v10 M108 122 v10", "none",
         ' stroke-width="4" stroke="#EFC04A"')
)

_A["fish"] = (
    _e(92, 76, 42, 27, ORANGE)
    + _poly("132,76 170,50 170,102", ORANGE)
    + _p("M82 50 q14 -14 28 -2", GOLD)
    + _p("M80 102 q14 12 26 0", GOLD)
    + _c(62, 68, 6, WHITE) + _c(62, 68, 3.4, COAL)
    + _p("M52 82 q10 8 20 2", extra=' stroke-width="2.5"')
    + _c(110, 72, 7, GOLD) + _c(98, 88, 6, GOLD) + _c(122, 88, 5, GOLD)
)

_A["crab"] = (
    _e(100, 88, 38, 26, RED)
    + _c(88, 78, 5, WHITE) + _c(112, 78, 5, WHITE)
    + _dot(88, 78, 2.6) + _dot(112, 78, 2.6)
    + _p("M88 100 q12 8 24 0", extra=' stroke-width="2.5"')
    + _p("M74 70 q-18 -14 -30 -2 M126 70 q18 -14 30 -2", extra=' stroke-width="5"')
    + _p("M44 68 q-14 -10 -18 2 q12 12 20 2 Z", RED)
    + _p("M156 68 q14 -10 18 2 q-12 12 -20 2 Z", RED)
    + _p("M72 106 l-18 16 M84 112 l-10 18 M128 106 l18 16 M116 112 l10 18",
        extra=' stroke-width="4"')
)

_A["butterfly"] = (
    _p("M96 76 q-42 -36 -52 -6 q-8 28 52 20 Z", ORANGE)
    + _p("M104 76 q42 -36 52 -6 q8 28 -52 20 Z", ORANGE)
    + _p("M96 80 q-34 22 -30 36 q10 12 30 -18 Z", YELLOW)
    + _p("M104 80 q34 22 30 36 q-10 12 -30 -18 Z", YELLOW)
    + _c(62, 62, 8, GOLD) + _c(138, 62, 8, GOLD)
    + _e(100, 86, 7, 28, COAL)
    + _c(100, 52, 9, COAL)
    + _p("M96 44 q-8 -18 -18 -20 M104 44 q8 -18 18 -20", extra=' stroke-width="2.5"')
    + _dot(96, 50, 2, WHITE) + _dot(104, 50, 2, WHITE)
)

_A["ant"] = (
    _c(70, 82, 14, COAL) + _e(98, 86, 13, 11, COAL) + _e(132, 88, 22, 17, COAL)
    + _p("M60 70 q-10 -18 -20 -20 M68 68 q0 -20 -8 -26", extra=' stroke-width="3"')
    + _p("M90 74 l-10 -20 M104 76 l8 -20 M92 98 l-12 20 M112 98 l10 20",
        extra=' stroke-width="3"')
    + _dot(64, 78, 3, WHITE)
)

_A["bee"] = (
    _e(104, 88, 32, 24, GOLD)
    + _p("M94 66 v44 M114 66 v44", "none", f' stroke-width="6" stroke="{COAL}"')
    + _c(68, 82, 15, COAL)
    + _dot(63, 78, 3, WHITE)
    + _p("M58 66 q-8 -16 2 -20 M62 64 q-6 -14 4 -18", extra=' stroke-width="2.5"')
    + _p("M96 64 q-16 -30 10 -28 q24 2 6 28 Z", WHITE, ' opacity=".85"')
    + _poly("136,92 152,98 136,102", COAL)
)

_A["snake"] = (
    _p("M36 110 q32 -30 60 -8 q28 22 56 -14", "none",
      f' stroke-width="18" stroke="{GREEN}" stroke-linecap="round"')
    + _p("M36 110 q32 -30 60 -8 q28 22 56 -14", "none", ' stroke-width="3"')
    + _c(152, 82, 15, GREEN)
    + _dot(156, 76, 3, WHITE) + _dot(156, 76, 1.6)
    + _p("M166 88 l14 4 M180 92 l-8 -6 M180 92 l-8 8", extra=' stroke-width="2.5"')
    + _c(70, 100, 5, MINT) + _c(112, 96, 5, MINT)
)

_A["tortoise"] = (
    _p("M46 102 a54 42 0 0 1 108 0 Z", GREEN)
    + _p("M74 102 a26 22 0 0 1 52 0", extra=' stroke-width="2.5"')
    + _p("M100 60 v42 M68 84 h64", extra=' stroke-width="2.5"')
    + _e(166, 100, 15, 11, MINT)
    + _dot(170, 96, 2.6)
    + _r(58, 100, 16, 18, MINT, 6) + _r(126, 100, 16, 18, MINT, 6)
)

_A["chameleon"] = (
    _e(96, 84, 34, 22, MINT)
    + _c(64, 72, 18, MINT)
    + _poly("50,58 64,54 70,68", GREEN)
    + _c(60, 70, 6, YELLOW) + _dot(60, 70, 2.6)
    + _p("M46 78 l-12 4", extra=' stroke-width="2.5"')
    + _p("M126 80 q32 6 26 30 q-4 14 -16 6 q12 -20 -14 -22", extra=' stroke-width="4"')
    + _c(88, 78, 5, GREEN) + _c(106, 88, 5, GREEN)
    + _legs4((84, 108), MINT, top=98, bottom=114, w=10)
)

_A["buffalo"] = (
    _legs4((84, 106, 130, 150), SLATE)
    + _e(114, 78, 40, 26, SLATE)
    + _tail("M152 68 q20 12 12 34", SLATE, 7)
    + _p("M78 92 q-14 -30 0 -40 q16 6 16 28 Z", SLATE)
    + _e(60, 62, 24, 19, SLATE)
    + _p("M40 52 q-22 -6 -22 -22 q20 -4 26 16 Z", "#4A505A")
    + _p("M80 52 q22 -6 22 -22 q-20 -4 -26 16 Z", "#4A505A")
    + _e(60, 74, 14, 10, COAL)
    + _dot(51, 60, 3, WHITE) + _dot(69, 60, 3, WHITE)
    + _dot(55, 74, 2.2, "#7C838B") + _dot(65, 74, 2.2, "#7C838B")
)

_A["ox"] = _A["buffalo"]

_A["lion"] = (
    _legs4((92, 112, 134, 152), SAND)
    + _e(120, 80, 36, 24, SAND)
    + _tail("M154 70 q18 12 10 32", SAND, 6) + _c(160, 106, 8, GOLD)
    + "".join(_c(60 + 38 * c, 62 + 38 * s, 13, GOLD)
              for c, s in [(1, 0), (.71, .71), (0, 1), (-.71, .71), (-1, 0),
                           (-.71, -.71), (0, -1), (.71, -.71),
                           (.92, .38), (.38, .92), (-.38, .92), (-.92, .38),
                           (-.92, -.38), (-.38, -.92), (.38, -.92), (.92, -.38)])
    + _c(60, 62, 38, GOLD)
    + _c(60, 62, 26, SAND)
    + _e(52, 58, 5, 6, COAL) + _e(68, 58, 5, 6, COAL)
    + _dot(51, 56, 1.8, WHITE) + _dot(67, 56, 1.8, WHITE)
    + _e(53, 74, 9, 7, "#C9A167") + _e(67, 74, 9, 7, "#C9A167")
    + _poly("60,66 54,71 66,71", COAL)
    + _p("M60 71 v5", extra=' stroke-width="2"')
)

_A["goat"] = (
    _legs4((88, 106, 128, 146), CREAM, w=11)
    + _e(114, 80, 38, 23, CREAM)
    + _tail("M150 70 q12 -10 8 -20", CREAM, 6)
    + _p("M82 94 q-12 -26 0 -34 q14 6 14 24 Z", CREAM)
    + _e(62, 62, 21, 17, CREAM)
    + _p("M48 48 q-10 -24 4 -28 q10 12 6 28 Z", SAND)
    + _p("M76 48 q10 -24 -4 -28 q-10 12 -6 28 Z", SAND)
    + _e(38, 68, 13, 8, CREAM) + _e(86, 68, 13, 8, CREAM)
    + _dot(55, 60, 3) + _dot(69, 60, 3)
    + _e(62, 74, 9, 6, PINK)
    + _p("M62 84 q-3 14 3 17", "none", f' stroke-width="5" stroke="{CREAM}"')
    + _p("M62 84 q-3 14 3 17", extra=' stroke-width="2"')
)

_A["horse"] = (
    _legs4((86, 106, 130, 150), BROWN)
    + _e(114, 80, 42, 25, BROWN)
    + _tail("M154 70 q22 18 10 42", BARK, 10)
    + _p("M76 96 q-16 -42 4 -54 q22 8 16 34 Z", BROWN)
    + _p("M80 46 q10 26 -2 40", "none",
         f' stroke-width="12" stroke="{BARK}" stroke-linecap="round"')
    + _p("M62 40 q-22 4 -22 20 q0 10 12 10 q18 0 26 -14 Z", BROWN)
    + _e(66, 40, 20, 17, BROWN)
    + _p("M56 24 q-4 -14 5 -13 q5 5 1 15 Z", BROWN)
    + _p("M74 24 q4 -14 -5 -13 q-5 5 -1 15 Z", BROWN)
    + _dot(58, 38, 3)
    + _e(42, 62, 8, 6, COAL)
    + _dot(40, 61, 2, "#8A8078")
)

_A["camel"] = (
    _legs4((88, 108, 132, 152), SAND, top=94, bottom=134, w=12)
    + _e(120, 90, 38, 20, SAND)
    + _c(106, 68, 20, SAND) + _c(136, 70, 18, SAND)
    + _tail("M156 84 q12 12 6 26", SAND, 5)
    + _p("M84 100 q-20 -50 -2 -62 q22 6 18 40 Z", SAND)
    + _e(70, 34, 19, 13, SAND, ' transform="rotate(-18 70 34)"')
    + _p("M62 22 q-3 -11 5 -10 q4 4 1 12 Z", SAND)
    + _e(52, 40, 9, 7, "#C9A167")
    + _dot(66, 28, 3)
    + _p("M52 44 q4 4 8 2", extra=' stroke-width="2"')
)

_N = {}

_N["sun"] = (
    _c(100, 76, 32, YELLOW)
    + "".join(_line(100 + 44 * c, 76 + 44 * s, 100 + 60 * c, 76 + 60 * s)
              for c, s in [(1, 0), (.707, .707), (0, 1), (-.707, .707),
                           (-1, 0), (-.707, -.707), (0, -1), (.707, -.707)])
)

_N["moon"] = (
    _p("M124 26 a52 52 0 1 0 0 100 a40 40 0 1 1 0 -100 Z", CREAM)
    + _c(96, 60, 5, "#E3D5B4") + _c(84, 92, 7, "#E3D5B4")
)

_N["night"] = (
    _r(0, 0, W, H, DEEP, 10)
    + _p("M124 34 a44 44 0 1 0 0 84 a34 34 0 1 1 0 -84 Z", CREAM)
    + _poly("44,34 48,48 62,52 48,56 44,70 40,56 26,52 40,48", WHITE)
    + _poly("64,96 67,105 76,108 67,111 64,120 61,111 52,108 61,105", WHITE)
)

_N["star"] = _poly(
    "100,20 118,68 170,68 128,98 144,146 100,116 56,146 72,98 30,68 82,68", YELLOW)

_N["cloud"] = (
    _c(76, 86, 26, WHITE) + _c(108, 74, 32, WHITE) + _c(140, 88, 24, WHITE)
    + _r(72, 88, 72, 24, WHITE, 12)
)

_N["sky"] = (
    _r(0, 0, W, H, SKY, 10)
    + _c(70, 60, 20, WHITE) + _c(96, 52, 25, WHITE) + _c(122, 62, 18, WHITE)
    + _r(68, 60, 56, 18, WHITE, 9)
    + _c(158, 34, 16, YELLOW)
)

_N["rain"] = (
    _c(74, 60, 22, GREY) + _c(104, 50, 28, GREY) + _c(132, 62, 20, GREY)
    + _r(70, 62, 64, 20, GREY, 10)
    + "".join(_p(f"M{x} 96 q-5 12 0 16 q7 -4 0 -16 Z", BLUE)
              for x in (74, 100, 126))
    + "".join(_p(f"M{x} 116 q-5 12 0 16 q7 -4 0 -16 Z", BLUE)
              for x in (88, 114))
)

_N["water"] = (
    _p("M100 20 q42 52 42 74 a42 42 0 0 1 -84 0 q0 -22 42 -74 Z", BLUE)
    + _p("M84 96 q10 12 22 4", extra=' stroke="#BEDCF2" stroke-width="4"')
)

_N["river"] = (
    _r(0, 0, W, H, MINT, 10)
    + _p("M20 132 q26 -40 42 -56 q18 -18 20 -56 h36 q0 40 20 58 q18 16 42 54 Z", BLUE)
    + _p("M76 100 q20 -8 42 0 M70 118 q30 -10 58 0",
        extra=' stroke="#BEDCF2" stroke-width="3"')
)

_N["sea"] = (
    _r(0, 0, W, 62, SKY, 10) + _c(150, 34, 15, YELLOW)
    + _p("M0 62 h200 v88 H0 Z", BLUE)
    + "".join(_p(f"M{x} {y} q10 -9 20 0 q10 9 20 0",
                 extra=' stroke="#BEDCF2" stroke-width="3"')
              for x, y in [(20, 84), (100, 84), (56, 110), (128, 112)])
)

_N["waterfall"] = (
    _r(0, 0, W, H, MINT, 10)
    + _p("M26 20 h48 v70 q0 34 -24 40 q-24 -6 -24 -40 Z", "#8B9299")
    + _r(74, 30, 52, 84, BLUE, 6)
    + _p("M84 44 v62 M100 40 v70 M116 46 v58",
        extra=' stroke="#BEDCF2" stroke-width="3"')
    + _e(100, 122, 46, 14, BLUE)
)

_N["stream"] = (
    _r(0, 0, W, H, MINT, 10)
    + _p("M14 40 q40 24 30 48 q-10 26 34 34 q40 8 108 4", extra=' stroke="#4E86BE" '
      'stroke-width="18" fill="none"')
    + _p("M14 40 q40 24 30 48 q-10 26 34 34 q40 8 108 4", extra=' stroke="#BEDCF2" '
      'stroke-width="4" fill="none"')
    + _c(48, 34, 10, GREY) + _c(150, 118, 12, GREY)
)

_N["well"] = (
    _r(58, 78, 84, 54, GREY, 6)
    + _p("M58 78 h84 M62 96 h76 M62 114 h76", extra=' stroke-width="2.5"')
    + _r(52, 68, 96, 12, BROWN, 4)
    + _line(70, 68, 70, 30) + _line(130, 68, 130, 30)
    + _poly("54,30 100,10 146,30", RED)
    + _r(92, 40, 16, 20, SAND, 3)
)

_N["tree"] = (
    _r(90, 84, 20, 48, BARK, 4)
    + _c(72, 70, 26, GREEN) + _c(128, 70, 26, GREEN) + _c(100, 52, 32, GREEN)
    + _c(100, 82, 26, GREEN)
)

_N["forest"] = (
    _poly("48,110 22,110 48,58 74,110", GREEN) + _r(42, 108, 12, 24, BARK, 3)
    + _poly("100,120 68,120 100,44 132,120", GREEN) + _r(93, 116, 14, 26, BARK, 3)
    + _poly("152,110 126,110 152,58 178,110", GREEN) + _r(146, 108, 12, 24, BARK, 3)
)

_N["plant"] = (
    _p("M100 128 v-46", extra=' stroke-width="5"')
    + _p("M100 96 q-32 -6 -34 -30 q28 -2 34 30 Z", LEAF)
    + _p("M100 88 q32 -6 34 -30 q-28 -2 -34 30 Z", LEAF)
    + _p("M100 66 q-4 -20 -18 -26 q4 20 18 26 Z", GREEN)
    + _p("M62 128 h76", extra=' stroke-width="4"')
)

_N["leaf"] = (
    _p("M46 118 q0 -80 108 -86 q6 84 -108 86 Z", LEAF)
    + _p("M46 118 q56 -20 92 -74", extra=' stroke-width="3"')
    + _p("M78 100 q6 -18 4 -30 M104 84 q4 -18 0 -28", extra=' stroke-width="2"')
)

_N["flower"] = (
    "".join(_e(100 + 34 * c, 72 + 34 * s, 20, 15, PINK,
               f' transform="rotate({a} {100 + 34 * c} {72 + 34 * s})"')
            for a, (c, s) in zip((0, 72, 144, 216, 288),
                                 [(0, -1), (.95, -.31), (.59, .81),
                                  (-.59, .81), (-.95, -.31)]))
    + _c(100, 72, 15, YELLOW)
    + _p("M100 88 v42", extra=' stroke-width="4"')
    + _p("M100 112 q-24 -4 -26 -20 q22 0 26 20 Z", GREEN)
)

_N["rose"] = (
    _c(100, 66, 32, RED)
    + _p("M100 44 a22 22 0 1 1 -0.1 0 M100 54 a12 12 0 1 1 -0.1 0",
        extra=' stroke-width="2.5"')
    + _p("M100 98 v34", extra=' stroke-width="4"')
    + _p("M100 112 q-24 -4 -26 -20 q22 0 26 20 Z", GREEN)
    + _p("M100 120 q22 -2 24 -16 q-20 -2 -24 16 Z", GREEN)
)

_LOTUS_PETAL = "M100 108 q-17 -22 0 -56 q17 34 0 56 Z"

_N["lotus"] = (
    _p("M22 118 h58 M120 118 h58", "none",
      f' stroke-width="5" stroke="{GREEN}"')
    + "".join(_p(_LOTUS_PETAL, "#EFC0C6", f' transform="rotate({a} 100 108)"')
              for a in (-72, -48, 48, 72))
    + "".join(_p(_LOTUS_PETAL, PINK, f' transform="rotate({a} 100 108)"')
              for a in (-24, 0, 24))
    + _e(100, 104, 13, 9, YELLOW)
    + _dot(94, 102, 2, GOLD) + _dot(100, 100, 2, GOLD)
    + _dot(106, 102, 2, GOLD)
    + _p("M14 126 h172", "none", f' stroke-width="5" stroke="{BLUE}"')
)

_N["hill"] = (
    _r(0, 0, W, H, SKY, 10)
    + _p("M0 132 q46 -70 76 -70 q30 0 60 70 Z", GREEN)
    + _p("M74 132 q44 -86 76 -86 q30 0 50 86 Z", "#4D8749")
    + _c(160, 34, 14, YELLOW)
)

_N["mountain"] = (
    _r(0, 0, W, H, SKY, 10)
    + _poly("0,134 58,42 116,134", "#7C838B")
    + _poly("38,72 58,42 78,72 68,66 58,74 48,66", WHITE)
    + _poly("84,134 138,54 192,134", "#5E656D")
    + _poly("120,80 138,54 156,80 146,74 138,82 130,74", WHITE)
)

_N["earth"] = (
    _c(100, 74, 48, BLUE)
    + _p("M62 52 q26 10 22 26 q-4 16 14 18 q18 2 12 22 q-4 12 -16 14", MINT,
        ' stroke-width="2.5"')
    + _p("M118 34 q-8 20 8 24 q18 4 26 -8", MINT, ' stroke-width="2.5"')
    + _c(100, 74, 48, "none")
)

_N["soil"] = (
    _r(0, 0, W, H, SKY, 10)
    + _p("M0 66 h200 v84 H0 Z", BROWN)
    + _p("M0 66 h200", extra=' stroke-width="4"')
    + _c(46, 92, 8, BARK) + _c(128, 108, 9, BARK) + _c(158, 84, 7, BARK)
    + _p("M96 66 v-24 M96 52 q-16 -4 -18 -16 q16 0 18 16 Z", GREEN)
)

_N["stone"] = (
    _p("M40 118 q-8 -34 26 -48 q34 -14 56 4 q24 18 12 44 Z", GREY)
    + _p("M64 108 q6 -20 26 -24", extra=' stroke-width="2.5"')
    + _e(150, 122, 20, 10, "#B4BAC0")
)

_N["fire"] = (
    _p("M100 130 q-42 -8 -38 -46 q2 -22 20 -34 q-2 20 12 22 q14 2 8 -34 "
      "q42 22 36 62 q-4 28 -38 30 Z", ORANGE)
    + _p("M100 130 q-22 -6 -20 -28 q2 -14 16 -22 q-2 14 8 16 q12 2 6 -12 "
      "q18 16 12 32 q-4 14 -22 14 Z", YELLOW)
)

_N["wind"] = (
    _r(0, 0, W, H, SKY, 10)
    + _p("M20 52 h74 a13 13 0 1 0 -13 -13", extra=' stroke-width="5"')
    + _p("M20 82 h104 a15 15 0 1 1 -15 15", extra=' stroke-width="5"')
    + _p("M20 112 h60 a11 11 0 1 0 -11 -11", extra=' stroke-width="5"')
)

_N["dew"] = (
    _p("M22 108 q46 -30 156 -14", extra=' stroke="#7CAF5A" stroke-width="7"')
    + "".join(_c(x, y, 9, "#BEDCF2") for x, y in
              [(52, 92), (86, 84), (120, 82), (152, 88)])
    + "".join(_dot(x - 3, y - 3, 2.4, WHITE) for x, y in
              [(52, 92), (86, 84), (120, 82), (152, 88)])
)

_N["shadow"] = (
    _r(0, 0, W, H, CREAM, 10)
    + _c(150, 34, 16, YELLOW)
    + _c(72, 56, 16, SKIN) + _r(58, 74, 28, 40, BLUE, 6)
    + _e(118, 116, 40, 12, "#B7AE9A")
)

_N["season"] = (
    _r(0, 0, 100, H, SKY, 10) + _r(100, 0, 100, H, CREAM, 10)
    + _c(48, 40, 16, YELLOW)
    + _r(44, 76, 10, 40, BARK, 3) + _c(48, 70, 22, GREEN)
    + _r(146, 76, 10, 40, BARK, 3) + _c(146, 70, 22, ORANGE)
    + _p("M100 8 v134", extra=' stroke-width="2.5"')
)

_N["ice"] = (
    _p("M100 20 v108 M56 46 l88 56 M144 46 l-88 56", extra=' stroke="#7FB6DE" '
      'stroke-width="8"')
    + _p("M100 40 l-12 -12 M100 40 l12 -12 M100 108 l-12 12 M100 108 l12 12",
        extra=' stroke="#7FB6DE" stroke-width="6"')
    + _c(100, 74, 12, WHITE)
)

_N["cold"] = _N["ice"]
_N["dust"] = (
    _r(0, 0, W, H, CREAM, 10)
    + "".join(_c(x, y, r, "#C9BFA6") for x, y, r in
              [(60, 90, 22), (96, 78, 26), (132, 92, 20), (104, 104, 18)])
    + _p("M28 122 h150", extra=' stroke-width="4"')
)

_N["palm"] = (
    _p("M96 132 q-6 -50 4 -70", extra=' stroke-width="9" stroke="#8B6A45"')
    + "".join(_p(f"M100 62 q{dx} {dy} {dx2} {dy2}", GREEN, ' stroke-width="3"')
              for dx, dy, dx2, dy2 in
              [(-30, -16, -56, 4), (30, -16, 56, 4), (-24, -26, -34, -30),
               (24, -26, 34, -30), (-8, -30, 0, -40)])
    + _c(88, 68, 7, BROWN) + _c(112, 70, 7, BROWN)
)

_N["coconut"] = (
    _c(100, 80, 40, BROWN)
    + _c(88, 66, 7, BARK) + _c(112, 66, 7, BARK) + _c(100, 88, 7, BARK)
    + _p("M74 54 q26 -16 52 0", extra=' stroke-width="2.5"')
)

_F = {}

_F["apple"] = (
    _p("M100 44 q34 -14 44 18 q10 34 -18 62 q-16 16 -26 2 q-10 14 -26 -2 "
      "q-28 -28 -18 -62 q10 -32 44 -18 Z", RED)
    + _p("M100 44 v-16 q0 -8 8 -12", extra=' stroke-width="4"')
    + _p("M104 26 q22 -12 30 4 q-20 10 -30 -4 Z", GREEN)
)

_F["mango"] = (
    _p("M92 34 q52 -6 62 42 q10 46 -40 60 q-48 12 -60 -34 q-10 -44 38 -68 Z", GOLD)
    + _p("M92 34 q-6 -12 4 -18", extra=' stroke-width="4"')
    + _p("M74 62 q22 -18 46 -12", extra=' stroke="#EFD9A0" stroke-width="4"')
)

_F["banana"] = (
    _p("M32 62 q6 66 74 64 q66 -2 62 -46 q-2 -12 -14 -6 q-4 32 -48 32 "
      "q-46 0 -50 -46 q-2 -12 -14 -6 Z", YELLOW)
    + _p("M32 62 q-4 -10 4 -12 M156 74 q10 -4 10 6", extra=' stroke-width="2.5"')
)

_F["lemon"] = (
    _e(100, 80, 50, 36, "#E9D24E")
    + _p("M52 66 q48 -16 96 0", extra=' stroke="#F2E58F" stroke-width="4"')
    + _p("M100 122 q-4 8 0 12 M100 38 q-4 -8 0 -12", extra=' stroke-width="3"')
)

_F["orange"] = (
    _c(100, 82, 44, ORANGE)
    + _p("M100 38 v88 M62 60 l76 44 M138 60 l-76 44",
        extra=' stroke="#F0B074" stroke-width="3"')
    + _p("M100 38 q4 -14 -6 -18", extra=' stroke-width="4"')
    + _p("M96 22 q20 -10 26 4 q-18 8 -26 -4 Z", GREEN)
)

_F["grapes"] = (
    "".join(_c(x, y, 13, PLUM) for x, y in
            [(78, 66), (104, 62), (128, 70), (66, 90), (92, 86), (118, 92),
             (80, 112), (106, 112)])
    + _p("M104 48 q2 -16 -10 -20", extra=' stroke-width="4"')
    + _p("M96 26 q22 -12 28 4 q-20 8 -28 -4 Z", GREEN)
)

_F["watermelon"] = (
    _p("M20 108 a80 80 0 0 1 160 0 Z", RED)
    + _p("M20 108 a80 80 0 0 1 160 0", extra=' stroke="#5C9A57" stroke-width="12"')
    + _p("M20 108 h160", extra=' stroke-width="3"')
    + "".join(_e(x, y, 4, 6, COAL) for x, y in
              [(74, 84), (100, 74), (126, 84), (88, 98), (114, 98)])
)

_F["pomegranate"] = (
    _c(100, 84, 44, "#C0463F")
    + _p("M100 40 v-16 M92 26 h16 M96 20 l4 6 l4 -6", extra=' stroke-width="3"')
    + "".join(_c(x, y, 5, "#E4736C") for x, y in
              [(86, 74), (102, 68), (116, 78), (90, 96), (110, 96), (100, 86)])
)

_F["dates"] = (
    "".join(_e(x, y, 13, 20, "#8A5A34", f' transform="rotate({a} {x} {y})"')
            for x, y, a in [(70, 82, -14), (100, 74, 0), (130, 84, 14),
                            (86, 108, -8), (116, 108, 8)])
    + _p("M100 54 q-4 -14 6 -18", extra=' stroke-width="3"')
)

_F["fruit"] = (
    _c(74, 88, 30, RED) + _p("M74 58 v-12", extra=' stroke-width="4"')
    + _e(132, 92, 26, 24, GOLD)
    + _p("M132 68 q-4 -12 4 -16", extra=' stroke-width="3"')
    + _p("M78 46 q20 -10 26 4 q-18 8 -26 -4 Z", GREEN)
)

_F["potato"] = (
    _p("M42 90 q-6 -34 34 -42 q44 -8 66 12 q22 22 2 44 q-22 24 -60 16 "
      "q-36 -8 -42 -30 Z", "#C9A167")
    + _dot(74, 76, 4, "#9C7A46") + _dot(104, 96, 4, "#9C7A46")
    + _dot(126, 74, 3.4, "#9C7A46")
)

_F["vegetable"] = (
    _p("M78 116 q-24 -20 -12 -44 q12 -22 34 -10 q22 -12 34 10 q12 24 -12 44 "
      "q-22 16 -44 0 Z", "#5C9A57")
    + _p("M100 62 v-24", extra=' stroke-width="4"')
    + _e(122, 44, 18, 10, LEAF, ' transform="rotate(-20 122 44)"')
)

_F["brinjal"] = (
    _p("M100 58 q-18 4 -24 30 q-8 28 8 40 q16 10 32 0 q16 -12 8 -40 "
       "q-6 -26 -24 -30 Z", "#7A5595")
    + _p("M84 62 q6 -16 16 -16 q10 0 16 16 q-8 6 -16 6 q-8 0 -16 -6 Z", GREEN)
    + _p("M100 46 v-12", extra=' stroke-width="4"')
)

_F["okra"] = (
    _p("M92 130 q-14 -34 -6 -62 q3 -12 14 -12 q11 0 14 12 q8 28 -6 62 Z", LEAF)
    + _p("M100 122 V64", "none", f' stroke-width="2.5" stroke="{GREEN}"')
    + _p("M88 118 q12 -30 8 -54 M112 118 q-12 -30 -8 -54", "none",
        ' stroke-width="2"')
    + _e(100, 50, 13, 8, GREEN)
    + _p("M100 44 v-10", extra=' stroke-width="4"')
)

_F["tomato"] = (
    _c(100, 86, 42, RED)
    + _p("M100 44 l-16 -12 M100 44 l16 -12 M100 44 l-22 4 M100 44 l22 4",
        extra=' stroke="#5C9A57" stroke-width="5"')
    + _c(100, 44, 7, GREEN)
    + _p("M76 64 q16 -12 30 -8", extra=' stroke="#E4736C" stroke-width="4"')
)

_F["chilli"] = (
    _p("M62 46 q54 -6 70 42 q14 46 -22 58 q-22 6 -22 -22 q0 -34 -26 -50 Z", RED)
    + _p("M62 46 q-12 -8 -6 -18", extra=' stroke-width="4"')
    + _e(58, 30, 16, 8, GREEN, ' transform="rotate(-24 58 30)"')
)

_F["onion"] = (
    _p("M100 130 q-46 0 -46 -40 q0 -34 46 -46 q46 12 46 46 q0 40 -46 40 Z", "#C79BBE")
    + _p("M78 122 q-4 -50 22 -78 M122 122 q4 -50 -22 -78", extra=' stroke-width="2.5"')
    + _p("M100 44 q-8 -20 -20 -26 M100 44 q8 -20 20 -26 M100 44 v-30",
        extra=' stroke="#7CAF5A" stroke-width="3"')
)

_F["maize"] = (
    _e(100, 84, 26, 46, GOLD)
    + "".join(_line(80, y, 120, y) for y in (56, 68, 80, 92, 104))
    + _line(100, 40, 100, 128)
    + _p("M74 92 q-24 -26 -14 -56 q26 12 26 52 Z", GREEN)
    + _p("M126 92 q24 -26 14 -56 q-26 12 -26 52 Z", GREEN)
)

_F["grain"] = (
    _p("M100 132 v-72", extra=' stroke-width="4"')
    + "".join(_e(100 + dx, y, 11, 7, GOLD, f' transform="rotate({a} {100 + dx} {y})"')
              for dx, y, a in [(-16, 56, -30), (16, 56, 30), (-16, 74, -30),
                               (16, 74, 30), (-16, 92, -30), (16, 92, 30),
                               (0, 42, 0)])
)

_F["rice"] = (
    _e(100, 96, 56, 26, WHITE)
    + _p("M44 92 a56 40 0 0 1 112 0", CREAM)
    + _e(100, 118, 62, 14, GREY)
    + _p("M78 66 q10 -12 22 -6 q12 -8 22 4", extra=' stroke="#BEBEBE" stroke-width="3"')
)

_F["meal"] = (
    _c(100, 84, 52, WHITE)
    + _c(100, 84, 40, "none")
    + _c(78, 72, 14, CREAM) + _c(112, 66, 12, GREEN) + _c(124, 94, 13, GOLD)
    + _c(82, 100, 12, ORANGE)
)

_F["plate"] = (
    _e(100, 84, 60, 42, WHITE) + _e(100, 84, 40, 27, "none")
)

_F["pot"] = (
    _p("M52 66 q0 62 48 62 q48 0 48 -62 Z", "#B4643E")
    + _e(100, 66, 48, 12, "#C97C52")
    + _p("M60 78 q40 14 80 0", extra=' stroke-width="2.5"')
)

_F["milk"] = (
    _p("M74 50 h52 l8 78 q-34 8 -68 0 Z", WHITE)
    + _r(80, 34, 40, 16, WHITE, 3)
    + _p("M72 92 q30 8 58 0", extra=' stroke-width="2.5"')
    + _c(100, 108, 10, SKY)
)

_F["curd"] = (
    _p("M56 62 h88 l-8 66 q-36 8 -72 0 Z", WHITE)
    + _e(100, 62, 44, 12, "#EFEFE8")
    + _p("M70 88 q30 10 60 0", extra=' stroke-width="2.5"')
)

_F["ghee"] = (
    _r(64, 56, 72, 72, GOLD, 8)
    + _r(76, 40, 48, 16, "#B4884A", 4)
    + _p("M74 84 q26 10 52 0", extra=' stroke-width="2.5"')
)

_F["honey"] = (
    _p("M64 54 h72 v52 q0 24 -36 24 q-36 0 -36 -24 Z", GOLD)
    + _r(80, 34, 40, 20, "#B4884A", 4)
    + _poly("100,66 112,73 112,87 100,94 88,87 88,73", "#EFD9A0")
)

_F["sugar"] = (
    _p("M56 74 h88 l-10 54 h-68 Z", WHITE)
    + _e(100, 74, 44, 12, "#F2F2EC")
    + "".join(_r(x, y, 12, 12, WHITE, 2) for x, y in [(80, 44), (96, 32), (110, 48)])
)

_F["salt"] = (
    _p("M70 62 q30 -20 60 0 l10 66 q-40 12 -80 0 Z", WHITE)
    + _e(100, 56, 30, 10, GREY)
    + "".join(_dot(x, y, 2.6, GREY) for x, y in
              [(88, 30), (100, 22), (112, 30), (96, 40), (108, 42)])
)

_F["oil"] = (
    _p("M78 52 h44 l10 76 q-32 8 -64 0 Z", GOLD)
    + _r(88, 30, 24, 22, "#B4884A", 3)
    + _p("M78 88 q22 8 44 0", extra=' stroke-width="2.5"')
)

_F["spice"] = (
    _c(66, 96, 26, "#B4562F") + _c(102, 88, 26, GOLD) + _c(138, 98, 24, "#7C5A2E")
    + _e(66, 96, 26, 10, "#C9673E") + _e(102, 88, 26, 10, "#EFD070")
    + _e(138, 98, 24, 9, "#96703C")
)

_F["dosa"] = (
    _p("M30 96 q28 -34 70 -34 q42 0 70 34 q-70 22 -140 0 Z", GOLD)
    + _p("M52 92 q48 -20 96 0", extra=' stroke="#E5C583" stroke-width="3"')
    + _e(100, 108, 74, 12, "#D9B96A")
)

_F["roti"] = (
    _c(100, 84, 50, CREAM)
    + _dot(82, 70, 4, "#C9A167") + _dot(112, 66, 4, "#C9A167")
    + _dot(96, 96, 5, "#C9A167") + _dot(122, 96, 4, "#C9A167")
)

_F["sweet"] = (
    _c(76, 92, 26, GOLD) + _c(124, 92, 26, GOLD) + _c(100, 66, 26, GOLD)
    + _dot(70, 86, 3, "#B4884A") + _dot(128, 88, 3, "#B4884A")
    + _dot(100, 60, 3, "#B4884A")
)

_F["spoon"] = (
    _e(72, 54, 20, 26, GREY)
    + _p("M78 76 q34 30 54 52", extra=' stroke-width="9" stroke="#9AA1A8"')
    + _p("M78 76 q34 30 54 52", extra=' stroke-width="3"')
)

_F["basket"] = (
    _p("M46 76 h108 l-12 52 h-84 Z", BROWN)
    + _p("M62 76 v52 M100 76 v52 M138 76 v52 M52 96 h96 M56 112 h88",
        extra=' stroke-width="2.5"')
    + _p("M62 76 a38 30 0 0 1 76 0", extra=' stroke-width="4"')
)

_F["box"] = (
    _r(52, 66, 96, 62, "#C9A167", 4)
    + _r(46, 52, 108, 18, "#B48C50", 3)
    + _p("M100 70 v58", extra=' stroke-width="2.5"')
    + _r(88, 44, 24, 10, BROWN, 3)
)

def _face(cx=100, cy=72, r=36, skin=SKIN):
    return (_c(cx, cy, r, skin)
            + _dot(cx - 13, cy - 4, 3.4) + _dot(cx + 13, cy - 4, 3.4)
            + _p(f"M{cx - 14} {cy + 14} q14 12 28 0", extra=' stroke-width="3"'))


_B = {}

_B["face"] = (
    _face()
    + _p("M64 46 q36 -30 72 0 q-6 -34 -36 -34 q-30 0 -36 34 Z", COAL)
    + _p("M76 58 q10 -6 20 -2 M124 58 q-10 -6 -20 -2", "none",
        ' stroke-width="3"')
    + _p("M100 68 v12 q-5 4 0 6", "none", ' stroke-width="3"')
)
_B["head"] = (
    _p("M40 132 q6 -30 34 -37 q12 -3 26 -3 q14 0 26 3 q28 7 34 37 Z", BLUE)
    + _r(88, 92, 24, 22, SKIN)
    + _c(100, 62, 34, SKIN)
    + _p("M64 58 q4 -34 36 -34 q32 0 36 34 q-14 -18 -36 -18 q-22 0 -36 18 Z", COAL)
    + _dot(88, 64, 3.4) + _dot(112, 64, 3.4)
    + _p("M88 80 q12 10 24 0", extra=' stroke-width="3"')
    + _e(66, 66, 6, 9, SKIN) + _e(134, 66, 6, 9, SKIN)
)

_B["hair"] = (
    _c(100, 78, 34, SKIN)
    + _p("M62 66 q6 -46 38 -46 q32 0 38 46 q-14 -18 -38 -18 q-24 0 -38 18 Z", COAL)
    + _p("M64 62 q-16 40 -6 68 M136 62 q16 40 6 68", extra=' stroke-width="7" '
      'stroke="#3B3730" fill="none"')
    + _dot(88, 76, 3) + _dot(112, 76, 3)
)

_B["eye"] = (
    _p("M22 76 q40 -44 78 -44 q38 0 78 44 q-40 44 -78 44 q-38 0 -78 -44 Z", WHITE)
    + _c(100, 76, 26, "#6B8FB4")
    + _c(100, 76, 12, COAL)
    + _dot(92, 68, 5, WHITE)
)

_B["ear"] = (
    _p("M118 24 q-52 -6 -58 48 q-4 40 8 58 q10 14 22 2 q10 -12 0 -22 "
      "q-12 -12 4 -22 q22 -14 34 -28 q14 -18 -10 -36 Z", SKIN)
    + _p("M104 52 q-22 4 -22 28 q0 16 8 22", extra=' stroke-width="3"')
    + _p("M96 68 q-10 4 -10 14", extra=' stroke-width="2.5"')
)

_B["nose"] = (
    _p("M100 20 q-6 40 -22 62 q-10 14 4 22 q18 10 36 0 q14 -8 4 -22 "
      "q-16 -22 -22 -62 Z", SKIN)
    + _e(84, 100, 8, 5, SKIN_D) + _e(116, 100, 8, 5, SKIN_D)
)

_B["mouth"] = (
    _p("M30 74 q70 -44 140 0 q-70 52 -140 0 Z", "#C2555A")
    + _p("M30 74 h140", extra=' stroke-width="3"')
    + _p("M52 62 h96 q-6 -12 -48 -12 q-42 0 -48 12 Z", WHITE)
    + _p("M56 86 h88 q-6 10 -44 10 q-38 0 -44 -10 Z", WHITE)
)

_B["tooth"] = (
    _p("M62 34 h76 q10 40 -4 78 q-10 26 -20 2 q-8 -20 -14 -20 q-6 0 -14 20 "
      "q-10 24 -20 -2 q-14 -38 -4 -78 Z", WHITE)
    + _p("M78 52 q22 -8 44 0", extra=' stroke="#DCDCD2" stroke-width="3"')
)

_B["hand"] = (
    _p("M64 128 q-14 -34 -10 -58 q4 -18 14 -4 l4 14 v-56 q0 -14 11 -14 q11 0 11 14 "
      "v44 v-52 q0 -14 11 -14 q11 0 11 14 v52 v-42 q0 -13 10 -13 q10 0 10 13 v44 "
      "v-26 q0 -12 10 -12 q10 0 10 12 v58 q0 32 -20 40 Z", SKIN)
)

_B["finger"] = (
    _p("M84 130 q-10 -30 -6 -54 q4 -18 14 -6 l4 12 v-62 q0 -14 12 -14 q12 0 12 14 "
      "v66 q0 34 -14 44 Z", SKIN)
    + _p("M104 34 q10 -4 16 4", extra=' stroke-width="2.5"')
)

_B["foot"] = (
    _p("M70 22 q34 -8 40 22 q4 22 10 40 q8 22 -6 36 q-20 18 -44 0 "
      "q-16 -14 -10 -40 q6 -30 10 -58 Z", SKIN)
    + "".join(_e(x, 30, 6, 8, SKIN_D) for x in (118, 132, 144, 154))
)

_B["leg"] = (
    _p("M84 20 h32 v56 q0 22 8 34 l10 16 h-56 q-8 -18 -2 -34 q8 -20 8 -38 Z", SKIN)
    + _p("M78 126 h64 q6 8 -4 10 h-56 q-10 -2 -4 -10 Z", "#B4562F")
)

_B["chest"] = (
    _c(100, 40, 22, SKIN)
    + _p("M62 132 q-6 -54 12 -66 q26 -14 52 0 q18 12 12 66 Z", BLUE)
    + _p("M84 66 q16 14 32 0", extra=' stroke-width="2.5"')
)

_B["bone"] = (
    _p("M56 52 a14 14 0 1 1 12 20 l64 36 a14 14 0 1 1 -12 20 a14 14 0 1 1 -12 -20 "
      "l-64 -36 a14 14 0 1 1 12 -20 Z", WHITE)
)

_B["breath"] = (
    _c(76, 84, 30, SKIN)
    + _dot(68, 78, 3) + _p("M66 96 q10 10 20 2", extra=' stroke-width="2.5"')
    + "".join(_c(x, y, r, WHITE) for x, y, r in
              [(120, 74, 10), (140, 64, 13), (162, 52, 8)])
)

_B["person"] = (
    _c(100, 44, 22, SKIN)
    + _p("M100 22 q-24 0 -24 20 q10 -10 24 -10 q14 0 24 10 q0 -20 -24 -20 Z", COAL)
    + _dot(92, 44, 3) + _dot(108, 44, 3)
    + _p("M64 132 q-4 -50 14 -60 q22 -12 44 0 q18 10 14 60 Z", GREEN)
    + _p("M70 82 l-14 24 M130 82 l14 24", extra=' stroke-width="5"')
)

_B["people"] = (
    _c(66, 54, 18, SKIN) + _p("M38 132 q-2 -44 12 -52 q16 -8 32 0 q14 8 12 52 Z", BLUE)
    + _c(134, 54, 18, SKIN)
    + _p("M106 132 q-2 -44 12 -52 q16 -8 32 0 q14 8 12 52 Z", RED)
    + _dot(60, 54, 2.6) + _dot(72, 54, 2.6)
    + _dot(128, 54, 2.6) + _dot(140, 54, 2.6)
)

_B["strong"] = (
    _c(100, 40, 20, SKIN)
    + _p("M70 128 q-4 -40 14 -48 q16 -8 32 0 q18 8 14 48 Z", RED)
    + _p("M76 88 q-22 -6 -22 -26 q0 -14 14 -12 q14 2 12 18", SKIN, ' stroke-width="3"')
    + _p("M124 88 q22 -6 22 -26 q0 -14 -14 -12 q-14 2 -12 18", SKIN, ' stroke-width="3"')
)

_B["smile"] = (
    _c(100, 76, 46, YELLOW)
    + _dot(84, 62, 5) + _dot(116, 62, 5)
    + _p("M72 88 q28 30 56 0", extra=' stroke-width="4"')
)

_B["heart"] = _p(
    "M100 130 q-56 -34 -66 -66 q-8 -28 14 -38 q22 -10 52 20 q30 -30 52 -20 "
    "q22 10 14 38 q-10 32 -66 66 Z", RED)

_B["think"] = (
    _c(80, 96, 28, SKIN)
    + _dot(72, 92, 3) + _p("M70 108 q10 8 20 0", extra=' stroke-width="2.5"')
    + _c(112, 68, 8, WHITE) + _c(128, 52, 12, WHITE) + _c(152, 34, 18, WHITE)
)

_HM = {}

_HM["house"] = (
    _r(50, 74, 100, 58, CREAM, 3)
    + _poly("36,76 100,26 164,76", RED)
    + _r(88, 96, 26, 36, BROWN, 2)
    + _r(60, 88, 20, 18, SKY, 2) + _r(120, 88, 20, 18, SKY, 2)
    + _dot(108, 116, 2.6)
)

_HM["building"] = (
    _r(46, 34, 50, 98, "#C9BFA6", 3) + _r(104, 60, 50, 72, "#B7AE9A", 3)
    + "".join(_r(x, y, 12, 12, SKY, 2) for y in (46, 68, 90)
              for x in (56, 76))
    + "".join(_r(x, y, 12, 12, SKY, 2) for y in (72, 94) for x in (114, 134))
)

_HM["village"] = (
    _r(0, 0, W, H, MINT, 10)
    + _r(28, 84, 46, 40, CREAM, 2) + _poly("18,86 51,58 84,86", RED)
    + _r(110, 78, 56, 46, CREAM, 2) + _poly("98,80 138,48 178,80", ORANGE)
    + _r(44, 100, 14, 24, BROWN, 2) + _r(130, 96, 16, 28, BROWN, 2)
    + _r(88, 96, 10, 28, BARK, 2) + _c(93, 88, 16, GREEN)
)

_HM["hospital"] = (
    _r(46, 46, 108, 86, WHITE, 4)
    + _r(88, 22, 24, 24, RED, 3)
    + _p("M100 26 v16 M92 34 h16", extra=' stroke="#FFFFFF" stroke-width="4"')
    + _r(88, 96, 24, 36, SKY, 2)
    + "".join(_r(x, y, 14, 14, SKY, 2) for y in (60, 82) for x in (58, 128))
)

_HM["school"] = (
    _r(40, 66, 120, 66, CREAM, 3)
    + _poly("30,68 100,24 170,68", DEEP)
    + _r(86, 92, 28, 40, BROWN, 2)
    + _r(54, 84, 20, 18, SKY, 2) + _r(126, 84, 20, 18, SKY, 2)
    + _p("M100 24 v-14", extra=' stroke-width="3"') + _poly("100,10 130,18 100,26", RED)
)

_HM["temple"] = (
    _r(52, 84, 96, 48, CREAM, 2)
    + _poly("44,86 100,22 156,86", ORANGE)
    + _p("M100 22 v-12", extra=' stroke-width="3"') + _c(100, 8, 6, GOLD)
    + _r(88, 100, 24, 32, RED, 2)
    + _p("M64 96 h20 M116 96 h20", extra=' stroke-width="3"')
)

_HM["station"] = (
    _r(38, 56, 124, 76, "#C9BFA6", 3)
    + _r(30, 42, 140, 16, DEEP, 3)
    + _r(84, 92, 32, 40, BROWN, 2)
    + _r(50, 70, 22, 18, SKY, 2) + _r(128, 70, 22, 18, SKY, 2)
    + _c(100, 24, 12, BLUE) + _p("M100 36 v6", extra=' stroke-width="3"')
)

_HM["tent"] = (
    _r(0, 0, W, H, MINT, 10)
    + _poly("28,124 100,30 172,124", ORANGE)
    + _poly("100,30 100,124 72,124", "#C96A2E")
    + _p("M100 30 v-12", extra=' stroke-width="3"')
    + _p("M28 124 h144", extra=' stroke-width="3"')
)

_HM["door"] = (
    _r(58, 28, 84, 104, BROWN, 4)
    + _r(72, 42, 56, 76, "#B48C50", 3)
    + _p("M100 42 v76", extra=' stroke-width="2.5"')
    + _c(90, 82, 5, GOLD) + _c(110, 82, 5, GOLD)
)

_HM["window"] = (
    _r(48, 32, 104, 92, SKY, 4)
    + _p("M100 32 v92 M48 78 h104", extra=' stroke-width="4"')
    + _r(40, 24, 120, 12, BROWN, 3)
    + _c(70, 56, 8, WHITE) + _c(128, 96, 7, WHITE)
)

_HM["wall"] = (
    "".join(_r(x, y, 44, 22, "#C4785A", 2)
            for y in (36, 62, 88, 114)
            for x in ((30, 78, 126) if y in (36, 88) else (54, 102, 150)))
)

_HM["bed"] = (
    _r(30, 82, 140, 32, BROWN, 4)
    + _r(26, 60, 22, 60, BARK, 4) + _r(152, 70, 22, 50, BARK, 4)
    + _r(44, 68, 44, 20, WHITE, 5)
    + _r(38, 84, 126, 16, SKY, 4)
)

_HM["table"] = (
    _r(30, 60, 140, 16, BROWN, 4)
    + _r(44, 76, 12, 56, BARK, 3) + _r(144, 76, 12, 56, BARK, 3)
)

_HM["chair"] = (
    _r(60, 26, 20, 74, BROWN, 4)
    + _r(60, 78, 84, 16, BROWN, 4)
    + _r(66, 94, 12, 38, BARK, 3) + _r(128, 94, 12, 38, BARK, 3)
    + _r(66, 40, 60, 10, "#B48C50", 3)
)

_HM["mat"] = (
    _p("M26 118 l30 -52 h88 l30 52 Z", SAND)
    + _p("M56 66 l-14 52 M86 66 l-8 52 M114 66 l8 52 M144 66 l14 52",
        extra=' stroke-width="2.5"')
    + _p("M46 84 h108 M36 102 h128", extra=' stroke-width="2.5"')
)

_HM["stove"] = (
    _r(38, 74, 124, 46, SLATE, 6)
    + _c(76, 74, 22, "#3B3730") + _c(128, 74, 18, "#3B3730")
    + _p("M76 60 q-12 -14 0 -26 q4 12 12 6 q6 12 -12 20 Z", ORANGE)
    + _c(56, 104, 7, RED) + _c(148, 104, 7, RED)
)

_HM["lamp"] = (
    _p("M46 96 q22 -22 54 -22 q32 0 54 22 q-24 20 -54 20 q-30 0 -54 -20 Z", "#B4884A")
    + _p("M154 96 q10 -34 -12 -44 q10 22 -8 30", ORANGE)
    + _r(76, 116, 48, 12, "#8A6A34", 4)
)

_HM["incense"] = (
    _r(56, 116, 88, 10, BROWN, 3)
    + _p("M88 116 v-56 M112 116 v-62", extra=' stroke-width="4"')
    + _p("M88 60 q-14 -20 2 -34 M112 54 q14 -18 -2 -32",
        extra=' stroke="#B7AE9A" stroke-width="3"')
    + _dot(88, 58, 4, RED) + _dot(112, 52, 4, RED)
)

_HM["clock"] = (
    _c(100, 78, 48, WHITE)
    + _c(100, 78, 40, "none")
    + _p("M100 78 v-26 M100 78 l22 12", extra=' stroke-width="4"')
    + _dot(100, 78, 4)
    + _p("M100 30 v-8 M148 78 h8 M100 126 v8 M52 78 h-8", extra=' stroke-width="3"')
)

_HM["calendar"] = (
    _r(38, 44, 124, 88, WHITE, 5)
    + _r(38, 44, 124, 22, RED, 5)
    + _p("M66 44 v-14 M134 44 v-14", extra=' stroke-width="5"')
    + "".join(_line(x, 74, x, 126) for x in (72, 100, 128))
    + "".join(_line(46, y, 154, y) for y in (86, 106))
)

_HM["ring"] = (
    _c(100, 92, 36, GOLD) + _c(100, 92, 24, GROUNDS["home"])
    + _poly("100,20 114,44 86,44", "#7FB6DE")
    + _p("M86 44 h28", extra=' stroke-width="2.5"')
)

_HM["earring"] = (
    _p("M100 30 a11 11 0 1 1 -0.1 0", "none", ' stroke-width="3"')
    + _c(100, 60, 8, GOLD)
    + _p("M68 98 q0 -32 32 -32 q32 0 32 32 Z", GOLD)
    + _e(100, 98, 32, 7, "#E9C05A")
    + _c(78, 112, 5.5, GOLD) + _c(100, 116, 5.5, GOLD)
    + _c(122, 112, 5.5, GOLD)
)

_HM["bangle"] = (
    _c(100, 78, 46, GREEN) + _c(100, 78, 32, GROUNDS["home"])
    + _c(100, 78, 46, "none")
    + _dot(100, 32, 4, GOLD) + _dot(146, 78, 4, GOLD) + _dot(100, 124, 4, GOLD)
)

_HM["gold"] = (
    _p("M40 118 h120 l-14 -30 h-92 Z", GOLD)
    + _p("M58 88 h84 l-12 -26 h-60 Z", "#E9C05A")
    + _p("M72 62 h56 l-10 -22 h-36 Z", GOLD)
)

_HM["coin"] = (
    _c(76, 92, 32, GOLD) + _c(76, 92, 22, "#E9C05A")
    + _c(124, 74, 32, GOLD) + _c(124, 74, 22, "#E9C05A")
    + _text("₹", 124, 84, 26, INK)
)

_HM["cloth"] = (
    _p("M40 34 q60 20 120 0 v70 q-60 26 -120 0 Z", BLUE)
    + _p("M40 62 q60 22 120 0 M40 84 q60 22 120 0",
        extra=' stroke="#7FB6DE" stroke-width="3"')
)

_HM["shirt"] = (
    _p("M62 40 l24 -10 q14 12 28 0 l24 10 l14 26 l-18 10 v56 h-68 v-56 l-18 -10 Z",
      SKY)
    + _p("M86 30 q14 16 28 0", extra=' stroke-width="2.5"')
    + _dot(100, 70, 3) + _dot(100, 92, 3)
)

_HM["saree"] = (
    _p("M56 132 q-4 -70 20 -96 q24 -26 48 0 q24 26 20 96 Z", "#C2555A")
    + _p("M76 36 q28 40 48 96", extra=' stroke="#EFC04A" stroke-width="5"')
    + _p("M62 106 h76", extra=' stroke="#EFC04A" stroke-width="4"')
)

_HM["towel"] = (
    _r(46, 34, 108, 96, MINT, 5)
    + _p("M46 56 h108 M46 108 h108", extra=' stroke="#5C9A57" stroke-width="4"')
    + _p("M60 34 v96 M140 34 v96", extra=' stroke-width="2"')
)

_HM["wool"] = (
    _c(100, 82, 46, PINK)
    + _p("M60 62 q40 40 80 0 M56 86 q44 34 88 0 M70 44 q30 60 60 0",
        extra=' stroke-width="2.5"')
    + _p("M146 82 q22 8 24 30", extra=' stroke-width="3"')
)

_HM["thread"] = (
    _r(78, 34, 44, 84, CREAM, 3)
    + _e(100, 34, 22, 8, "#B48C50") + _e(100, 118, 22, 8, "#B48C50")
    + _p("M78 50 h44 M78 66 h44 M78 82 h44 M78 98 h44",
        extra=' stroke="#C2555A" stroke-width="3"')
    + _p("M122 76 q28 10 28 34", extra=' stroke="#C2555A" stroke-width="3"')
)

_HM["rope"] = (
    _p("M28 96 q18 -26 36 0 q18 26 36 0 q18 -26 36 0 q18 26 36 0",
      extra=' stroke-width="11" stroke="#C9A167"')
    + _p("M28 96 q18 -26 36 0 q18 26 36 0 q18 -26 36 0 q18 26 36 0",
        extra=' stroke-width="3"')
)

_HM["stick"] = (
    _p("M52 128 q10 -70 44 -96 q22 -16 46 -8", extra=' stroke-width="11" '
      'stroke="#9A6B43"')
    + _p("M52 128 q10 -70 44 -96 q22 -16 46 -8", extra=' stroke-width="3"')
)

_HM["ball"] = (
    _c(100, 80, 46, WHITE)
    + _poly("100,52 122,68 114,94 86,94 78,68", COAL)
    + _p("M100 34 v18 M60 66 l18 2 M140 66 l-18 2 M78 116 l8 -22 M122 116 l-8 -22",
        extra=' stroke-width="3"')
)

_HM["kite"] = (
    _poly("100,20 150,74 100,128 50,74", RED)
    + _p("M100 20 v108 M50 74 h100", extra=' stroke-width="2.5"')
    + _p("M100 128 q14 16 -2 26 q-16 10 0 24", extra=' stroke-width="2.5"')
)

_HM["drum"] = (
    _p("M60 50 h80 l12 68 h-104 Z", BROWN)
    + _e(100, 50, 40, 12, CREAM)
    + _p("M66 70 h68 M62 92 h76", extra=' stroke-width="3"')
    + _p("M150 40 l22 -18 M162 30 a5 5 0 1 0 .1 0", extra=' stroke-width="3"')
)

_HM["damaru"] = (
    _p("M52 30 q48 24 96 0 l-30 46 l30 46 q-48 -24 -96 0 l30 -46 Z", BROWN)
    + _e(100, 34, 48, 10, CREAM) + _e(100, 118, 48, 10, CREAM)
    + _p("M100 76 h34 M134 76 a6 6 0 1 0 .1 0", extra=' stroke-width="2.5"')
)

_HM["bell"] = (
    _p("M100 24 q-40 8 -40 56 q0 22 -12 34 h104 q-12 -12 -12 -34 q0 -48 -40 -56 Z",
      GOLD)
    + _c(100, 20, 8, "#B4884A")
    + _e(100, 122, 12, 10, "#B4884A")
    + _p("M76 92 q24 8 48 0", extra=' stroke-width="2.5"')
)

_HM["conch"] = (
    _p("M60 116 q-16 -40 12 -68 q28 -28 60 -20 q26 8 20 34 q-6 24 -34 26 "
      "q-22 2 -22 20 q0 10 10 12 Z", CREAM)
    + _p("M84 96 q-8 -30 14 -46 q18 -14 34 -6", extra=' stroke-width="2.5"')
)

_HM["om"] = _text("ॐ", 100, 106, 92, ORANGE, "400", "kn")

_HM["yoga"] = (
    _c(100, 40, 18, SKIN)
    + _p("M100 58 v40", extra=' stroke-width="7"')
    + _p("M100 66 l-34 22 M100 66 l34 22", extra=' stroke-width="5"')
    + _p("M100 98 l-38 24 h76 Z", ORANGE)
)

_HM["sage"] = (
    _c(100, 46, 22, SKIN)
    + _p("M78 34 q22 -22 44 0 q0 -22 -22 -22 q-22 0 -22 22 Z", WHITE)
    + _dot(92, 46, 2.8) + _dot(108, 46, 2.8)
    + _p("M84 60 q16 34 32 0", WHITE, ' stroke-width="2.5"')
    + _p("M66 132 q-4 -46 34 -46 q38 0 34 46 Z", ORANGE)
)

_HM["namaskara"] = (
    _p("M64 132 q-2 -46 36 -46 q38 0 36 46 Z", ORANGE)
    + _c(100, 40, 22, SKIN)
    + _p("M78 38 q0 -24 22 -24 q22 0 22 24 q-8 -11 -22 -11 q-14 0 -22 11 Z", COAL)
    + _p("M89 42 q5 5 10 0 M111 42 q-5 5 -10 0", extra=' stroke-width="2.5"')
    + _p("M93 54 q7 5 14 0", extra=' stroke-width="2.5"')
    + _dot(100, 22, 3, RED)
    + _p("M100 118 q-13 -10 -10 -24 q3 -12 10 -10 q7 -2 10 10 q3 14 -10 24 Z", SKIN)
    + _p("M100 84 v34", extra=' stroke-width="2"')
)

_HM["please"] = (
    _p("M96 128 q-30 -6 -38 -34 q-6 -22 2 -40 q4 -10 11 -6 q6 4 3 14 l-5 18 "
      "q6 -30 12 -46 q3 -10 11 -7 q7 3 4 13 l-8 34 q6 -26 12 -40 q4 -9 11 -6 "
      "q7 4 4 13 l-10 38 Z", SKIN)
    + _p("M104 128 q30 -6 38 -34 q6 -22 -2 -40 q-4 -10 -11 -6 q-6 4 -3 14 l5 18 "
      "q-6 -30 -12 -46 q-3 -10 -11 -7 q-7 3 -4 13 l8 34 q-6 -26 -12 -40 "
      "q-4 -9 -11 -6 q-7 4 -4 13 l10 38 Z", SKIN)
    + _p("M100 122 v-56", extra=' stroke-width="2.5"')
    + _c(74, 30, 7, PINK) + _c(100, 22, 9, PINK) + _c(126, 30, 7, PINK)
)

_HM["thanks"] = (
    _c(100, 36, 19, SKIN)
    + _p("M100 17 q-19 0 -19 15 q8 -7 19 -7 q11 0 19 7 q0 -15 -19 -15 Z", COAL)
    + _dot(93, 36, 2.8) + _dot(107, 36, 2.8)
    + _p("M92 45 q8 7 16 0", extra=' stroke-width="2.5"')
    + _p("M66 132 q-2 -44 34 -44 q36 0 34 44 Z", GREEN)
    + _p("M100 118 q-26 -16 -30 -32 q-4 -14 8 -18 q11 -3 22 10 q11 -13 22 -10 "
      "q12 4 8 18 q-4 16 -30 32 Z", RED)
    + _p("M72 104 q-8 -8 -6 -18", "none",
         f' stroke-width="9" stroke="{SKIN}" stroke-linecap="round"')
    + _p("M128 104 q8 -8 6 -18", "none",
         f' stroke-width="9" stroke="{SKIN}" stroke-linecap="round"')
)

_HM["sorry"] = (
    _c(100, 52, 30, SKIN)
    + _dot(90, 46, 3) + _dot(110, 46, 3)
    + _p("M86 70 q14 -12 28 0", extra=' stroke-width="3"')
    + _p("M70 132 q-2 -38 30 -38 q32 0 30 38 Z", SKY)
    + _p("M84 100 q16 10 32 0", extra=' stroke-width="2.5"')
)

_HM["peace"] = (
    _c(100, 74, 46, WHITE)
    + _p("M100 28 v92 M100 74 l-32 32 M100 74 l32 32", extra=' stroke-width="6"')
    + _c(100, 74, 46, "none")
)

_HM["unity"] = (
    _c(66, 46, 16, SKIN) + _c(134, 46, 16, SKIN)
    + _dot(60, 44, 2.6) + _dot(72, 44, 2.6)
    + _dot(128, 44, 2.6) + _dot(140, 44, 2.6)
    + _p("M60 54 q6 6 12 0 M128 54 q6 6 12 0", extra=' stroke-width="2.5"')
    + _p("M38 128 q-2 -42 28 -42 q30 0 28 42 Z", BLUE)
    + _p("M106 128 q-2 -42 28 -42 q30 0 28 42 Z", RED)
    + _p("M84 92 q16 -14 32 0", extra=' stroke-width="5"')
)

_HM["friend"] = (
    _c(70, 50, 18, SKIN) + _c(130, 50, 18, SKIN)
    + _dot(64, 50, 2.6) + _dot(76, 50, 2.6)
    + _dot(124, 50, 2.6) + _dot(136, 50, 2.6)
    + _p("M42 132 q-2 -42 28 -42 q30 0 28 42 Z", GREEN)
    + _p("M102 132 q-2 -42 28 -42 q30 0 28 42 Z", ORANGE)
    + _p("M88 96 q12 -12 24 0", extra=' stroke-width="4"')
)

def _person(cx, top, skin, shirt, hair=COAL, hair_long=False, small=False):
    """A simple standing figure.

    Long hair is drawn *behind* the head, wider than it, so it frames the face
    instead of painting over it.
    """
    r = 15 if small else 19
    head_y = top + r
    body_top = head_y + r
    body_h = 54 if small else 66
    parts = []

    if hair_long:
        w = r + 7
        parts.append(_p(f"M{cx - w} {head_y} a{w} {w} 0 0 1 {2 * w} 0 "
                        f"l3 {r + 30} h-{2 * w + 6} Z", hair))

    parts.append(_c(cx, head_y, r, skin))
    parts.append(_p(f"M{cx - r} {head_y - 4} a{r} {r} 0 0 1 {2 * r} 0 "
                    f"q-{r} -12 -{2 * r} 0 Z", hair))
    parts.append(_dot(cx - 7, head_y - 1, 2.8))
    parts.append(_dot(cx + 7, head_y - 1, 2.8))
    parts.append(_p(f"M{cx - 8} {head_y + 9} q8 7 16 0", extra=' stroke-width="2.5"'))
    parts.append(_p(f"M{cx - 24} {body_top + body_h} q-2 -{body_h} 24 -{body_h} "
                    f"q26 0 24 {body_h} Z", shirt))
    return "".join(parts)



def _features(cx, cy, r, skin=SKIN, smile=True):
    """Eyes, ears and a mouth on a head of radius `r`."""
    e = r * 0.36
    parts = [
        _dot(cx - e, cy - 1, r * 0.13),
        _dot(cx + e, cy - 1, r * 0.13),
        _e(cx - r, cy + 2, r * 0.30, r * 0.22, skin),
        _e(cx + r, cy + 2, r * 0.30, r * 0.22, skin),
    ]
    if smile:
        parts.append(_p(f"M{cx - e} {cy + r * 0.52} q{e} {r * 0.32} {2 * e} 0",
                        extra=' stroke-width="2.5"'))
    return "".join(parts)


def _fringe(cx, cy, r, colour=COAL):
    """Hair across the top of the head, stopping above the eyes."""
    return _p(f"M{cx - r} {cy + 2} q0 -{r * 1.42} {r} -{r * 1.42} "
              f"q{r} 0 {r} {r * 1.42} q-{r * 0.34} -{r * 0.62} -{r} -{r * 0.62} "
              f"q-{r * 0.66} 0 -{r} {r * 0.62} Z", colour)


_P = {}

_P["mother"] = (
    _p("M74 54 q0 -34 26 -34 q26 0 26 34 l6 64 h-64 Z", COAL)
    + _r(92, 62, 16, 24, SKIN)
    + _p("M64 134 q-2 -52 36 -52 q38 0 36 52 Z", "#C2555A")
    + _p("M74 122 h52", "none", f' stroke-width="5" stroke="{GOLD}"')
    + _c(100, 48, 22, SKIN)
    + _fringe(100, 48, 22)
    + _features(100, 48, 22)
    + _dot(100, 39, 3.2, RED)
)
_P["father"] = (
    _r(92, 62, 16, 24, SKIN_D)
    + _p("M64 134 q-2 -52 36 -52 q38 0 36 52 Z", BLUE)
    + _p("M88 82 l12 14 l12 -14", "none", ' stroke-width="3"')
    + _c(100, 48, 22, SKIN_D)
    + _fringe(100, 48, 22)
    + _features(100, 48, 22, skin=SKIN_D, smile=False)
    + _p("M87 60 q13 -7 26 0", "none", f' stroke-width="5" stroke="{COAL}"')
    + _p("M91 68 q9 6 18 0", extra=' stroke-width="2.5"')
)

_P["brother"] = (
    _r(94, 74, 12, 18, SKIN)
    + _p("M74 134 q-2 -42 26 -42 q28 0 26 42 Z", GOLD)
    + _p("M90 92 l10 12 l10 -12", "none", ' stroke-width="3"')
    + _p("M100 112 v18", "none", ' stroke-width="2.5"')
    + _c(100, 62, 18, SKIN)
    + _fringe(100, 62, 18)
    + _features(100, 62, 18)
)
_P["sister"] = (
    _r(94, 74, 12, 18, SKIN)
    + _p("M74 134 q-2 -42 26 -42 q28 0 26 42 Z", MINT)
    + _p("M88 96 v14 M112 96 v14", "none", ' stroke-width="3"')
    + _c(100, 62, 18, SKIN)
    + _fringe(100, 62, 18)
    + _features(100, 62, 18)
    + _p("M84 70 q-10 16 -4 30", "none", f' stroke-width="7" stroke="{COAL}"')
    + _p("M116 70 q10 16 4 30", "none", f' stroke-width="7" stroke="{COAL}"')
    + _c(80, 102, 4.5, RED) + _c(120, 102, 4.5, RED)
)

_P["child"] = (
    _r(94, 82, 12, 14, SKIN)
    + _p("M80 134 q-2 -34 20 -34 q22 0 20 34 Z", ORANGE)
    + _c(100, 66, 24, SKIN)
    + _fringe(100, 66, 24)
    + _p("M100 40 q-3 -12 6 -14 q-2 8 2 12", COAL)
    + _features(100, 66, 24)
)
_P["girl"] = (
    _p("M76 58 q0 -32 24 -32 q24 0 24 32 l6 58 h-60 Z", COAL)
    + _r(93, 66, 14, 20, SKIN)
    + _p("M68 134 q-2 -48 32 -48 q34 0 32 48 Z", PINK)
    + _c(100, 52, 20, SKIN)
    + _fringe(100, 52, 20)
    + _features(100, 52, 20)
)
_P["grandfather"] = (
    _p("M64 132 q-2 -48 36 -48 q38 0 36 48 Z", SKY)
    + _c(100, 46, 23, SKIN)
    + _p("M77 44 q0 -26 23 -26 q23 0 23 26 q-8 -12 -23 -12 q-15 0 -23 12 Z", WHITE)
    + _dot(91, 46, 2.8) + _dot(109, 46, 2.8)
    + _p("M92 58 q8 6 16 0", extra=' stroke-width="2.5"')
    + _p("M79 54 q4 32 21 32 q17 0 21 -32 q-8 18 -21 18 q-13 0 -21 -18 Z", WHITE)
    + _e(72, 46, 7, 5, SKIN) + _e(128, 46, 7, 5, SKIN)
    + _p("M146 132 V80", "none", f' stroke-width="7" stroke="{BROWN}"')
    + _p("M146 132 V80", extra=' stroke-width="2.5"')
    + _p("M146 80 q-10 0 -10 8", "none", f' stroke-width="7" stroke="{BROWN}"')
)
_P["grandmother"] = (
    _p("M64 132 q-2 -48 36 -48 q38 0 36 48 Z", "#B48CA8")
    + _p("M74 112 h52", "none", f' stroke-width="4" stroke="{GOLD}"')
    + _c(100, 46, 23, SKIN)
    + _p("M76 48 q0 -30 24 -30 q24 0 24 30 q-7 -14 -24 -14 q-17 0 -24 14 Z", WHITE)
    + _c(100, 18, 11, WHITE)
    + _dot(91, 46, 2.8) + _dot(109, 46, 2.8)
    + _p("M92 58 q8 6 16 0", extra=' stroke-width="2.5"')
    + _dot(100, 32, 3, RED)
    + _e(72, 48, 7, 5, SKIN) + _e(128, 48, 7, 5, SKIN)
)
_P["teacher"] = (
    _r(112, 30, 76, 62, GREEN, 4)
    + _p("M122 48 h50 M122 64 h36", extra=' stroke="#FFFFFF" stroke-width="3"')
    + _person(60, 26, SKIN, BLUE)
    + _p("M84 96 l24 -18", extra=' stroke-width="5"')
)
_P["doctor"] = (
    _c(100, 40, 20, SKIN)
    + _dot(93, 38, 2.8) + _dot(107, 38, 2.8)
    + _p("M70 132 q-2 -46 30 -46 q32 0 30 46 Z", WHITE)
    + _p("M100 86 v22 M89 97 h22", extra=' stroke="#D2564B" stroke-width="5"')
    + _p("M84 62 q-10 22 4 30 a8 8 0 1 0 12 4", extra=' stroke-width="3"')
)
_P["run"] = (
    _c(120, 34, 17, SKIN)
    + _p("M96 96 q-6 -34 20 -42 q24 -6 26 20 q2 20 -14 26 Z", ORANGE)
    + _p("M96 96 l-30 28 M126 100 l14 32", extra=' stroke-width="6"')
    + _p("M104 66 l-32 8 M132 70 l24 -16", extra=' stroke-width="5"')
)
_P["swimming"] = (
    _r(0, 60, W, 90, SKY, 0)
    + _c(74, 52, 17, SKIN)
    + _p("M92 66 q34 -4 46 8", extra=' stroke-width="9" stroke="#E4873F"')
    + _p("M56 46 q-16 -14 -30 -6", extra=' stroke-width="5"')
    + _p("M0 84 q18 -12 36 0 q18 12 36 0 q18 -12 36 0 q18 12 36 0 q18 -12 36 0",
        extra=' stroke="#4E86BE" stroke-width="4" fill="none"')
)
_P["pool"] = (
    _r(24, 44, 152, 84, SKY, 8)
    + _r(24, 44, 152, 84, "none", 8)
    + _p("M32 74 q18 -12 36 0 q18 12 36 0 q18 -12 36 0 q18 12 30 0",
        extra=' stroke="#4E86BE" stroke-width="4" fill="none"')
    + _p("M32 100 q18 -12 36 0 q18 12 36 0 q18 -12 36 0 q18 12 30 0",
        extra=' stroke="#4E86BE" stroke-width="4" fill="none"')
    + _p("M68 44 v84 M132 44 v84", extra=' stroke="#FFFFFF" stroke-width="4"')
)
_P["speak"] = (
    _c(70, 66, 26, SKIN)
    + _dot(62, 60, 3) + _p("M60 78 q12 12 22 0", extra=' stroke-width="3"')
    + _p("M108 40 h68 q10 0 10 10 v40 q0 10 -10 10 h-44 l-18 18 v-18 q-6 0 -6 -10 "
      "v-40 q0 -10 10 -10 Z", WHITE)
    + _p("M122 60 h40 M122 76 h26", extra=' stroke-width="2.5"')
)

_S = {}

_S["book"] = (
    _p("M26 40 q34 -14 74 4 v82 q-40 -18 -74 -4 Z", RED)
    + _p("M174 40 q-34 -14 -74 4 v82 q40 -18 74 -4 Z", BLUE)
    + _p("M100 44 v82", extra=' stroke-width="3"')
    + _p("M44 62 h40 M44 80 h40 M116 62 h40 M116 80 h40",
        extra=' stroke-width="2" stroke="#FFFFFF"')
)

_S["board"] = (
    _r(30, 28, 140, 84, "#2F4F3E", 4)
    + _r(38, 36, 124, 68, "#3A614C", 2)
    + _p("M56 60 h50 M56 78 h72", extra=' stroke="#FFFFFF" stroke-width="3"')
    + _r(60, 112, 80, 10, BROWN, 3)
)

_S["pen"] = (
    _p("M40 124 l12 -34 l72 -68 l22 22 l-72 68 Z", BLUE)
    + _poly("40,124 52,90 62,112", GOLD)
    + _p("M112 34 l22 22", extra=' stroke-width="2.5"')
)

_S["ruler"] = (
    _r(24, 62, 152, 30, CREAM, 3)
    + "".join(_line(x, 62, x, 74) for x in range(44, 170, 20))
    + "".join(_line(x, 62, x, 70) for x in range(34, 170, 20))
)

_S["numbers"] = (
    _text("1 2 3", 100, 92, 46, DEEP)
)

_S["line"] = (
    _p("M28 110 L172 46", extra=' stroke-width="6"')
    + _c(28, 110, 8, RED) + _c(172, 46, 8, BLUE)
)

_S["question"] = _text("?", 100, 112, 96, PLUM)
_S["check"] = _p("M46 80 l30 30 l70 -70", extra=' stroke="#5C9A57" stroke-width="14" '
                 'fill="none"')
_S["alert"] = (
    _poly("100,22 176,128 24,128", YELLOW)
    + _p("M100 56 v34", extra=' stroke-width="7"') + _dot(100, 108, 5)
)
_S["target"] = (
    _c(100, 76, 48, WHITE) + _c(100, 76, 34, RED) + _c(100, 76, 20, WHITE)
    + _c(100, 76, 8, RED)
)
_S["letter"] = (
    _r(28, 44, 144, 84, WHITE, 4)
    + _p("M28 48 l72 48 l72 -48", extra=' stroke-width="3"')
    + _r(120, 52, 34, 24, RED, 2)
)
_S["stamp"] = (
    _r(40, 40, 120, 84, WHITE, 3)
    + _r(54, 54, 92, 56, RED, 2)
    + _c(100, 82, 18, WHITE)
    + "".join(_dot(x, 40, 3, GROUNDS["school"]) for x in range(48, 165, 16))
    + "".join(_dot(x, 124, 3, GROUNDS["school"]) for x in range(48, 165, 16))
)
_S["ticket"] = (
    _p("M28 50 h144 v24 a12 12 0 0 0 0 24 v24 h-144 v-24 a12 12 0 0 0 0 -24 Z", GOLD)
    + _p("M100 54 v14 M100 78 v14 M100 102 v14", extra=' stroke-width="2.5"')
    + _p("M46 76 h34", extra=' stroke-width="3"')
)
_S["picture"] = (
    _r(30, 34, 140, 96, WHITE, 4)
    + _r(42, 46, 116, 72, SKY, 2)
    + _c(66, 66, 11, YELLOW)
    + _poly("46,116 88,74 118,116", GREEN) + _poly("94,116 132,80 158,116", "#4D8749")
)
_S["colours"] = (
    _c(70, 60, 22, RED) + _c(126, 58, 22, BLUE) + _c(74, 104, 22, YELLOW)
    + _c(130, 104, 22, GREEN)
)
_S["music"] = (
    _p("M76 106 v-62 l58 -14 v62", extra=' stroke-width="5"')
    + _e(64, 108, 16, 12, PLUM) + _e(122, 94, 16, 12, PLUM)
    + _p("M76 60 l58 -14", extra=' stroke-width="5"')
)
_S["veena"] = (
    _c(60, 100, 30, BROWN)
    + _p("M84 88 l72 -50", extra=' stroke-width="11" stroke="#9A6B43"')
    + _c(160, 34, 14, BROWN)
    + _p("M78 92 l70 -48 M82 98 l70 -48", extra=' stroke-width="2" stroke="#F5E9D2"')
)
_S["om"] = _HM["om"]
_S["crown"] = (
    _p("M40 110 l-8 -60 l30 24 l38 -44 l38 44 l30 -24 l-8 60 Z", GOLD)
    + _p("M40 110 h120", extra=' stroke-width="3"')
    + _c(100, 42, 7, RED) + _c(62, 68, 6, GREEN) + _c(138, 68, 6, BLUE)
)
_S["shield"] = (
    _p("M100 20 l58 20 v40 q0 40 -58 62 q-58 -22 -58 -62 v-40 Z", BLUE)
    + _p("M100 38 l38 14 v30 q0 26 -38 42 q-38 -16 -38 -42 v-30 Z", CREAM)
)
_S["bow"] = (
    _p("M62 20 q52 56 0 108", extra=' stroke-width="7" stroke="#9A6B43"')
    + _p("M62 20 L62 128", extra=' stroke-width="2.5"')
    + _p("M62 74 h96", extra=' stroke-width="4"')
    + _poly("158,74 138,66 138,82", GREY)
)
_S["arrow"] = (
    _p("M28 76 h124", extra=' stroke-width="6"')
    + _poly("172,76 138,58 138,94", SLATE)
    + _p("M34 60 l16 16 l-16 16 M46 62 l14 14 l-14 14", extra=' stroke-width="3"')
)
_S["arrow_up"] = (
    _p("M100 130 v-84", extra=' stroke-width="8"')
    + _poly("100,20 132,58 68,58", GREEN)
)
_S["spear"] = (
    _p("M46 128 L142 40", extra=' stroke-width="8" stroke="#9A6B43"')
    + _poly("158,24 132,34 148,50", GREY)
    + _p("M138 44 l-10 -10", extra=' stroke-width="3"')
)
_S["compass"] = (
    _c(100, 76, 48, WHITE) + _c(100, 76, 40, "none")
    + _poly("100,38 112,76 100,114 88,76", RED)
    + _p("M100 76 l12 0 l-12 38 l-12 -38 Z", WHITE)
    + _dot(100, 76, 4)
)
_S["gear"] = (
    _c(100, 76, 40, SLATE)
    + "".join(_r(94, 16, 12, 24, SLATE, 2).replace(
        'x="94" y="16"', f'x="94" y="16"').replace(
        '/>', f' transform="rotate({a} 100 76)"/>') for a in range(0, 360, 45))
    + _c(100, 76, 40, "none")
    + _c(100, 76, 16, GROUNDS["school"])
)
_S["wheel"] = (
    _c(100, 76, 48, COAL) + _c(100, 76, 32, GREY) + _c(100, 76, 12, SLATE)
    + "".join(_line(100 + 12 * c, 76 + 12 * s, 100 + 32 * c, 76 + 32 * s)
              for c, s in [(1, 0), (.5, .87), (-.5, .87), (-1, 0),
                           (-.5, -.87), (.5, -.87)])
)
_S["cube"] = (
    _poly("60,58 100,36 140,58 100,80", "#B7AE9A")
    + _poly("60,58 100,80 100,124 60,102", "#9AA1A8")
    + _poly("140,58 100,80 100,124 140,102", "#7C838B")
)
_S["weight"] = (
    _p("M52 128 l10 -60 h76 l10 60 Z", SLATE)
    + _p("M84 68 q0 -24 16 -24 q16 0 16 24", extra=' stroke-width="6"')
    + _text("5", 100, 112, 26, WHITE)
)
_S["tongs"] = (
    _p("M70 26 q-10 50 10 100 M130 26 q10 50 -10 100", extra=' stroke-width="6"')
    + _c(100, 30, 8, GREY)
)
_S["plough"] = (
    _p("M40 124 L124 46", extra=' stroke-width="9" stroke="#9A6B43"')
    + _poly("40,124 30,104 58,110", SLATE)
    + _p("M124 46 h40", extra=' stroke-width="6" stroke="#9A6B43"')
    + _c(96, 74, 6, SLATE)
)
_S["ladder"] = (
    _p("M62 24 v106 M138 24 v106", extra=' stroke-width="7" stroke="#9A6B43"')
    + "".join(_p(f"M62 {y} h76", extra=' stroke-width="6" stroke="#9A6B43"')
              for y in (44, 66, 88, 110))
)
_S["road"] = (
    _r(0, 0, W, H, MINT, 10)
    + _p("M64 150 L88 30 h24 L136 150 Z", SLATE)
    + _p("M100 40 v14 M100 68 v16 M100 98 v18 M100 130 v20",
        extra=' stroke="#FFFFFF" stroke-width="4"')
)
_S["train"] = (
    _r(30, 56, 92, 52, RED, 5)
    + _r(122, 44, 48, 64, DEEP, 5)
    + _r(42, 68, 26, 22, SKY, 2) + _r(80, 68, 26, 22, SKY, 2)
    + _r(134, 58, 26, 22, SKY, 2)
    + _c(56, 116, 12, COAL) + _c(96, 116, 12, COAL) + _c(146, 116, 12, COAL)
    + _r(24, 100, 152, 8, SLATE, 2)
)
_S["bus"] = (
    _r(24, 44, 152, 64, GOLD, 8)
    + _r(36, 56, 34, 26, SKY, 2) + _r(78, 56, 34, 26, SKY, 2)
    + _r(120, 56, 34, 26, SKY, 2)
    + _r(24, 92, 152, 10, "#B4884A", 2)
    + _c(58, 114, 13, COAL) + _c(142, 114, 13, COAL)
)
_S["car"] = (
    _p("M22 106 v-20 l22 -6 l24 -26 h64 l16 26 l30 6 v20 Z", BLUE)
    + _r(56, 60, 34, 22, SKY, 2) + _r(96, 60, 34, 22, SKY, 2)
    + _c(58, 108, 14, COAL) + _c(142, 108, 14, COAL)
    + _c(58, 108, 6, GREY) + _c(142, 108, 6, GREY)
)
_S["aeroplane"] = (
    _r(0, 0, W, H, SKY, 10)
    + _p("M20 84 l50 -10 l30 -40 h16 l-10 38 l40 -6 l14 -20 h12 l-6 22 l30 4 "
      "v10 l-30 4 l6 22 h-12 l-14 -20 l-40 -6 l10 38 h-16 l-30 -40 Z", WHITE)
)
_S["chariot"] = (
    _p("M46 100 h96 l-8 -44 h-80 Z", "#B4562F")
    + _c(64, 112, 20, BROWN) + _c(132, 112, 20, BROWN)
    + _c(64, 112, 7, SAND) + _c(132, 112, 7, SAND)
    + _p("M142 78 h34", extra=' stroke-width="5"')
    + _poly("54,56 100,30 146,56", GOLD)
)
_S["flag"] = (
    _p("M52 128 V22", extra=' stroke-width="7"')
    + _p("M56 26 h100 v22 h-100 Z", ORANGE)
    + _p("M56 48 h100 v22 h-100 Z", WHITE)
    + _p("M56 70 h100 v22 h-100 Z", GREEN)
    + _c(106, 59, 9, DEEP)
)
_S["rangoli"] = (
    _c(100, 78, 46, "none")
    + "".join(_e(100 + 30 * c, 78 + 30 * s, 16, 10, PINK,
                 f' transform="rotate({a} {100 + 30 * c} {78 + 30 * s})"')
              for a, (c, s) in zip(range(0, 360, 45),
                                   [(1, 0), (.71, .71), (0, 1), (-.71, .71),
                                    (-1, 0), (-.71, -.71), (0, -1), (.71, -.71)]))
    + _c(100, 78, 14, YELLOW)
    + "".join(_dot(100 + 56 * c, 78 + 56 * s, 4, GREEN)
              for c, s in [(1, 0), (0, 1), (-1, 0), (0, -1)])
)
_S["fair"] = (
    _c(100, 74, 46, "none")
    + "".join(_line(100, 74, 100 + 46 * c, 74 + 46 * s)
              for c, s in [(1, 0), (.71, .71), (0, 1), (-.71, .71),
                           (-1, 0), (-.71, -.71), (0, -1), (.71, -.71)])
    + "".join(_c(100 + 46 * c, 74 + 46 * s, 8, col)
              for (c, s), col in zip(
                  [(1, 0), (.71, .71), (0, 1), (-.71, .71), (-1, 0),
                   (-.71, -.71), (0, -1), (.71, -.71)],
                  [RED, YELLOW, GREEN, BLUE, ORANGE, PLUM, PINK, GOLD]))
    + _c(100, 74, 9, SLATE)
    + _p("M84 128 h32 M100 120 v8", extra=' stroke-width="4"')
)
_S["garden"] = (
    _r(0, 0, W, H, MINT, 10)
    + _p("M0 112 h200", extra=' stroke-width="4"')
    + "".join(_c(x, y, 11, col) + _p(f"M{x} {y + 11} v{112 - y - 11}",
                                     extra=' stroke-width="3"')
              for x, y, col in [(40, 72, RED), (76, 60, YELLOW),
                                (120, 66, PINK), (158, 78, PLUM)])
    + _c(40, 72, 4, GOLD) + _c(76, 60, 4, GOLD)
    + _c(120, 66, 4, GOLD) + _c(158, 78, 4, GOLD)
)
_S["nest"] = (
    _p("M40 92 q0 40 60 40 q60 0 60 -40 q-60 -18 -120 0 Z", BROWN)
    + _p("M44 96 q56 -14 112 0 M48 110 q52 -10 104 0", extra=' stroke-width="2.5"')
    + _e(80, 88, 15, 12, SKY) + _e(112, 86, 15, 12, SKY) + _e(96, 76, 15, 12, SKY)
)
_S["shell"] = (
    _p("M100 124 q-56 -6 -60 -48 q-2 -34 60 -40 q62 6 60 40 q-4 42 -60 48 Z", CREAM)
    + _p("M100 124 v-88 M76 118 l-14 -78 M124 118 l14 -78 M56 100 l-14 -50 "
      "M144 100 l14 -50", extra=' stroke-width="2.5"')
)
_S["brick"] = (
    _r(30, 52, 140, 34, "#C4785A", 3) + _r(30, 90, 140, 34, "#B46A4E", 3)
    + _p("M100 52 v34 M66 90 v34 M134 90 v34", extra=' stroke-width="2.5"')
)
_S["charcoal"] = (
    _p("M34 116 q-6 -30 26 -38 q34 -8 52 8 q28 16 16 34 Z", COAL)
    + _p("M120 118 q-4 -24 20 -30 q26 -6 26 16 q0 14 -14 16 Z", "#4A453D")
    + _p("M58 96 q14 -14 32 -10", extra=' stroke="#6B655A" stroke-width="2.5"')
)
_S["cap"] = (
    _p("M46 92 q0 -56 54 -56 q54 0 54 56 Z", BLUE)
    + _p("M46 92 h124 q4 12 -14 12 h-110 Z", DEEP)
    + _p("M100 36 v-8", extra=' stroke-width="3"') + _c(100, 26, 6, RED)
)
_S["umbrella"] = (
    _p("M20 82 q0 -58 80 -58 q80 0 80 58 Z", RED)
    + _p("M20 82 q20 -16 40 0 q20 -16 40 0 q20 -16 40 0 q20 -16 40 0",
        extra=' stroke-width="3"')
    + _p("M100 82 v40 q0 14 -16 14 q-12 0 -12 -10", extra=' stroke-width="5"')
)
_S["medicine"] = (
    _r(56, 46, 88, 74, WHITE, 6)
    + _r(72, 30, 56, 18, RED, 4)
    + _p("M100 62 v42 M79 83 h42", extra=' stroke="#D2564B" stroke-width="9"')
    + _c(40, 108, 12, GOLD) + _c(160, 106, 12, SKY)
)
_S["fan"] = (
    _c(100, 74, 12, SLATE)
    + "".join(_p(f"M100 74 q26 -34 44 -14 q14 16 -44 14 Z", "#7FB6DE",
                 f' transform="rotate({a} 100 74)"')
              for a in (0, 120, 240))
    + _c(100, 74, 12, SLATE)
    + _p("M100 86 v34 M84 124 h32", extra=' stroke-width="4"')
)

_S["phone"] = (
    _r(64, 24, 72, 102, SLATE, 10)
    + _r(72, 40, 56, 70, SKY, 3)
    + _p("M88 32 h24", extra=' stroke-width="3"')
    + _c(100, 118, 6, GREY)
)

_COL = {}
for _name, _hex in [("red", RED), ("green", GREEN), ("yellow", YELLOW),
                    ("blue", BLUE), ("black", COAL), ("white", WHITE)]:
    _COL[_name] = (
        _r(34, 26, 132, 98, _hex, 12)
        + _p("M34 92 h132", extra=' stroke-width="2" opacity=".28"')
        + _e(62, 50, 18, 11, WHITE, ' opacity=".22" stroke="none"')
    )

_COL["evening"] = (
    _r(0, 0, W, 76, "#E8A05C", 10) + _r(0, 76, W, 74, DEEP, 10)
    + _c(100, 76, 26, "#E4732F")
    + _p("M0 76 h200", extra=' stroke-width="3"')
)

_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "fifty": 50,
}

_BEAD_COLOURS = [RED, BLUE, GREEN, ORANGE, PLUM, GOLD]


def _counting(n):
    """N counting beads, laid out the way an abacus or a number chart would.

    Up to 10 they are big enough to count one by one.  Past that they are
    grouped in rows of ten, so the shape of the number is what you read - which
    is exactly how a wall chart teaches twenty-four.
    """
    n = max(1, min(50, int(n)))
    body = [_text(str(n), 100, 42, 34, INK)]

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


ICONS = {}
ICONS.update(_A)
ICONS.update(_N)
ICONS.update(_F)
ICONS.update(_B)
ICONS.update(_HM)
ICONS.update(_P)
ICONS.update(_S)
ICONS.update(_COL)

_GROUND_OF = {}
for _d, _g in ((_A, "animals"), (_N, "nature"), (_F, "food"), (_B, "body"),
               (_HM, "home"), (_P, "people"), (_S, "school"), (_COL, "plain")):
    for _k in _d:
        _GROUND_OF[_k] = _g

ALIASES = {
    "mother": "mother", "father": "father",
    "elder brother": "brother", "younger brother": "brother",
    "elder sister": "sister", "younger sister": "sister",
    "cooked rice": "rice", "flatbread": "roti", "idli": "rice",
    "butter": "ghee", "brinjal": "brinjal", "okra": "okra",
    "pencil": "pen", "chair": "chair", "leg": "leg",
    "a bird": "bird", "a flower": "flower", "a tiger": "tiger",
    "a tooth": "tooth", "a rope": "rope", "a song": "music",
    "a hen": "hen", "a book": "book", "a story": "book",
    "the sun": "sun", "the earth": "earth", "the sea": "sea",
    "the moon": "moon", "the ground": "earth", "the body": "person",
    "a friend": "friend", "a lion": "lion", "a child": "child",
    "damaru drum": "damaru", "police station": "station",
    "a tin box": "box", "walking stick": "stick", "incense stick": "incense",
    "swimming pool": "pool", "to swim": "swimming", "swimming": "swimming",
    "a guess": "think", "a thought": "think", "to blow": "breath",
    "to feed": "meal", "to read": "book", "to run": "run",
    "a race": "run", "moving about": "run", "a day": "calendar",
    "today": "calendar", "tomorrow": "calendar", "now": "clock",
    "a moment": "clock", "sage": "sage", "holy sage": "sage",
    "greetings": "namaskara", "respectful greetings": "namaskara",
    "respect": "namaskara", "thank you": "thanks", "please": "please",
    "please forgive me": "sorry", "kindness": "heart", "a good thing": "heart",
}


def _clean(name):
    return (name or "").strip().lower()


def has(name):
    """Is there a real drawing for this icon name?"""
    name = _clean(name)
    if name.startswith("count:"):
        return True
    return name in ICONS or ALIASES.get(name) in ICONS or name in _NUMBER_WORDS


def resolve(name):
    """Map an icon name (or an English meaning) onto a drawing key."""
    name = _clean(name)
    if name in ICONS:
        return name
    if name in ALIASES and ALIASES[name] in ICONS:
        return ALIASES[name]
    if name in _NUMBER_WORDS:
        return f"count:{_NUMBER_WORDS[name]}"
    return None


def render(name, label=""):
    """SVG markup for `name`, or a typographic card when nothing is drawn.

    `label` is the word the card is teaching; it is what the fallback shows.
    """
    name = _clean(name)

    if name.startswith("count:"):
        try:
            n = int(name.split(":", 1)[1])
        except ValueError:
            n = 1
        return _svg(_counting(n), "numbers")

    key = resolve(name)
    if key and key.startswith("count:"):
        return render(key, label)
    if key:
        return _svg(ICONS[key], _GROUND_OF.get(key, "plain"))

    text = (label or name or "?").strip()
    size = 76 if len(text) <= 2 else 54 if len(text) <= 5 else 34
    return _svg(
        _c(100, 75, 58, WHITE)
        + _text(text, 100, 75 + size * 0.34, size, INK, "600", "kn"),
        "plain",
    )
