"""
config.py — configuration that must not live in the database.

The teacher PIN lives HERE, never in a students table, so a student session has
no data path to it.

It is read from, in order of precedence:
  1. the TUTOR_TEACHER_PIN environment variable   (Docker, systemd, a local shell)
  2. Streamlit secrets                            (Streamlit Community Cloud, which
                                                   has no way to set env vars)
  3. the development default below

Both mechanisms are supported because a deployment that can only use one of them
would otherwise be stuck running on the default PIN — and a default PIN on a
public URL is the same as no PIN.
"""

import os

DEFAULT_PIN = "1234"


def _from_streamlit_secrets():
    """The PIN from .streamlit/secrets.toml, or None.

    Wrapped defensively: importing streamlit is fine, but *touching* st.secrets
    raises when no secrets file exists, and this module is also imported by the
    command-line tools (build_dataset, validate_asr…) which run with no Streamlit
    runtime at all.
    """
    try:
        import streamlit as st

        return st.secrets["TUTOR_TEACHER_PIN"]
    except Exception:
        return None


TEACHER_PIN = str(
    os.environ.get("TUTOR_TEACHER_PIN")
    or _from_streamlit_secrets()
    or DEFAULT_PIN
)

# True when the app is running on the shipped default — the UI warns, loudly,
# because "we forgot to change the PIN" is how the teacher dashboard ends up
# world-readable.
IS_DEFAULT_PIN = TEACHER_PIN == DEFAULT_PIN
