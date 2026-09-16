# Kannada / Tulu Literacy Tutor

An interactive speech tutor that teaches children to read and pronounce Kannada
or Tulu. A child picks which language they came to learn, then sees a letter,
word or sentence with a picture, hears it spoken, says it into the microphone,
and is scored on their pronunciation. A prerequisite graph decides what they see
next, so the alphabet unlocks the vocabulary that uses it, and the vocabulary
unlocks the sentences built from it.

**The two languages are two separate curricula.** They share this application and
nothing else: a Tulu learner is never served a Kannada card, a Kannada learner is
never shown a Tulu translation they did not ask for, and progress in each is kept
and counted separately. The choice is stored on the learner's record, so signing
in on another device resumes the same track.

Learners and teachers have separate accounts and separate sign-in pages. Teachers
get a dashboard that answers "who needs me today" in sentences — plus an alphabet
chart, coloured in per child, of the kind already on the classroom wall.

Everything runs **locally and for free**. The speech recogniser is not a cloud
API: it is a model that runs on the machine's CPU. No child's voice ever leaves
the machine. There is no key, no billing, and no copyleft licence anywhere in the
stack (see **[LICENCES.md](LICENCES.md)**).

---

## Quick start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open <http://localhost:8501>. The first recording that gets scored pulls the
Kannada speech model (~250 MB) from the HuggingFace Hub and caches it; everything
after that runs offline.

To build the model locally instead, so the machine never needs the network at
all, run the one-off conversion first. It needs two packages that are
deliberately **not** in `requirements.txt`, because only the conversion uses them
and they are a gigabyte the tutor would otherwise carry for nothing:

```bash
pip install transformers torch
python -m scripts.convert_model
```

Everything is run from the project root, so `./data` and `./models` resolve.

---

## Accounts

There are two doors, named for who walks through them.

| | Learner | Teacher |
|---|---|---|
| Entry point | **Start learning** | **Teacher sign in** |
| Sign in with | username + password | username + password |
| Create an account with | name, username, password, *class code (optional)* | name, username, password, **teacher PIN** |
| Lands on | the flashcard loop | their own class dashboard |

The teacher PIN is a **registration secret**, required once when the account is
created — not a password typed in front of a classroom on every visit. It appears
only on the teacher door; a learner is never shown it. Signing in with the wrong
kind of account is refused and explained, so nobody ends up in a view that does
not match the account they typed.

The teacher PIN defaults to `1234` — **change it** (see *Deploying*).

Accounts live in a SQLite file on whichever machine is running the app, so one
account does **not** work on a second machine running its own copy — see *An
account does not follow you to another machine*.

Every password is stored as a **scrypt** hash with a per-user random salt, and
compared in constant time. The role lives on the user row and is re-read from the
database on every rerun, so a student session has no path to the dashboard: there
is no session flag a client could set to promote itself.

Each account gets its **own** progress record, which matters because two children
in one class are routinely both called Ravi. Sign-up allocates a new learner row
rather than reusing whichever one happens to match by name, and a duplicate shows
on the dashboard with the username appended — `Ravi`, then `Ravi (ravi_b)` — so a
teacher can tell them apart.

### Which teacher gets which child

A school runs two or three teachers at once, and a dashboard listing every child
in the building is no use to any of them: nobody can tell which Ravi is theirs,
and every class-wide number on the page — the average, the hardest words, the
daily trend — is computed over other people's children.

So each teacher has a **class code**, and a child belongs to exactly one class.

- A teacher account is given a six-character code when it is created — `GH2-3JQ`,
  from an alphabet with no `I`, `O`, `0` or `1`, because it gets read out loud and
  copied off a whiteboard. It is the first thing on their dashboard. Teacher
  accounts made before class codes existed are given one the next time they sign
  in, rather than having to be remade.
- A child types it into the **Class code** box when they create their account, or
  afterwards into the box in their own sidebar, which stays in front of them until
  they have joined one. From then on their work appears on that teacher's
  dashboard and on no other.
- Typing a second teacher's code **moves** the child rather than adding them to
  both. A child sits in one class, and their old teacher stops seeing them.

Assignment is deliberately the child's move rather than the teacher's. A teacher
picking children off a shared list races the teacher next to them for the same
child, and neither can see what the other has already done.

The code is **not a secret and not a password.** It admits a child to a class and
does nothing else: it opens no dashboard, needs no password to be useful to its
owner, and shows nobody else's work. A wrong code is refused *before* the account
is written, so a mistyped code never leaves a child with a half-made account.

Children who are in no class — everyone who signed up before class codes existed,
and anyone who left the box blank — are named on every dashboard under a notice
saying so. Their work is still being recorded; it is simply on nobody's list until
they enter a code. No teacher can pull them in, which is the same rule as above.

---

## What the curriculum is

404 concepts across **two independent curricula**, generated by
`scripts/build_dataset.py` into `data/vocabulary.csv` and then brought up to the
current syllabus by `scripts/upgrade_curriculum.py` and
`scripts/letters_first.py`. Every row carries a `language` column, and a learner
is only ever served, and only ever measured against, the track they chose.

**Both tracks start at the alphabet, and letters are taught alone.** A letter
card used to read "ಅ is for ಅಮ್ಮ" and ask the child to say both, which put a
whole word in front of a child on their very first card, before they could read
a single letter. A letter card now carries the letter, the sound it makes and
nothing else — no example word, and no picture borrowed from one. The words
come afterwards, once every letter is done.

### The Kannada track — 243 concepts, five stages

| stage | | | count | taught as |
|---|---|---|---|---|
| 1 | Letters | Vowels (swaragalu) | 13 | the letter alone |
| 1 | Letters | Consonants (vyanjanagalu) | 32 | the letter alone |
| 2 | Words | Words | 98 | the word, beside its letter's family |
| 2 | Words | Courtesy words | 6 | the word, beside its letter's family |
| 3 | Numbers | Numbers 1–50 | 50 | the number word |
| 4 | Phrases | Two-word phrases | 14 | the whole phrase |
| 5 | Sentences | Complete sentences | 30 | the whole sentence |

**The stages are gated, not merely ordered.** A learner meets every letter
before the first whole word, every word before the first number, every number
before the first phrase. `get_next_concept` sorts candidates by stage before
anything else, so a word can never surface early just because its own letter
happens to be cleared: a child who has done ಹ but not the other 44 letters is
still on letters, not on ಹಸು.

Gating a stage on *mastery* alone would trap a child on one hard letter
forever, so a stage opens on **cleared**, which is mastered *or* parked after
six tries (see "Nobody gets stuck"). Everything the learner sees is stage-aware:
a strip across the top of the card shows the five stages with the ones ahead
locked, and crossing from one to the next is announced rather than passing
silently.

**Stage 2 is taught one letter's family at a time.** Every word sits directly
behind the letter it begins with, and the stage is ordered by that letter in
alphabet order — so a child meets all of ಅ's words together, then all of ಆ's.
Beside the card sits the whole family: the words of this letter they will be
asked for, marked with the one they are on, and below those the extra reading
words for the same letter. The card itself carries the line an alphabet chart
uses — ಅ **is for** ಅಮ್ಮ — which is where that line belongs now that the letter
cards teach the letter alone.

Counting is a stage of its own after the words, ordered one to fifty rather
than by letter, because its order is numeric and has nothing to do with the
alphabet. Phrases and sentences sit behind a content word they are built from —
ನಾನು ಶಾಲೆಗೆ ಹೋಗುತ್ತೇನೆ ("I go to school") only appears once ಶಾಲೆ can be read —
so nothing in them is ever new vocabulary. The skill being practised is reading
known words together.

The sentences tier exists because that is what the measure this project is aimed
at actually asks for: ASER counts a child as literate when they can read a text,
not a word list.

### The Tulu track — 161 concepts, four stages

| stage | | count |
|---|---|---|
| 1 | Letters | Vowels and consonants | 45 |
| 2 | Words | Everyday words | 56 |
| 2 | Words | Courtesy words | 4 |
| 3 | Numbers | Numbers 1–50 | 50 |
| 4 | Phrases | Two-word phrases | 6 |

**Tulu starts at the alphabet too.** Tulu is written in the Kannada script, so
its letters are the same 45 aksharas — but a Tulu learner is not sent to the
Kannada track to get them. They are Tulu concepts of their own (`TV01`–`TV13`,
`TC01`–`TC32`) with their own progress, so a child learning Tulu learns to read
before they are asked to read a word, and their Tulu record is complete on its
own. The prerequisite graph still never crosses languages.

Tulu words are sequenced the same way as Kannada ones: each sits behind the
Tulu letter it begins with, and the stage runs letter by letter in alphabet
order rather than by topic. The word family beside the card is drawn from the
Tulu syllabus itself — `data/letter_words.csv` carries extra reading words for
Kannada only, and no Tulu word is invented to fill the column.

Every Tulu word is derived from a sourced Tulu form on the Kannada word list, so
each is written down in exactly one place and the two cannot drift apart. The 100+
Kannada words with no reliable Tulu source simply produce no Tulu card — a missing
word, never a guessed one. The eight Tulu phrases are marked in the generator as
awaiting native-speaker validation.

218 rows pair a Kannada word with its Tulu equivalent. That pairing is the dataset
this project contributes and the teacher dashboard reads it, but **only one of the
two is ever put in front of a learner.**

#### Tulu is scored by the Kannada recogniser, and it shows

There is no Tulu acoustic model anywhere — the Kannada fine-tune is what scores
this track. On the first ASR pass **every Kannada concept passed and all 14
failures were Tulu**: one- and two-syllable words unlike their Kannada cognates,
with almost nothing for the recogniser to go on (ಕೈ came back as ತಾಯಿ, ಪೆತ್ತ as
ವಿತ್, ಅಪ್ಪೆ as ಪಿ).

They were fixed the same way bare letters were — each was re-measured inside
several frames built only from Tulu words the track already teaches, and the one
that was actually *heard* became its `spoken_form`. ಕೈ is asked for as ಎನ್ನ ಕೈ
("my hand"); the card still teaches the single word.

Four words could not be rescued honestly and now have **no card**: ಎಲೆ (leaf),
ಪೂ (flower), ಏಳ್ (seven) and ಐನ್ (five). Two rescues were rejected despite scoring above the
pass mark, and the reasoning matters more than the result:

- a frame the recogniser passed **by dropping the target word** — "ಕೆಂಪು ಪೂ"
  scores 0.83 while being transcribed as just "ಕೆಂಪು", so a child who said only
  *red* would pass. That is a false accept, and a false accept silently teaches a
  wrong pronunciation;
- anything under **0.75**. Clean TTS is far easier to recognise than a
  six-year-old, so a card sitting 0.02 above the pass mark on synthetic audio is
  already failing in a classroom.

One rescue was also re-done for a subtler reason: ಎನ್ನ ಅಪ್ಪೆ measured 0.86 on one
TTS render and 0.59 on a later one. gTTS is not byte-identical between sessions,
and a frame that is only *sometimes* heard is not a card — ಅಪ್ಪೆ ಬತ್ತೆರ್ holds at
0.84 across renders with the target word audible in the transcript.

The four dropped words keep their place in the `tulu_word` column of the Kannada
rows, so the paired dataset is unchanged — what is gone is four lessons we knew a
child could not pass.

### Why letters are taught on their own

This is the heart of the project.

**A letter card teaches one letter and asks for one letter.** It used to do
neither. The card read "ಅ is for ಅಮ್ಮ", showed a picture of a mother, and the
child had to say both — so a child who could not yet read a single letter met a
whole word on their very first card, and the alphabet and the vocabulary were
taught in the same breath. The words now wait until every letter is done.

That change had to be paid for, because the reason the anchor word was there in
the first place was real:

**A one-phoneme utterance is very hard to recognise.** Measured on this
project's own audio, a bare `ಅ` synthesised alone is 0.2 s long and comes back
as `ಮಾರ್ಕ್`. `ಅ` is the first card in the curriculum, so a child could say it
perfectly and be marked wrong. Initial prompts, hotwords, silence padding and a
temperature sweep were all tried when this was first hit, and all failed.

Two things fix it without putting a word back on the card:

- **A letter is played twice.** Tapping Listen on `ಅ` plays "ಅ, ಅ" — the way a
  teacher says it. One sound on its own is too short for a child to catch, let
  alone a recogniser; two gives both something to work with. `listen_form()` in
  `graph_engine` is the only place this lives, and `validate_asr` measures the
  same audio the child hears.
- **A letter is accepted said once or repeated.** `accepted_forms()` takes `ಅ`
  or `ಅ ಅ`. It no longer takes the example word: taking it would let a child
  pass the card for `ಅ` by saying *amma* without ever saying the letter.

Measured after the change: **13 of 13 vowels and 27 of 27 scored consonants
recognised, in both languages** (`python -m tests.validate_asr --only V`).

#### Five letters the app refuses to mark

Four aspirated stops — `ಛ`, `ಠ`, `ಢ`, `ಧ` — cannot be heard alone at all. They
come back *confidently* as an unrelated word (`ಢ` as ನಂತರ, `ಧ` as ನಾನು), because
a model trained on connected Kannada speech has next to no prior for a bare
aspirate. `ಘ` fails differently: it lands either side of the 0.65 threshold on
the same input, scoring 0.67 once and 0.50 the next time, so it would mark a
child wrong about half the times they said it correctly.

These were invisible before, because the anchor word carried the recognition.
Teaching letters alone exposed them.

The app does not mark them. An attempt on one of the five is a **retry, never a
wrong answer** — the child is told plainly that this is a letter the app cannot
hear and to say it for their teacher instead — and after the usual six tries
they are moved on like any other parked concept. On the teacher's alphabet
chart the five are greyed with a dashed border and read *"the app cannot hear
this letter on its own — listen to this one yourself"*, rather than the red of a
child who is stuck. A coin toss is worse than an honest refusal to judge, and a
chart that blames a child for a limit of the tool is worse than both.

They live in `pronunciation.UNSCOREABLE_ALONE`, and `validate_asr` reports them
separately instead of failing the build on them.

The two-word trick the anchor word used is still how three short Kannada words
(ತಲೆ, ಎಲೆ, ಕೈ) and eight short Tulu ones are made recognisable — they are spoken
in a phrase ("ನನ್ನ ತಲೆ", *my head*). It remains the project's standard answer to
"the recogniser has nothing to go on"; it is just no longer applied to letters.

### One letter, its whole family of words

A letter card teaches the *shape* and the *sound*. It takes a column of words to
show that sound doing its work, which is why no classroom wall chart has ever
shown one word per letter — and why that column now appears in stage two, where
words belong, rather than on the letter card itself.

The word stage runs one letter at a time in alphabet order, and beside the card
sits that letter's whole family: `ಕ` opens ಕಮಲ, ಕಣ್ಣು, ಕಾಗೆ, ಕಪ್ಪು, ಕುದುರೆ, ಕೈ,
ಕಿವಿ, ಕೋಳಿ, ಕಲ್ಲು, ಕುರಿ. The words the child will actually be asked for come
first, with the one they are on marked *you are here*; the extra reading words
follow under a divider, so it is always clear which are being taught and which
are there to be read. The panel does not change while the child works through
the letter — the point is to see the same sound open word after word.

The words the child is asked for come from the syllabus itself, so the panel is
a fact of the prerequisite graph rather than a second list that could drift.
`data/letter_words.csv` supplies the extra reading words on top: 444 words
across all 45 Kannada letters. Thirty-six letters carry the full ten. Three do
not, and that is the language rather than the dataset: ಋ, ಠ and ಢ have eight
apiece because modern written Kannada has few common words that begin with them,
and padding them out would mean inventing vocabulary no child will meet.

The file carries a `language` column and holds Kannada only. A Tulu letter's
panel is drawn from the Tulu syllabus alone, because inventing 450 Tulu words to
fill a column is exactly the kind of guessing the rest of the dataset refuses to
do.

### The pictures are drawn, not photographed

Every card draws itself. `tutor/illustrations.py` holds 242 flat vector
drawings — one object, bold outline, bright fill, nothing else in the frame,
in the shape of the primer charts children actually learn from.

This replaced a Wikimedia Commons image search, and it was not a cosmetic
change. A search API cannot tell the difference between a picture *of* a thing
and a picture *about* a thing:

| card | what the search returned |
|---|---|
| ಘ — ಘಂಟೆ (bell) | a labelled engineering diagram of a bell, numbered 1–10, on black |
| ಗ — ಗಿಡ (sapling) | a mature flowering cherry tree in a Swiss meadow |
| ಭ — ಭೂಮಿ (earth) | a NASA composite of the planet |
| ಯ — ಯಂತ್ರ (machine) | factory plant, no single object in frame |

None of those teaches a five-year-old anything. The drawings are ~1–2 KB each,
stay sharp at any size, need no network, and never need reviewing for licence
or for what happens to be in the background.

Numbers are drawn procedurally: the numeral plus that many counting beads, in
rows of ten past ten, so twenty-four *looks* like two full rows and four —
which is how a wall chart teaches place value. `render("count:24")`.

**A card never shows a photograph.** It used to fall back to the photograph
library for anything not yet drawn, and what came back off the web was not fit
to put in front of a child — the bell arrived as a labelled engineering diagram
on a black ground. Nothing reaches a card now that was not drawn here on
purpose; anything undrawn falls back to a clean typographic card showing the
word itself, which is plain but safe. `validate_dataset` fails the build if a
row that needs a drawing has none, so the fallback stays theoretical: all 359
concepts that take a picture have one.

Letters take no picture at all. The picture on a letter card used to be
borrowed from its example word, which is exactly the mixing of letters and
words that stage one no longer does.

#### One subject in the frame

A review panel looking at the ಅಮ್ಮ (mother) card said they could not tell what
it meant, because a child was standing next to the mother in the picture. They
were right, and the fault was general rather than particular: `mother`,
`father`, `brother` and `sister` were each drawn as an adult with a smaller
figure beside them, which made all four nearly the same picture and none of
them a picture of one thing.

Three rules came out of it, and the drawings now hold to them:

- **One subject to a frame.** Those four are now single figures, told apart by
  height and dress — a sari and bindi, a moustache, a school shirt, a pinafore
  with plaits — rather than by who is standing next to whom.
- **No two letters share a picture.** Three letters (ಓ, ಥ, ಪ) were all showing
  the same book, so the picture said nothing about which letter the card was
  teaching. ಓ took ಓಡು (to run) and ಥ took ರಥ (chariot); all 45 letters now
  carry a distinct drawing.
- **The picture must be the thing, not its category.** `brinjal` and `okra`
  were both a generic green blob; they are now drawn as themselves. `head` and
  `face` were literally the same drawing (`_B["head"] = _B["face"]`) for two
  different words, ತಲೆ and ಮುಖ; the head is now drawn on a neck and shoulders.

`scripts/assign_icons.py` and the letter chart in the tests will tell you if a
letter loses its own picture again.

### Respectful language

The word list is taught to children, so it is held to the register a classroom
would use. Four entries were replaced and one sentence corrected:

| was | now | why |
|---|---|---|
| ದೋಸ್ತಿ *dosti* (Tulu, friend) | ಗೆಳೆಯೆ *geḷeye* | Hindi/Urdu street-slang loan |
| ಹಂದಿ *handi* / ಪಂಜಿ *panji* (pig) | ಎಮ್ಮೆ *emme* / ಎರ್ಮೆ *erme* (buffalo) | in daily use as an insult; the buffalo is also the Kambala animal, so it belongs on a Tulu Nadu word list |
| ಮಂಗ *manga* (monkey) | ಕೋತಿ *kōti* | ಮಂಗ also means "fool" |
| ನನ್ನ ಅಣ್ಣ ಶಾಲೆಗೆ **ಹೋಗುತ್ತಾನೆ** | …**ಹೋಗುತ್ತಾರೆ** | an elder brother takes the honorific verb |

A `courtesy` topic was added in its place — ನಮಸ್ಕಾರ, ದಯವಿಟ್ಟು, ಧನ್ಯವಾದ, ಕ್ಷಮಿಸಿ,
ದಯೆ, ಗೌರವ in Kannada, and ಸೊಲ್ಮೆಲು (the Tulu greeting), ನಮಸ್ಕಾರ, ದಯೆ, ಗೌರವ in
Tulu.

The swaps live in `RESPECTFUL_SWAPS` in `scripts/upgrade_curriculum.py`, each
with its reason, so the decision is reviewable rather than buried in a diff.

### Why ಙ and ಞ are not included

The varnamale lists 34 consonants, but ಙ and ಞ do not occur independently in modern
written Kannada — the anusvara ಂ replaced them. They cannot be spoken alone, cannot
anchor a word, and could never be scored. Including them would only manufacture
cards no child can pass. This is a deliberate curriculum decision.

---

## How pronunciation is scored

1. The browser records the child (`st.audio_input`) and uploads a WAV.
2. The clip is decoded to 16 kHz mono, DC-corrected, and **inspected before it is
   transcribed** — a muted mic, a 0.1 s blip, or a 20-second ramble is bounced back
   as *"I didn't hear you"*, a free retry that is **never counted as a wrong
   answer**. This matters: Whisper does not fail on silence, it *hallucinates*.
3. The clip is trimmed to the spoken word and **normalised** — a soft voice is
   amplified rather than refused. Trimming also makes it several times faster,
   because Whisper re-encodes a fresh 30-second window per seek.
4. `faster-whisper` (a Kannada fine-tune, int8 on CPU) transcribes it.
5. Both the expected and heard text are **romanised** to a common Latin form before
   comparison, because Whisper frequently writes Kannada speech in *Devanagari* —
   comparing raw scripts scores a perfect answer 0.0.
6. Similarity is an indel-normalised Levenshtein ratio, and it must clear **0.65**.

### That 0.65 is measured, not guessed

`python -m scripts.tune_threshold` scores every concept against its own audio
(267 correct answers) and against twelve other concepts' each (3,204 wrong
answers), then sweeps. Re-measured across the whole 267-concept curriculum:

| threshold | accepts correct | accepts **wrong** |
|---|---|---|
| 0.55 | 100% | 3.0% |
| **0.65** | **100%** | **1.1%** |
| 0.70 *(the original guess)* | 96% | 0.7% |

Youden's J peaks at 0.65 (0.989), and 0.65 is the highest value that still accepts
*every* correct pronunciation — at 0.70 the scorer starts marking correctly-spoken
words wrong, which is the failure this project exists to remove. Every step below
0.65 buys nothing in return and lets through more genuinely wrong pronunciations,
and a false accept silently teaches a child the wrong sound.

The same run doubles as proof that **every card is passable**: all 267 concepts
score at or above 0.65 against their own audio, so there is no card on which a
child pronouncing the word perfectly would be marked wrong.

> **This measurement predates the current curriculum.** It was run against the
> 267 concepts that existed at the time. The 92 rows added since — numbers 11–50
> in both languages, and the courtesy words — have **not** been through
> `tune_threshold` or `validate_asr`. Re-run both before relying on the scorer
> for them:
>
> ```bash
> python -m scripts.tune_threshold
> python -m tests.validate_asr
> ```
>
> Long Kannada number words (ಇಪ್ಪತ್ತೊಂಬತ್ತು) give the recogniser far more to work
> with than a bare vowel does, so they are the *easy* end of the range — but that
> is a prediction, not a measurement, and it is not stated here as one.

### A word it could not make out is never a wrong answer

Clearing the microphone gate only proves a sound *arrived*. It does not prove the
recogniser understood it. So a non-match is interrogated before it is allowed to
count. The recogniser reports its own certainty per clip (`avg_logprob`,
`no_speech_prob`), and measured on this corpus those separate cleanly:

| the clip | avg_logprob | verdict |
|---|---|---|
| a word it heard — **right or wrong** | −0.00 … −0.17 | confident |
| a clip it could not make out | −0.25 … −0.56 | guessing |

The recogniser also has a **filler** it emits for silence — this model answers an
empty clip with `ಮುಕ್ತಾಯ` ("the end") at a confident-looking log-probability. That
specific output is recognised and treated as "we heard nothing", never as a wrong
word.

Every scored attempt resolves to one of four outcomes, and only the last one costs
a mark:

| outcome | meaning |
|---|---|
| **correct** | matched — logged, mastery updated, the child advances |
| **retry** | unusable capture, the recogniser was guessing, or a concept it cannot score at all — free |
| **soft** | a confident non-match, still inside the grace window — free |
| **wrong** | a confident non-match that keeps happening — logged |

The grace window exists because on real-world audio the recogniser will
occasionally, and confidently, mis-transcribe a correctly-spoken word. What
separates "correct word, mis-heard once" from "a different word" is repetition: a
child saying the right word lands a clean decode within a couple of tries. So the
first two confident non-matches on a concept are free, and only after that does a
miss become a logged wrong answer. This never causes a false *accept* — nothing
below 0.65 is ever accepted.

---

## Nobody gets stuck

If a child cannot master a concept — an unusual voice, a poor microphone, a word
this model happens to mishear — they are **moved on after 6 attempts**, and the
concept is flagged to the teacher under *Needs help*. It is **not** counted as
mastered, so the scores stay honest.

Without this the tutor traps them: `get_next_concept()` always returns the lowest
unmastered concept that is ready, so an unpassable one is served forever and the
rest of the curriculum is unreachable. `tests/test_graph.py` has a regression test
that drives a learner who answers *everything* wrong and asserts they still progress.

### The lock is currently off

**This build ships with the prerequisite lock lifted.** `UNLOCK_ALL` in
`tutor/config.py` defaults to `True`, which turns the lesson loop into a browser:
the card gains **Back** and **Next** arrows and a box that jumps straight to any
of the 243 Kannada or 161 Tulu concepts, whether or not it has been earned. The
stage strip stops greying stages out, because with the lock off "locked" is
simply untrue, and a banner across the top of the card says the lock is lifted —
otherwise a child could be looking at a sentence on their first morning and
nobody would know why.

Nothing else changes. Speaking a card still scores it and still writes mastery,
so anything practised while browsing counts normally.

**To put the lock back**, change that one default to `False`:

```python
UNLOCK_ALL = _flag("TUTOR_UNLOCK_ALL", default=False)
```

The arrows, the jump box and the banner all hang off that flag and go with it,
and a session that was open at the time is pulled back to the card the learner
had actually reached rather than being left standing in a sentence. `TUTOR_UNLOCK_ALL=off`
does the same thing for a single run. `browse_mode_tests` in `tests/test_app_boot.py`
covers both directions — every concept reachable with the flag on, gate and
banner gone with it off — and the rest of the suite runs locked, because the
lock is what a classroom actually gets.

## How progress is measured

Mastery is a **recency-weighted moving average** rather than a running total:

```
new_score = (1 - alpha) * old_score + alpha * target     alpha = 0.75, target = 1.0 or 0.0
```

A concept counts as mastered at **0.7**. The weighting is deliberately reactive —
these are short classroom sessions, and a cumulative average would keep punishing a
child for their first fumbling attempts long after they had improved. Every attempt
is also written to a history table with its match score, its timestamp, and what the
recogniser actually heard.

---

## The teacher dashboard

The dashboard is read-only over the same database — no recogniser involved.

**It shows one teacher's class and nobody else's.** The roster, the four metrics,
*What the class finds hardest* and the daily trend are all computed over the
children who joined *this* teacher's class code (see *Which teacher gets which
child*); `get_attempts()` and `get_concept_stats()` take the class's student ids
and filter on them in SQL. An empty class matches nothing rather than everything —
`IN ()` is not valid SQL, so it becomes a false clause. `test_app_teacher` runs two
teachers side by side and asserts neither sees the other's child or class code.

### It is written for a teacher, not for an analyst

The dashboard used to lead with a **NetworkX diagram**: a few hundred coloured dots
laid out left-to-right by prerequisite depth, unlabelled, because labelling them
turned it into a smear. Reading it required already knowing what a directed acyclic
graph is — and even a correct reading could not tell you *which letter* a child was
stuck on, because the dots had no names. For a teacher in a village primary school
it was decoration.

It has been replaced by two things that need no explaining, both in
`tutor/insight.py`:

**The varnamale chart.** The alphabet, laid out the way it already is on the
classroom wall, each letter printed with its romanization and coloured by how that
child is doing on it — green *learned*, amber *practising*, red *stuck*, grey *not
started*. A teacher points at a red cell and knows both which letter it is and that
this child needs help with it.

**Findings.** Short sentences with the child's name and the word in them:

> · Ravi has learned 45 of 45 letters of the alphabet and 7 of 108 whole words.
> There are 2 more stages after that.
> · Ravi has tried ಬೆಕ್ಕು ('cat') 2 times and still not got it.
> → Sit with Ravi on ಬೆಕ್ಕು — say it together a few times, then let them try the
> microphone again.
> · Next lesson: ಬೆಕ್ಕು (bekku — cat).

Every finding is derived from the same progress rows the tables below it are built
from, so a sentence and the number it came from can never disagree.

**Across the class**

- **What needs you today** — findings first: who has not started, who has not
  practised in a week, who is stuck on the most, and what the class as a whole keeps
  missing.
- Children, things practised, average progress, and how many have been inactive for
  a week or more.
- A roster of every child with progress, **needs-help** and **moved-on** counts,
  attempts and days idle — sorted so the children in trouble come first. Each child
  is counted out of **the curriculum they are actually learning**, so a Tulu learner
  is not measured against the Kannada total.
- **What the class finds hardest**, aggregated across children. This is the view that
  separates *one child is stuck* from *this lesson needs reteaching*, which no
  per-child page can answer. Filterable to things at least two children have tried.
- **The class over time** — practice per day, accuracy per day, and a running total
  of things learned.
- One-click CSV export of the whole class.

**For one child**

- **What they need** — the findings above, for this child.
- Learned / tried / stuck-on counts.
- **The alphabet chart**, coloured in.
- **Words by topic** — labelled bars, the topics they have started and are furthest
  behind on at the top. "Animals 3 of 18" is a fact a teacher can turn into a lesson;
  "42 of 197" is not.
- **Stuck on these** — tried at least twice and still not got it, with the ones the
  tutor has moved on marked.
- **What they actually said** — non-matching attempts grouped by what the recogniser
  heard, most repeated first. A form that keeps coming back for one word is a real,
  repeatable mispronunciation worth correcting directly.
- A curriculum picker (a child who switched tracks has history on both), the full
  concept list and attempt history behind expanders, and a per-child CSV export.

---

## Nothing on screen is silently busy

Streamlit blocks the whole page while a callback runs, and a blocked page looks
exactly like a crashed one. Every boundary that can take a visible moment shows a
spinner with a running clock — `ui.loading()`, one helper, so the wording and the
counter stay the same everywhere:

| What is being waited for | How long it can take |
|---|---|
| Building the curriculum on first boot | ~0.8 s, once per process — and only then; the spinner is skipped on every rerun after it |
| **Listen**, on a word not yet cached | a network round trip to gTTS; after the first play it is served off disk |
| Waking the speech recogniser | tens of seconds on a cold start, first time only |
| Scoring a recording | a second or two |
| Signing in, creating an account, joining a class | a deliberate scrypt hash, plus the write |
| Adding up a class, or one child's progress | one graph walk per child — it shows with a full class |
| Drawing the lesson plan | lays out every concept in the track |

The counter is the point: a spinner with no clock is indistinguishable from a
frozen tab after about two seconds, and the two slowest things here are well past
that.

---

## Running the checks

```bash
python run_tests.py            # fast suite: scorer, accounts, graph, boot, access
python run_tests.py --full     # + re-verify the recogniser can hear every card
```

| script | what it protects |
|---|---|
| `tests/validate_dataset.py` | structure: duplicate ids, dangling/cyclic prerequisites |
| `tests/validate_asr.py` | **that every card is passable** — speaks each concept and scores it |
| `scripts/tune_threshold.py` | the pass mark, from measured true/false accept rates |
| `tests/test_pronunciation.py` | cross-script matching, the mic gate, the confidence gate, the grace rule |
| `tests/test_graph.py` | curriculum order, and that a failing learner is never trapped |
| `tests/test_app_boot.py` | the whole journey: landing -> account -> flashcard; **no emoji** |
| `tests/test_auth.py` | passwords are unrecoverable from the DB; the teacher PIN is enforced |
| `tests/test_app_teacher.py` | a student cannot reach the dashboard — *even by forging the session* |
| `tests/validate_mic.py` | **that a quiet child is still heard** — every concept, through simulated mics |

`validate_asr.py` is the important one. A structurally valid dataset can still
contain cards no child can ever pass, and that is invisible until you speak every
one of them.

`validate_mic.py` is the second. The microphone gate keys on **signal-to-noise**,
not on absolute level, because level is a fact about mic gain and distance rather
than about whether a child spoke. It replays every concept through simulated
microphones and is the only check that can catch that class of injustice:

Measured over the corpus at the time the gate was rewritten:

| microphone | accepted | scored correct |
|---|---|---|
| normal voice, quiet room | 100% | 98.3% |
| soft voice, quiet room | 100% | 97.5% |
| faint voice, quiet room | 100% | 94.2% |
| no voice, noisy room | 0% | — |
| mic muted | 0% | — |

The faint row is the point: a peak-level threshold rejected **all** of it, while the
recogniser transcribes it perfectly.

---

## Regenerating the data

```bash
python -m scripts.build_dataset               # curriculum -> data/vocabulary.csv
python -m scripts.upgrade_curriculum          # numbers 1-50, courtesy words, respectful swaps
python -m scripts.letters_first               # alphabet first, in both languages
python -m scripts.assign_icons                # give every row its drawing
python -m tests.validate_asr                  # also fills the offline audio cache
```

`upgrade_curriculum`, `letters_first` and `assign_icons` are all idempotent —
run them twice and the file does not change. Run them in that order after any
edit to the curriculum; `assign_icons` fails loudly, naming the row, if a
concept ends up with no drawing.

The photograph fetcher is still here and still works, but nothing needs it now:

```bash
python -m scripts.fetch_images                # pictures (free licences only)
python -m scripts.fetch_images --contact-sheet  # LOOK at them before you ship them
```

**Look at the contact sheet.** A search API will hand you a blue whale for "mother",
a heron for "mouse", and a piece of milk-glass tableware for "milk" — all three
actually happened here. Every image is reviewed, and the ones that needed steering
are named explicitly in `scripts/fetch_images.py`.

That reasoning is why **every** card is now drawn locally rather than fetched —
see "The pictures are drawn, not photographed" above. What began as an exception
for colours and numbers turned out to be the right rule for the whole deck.

To review the drawings, render them to a contact sheet and *look at them*:

```bash
python -c "from tutor import illustrations as i; print(len(i.ICONS))"
```

Spoken audio is generated with gTTS on first use and cached at
`data/audio/{concept_id}_{hash}.mp3`. The filename carries a hash of the text, so
editing a word in the CSV invalidates its old audio automatically — otherwise a
child would keep hearing the previous word while being scored against the new one.
The cache is regenerable and is not kept in the repository.

---

## Deploying

### An account does not follow you to another machine

**Known limitation.** Accounts and progress live in one SQLite file,
`data/tutor.db`, on the machine the app is running on. It is gitignored, so it is
never pushed and never pulled.

That has a consequence worth stating plainly, because it reads as a login bug:

> If two devices each run `streamlit run app.py`, they each have their **own**
> database. An account created on one **does not exist** on the other, so signing
> in there fails with *Incorrect username or password* — which is accurate. The
> account is not broken; it is not there. The same applies to teacher accounts and
> to class codes: a code minted on one laptop matches no class on another.

There are three ways this bites, and one of them is data loss:

| How it is run | What happens |
|---|---|
| `streamlit run` on each device | Separate databases. Accounts, progress and class codes do not cross. |
| One deployed URL (Streamlit Community Cloud) | Everyone shares the container's database — until the container restarts or redeploys, which **wipes it**, because `data/tutor.db` is gitignored and is not in the image. |
| Docker without a volume | The database dies with the container. Mount one: `-v tutor-data:/app/data`. |

**The fix is a database that lives outside the machine** — a hosted Postgres
(Neon, Supabase) or a hosted SQLite (Turso/libSQL) behind `TUTOR_DB_PATH`'s
replacement — so that every device talks to the same store. That work is not done
here: `tutor/db.py` and `tutor/auth.py` both open `sqlite3` connections directly,
and moving them behind one connection layer is the change that has to happen
first. Until then, **run the app in one place and have everyone open that URL**,
over HTTPS so the microphone works.

**Set the teacher PIN.** A default PIN on a public URL is the same as no PIN, and
the app warns you on the teacher screen until you change it.

- Environment: `TUTOR_TEACHER_PIN=…`
- Streamlit Community Cloud (which cannot set env vars): put it in
  **Settings -> Secrets** as `TUTOR_TEACHER_PIN = "…"`.

### Streamlit Community Cloud (free)

Push to GitHub and point Streamlit Cloud at `app.py`. `packages.txt` installs
`ffmpeg` and `libgomp1`, which the recogniser needs. `models/` is gitignored (too
big for GitHub), so the app downloads the model on first boot.

### Docker (free, and works offline)

```bash
docker build -t kannada-tutor .
docker run -p 8501:8501 -e TUTOR_TEACHER_PIN=<pin> -v tutor-data:/app/data kannada-tutor
```

The build caches the speech model inside the image, so the container needs no
network at run time. It pulls the already-converted CTranslate2 build rather than
running `scripts/convert_model.py`, which would drag `transformers` and `torch`
into the image for the same result. If that pull fails the build still succeeds
and the app fetches the model on first use instead.

For the Listen button to work offline too, run `python -m tests.validate_asr`
before building: it fills `data/audio/` with a clip for every concept, and the
build copies that cache in. Without it the first play of each word needs the
network once.

`.dockerignore` keeps `data/tutor.db` and `.streamlit/secrets.toml` out of the
image — children's names and your teacher PIN must not be baked into something
you push to a registry.

Mount a volume on `/app/data` or the children's progress dies with the
container.

### The microphone needs HTTPS

Browsers only expose the mic on a **secure origin**. `http://localhost` counts as
secure, so local runs are fine. **Any other host must be served over HTTPS** or the
mic button simply will not appear. Streamlit Cloud gives you HTTPS; a self-hosted
deploy needs a TLS reverse proxy (Caddy, or nginx with Let's Encrypt — both free).

Privacy-hardened browsers can interfere with microphone capture: shields or
fingerprinting protection that alter the Web Audio API affect the recording the page
uploads. If recordings arrive silent, lower the browser's shields for the site.

---

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `TUTOR_TEACHER_PIN` | `1234` | Secret required to *create* a teacher account. **Change it.** |
| `TUTOR_DB_PATH` | `data/tutor.db` | Where learner progress is stored. |
| `TUTOR_WHISPER_MODEL` | *(auto)* | Override the speech model (size, Hub id, or path). |
| `TUTOR_MIC_GATE` | *on* | Set to `off` to bypass the microphone quality gate. |
| `TUTOR_SKIP_WARMUP` | *(unset)* | Skip loading the model at boot (used by the tests). |
| `TUTOR_UNLOCK_ALL` | ***on*** | **Testing.** Lifts the prerequisite lock — see *The lock is currently off*. Set to `off` to put it back. |
| `TUTOR_CONTACT` | *(unset)* | Your email/URL, sent to Wikimedia when fetching images. |

Everything else lives in `.streamlit/config.toml`: the theme, the 5 MB upload cap
that bounds a recording, and the error-detail setting described under *Data and
privacy*.

---

## How it fits together

```
app.py              Streamlit entry point  (streamlit run app.py)
run_tests.py        the check runner
tutor/              the application package
scripts/            one-off data prep + tuning  (python -m scripts.<name>)
tests/              tests and validators       (python -m tests.<name>)
data/               vocabulary.csv, letter_words.csv, images, cached audio, tutor.db
models/             the offline Kannada speech model
Dockerfile          the offline container build
.dockerignore       keeps tutor.db and secrets out of the image
```

**The source carries no explanatory comments** (the drawing library keeps a handful of one-word labels naming which shape is which limb, because raw SVG coordinates are otherwise unnavigable). This README is the documentation, and the
reasoning that would otherwise sit in a docstring is written up here, next to the
measurement that settled it — why letters are taught with an anchor word, why the
pass mark is 0.65 and not 0.55, why a clip the recogniser could not make out is
never a wrong answer, why the dashboard is sentences instead of a graph. The test
names carry the rest: each one states the behaviour it protects.

| Module | Responsibility |
|---|---|
| `app.py` | Streamlit UI: landing, the two sign-in doors, student flashcard loop, teacher dashboard |
| `tutor/ui.py` | The design system — flat, ink-only, phone-first, no gradients, blur or emoji |
| `tutor/insight.py` | Turns progress data into the sentences and charts the teacher reads |
| `tutor/auth.py` | Accounts: scrypt password hashing, roles, rate limiting |
| `tutor/graph_engine.py` | The two curricula, sequencing per language, and the no-trap parking rule |
| `tutor/pronunciation.py` | Speech recognition, romanisation, scoring, and the microphone gate |
| `tutor/db.py` | SQLite: students, mastery (EMA), attempt history, class aggregates |
| `tutor/media.py` | Text-to-speech (cached) and image resolution |
| `tutor/illustrations.py` | The 240 flat card drawings, and the procedural counting cards |
| `tutor/cogmap.py` | Lays out the prerequisite graph for the structural view at the foot of a child's page |
| `tutor/config.py` | The teacher registration PIN, from env or Streamlit secrets |
| `scripts/build_dataset.py` | **The curriculum itself** — generates `data/vocabulary.csv` |
| `scripts/upgrade_curriculum.py` | Numbers to 50, courtesy words, and the respectful-language swaps |
| `scripts/letters_first.py` | Letters taught alone, the Tulu alphabet, every word behind its letter, counting on its own |
| `scripts/assign_icons.py` | Gives every curriculum row its drawing |
| `scripts/fetch_images.py` | Free-licensed pictures + attribution, and locally drawn cards |
| `scripts/convert_model.py` | Builds the offline Kannada speech model |

`tutor/` is a package so the teaching code is importable as one unit and cannot be
confused with the throwaway scripts that generated the data. Scripts and tests are
run as modules from the root (`python -m scripts.build_dataset`) so that
`from tutor import …` resolves and `./data` still points where they expect.

### The stack

| Layer | What |
|---|---|
| Interface | Streamlit |
| Speech recognition | faster-whisper on CTranslate2 (int8, CPU), running a Kannada fine-tune of Whisper-small from Speech Lab, IIT Madras |
| Audio decoding | PyAV, with NumPy for the level analysis |
| Curriculum | NetworkX — a directed acyclic graph, validated acyclic at load |
| Scoring | RapidFuzz (indel-normalised Levenshtein) over IAST-romanised text |
| Romanisation | indic-transliteration |
| Storage | SQLite, via the standard library |
| Speech synthesis | gTTS, cached to disk |
| Images | Pillow |

The only neural model in the application is Whisper, used purely for inference and
run entirely on the local CPU. Everything else is classical: graph traversal, edit
distance, a moving average, and a key-derivation function.

---

## Data and privacy

`data/tutor.db` holds **real children's names and scores**. It is in `.gitignore`
and in `.dockerignore`, so it is neither committed nor baked into a container
image. Keep it that way, and mount it as a volume instead.

Speech is recognised on the machine running the app. No recording of a child's voice
is ever sent anywhere.

`.streamlit/config.toml` sets `client.showErrorDetails = "none"`, so an uncaught
error shows a short generic message instead of a Python traceback with server
paths in it. The real error still goes to the server log. While developing,
override it: `streamlit run app.py --client.showErrorDetails=full`.

(The obvious-looking `showErrorDetails = false` does **not** do this. Streamlit
keeps `false` as a legacy value meaning *stacktrace*, so it hides the message and
then prints the traceback anyway.)
