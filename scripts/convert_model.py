import os
import shutil
import sys

SOURCE = "vasista22/whisper-kannada-small"
OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "whisper-kannada-small-ct2"
)


def _write_tokenizer(output_dir):
    from transformers import WhisperTokenizerFast

    tokenizer = WhisperTokenizerFast.from_pretrained(SOURCE)
    tokenizer.backend_tokenizer.save(os.path.join(output_dir, "tokenizer.json"))


def main():
    try:
        from ctranslate2.converters import TransformersConverter
    except ImportError:
        sys.exit("ctranslate2 is required: pip install ctranslate2")
    try:
        import transformers
    except ImportError:
        sys.exit("conversion needs transformers + torch: pip install transformers torch")

    if os.path.isdir(OUTPUT_DIR):
        print(f"{OUTPUT_DIR} already exists — removing and rebuilding.")
        shutil.rmtree(OUTPUT_DIR)

    print(f"Converting {SOURCE} -> {OUTPUT_DIR} (int8)…")
    print("First run downloads ~1 GB of source weights; this takes a few minutes.")
    converter = TransformersConverter(
        SOURCE, copy_files=["preprocessor_config.json"], load_as_float16=False
    )
    converter.convert(OUTPUT_DIR, quantization="int8", force=True)

    print("Writing tokenizer.json…")
    _write_tokenizer(OUTPUT_DIR)

    size_mb = sum(
        os.path.getsize(os.path.join(OUTPUT_DIR, f)) for f in os.listdir(OUTPUT_DIR)
    ) / 1e6
    print(f"Done — {size_mb:.0f} MB in {OUTPUT_DIR}")
    print("The tutor will now load this model automatically, with no network access.")


if __name__ == "__main__":
    main()
