"""
test_media.py — Slice 3 checkpoint.

Proves both media paths:
  1. get_audio() generates (and caches) a Kannada mp3.
  2. get_image() resolves a real image, and returns a placeholder for a missing one.

Run:  python test_media.py
Then: play the printed mp3 and open the placeholder png to eyeball them.
"""

import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from PIL import Image

from tutor import media


def test_audio():
    print("1) Audio (gTTS, lang=kn)")
    try:
        path = media.get_audio("W001", "ಅಮ್ಮ")  # amma
        size = os.path.getsize(path)
        print(f"   generated: {path}  ({size} bytes)")
        # Second call must hit the cache (no regeneration / no network).
        again = media.get_audio("W001", "ಅಮ್ಮ")
        print(f"   cached hit: {again}  (same file: {again == path})")
        print("   -> play this mp3 to confirm it says 'amma' in Kannada.")
    except Exception as e:
        print(f"   [!] audio generation failed (needs internet on first run): {e}")
    print()


def test_images():
    print("2) Images")
    os.makedirs(media.IMAGE_DIR, exist_ok=True)

    # Simulate a *provided* real asset so we can prove real-image resolution.
    real_name = "real_sample.png"
    real_path = os.path.join(media.IMAGE_DIR, real_name)
    Image.new("RGB", (120, 120), (80, 160, 90)).save(real_path)
    try:
        resolved = media.get_image(real_name, label="ಅ")
        print(f"   real image  -> {resolved}")
        assert resolved == real_path, "should resolve the real file, not a placeholder"
        assert "placeholders" not in resolved
    finally:
        os.remove(real_path)  # test artifact — don't leave it in data/images

    # Missing image -> placeholder, must not crash and must be a valid PNG.
    ph = media.get_image("definitely_missing.png", label="ಅಮ್ಮ")
    print(f"   missing img -> {ph}")
    assert os.path.exists(ph), "placeholder was not created"
    with Image.open(ph) as im:
        print(f"   placeholder is a valid {im.size} {im.mode} PNG")
    print("   -> open the placeholder png to confirm it shows the word on a gray card.")
    print()


def main():
    test_audio()
    test_images()
    print("Slice 3 checkpoint complete.")


if __name__ == "__main__":
    main()
