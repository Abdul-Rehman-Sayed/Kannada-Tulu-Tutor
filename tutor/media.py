import base64
import csv
import functools
import glob
import hashlib
import os
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR = os.path.join(BASE_DIR, "data", "audio")
IMAGE_DIR = os.path.join(BASE_DIR, "data", "images")
CREDITS_PATH = os.path.join(IMAGE_DIR, "CREDITS.csv")


def get_audio(concept_id, text, lang="kn"):
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


def photo_path(image_file):
    """The photograph for a card, or None.

    None is a real answer, not a gap to fill: a card whose word has no
    photograph that shows it plainly gets no picture at all, rather than a
    placeholder or a near miss.
    """
    if not image_file:
        return None
    path = os.path.join(IMAGE_DIR, os.path.basename(image_file))
    return path if os.path.isfile(path) else None


@functools.lru_cache(maxsize=None)
def _data_uri(path, mtime):
    with open(path, "rb") as f:
        return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("ascii")


def photo_data_uri(image_file):
    path = photo_path(image_file)
    return _data_uri(path, os.path.getmtime(path)) if path else None


@functools.lru_cache(maxsize=1)
def _credits(mtime):
    with open(CREDITS_PATH, encoding="utf-8-sig", newline="") as f:
        return {r["image_file"]: r for r in csv.DictReader(f)}


def photo_credit(image_file):
    """Who took a photograph and under what licence, as one short line.

    Most of the photographs are CC BY or CC BY-SA, which require the author and
    licence to be named where the picture is shown.  Public-domain ones need no
    credit and get none.
    """
    if not image_file or not os.path.exists(CREDITS_PATH):
        return ""
    row = _credits(os.path.getmtime(CREDITS_PATH)).get(os.path.basename(image_file))
    if not row:
        return ""
    licence = row.get("licence", "").strip()
    if licence.lower() in ("public domain", "cc0", "pd"):
        return ""
    author = row.get("author", "").strip() or "unknown"
    return f"Photo: {author} · {licence}"
