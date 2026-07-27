# Licences, costs and attribution

Short version: **nothing in this project is paid, nothing needs an API key or a
credit card, and nothing obliges you to open-source your own work.** This file
records exactly what is used, under what licence, so that claim can be checked
rather than taken on trust.

## Cost

| Thing | Cost | Needs an account? |
|---|---|---|
| Speech recognition (faster-whisper + Kannada model) | free, runs on the CPU of the machine it is deployed on | no |
| Spoken audio (gTTS) | free | no |
| Pictures (Wikipedia / Wikimedia Commons) | free | no |
| Hosting (Streamlit Community Cloud, or self-hosted Docker) | free tier is sufficient | a GitHub login, for Streamlit Cloud |
| Every Python dependency | free | no |

There is no paid API anywhere in this project. The speech model runs **locally** —
it is not a cloud service and it is not metered.

## Python dependencies

Audited with `pip` metadata on the pinned versions in `requirements.txt`.

| Package | Licence | Copyleft? |
|---|---|---|
| streamlit 1.49.1 | Apache-2.0 | no |
| faster-whisper 1.2.1 | MIT | no |
| ctranslate2 4.8.1 | MIT | no |
| rapidfuzz 3.14.5 | MIT | no |
| indic-transliteration 2.3.82 | MIT | no |
| networkx 3.5 | BSD-3-Clause | no |
| pandas 2.3.3 | BSD-3-Clause | no |
| numpy 1.26.4 | BSD-3-Clause | no |
| pillow 11.3.0 | MIT-CMU | no |
| matplotlib 3.10.7 | PSF (BSD-compatible) | no |
| gTTS 2.5.4 | MIT | no |

### One dependency was removed for licence reasons

The project previously imported **`python-Levenshtein`**, which is
**GPL-2.0-or-later**. The GPL is *copyleft*: distributing an application that
imports a GPL library obliges you to license that whole application under the GPL
too. That is a real obligation, not a formality, and it was sitting in the middle
of the scoring code.

It has been replaced with **`rapidfuzz`** (MIT). This is not an approximation —
`Levenshtein.ratio()` and `rapidfuzz.distance.Indel.normalized_similarity()`
compute the same quantity by definition. The swap was verified: identical results
on 200,000 random string pairs (max difference 0.00e+00) and on all 121
curriculum concepts (0 scores changed).

**Do not add `python-Levenshtein` back.**

## The speech model

- **Model:** `vasista22/whisper-kannada-small`, converted to CTranslate2 int8 by
  `convert_model.py`.
- **Author:** Speech Lab, IIT Madras. Compute funded by *Bhashini*, India's
  National Language Translation Mission.
- **Licence:** **Apache-2.0** — free to use, redistribute, and use commercially,
  provided the licence is included and modifications are noted.
- **Cost:** none. It runs on the local CPU.

Stock multilingual Whisper is *not* a substitute here: it recognises 2 of 8
Kannada test words and writes Kannada in Devanagari. The Kannada fine-tune is
what makes the scoring honest.

## Pictures

Every picture is fetched from **Wikipedia / Wikimedia Commons** by
`fetch_images.py`, which **only accepts freely-licensed files** (public domain,
CC0, CC BY, CC BY-SA, GFDL). Anything whose licence is not recognised as free is
skipped rather than shipped.

Attribution — a *condition* of the CC BY / CC BY-SA licences, not a courtesy — is
recorded for every single image in **`data/images/CREDITS.csv`**, with the file,
the source page, the licence and the author.

If you publish this app, keep `CREDITS.csv` with it. That is what satisfies the
attribution requirement.

Colour and number cards are **not** fetched — they are drawn locally by
`fetch_images.py`, so they carry no licence at all.

## Spoken audio (gTTS) — read this one

`gTTS` is MIT-licensed code, and it is free. What it does is send text to the
**public Google Translate text-to-speech endpoint** and save the audio. There is
no API key, no billing, and no account.

Two honest caveats:

1. It is an **undocumented public endpoint**, not a supported API. Google could
   change it, and Google's terms discourage automated access. There is no cost
   or licence exposure to you, but there is a *reliability* risk.
2. Because of that, the app **caches every clip** in `data/audio/`. Run
   `python validate_asr.py` once and all 121 clips are generated and cached; the
   deployed app then never calls the network for audio again. A classroom
   deployment works fully offline.

If you want to remove even that dependency, `media.py` isolates all text-to-speech
behind `get_audio()`; a locally-installed engine such as **espeak-ng**
(GPL-3.0, invoked as a separate binary, which does *not* impose the GPL on this
app) supports Kannada and can be dropped in there. The default is gTTS because
its voice quality is markedly better, and the entire curriculum has been
validated against it.

## Fonts

The UI requests **Inter** and **Noto Sans Kannada** from Google Fonts, both under
the **SIL Open Font License 1.1** (free, redistributable). If the network is
unavailable the CSS falls back to the system Kannada font (Nirmala UI on Windows,
Noto on Linux), so text never renders as tofu boxes.

## Your own code

Nothing above requires you to publish this project under any particular licence.
MIT, Apache-2.0, or keeping it private are all fine.
