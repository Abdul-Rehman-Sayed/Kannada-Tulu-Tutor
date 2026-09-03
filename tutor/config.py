import os

DEFAULT_PIN = "1234"


def _from_streamlit_secrets():
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

IS_DEFAULT_PIN = TEACHER_PIN == DEFAULT_PIN
