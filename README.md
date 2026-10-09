# Kannada & Tulu Literacy Tutor

A speaking tutor that teaches children to read Kannada or Tulu. The child sees a
letter, word or sentence, hears it spoken, says it into the microphone and is
scored on pronunciation. A prerequisite graph decides what comes next, so the
alphabet comes before words, and words before phrases and sentences.

Everything runs locally and for free. Speech is recognised on the machine's own
CPU; no recording ever leaves it.

## Features

- **Two separate curricula.** Kannada and Tulu share the app and nothing else.
  Each learner picks a track, and their progress in it is kept on its own.
- **Letters first.** Each letter is taught on its own. Words are taught one
  letter's family at a time, with the whole family listed beside the card.
- **Tulu lipi.** Tulu letters are shown in the Tulu-Tigalari script, with the
  Kannada letter underneath. Tulu words stay in the Kannada script for now.
- **Fair scoring.** Soft voices are amplified, unclear recordings are a free
  retry, and a look-alike word (ಬೇರು for ಬೆರಳು) is not accepted as correct.
- **Nobody gets stuck.** After 6 tries a concept is parked and flagged for the
  teacher, not counted as learned.
- **Teacher dashboard.** Each teacher has a class code. The dashboard shows only
  their own class: plain-language findings, an alphabet chart coloured in for
  each child, the hardest words, progress over time and CSV export.
- **Real photographs.** Word cards use hand-picked Wikimedia Commons photos with
  credit lines. Numbers are drawn as Kannada numerals over counting beads.

## Curriculum

| Stage | Kannada (243) | Tulu (161) |
|---|---|---|
| Letters | 45 | 45 |
| Words | 104 | 60 |
| Numbers 1–50 | 50 | 50 |
| Phrases | 14 | 6 |
| Sentences | 30 | — |

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env        # then set your own TUTOR_TEACHER_PIN in .env
streamlit run app.py
```

Open <http://localhost:8501>. The first scored recording downloads the Kannada
speech model (~250 MB) once; after that it runs offline. To build the model
locally instead:

```bash
pip install transformers torch
python -m scripts.convert_model
```

Run everything from the project root.

## Accounts

| | Learner | Teacher |
|---|---|---|
| Entry | **Start learning** | **Teacher sign in** |
| Sign up with | name, username, password, class code (optional) | name, username, password, **teacher PIN** |
| Lands on | the lesson cards | their class dashboard |

Passwords are stored as salted scrypt hashes. A child joins a class by typing
the teacher's class code, either at sign-up or later from their sidebar.

## How scoring works

1. The recording is decoded to 16 kHz mono and checked. Silence, a blip or a
   ramble is sent back as a free retry.
2. It is trimmed and normalised, then transcribed by `faster-whisper` (a Kannada
   fine-tune of Whisper-small, int8 on CPU).
3. The expected text and the heard text are both romanised and compared with a
   normalised Levenshtein ratio. The pass mark is **0.65**, measured with
   `scripts/tune_threshold.py`.
4. No other card, and no word in `data/lookalike_words.csv`, may match better.
5. Mastery is a moving average (`alpha = 0.75`). A concept counts as learned at
   0.7.

## Tests

```bash
python run_tests.py          # fast suite
python run_tests.py --full   # also checks the recogniser can hear every card
```

## Regenerating the data

```bash
python -m scripts.build_dataset
python -m scripts.upgrade_curriculum
python -m scripts.letters_first
python -m scripts.assign_icons
python -m scripts.fetch_images      # photographs, by exact Commons file name
python -m tests.validate_asr        # also fills the offline audio cache
```

## Deploying

```bash
docker build -t kannada-tutor .
docker run -p 8501:8501 --env-file .env -v tutor-data:/app/data kannada-tutor
```

- **Set the teacher PIN.** There is no built-in default: until
  `TUTOR_TEACHER_PIN` is set, teacher sign-up is closed. `.env` is never
  committed or copied into the Docker image.
- **The microphone needs HTTPS** on any host other than `localhost`.
- **Accounts live in one SQLite file** (`data/tutor.db`) on the machine running
  the app. Run it in one place and have everyone open that URL. Mount a volume,
  or the data is lost when the container is removed.
- On Streamlit Community Cloud, `packages.txt` installs `ffmpeg` and `libgomp1`,
  and the PIN goes in **Settings → Secrets**.

## Configuration

Settings are read from the environment, or from a `.env` file in the project
root (see `.env.example`). Variables already set in the environment take
precedence.

| Variable | Purpose |
|---|---|
| `TUTOR_TEACHER_PIN` | Secret required to create a teacher account |
| `TUTOR_DB_PATH` | Where the database is stored (default `data/tutor.db`) |
| `TUTOR_WHISPER_MODEL` | Use a different speech model (size, Hub id or path) |
| `TUTOR_MIC_GATE` | Set to `off` to bypass the microphone check |
| `TUTOR_SKIP_WARMUP` | Skip loading the model at start-up |

## Project structure

```
app.py                  Streamlit app: landing, sign-in, lessons, teacher dashboard
tutor/graph_engine.py   curricula, lesson order, parking rule
tutor/pronunciation.py  speech recognition, romanisation, scoring, mic check
tutor/db.py             SQLite: students, mastery, attempt history
tutor/auth.py           accounts, password hashing, class codes
tutor/insight.py        findings and charts for the teacher
tutor/media.py          text-to-speech cache, photographs, credits
tutor/illustrations.py  counting cards and colour swatches
tutor/tulu_lipi.py      Kannada-script Tulu to Tulu lipi
tutor/ui.py             styles
scripts/                dataset generation, model conversion, threshold tuning
tests/                  tests and validators
data/                   vocabulary, letter words, look-alikes, images
```

## Stack and credits

Streamlit · faster-whisper / CTranslate2 (Kannada Whisper-small fine-tune from
Speech Lab, IIT Madras) · RapidFuzz · indic-transliteration · NetworkX · SQLite ·
gTTS · Pillow.

The Tulu lipi font is **Mallige** v1.4 by Prahlad Prasad Tantry (SIL OFL 1.1), in
`static/fonts/`. Photo credits are in `data/images/CREDITS.csv`.
