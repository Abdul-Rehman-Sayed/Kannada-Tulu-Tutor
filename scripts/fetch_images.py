"""
fetch_images.py — download one freely-licensed picture per concept.

Source: Wikimedia Commons, via its public MediaWiki API. No key, no account, no
paid service, and everything on Commons is under a free licence (public domain or
Creative Commons), so the pictures can ship with the app and be shown in a
classroom. Every file's licence and author are recorded in data/images/CREDITS.csv
— attribution is a condition of the CC licences, not an optional courtesy.

Each image is normalised to a 640x480 JPEG so the flashcards are a uniform size
(a wall of differently-shaped photos is what made the old UI feel broken).

    python fetch_images.py                # fetch everything still missing
    python fetch_images.py --force        # re-fetch even if a file exists
    python fetch_images.py --only V01,W003
    python fetch_images.py --contact-sheet  # build a montage to eyeball the set

Images already present are left alone, so a teacher can drop in a better picture
(same filename) and it will never be overwritten.
"""

import argparse
import csv
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageOps

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAB = os.path.join(BASE, "data", "vocabulary.csv")
IMAGE_DIR = os.path.join(BASE, "data", "images")
CREDITS = os.path.join(IMAGE_DIR, "CREDITS.csv")

API = "https://commons.wikimedia.org/w/api.php"

# Wikimedia's User-Agent policy requires a tool name, a version, and a way to
# CONTACT the operator. A UA without a contact gets served HTTP 429 "your request
# does not comply with our robot policy" — which is exactly what happened on the
# first run here. Set TUTOR_CONTACT to your own email or project URL before a
# large fetch; the default is deliberately honest about being unset.
_CONTACT = os.environ.get("TUTOR_CONTACT", "https://github.com/ - set TUTOR_CONTACT")
UA = f"KannadaTuluLiteracyTutor/1.0 ({_CONTACT}) python-urllib"

# Commons is free and donation-funded. Being slow is the price of using it, and
# hammering it is how you get the whole project's IP blocked.
REQUEST_PAUSE = 1.1          # seconds between concepts
MAX_RETRIES = 4

CARD_W, CARD_H = 640, 480

# Licences we accept. Commons also hosts a few "fair use" files via templates;
# anything whose licence we do not recognise as free is skipped rather than
# shipped, because the app is redistributed.
_FREE_HINTS = ("cc", "public domain", "pd", "gfdl", "attribution")


def _open(url, timeout=30):
    """GET with backoff. Honours Retry-After on 429; retries transient 5xx."""
    delay = 2.0
    last = None
    for attempt in range(MAX_RETRIES):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            return urllib.request.urlopen(req, timeout=timeout).read()
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 429:
                # The server tells us how long to wait — believe it rather than
                # guessing, otherwise we just get throttled again.
                wait = float(e.headers.get("Retry-After") or delay)
                print(f"        rate-limited; waiting {wait:.0f}s")
                time.sleep(min(wait, 60))
                delay *= 2
                continue
            if 500 <= e.code < 600:
                time.sleep(delay)
                delay *= 2
                continue
            raise
        except urllib.error.URLError as e:
            last = e
            time.sleep(delay)
            delay *= 2
    raise last


def _get(params):
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json"})
    return json.loads(_open(url))


def _is_free(licence):
    lic = (licence or "").strip().lower()
    if not lic:
        return False
    return any(h in lic for h in _FREE_HINTS)


WIKI_API = "https://en.wikipedia.org/w/api.php"

# Per-concept image overrides, as ("wiki", article) or ("commons", query).
#
# Neither source is reliable on its own, and they fail in *different* ways, so
# the source is named per concept rather than left to a fallback chain:
#
#   Commons free-text search matches file TEXT, not subject. It returned a blue
#   whale for "mother", a campervan for "father", a great egret for "mouse".
#
#   Wikipedia lead images are curated, but they depict the ARTICLE, which is not
#   always the everyday sense a six-year-old needs: "Head" leads with a meerkat,
#   "Bird" with a taxonomy collage, "Milk" with a piece of milk-glass tableware,
#   "Sea" with a map, "Child" with a toy console.
#
# Every entry below is a correction for something a contact-sheet review actually
# caught. Re-run `python fetch_images.py --contact-sheet` after any change and
# LOOK at the result: an unreviewed image set is how you ship a photo of a
# deathbed painting on the card that teaches a child the word "mother".
OVERRIDE = {
    # --- letters -------------------------------------------------------------
    "V01": ("wiki", "Mother"),
    "V03": ("wiki", "House mouse"),
    "V05": ("wiki", "Salt"),
    "V07": ("wiki", "Rishi"),
    "V12": ("commons", "child reading book"),      # wiki "Reading" -> a Greek vase
    "C07": ("wiki", "Chital"),                     # spotted deer
    "C11": ("commons", "metal tin box"),           # wiki -> a sheet of tin labels
    "C13": ("commons", "archery arrow"),           # wiki "Arrow" -> a clover field
    "C14": ("commons", "boy face portrait smiling"),  # wiki "Head" -> a meerkat
    "C15": ("wiki", "Children's literature"),
    "C20": ("wiki", "Fruit"),                      # commons -> a still-life painting
    "C24": ("wiki", "Machine"),
    "C30": ("wiki", "Sun"),
    "C32": ("commons", "rain drops falling"),      # wiki "Rain" -> wet tarmac
    # --- words ---------------------------------------------------------------
    "W001": ("wiki", "Mother"),
    "W002": ("wiki", "Father"),
    "W003": ("wiki", "Sibling"),
    "W004": ("wiki", "Sibling"),
    "W005": ("wiki", "Boy"),
    "W006": ("wiki", "Girl"),
    "W007": ("commons", "smiling child portrait"), # wiki "Child" -> a toy console
    "W009": ("commons", "grandmother portrait"),   # wiki -> an unsettling painting
    "W010": ("wiki", "Friendship"),
    "W016": ("wiki", "Pig"),
    "W018": ("wiki", "House mouse"),
    "W020": ("wiki", "House sparrow"),             # wiki "Bird" -> a taxonomy collage
    "W026": ("commons", "rain drops falling"),
    "W027": ("wiki", "Sun"),
    "W031": ("wiki", "Flower"),
    "W034": ("wiki", "Ocean"),                     # wiki "Sea" -> a map
    "W035": ("commons", "cooked rice bowl"),
    # Commons "glass of milk" returns milk-GLASS — the opaque white tableware.
    # The Wikipedia article leads with an actual glass of milk.
    "W036": ("wiki", "Milk"),
    "W038": ("wiki", "Fruit"),
    "W042": ("wiki", "Roti"),                      # commons -> a bakery interior
    # "Human head" leads with an anatomical drawing; children need a face.
    "W043": ("commons", "boy face portrait smiling"),
    "W044": ("wiki", "Human eye"),
    "W045": ("wiki", "Ear"),
    "W046": ("wiki", "Human nose"),
    "W047": ("wiki", "Lip"),
    "W048": ("wiki", "Hand"),
    "W049": ("commons", "human legs walking jeans"),  # wiki -> a 3D anatomy render
    "W050": ("wiki", "Human tooth"),
    "W068": ("commons", "wooden door house"),
}


def search_wikipedia_image(query, title=None):
    """
    The lead image of the best-matching Wikipedia article.

    Far more reliable than a raw image search: an article's lead image has been
    chosen by editors to *depict the subject*, whereas a file-name search just
    matches text. Lead images live on Commons, so the licence is still free — we
    look it up and record it exactly as for a Commons hit.
    """
    if title:
        params = {"action": "query", "titles": title}
    else:
        params = {"action": "query", "generator": "search",
                  "gsrsearch": query, "gsrlimit": 1, "gsrnamespace": 0}
    params.update({"prop": "pageimages", "piprop": "thumbnail|name", "pithumbsize": 800})

    url = WIKI_API + "?" + urllib.parse.urlencode({**params, "format": "json"})
    data = json.loads(_open(url))
    pages = (data.get("query") or {}).get("pages") or {}
    for page in pages.values():
        thumb = (page.get("thumbnail") or {}).get("source")
        fname = page.get("pageimage")
        if not thumb or not fname:
            continue
        licence, author = _commons_licence(f"File:{fname}")
        if not _is_free(licence):
            continue
        return thumb, licence, author, f"File:{fname}"
    return None, None, None, None


def _commons_licence(file_title):
    """(licence, author) for a Commons file, so attribution can be recorded."""
    try:
        data = _get({"action": "query", "titles": file_title,
                     "prop": "imageinfo", "iiprop": "extmetadata"})
    except Exception:
        return "", ""
    for page in ((data.get("query") or {}).get("pages") or {}).values():
        meta = ((page.get("imageinfo") or [{}])[0]).get("extmetadata") or {}
        return (
            (meta.get("LicenseShortName") or {}).get("value", ""),
            _strip_html((meta.get("Artist") or {}).get("value", "")),
        )
    return "", ""


def search_image(query):
    """Best free bitmap on Commons for `query` -> (image_url, licence, author, page)."""
    data = _get({
        "action": "query",
        "generator": "search",
        "gsrsearch": f"filetype:bitmap {query}",
        "gsrnamespace": 6,          # File: namespace only
        "gsrlimit": 8,              # a few, so we can skip non-free / odd ones
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": 800,          # server-side thumbnail: no giant downloads
    })
    pages = (data.get("query") or {}).get("pages") or {}
    # `generator=search` loses ranking in the dict, so restore it via index.
    ordered = sorted(pages.values(), key=lambda p: p.get("index", 999))

    for page in ordered:
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        licence = (meta.get("LicenseShortName") or {}).get("value", "")
        author = (meta.get("Artist") or {}).get("value", "")
        url = info.get("thumburl") or info.get("url")
        if not url or not _is_free(licence):
            continue
        # Strip the HTML Commons puts in the Artist field.
        author = _strip_html(author)
        return url, licence, author, page.get("title", "")
    return None, None, None, None


def _strip_html(s):
    out, depth = [], 0
    for ch in s or "":
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(ch)
    return " ".join("".join(out).split())[:120]


def download_card(url, dest):
    """Fetch `url` and write it as a CARD_W x CARD_H JPEG (centre-cropped)."""
    raw = _open(url, timeout=60)
    img = Image.open(io.BytesIO(raw))
    img = ImageOps.exif_transpose(img)          # honour camera rotation
    img = img.convert("RGB")
    # Crop to the card's aspect ratio rather than squashing it — a stretched cow
    # is worse than a cropped one.
    img = ImageOps.fit(img, (CARD_W, CARD_H), method=Image.LANCZOS, centering=(0.5, 0.4))
    # Write via a temp file so an interrupted run can't leave a truncated JPEG
    # that the app would then fail to open.
    tmp = dest + ".part"
    img.save(tmp, "JPEG", quality=86, optimize=True)
    os.replace(tmp, dest)


def load_rows():
    with open(VOCAB, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


# Locally drawn cards
#
# Colours and numbers are NOT fetched. A photograph is simply the wrong medium
# for them: "a photo of the colour red" is whatever the search engine feels like
# that day, and "a photo of the number five" teaches nothing. A flat swatch and a
# set of countable dots are unambiguous, better pedagogy, need no network, and
# carry no licence. They are drawn here instead.
_SWATCHES = {
    "red": (208, 63, 52), "green": (46, 139, 87), "yellow": (240, 190, 40),
    "blue": (52, 110, 200), "black": (38, 40, 48), "white": (250, 250, 252),
}

# Kannada digits ೦-೯, so the numeral on the card is the one the child will read.
_KN_DIGITS = "೦೧೨೩೪೫೬೭೮೯"
_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}


def _kn_numeral(n):
    return "".join(_KN_DIGITS[int(d)] for d in str(n))


def draw_colour_card(meaning, dest):
    rgb = _SWATCHES[meaning]
    img = Image.new("RGB", (CARD_W, CARD_H), (250, 250, 252))
    d = ImageDraw.Draw(img)
    m = 48
    # The outline must contrast with the SWATCH, not with the page: a white
    # swatch on a near-white card is otherwise an invisible blank rectangle,
    # which is what the first render of "ಬಿಳಿ / white" actually looked like.
    luma = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
    outline = (120, 126, 140) if luma > 200 else (255, 255, 255)
    d.rounded_rectangle([m, m, CARD_W - m, CARD_H - m], radius=28, fill=rgb,
                        outline=outline, width=3)
    img.save(dest, "JPEG", quality=92)


def draw_number_card(meaning, dest):
    """The Kannada numeral plus exactly that many dots, so it can be counted."""
    from PIL import ImageDraw
    n = _NUMBERS[meaning]
    img = Image.new("RGB", (CARD_W, CARD_H), (250, 250, 252))
    d = ImageDraw.Draw(img)

    # Dots laid out in rows of five — the way counting is taught.
    cols = 5
    rows_n = (n + cols - 1) // cols
    r, gap = 34, 26
    grid_h = rows_n * (2 * r) + (rows_n - 1) * gap
    top = (CARD_H - grid_h) / 2 + 40
    for i in range(n):
        row, col = divmod(i, cols)
        in_row = min(cols, n - row * cols)
        grid_w = in_row * (2 * r) + (in_row - 1) * gap
        left = (CARD_W - grid_w) / 2
        cx = left + col * (2 * r + gap) + r
        cy = top + row * (2 * r + gap) + r
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(92, 107, 192))

    numeral = _kn_numeral(n)
    font = _card_font(96)
    box = d.textbbox((0, 0), numeral, font=font)
    d.text(((CARD_W - (box[2] - box[0])) / 2, 26), numeral, fill=(43, 45, 66), font=font)
    img.save(dest, "JPEG", quality=92)


def _card_font(size):
    """A font that can actually render Kannada digits — else they come out tofu."""
    from PIL import ImageFont
    for path in (
        r"C:\Windows\Fonts\Nirmala.ttc",
        r"C:\Windows\Fonts\Tunga.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansKannada-Regular.ttf",
    ):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def draw_local(row, dest):
    """Draw this concept's card locally. Returns True if it was handled here."""
    meaning = (row.get("english_meaning") or "").strip().lower()
    if row.get("category") == "colours" and meaning in _SWATCHES:
        draw_colour_card(meaning, dest)
        return True
    if row.get("category") == "numbers" and meaning in _NUMBERS:
        draw_number_card(meaning, dest)
        return True
    return False


def contact_sheet(rows, per_page=36):
    """
    Labelled montages of every fetched image.

    A search API will happily return a heron for "mouse" and an oil painting for
    "mother", and you cannot tell which tile is which concept from an unlabelled
    grid. Each thumbnail is captioned with its concept id and meaning, so the
    sheet can actually be checked rather than glanced at. Paginated, because 121
    legible captions do not fit on one image.
    """
    from PIL import ImageDraw

    have = [r for r in rows if os.path.exists(os.path.join(IMAGE_DIR, r["image_file"]))]
    if not have:
        sys.exit("No images fetched yet.")

    cols, thumb, cap = 6, 190, 30
    font = _card_font(15)
    pages = (len(have) + per_page - 1) // per_page
    outs = []

    for pg in range(pages):
        chunk = have[pg * per_page:(pg + 1) * per_page]
        rows_n = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * thumb, rows_n * (thumb + cap)), (250, 250, 252))
        d = ImageDraw.Draw(sheet)
        for i, r in enumerate(chunk):
            x, y = (i % cols) * thumb, (i // cols) * (thumb + cap)
            im = Image.open(os.path.join(IMAGE_DIR, r["image_file"]))
            im = ImageOps.fit(im, (thumb - 4, thumb - 4), method=Image.LANCZOS)
            sheet.paste(im, (x + 2, y + 2))
            label = f'{r["concept_id"]} {r["english_meaning"]}'[:30]
            d.text((x + 4, y + thumb + 4), label, fill=(30, 32, 44), font=font)
        out = os.path.join(BASE, "data", f"contact_sheet_{pg + 1}.jpg")
        sheet.save(out, "JPEG", quality=85)
        outs.append(out)
        print(f"Contact sheet page {pg + 1} ({len(chunk)} images) -> {out}")
    return outs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-fetch images that already exist")
    ap.add_argument("--only", default="", help="comma-separated concept ids")
    ap.add_argument("--contact-sheet", action="store_true", help="build a montage and exit")
    args = ap.parse_args()

    os.makedirs(IMAGE_DIR, exist_ok=True)
    rows = load_rows()

    if args.contact_sheet:
        contact_sheet(rows)
        return

    if args.only:
        wanted = {c.strip() for c in args.only.split(",")}
        rows = [r for r in rows if r["concept_id"] in wanted]

    credits, failed = [], []
    # Keep any credits we already recorded for images we're not re-fetching.
    if os.path.exists(CREDITS):
        with open(CREDITS, encoding="utf-8-sig") as f:
            credits = [r for r in csv.DictReader(f)]

    for i, r in enumerate(rows, 1):
        cid = r["concept_id"]
        dest = os.path.join(IMAGE_DIR, r["image_file"])
        query = (r.get("image_query") or r.get("english_meaning") or "").strip()

        if os.path.exists(dest) and not args.force:
            print(f"[{i:3}/{len(rows)}] {cid:5} have    {r['image_file']}")
            continue

        # Colours and numbers are drawn, not searched (see draw_local).
        try:
            if draw_local(r, dest):
                credits = [c for c in credits if c.get("concept_id") != cid]
                print(f"[{i:3}/{len(rows)}] {cid:5} drawn   {r['english_meaning']}")
                continue
        except Exception as e:
            print(f"[{i:3}/{len(rows)}] {cid:5} ERROR   drawing card: {e}")
            failed.append((cid, str(e)))
            continue

        if not query:
            failed.append((cid, "no image_query"))
            continue

        try:
            source, target = OVERRIDE.get(cid, (None, None))
            if source == "commons":
                url, licence, author, page = search_image(target)
            elif source == "wiki":
                url, licence, author, page = search_wikipedia_image(target, title=target)
            else:
                # No override: Wikipedia's curated lead image first, since a raw
                # Commons file search is much likelier to return something that
                # merely mentions the word. Commons only as a fallback.
                url, licence, author, page = search_wikipedia_image(query)
                if not url:
                    url, licence, author, page = search_image(query)
            if not url:
                print(f"[{i:3}/{len(rows)}] {cid:5} MISS    no free image for {query!r}")
                failed.append((cid, f"no free image for {query!r}"))
                continue
            download_card(url, dest)
            credits = [c for c in credits if c.get("concept_id") != cid]
            credits.append({
                "concept_id": cid, "image_file": r["image_file"], "query": query,
                "source_page": page, "licence": licence, "author": author,
                "source_url": url,
            })
            print(f"[{i:3}/{len(rows)}] {cid:5} ok      {query!r} <- {licence}")
        except Exception as e:
            print(f"[{i:3}/{len(rows)}] {cid:5} ERROR   {query!r}: {e}")
            failed.append((cid, str(e)))
        time.sleep(REQUEST_PAUSE)   # a free, donation-funded API: don't hammer it

    if credits:
        with open(CREDITS, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=[
                "concept_id", "image_file", "query", "source_page",
                "licence", "author", "source_url",
            ])
            w.writeheader()
            w.writerows(sorted(credits, key=lambda c: c["concept_id"]))
        print(f"\nAttribution for {len(credits)} images -> {CREDITS}")

    if failed:
        print(f"\n{len(failed)} concept(s) have no image (the app draws a lettered "
              f"card for these, so nothing breaks):")
        for cid, why in failed:
            print(f"  {cid:5} {why}")


if __name__ == "__main__":
    main()
