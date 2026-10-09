import os


def _from_streamlit_secrets():
    try:
        import streamlit as st

        return st.secrets["TUTOR_TEACHER_PIN"]
    except Exception:
        return None


TEACHER_PIN = str(
    os.environ.get("TUTOR_TEACHER_PIN")
    or _from_streamlit_secrets()
    or ""
).strip()
