"""
media.py — audio (TTS) and image assets for the tutor.

get_audio() speaks a word with gTTS and caches the mp3 so it only hits the network
once (offline thereafter). get_image() resolves a word's picture, and — crucially —
synthesizes a labelled placeholder instead of crashing when the file is missing.

Public API:
    get_audio(concept_id, text) -> path to mp3
    get_image(image_file, label=None) -> path to png (real asset or placeholder)
"""

import glob
import hashlib
import os
import tempfile

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR = os.path.join(BASE_DIR, "data", "audio")
IMAGE_DIR = os.path.join(BASE_DIR, "data", "images")
PLACEHOLDER_DIR = os.path.join(BASE_DIR, "data", "placeholders")

_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\Nirmala.ttc",
    r"C:\Windows\Fonts\NirmalaB.ttc",
    r"C:\Windows\Fonts\Tunga.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansKannada-Regular.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def get_audio(concept_id, text, lang="kn"):
    """
    Return the path to an mp3 of `text` spoken in `lang`, cached at
    data/audio/{concept_id}_{texthash}.mp3. Generates it with gTTS on first use
    only; subsequent calls return the cached file without touching the network.

    The filename includes a hash of (lang, text) so editing a word in the CSV
    invalidates its cached audio — otherwise the child would keep hearing the
    OLD word while being scored against the new one.

    Raises on a network failure during first generation (the caller/UI should
    catch it), but never leaves a corrupt half-written cache file behind.
    """
    os.makedirs(AUDIO_DIR, exist_ok=True)
    safe_id = "".join(c if (c.isalnum() or c in "-_") else "_" for c in str(concept_id)) or "audio"
    digest = hashlib.md5(f"{lang}:{text}".encode("utf-8")).hexdigest()[:8]
    path = os.path.join(AUDIO_DIR, f"{safe_id}_{digest}.mp3")

    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path

    legacy = os.path.join(AUDIO_DIR, f"{safe_id}.mp3")
    if os.path.exists(legacy) and os.path.getsize(legacy) > 0:
        os.replace(legacy, path)
        return path

    from gtts import gTTS

    tts = gTTS(text=text, lang=lang)
    fd, tmp = tempfile.mkstemp(suffix=".mp3", dir=AUDIO_DIR)
    os.close(fd)
    try:
        tts.save(tmp)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    for old in glob.glob(os.path.join(AUDIO_DIR, f"{safe_id}_????????.mp3")):
        if old != path:
            try:
                os.remove(old)
            except OSError:
                pass
    return path


def get_image(image_file, label=None):
    """
    Return a filesystem path to the concept's image.

    If data/images/{image_file} exists, return it. Otherwise synthesize (and
    cache) a gray placeholder card showing `label` (or the filename) so the UI
    always has something to display. Never raises on a missing image.
    """
    if image_file:
        real = os.path.join(IMAGE_DIR, os.path.basename(image_file))
        if os.path.exists(real):
            return real

    return _make_placeholder(label or _stem(image_file) or "?", image_file)


def _stem(filename):
    if not filename:
        return ""
    return os.path.splitext(os.path.basename(filename))[0]


def _load_font(size):
    for candidate in _FONT_CANDIDATES:
        if os.path.exists(candidate):
            try:
                return ImageFont.truetype(candidate, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _make_placeholder(text, image_file=None):
    """Create (and cache) a 400x300 gray card with centered `text`."""
    os.makedirs(PLACEHOLDER_DIR, exist_ok=True)
    key = image_file or text
    safe = "".join(c if c.isalnum() else "_" for c in str(key))[:48] or "placeholder"
    path = os.path.join(PLACEHOLDER_DIR, f"ph_{safe}.png")
    if os.path.exists(path):
        return path

    width, height = 400, 300
    img = Image.new("RGB", (width, height), (210, 210, 210))
    draw = ImageDraw.Draw(img)

    draw.rectangle([4, 4, width - 5, height - 5], outline=(150, 150, 150), width=3)

    text = str(text)
    font = _load_font(56)
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        tw, th = font.getsize(text) if hasattr(font, "getsize") else (len(text) * 20, 40)
    draw.text(
        ((width - tw) / 2, (height - th) / 2 - 10),
        text,
        fill=(70, 70, 70),
        font=font,
    )

    caption = "(image unavailable)"
    cfont = _load_font(20)
    try:
        cb = draw.textbbox((0, 0), caption, font=cfont)
        cw = cb[2] - cb[0]
    except Exception:
        cw = len(caption) * 8
    draw.text(((width - cw) / 2, height - 44), caption, fill=(120, 120, 120), font=cfont)

    img.save(path)
    return path
