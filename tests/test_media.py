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
        path = media.get_audio("W001", "ಅಮ್ಮ")
        size = os.path.getsize(path)
        print(f"   generated: {path}  ({size} bytes)")
        again = media.get_audio("W001", "ಅಮ್ಮ")
        print(f"   cached hit: {again}  (same file: {again == path})")
        print("   -> play this mp3 to confirm it says 'amma' in Kannada.")
    except Exception as e:
        print(f"   [!] audio generation failed (needs internet on first run): {e}")
    print()


def test_images():
    print("2) Photographs")
    os.makedirs(media.IMAGE_DIR, exist_ok=True)

    real_name = "real_sample.jpg"
    real_path = os.path.join(media.IMAGE_DIR, real_name)
    Image.new("RGB", (120, 90), (80, 160, 90)).save(real_path)
    try:
        resolved = media.photo_path(real_name)
        print(f"   real photo    -> {resolved}")
        assert resolved == real_path, "should resolve the real file"
        uri = media.photo_data_uri(real_name)
        assert uri and uri.startswith("data:image/jpeg;base64,"), uri
        print(f"   inline        -> {uri[:40]}... ({len(uri)} chars)")
    finally:
        os.remove(real_path)

    for missing in ("definitely_missing.jpg", "", None):
        assert media.photo_path(missing) is None, \
            f"a missing photo must give no picture, not a stand-in: {missing!r}"
        assert media.photo_data_uri(missing) is None
    print("   missing photo -> no picture at all (no placeholder card)")

    assert media.photo_credit("") == ""

    import csv
    vocab = os.path.join(os.path.dirname(media.IMAGE_DIR), "vocabulary.csv")
    with open(vocab, encoding="utf-8") as f:
        photos = {r["image_file"] for r in csv.DictReader(f) if r["image_file"]}
    for name in sorted(photos):
        assert media.photo_data_uri(name), f"{name} is on a card but does not load"
        with open(media.CREDITS_PATH, encoding="utf-8") as f:
            licence = next(r["licence"] for r in csv.DictReader(f)
                           if r["image_file"] == name)
        if licence.lower().startswith("cc by"):
            assert licence in media.photo_credit(name), \
                f"{name} is {licence} but its card would not credit the author"
    print(f"   all {len(photos)} card photographs load, and every CC BY one "
          "carries its credit")
    print()


def main():
    test_audio()
    test_images()
    print("Slice 3 checkpoint complete.")


if __name__ == "__main__":
    main()
