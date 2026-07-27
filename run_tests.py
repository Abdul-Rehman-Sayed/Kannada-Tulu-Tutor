"""
run_tests.py — run every check, in the order that fails fastest.

    python run_tests.py            # the fast suite (no network, no model)
    python run_tests.py --full     # also re-checks that the recogniser can hear
                                   # every concept (slow: loads whisper, ~5 min)

The fast suite is what you run before every commit. --full is what you run after
touching the curriculum or the scorer, because that is the only thing that can
tell you a card has become unpassable.
"""

import argparse
import subprocess
import sys
import time

# Tests and validators live in tests/ and are run as modules from the project
# root, so `from tutor import ...` resolves and their relative data paths still
# point at ./data and ./models.
FAST = [
    ("dataset structure",  [sys.executable, "-m", "tests.validate_dataset", "data/vocabulary.csv"]),
    ("speech scorer",      [sys.executable, "-m", "tests.test_pronunciation"]),
    ("accounts + hashing", [sys.executable, "-m", "tests.test_auth"]),
    ("curriculum graph",   [sys.executable, "-m", "tests.test_graph"]),
    ("media + images",     [sys.executable, "-m", "tests.test_media"]),
    ("app boots",          [sys.executable, "-m", "tests.test_app_boot"]),
    ("access separation",  [sys.executable, "-m", "tests.test_app_teacher"]),
]

SLOW = [
    ("recogniser hears every concept", [sys.executable, "-m", "tests.validate_asr", "--quiet"]),
    # The microphone gate got it backwards once: it threw away a correctly-spoken
    # word for being quiet. This replays every concept through simulated mics —
    # loud, soft, faint, and muted — and is the only check that can catch that.
    ("mic gate: soft voices heard, silence refused", [sys.executable, "-m", "tests.validate_mic"]),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true",
                    help="also run the slow end-to-end speech check")
    args = ap.parse_args()

    suite = FAST + (SLOW if args.full else [])
    results, failed = [], 0

    for name, cmd in suite:
        print(f"\n{'=' * 70}\n  {name}\n{'=' * 70}")
        t0 = time.time()
        proc = subprocess.run(cmd)
        took = time.time() - t0
        ok = proc.returncode == 0
        failed += 0 if ok else 1
        results.append((name, ok, took))

    print(f"\n{'=' * 70}\n  SUMMARY\n{'=' * 70}")
    for name, ok, took in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name:38} {took:6.1f}s")

    if not args.full:
        print("\n  (skipped the slow speech check — run with --full after changing "
              "the curriculum or the scorer)")

    print()
    if failed:
        print(f"{failed} of {len(results)} checks FAILED")
        sys.exit(1)
    print(f"All {len(results)} checks passed.")


if __name__ == "__main__":
    main()
