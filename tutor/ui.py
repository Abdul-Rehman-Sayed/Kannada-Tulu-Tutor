"""
ui.py — the design system.

Everything visual lives here so app.py can stay about teaching.

The look is deliberately plain: a flat near-white page, white cards separated by
hairline borders, one accent colour, and type doing most of the work. There are
no gradients, no blur, no glass, and no emoji anywhere in the interface.

Three rules this follows.

1. No gradients. A gradient headline, a gradient button and a gradient icon tile
   are decoration standing in for hierarchy. Rank is carried by size, weight and
   space instead, and colour is spent only where it means something: the primary
   action, the focus ring, and the pass/fail of an answer.

2. It does not fake any control. Every button, field and recorder on screen is a
   real Streamlit widget that has been restyled — there is no decorative HTML
   pretending to be interactive. A child tapping something that only looks like a
   button is a bug, not a design.

3. Inputs are styled on their CONTAINER, never on the bare <input>. Streamlit
   wraps a field and its trailing controls (the password reveal eye) together in
   one [data-baseweb="input"] box. Bordering the inner <input> alone leaves that
   eye button stranded outside the field — which is exactly how the sign-up form
   came to look broken.

Streamlit chrome (toolbar, Deploy, menu) is removed in .streamlit/config.toml,
not here: data-testid names change between releases, and a stylesheet that hides
the Deploy button is one upgrade away from it reappearing over a flashcard.
"""

import streamlit as st

# One accent, used sparingly. Everything else is neutral.
ACCENT = "#4F46E5"

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Kannada:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,0,0&display=block');
.material-symbols-rounded{{
  font-family:'Material Symbols Rounded';
  font-weight:normal; font-style:normal; line-height:1;
  letter-spacing:normal; text-transform:none; display:inline-block;
  white-space:nowrap; word-wrap:normal; direction:ltr;
  -webkit-font-feature-settings:'liga'; -webkit-font-smoothing:antialiased;
}}

:root{{
  --accent:{ACCENT};
  --accent-hover:#4338CA;
  --accent-soft:#F5F5FF;
  --accent-line:#E0E0FA;
  --accent-ring:rgba(79,70,229,.16);

  --ink:#111827;      /* headings */
  --body:#374151;     /* body copy */
  --muted:#6B7280;    /* secondary */
  --faint:#9CA3AF;    /* tertiary */

  --bg:#FAFAFA;
  --surface:#FFFFFF;
  --line:#E5E7EB;
  --line-strong:#D1D5DB;

  --r:10px; --r-sm:8px;
  --ease:cubic-bezier(.22,.61,.36,1);
  --dur:.15s;

  --ok:#047857;   --ok-bg:#ECFDF5;   --ok-brd:#A7F3D0;
  --no:#B91C1C;   --no-bg:#FEF2F2;   --no-brd:#FECACA;
  --warn:#92400E; --warn-bg:#FFFBEB; --warn-brd:#FDE68A;
}}

.stApp{{ background:var(--bg); }}

html,body,[class*="css"],.stMarkdown,button,input,textarea,select{{
  font-family:'Inter',system-ui,-apple-system,'Segoe UI',sans-serif;
  color:var(--body);
  -webkit-font-smoothing:antialiased;
}}
/* Kannada must never fall back to a Latin face — it renders as tofu boxes. */
.kn{{ font-family:'Noto Sans Kannada','Nirmala UI','Tunga',sans-serif; }}

/* Layout: full-bleed by default (Streamlit's centred column wastes half a
   classroom projector). The reading measure is restored per-view via narrow(). */
.stMainBlockContainer,.block-container{{
  padding:2.4rem 2.4rem 5rem !important;
  max-width:none !important;
}}
@media (max-width:900px){{
  .stMainBlockContainer,.block-container{{ padding:1.6rem 1.4rem 4.5rem !important; }}
}}
@media (max-width:640px){{
  .stMainBlockContainer,.block-container{{ padding:1.2rem 1rem 4rem !important; }}
}}

h1,h2,h3,h4{{ color:var(--ink); letter-spacing:-.018em; font-weight:600; }}

/* Card: the one surface. A hairline border, no shadow, no blur. */
.card{{
  background:var(--surface);
  border:1px solid var(--line);
  border-radius:var(--r);
}}

/* Hero. */
.hero{{ text-align:center; padding:clamp(28px,5vw,44px) clamp(20px,4vw,36px); }}
.hero .eyebrow{{
  display:inline-block; margin-bottom:16px;
  color:var(--muted); font-size:11.5px; font-weight:600;
  letter-spacing:.12em; text-transform:uppercase;
}}
.hero h1{{
  font-size:clamp(28px,5vw,42px); font-weight:600; line-height:1.15;
  margin:0 0 14px; letter-spacing:-.025em; color:var(--ink);
}}
.hero .lede{{
  font-size:clamp(14.5px,1.6vw,16.5px); line-height:1.65; color:var(--muted);
  max-width:58ch; margin:0 auto;
}}
.hero .script{{
  font-size:clamp(26px,4.5vw,36px); margin:20px 0 6px; color:var(--ink);
  font-weight:500; letter-spacing:.14em;
}}

/* Panels. */
.panel{{ padding:clamp(18px,2.5vw,26px); }}
.panel-tight{{ padding:clamp(14px,2vw,18px); }}

.feature{{ padding:22px; height:100%; }}
.feature .ico{{
  width:36px;height:36px;border-radius:var(--r-sm);display:grid;place-items:center;
  margin-bottom:14px; color:var(--accent); background:var(--accent-soft);
  border:1px solid var(--accent-line);
}}
.feature .ico .material-symbols-rounded{{ font-size:20px; }}
.feature h3{{ font-size:15px; margin:0 0 6px; font-weight:600; color:var(--ink); }}
.feature p{{ font-size:13.5px; line-height:1.6; color:var(--muted); margin:0; }}

.stat{{ text-align:center; padding:18px 12px; }}
.stat .n{{ font-size:clamp(22px,3vw,28px); font-weight:600; letter-spacing:-.02em;
  color:var(--ink); }}
.stat .l{{ font-size:11px; color:var(--faint); text-transform:uppercase;
  letter-spacing:.08em; font-weight:600; margin-top:4px; }}

/* Flashcard. */
.word-card{{ padding:clamp(20px,3vw,30px); text-align:center; }}
.kannada-word{{
  font-size:clamp(56px,14vw,104px); font-weight:500; line-height:1.15;
  color:var(--ink); margin:0 0 8px; word-break:break-word;
}}
.translit{{ font-size:clamp(16px,3vw,20px); color:var(--accent); font-weight:600; margin:0; }}
.meaning{{ font-size:clamp(14px,2.6vw,16px); color:var(--muted); margin:6px 0 0; }}
.tulu{{
  font-size:clamp(12.5px,2.4vw,14px); color:var(--muted); margin:16px 0 0;
  padding-top:14px; border-top:1px solid var(--line);
}}
.tulu b{{ color:var(--body); font-weight:600; }}

.badges{{ margin-top:16px; display:flex; gap:6px; justify-content:center; flex-wrap:wrap; }}
.badge{{
  padding:4px 10px; border-radius:999px; font-size:11.5px; font-weight:500;
  border:1px solid var(--line); background:var(--surface); color:var(--muted);
}}
.badge-cat{{ color:var(--accent); background:var(--accent-soft);
  border-color:var(--accent-line); }}
.badge-diff{{ color:var(--muted); }}

/* The single most important instruction on the page: what to actually say. */
.say-box{{
  margin-top:18px; padding:16px 20px; border-radius:var(--r-sm); text-align:center;
  background:var(--accent-soft); border:1px solid var(--accent-line);
}}
.say-box .lbl{{
  font-size:11px; font-weight:600; letter-spacing:.1em; text-transform:uppercase;
  color:var(--accent); margin:0 0 6px;
}}
.say-box .val{{ font-size:clamp(22px,4.6vw,30px); font-weight:500; color:var(--ink); }}
.say-box .hint{{ font-size:12.5px; color:var(--muted); margin-top:6px; }}

/* Feedback. */
.fb{{ padding:14px 18px; border-radius:var(--r-sm); text-align:center; margin-bottom:10px; }}
.fb .hd{{ font-size:clamp(15px,2.6vw,17px); font-weight:600; }}
.fb .sub{{ font-size:12.5px; font-weight:400; margin-top:4px; opacity:.9; }}
.fb-ok{{ background:var(--ok-bg); border:1px solid var(--ok-brd); color:var(--ok); }}
.fb-no{{ background:var(--no-bg); border:1px solid var(--no-brd); color:var(--no); }}
.fb-warn{{ background:var(--warn-bg); border:1px solid var(--warn-brd); color:var(--warn); }}
.meter{{ height:4px; border-radius:999px; background:rgba(0,0,0,.07);
  margin-top:12px; overflow:hidden; }}
.meter > i{{ display:block; height:100%; border-radius:999px; background:currentColor; }}

/* Buttons. Flat: a solid accent for the one real action, white for the rest. */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button{{
  border-radius:var(--r-sm) !important; font-weight:500 !important; min-height:44px;
  background:var(--surface) !important;
  border:1px solid var(--line-strong) !important;
  color:var(--ink) !important;
  box-shadow:none !important;
  transition:background var(--dur) var(--ease), border-color var(--dur) var(--ease) !important;
}}
.stButton > button:hover, .stDownloadButton > button:hover,
.stFormSubmitButton > button:hover{{
  background:#F9FAFB !important; border-color:var(--faint) !important;
  color:var(--ink) !important;
}}
.stButton > button:focus-visible, .stDownloadButton > button:focus-visible,
.stFormSubmitButton > button:focus-visible{{
  outline:none !important; border-color:var(--accent) !important;
  box-shadow:0 0 0 3px var(--accent-ring) !important;
}}

/* The one real action. Matched with a PREFIX selector on purpose: a plain button
   is kind="primary", but a form's submit button is kind="primaryFormSubmit" — an
   exact match silently leaves every form's main button looking secondary, which
   is what made "Create account" render as a plain white box. */
.stButton > button[kind^="primary"],
.stFormSubmitButton > button[kind^="primary"]{{
  background:var(--accent) !important;
  border:1px solid var(--accent) !important;
  color:#fff !important;
}}
.stButton > button[kind^="primary"]:hover,
.stFormSubmitButton > button[kind^="primary"]:hover{{
  background:var(--accent-hover) !important; border-color:var(--accent-hover) !important;
  color:#fff !important;
}}
.stButton > button[kind^="primary"] p,
.stFormSubmitButton > button[kind^="primary"] p{{ color:#fff !important; }}

/* Inputs.
   The border goes on the BaseWeb CONTAINER, which holds the field AND its
   trailing controls. Bordering the inner <input> instead is what left the
   password reveal button sitting outside the box. The inner input is then made
   transparent so only one box is ever drawn. */
div[data-baseweb="input"],
.stSelectbox div[data-baseweb="select"] > div{{
  background:var(--surface) !important;
  border:1px solid var(--line-strong) !important;
  border-radius:var(--r-sm) !important;
  box-shadow:none !important;
  min-height:44px;
  overflow:hidden;
  transition:border-color var(--dur) var(--ease), box-shadow var(--dur) var(--ease);
}}
div[data-baseweb="input"]:focus-within,
.stSelectbox div[data-baseweb="select"] > div:focus-within{{
  border-color:var(--accent) !important;
  box-shadow:0 0 0 3px var(--accent-ring) !important;
}}
div[data-baseweb="input"] div[data-baseweb="base-input"],
div[data-baseweb="base-input"]{{
  background:transparent !important; border:none !important; box-shadow:none !important;
}}
div[data-baseweb="input"] input, .stTextInput input, .stNumberInput input, textarea{{
  background:transparent !important;
  border:none !important;
  box-shadow:none !important;
  color:var(--ink) !important;
}}
/* The password reveal sits inside the field's border — it is not a second box. */
div[data-baseweb="input"] button{{
  background:transparent !important; border:none !important; box-shadow:none !important;
  color:var(--muted) !important;
}}
/* Streamlit prints "Press Enter to submit form" on top of what the user typed.
   Every form here has a visible submit button, so the hint is only clutter. */
[data-testid="InputInstructions"]{{ display:none !important; }}

[data-testid="stForm"]{{
  background:transparent !important; border:none !important; padding:0 !important;
}}

/* The recorder — the thing the whole app is for. */
[data-testid="stAudioInput"]{{
  background:var(--surface) !important;
  border:1px solid var(--line) !important;
  border-radius:var(--r-sm) !important;
  box-shadow:none !important;
}}
[data-testid="stAudio"] audio{{ width:100%; }}
[data-testid="stImage"] img{{ border-radius:var(--r-sm); }}

/* Tabs: a quiet underline, not a pill. */
.stTabs [data-baseweb="tab-list"]{{
  gap:20px; background:transparent; padding:0;
  border-bottom:1px solid var(--line); flex-wrap:wrap;
}}
.stTabs [data-baseweb="tab"]{{
  background:transparent !important; padding:10px 2px; font-weight:500;
  color:var(--muted); border-bottom:2px solid transparent; margin-bottom:-1px;
  transition:color var(--dur) var(--ease), border-color var(--dur) var(--ease);
}}
.stTabs [aria-selected="true"]{{
  color:var(--ink) !important; border-bottom-color:var(--accent);
}}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"]{{ display:none; }}

/* Metrics + tables. */
[data-testid="stMetric"]{{
  background:var(--surface); border:1px solid var(--line);
  border-radius:var(--r); padding:16px 18px;
}}
[data-testid="stMetricValue"]{{ color:var(--ink); font-weight:600; }}
[data-testid="stDataFrame"]{{
  border-radius:var(--r-sm); overflow:hidden; border:1px solid var(--line);
}}
[data-testid="stExpander"] details{{
  background:var(--surface); border:1px solid var(--line) !important;
  border-radius:var(--r-sm) !important;
}}

/* Progress. */
.stProgress > div > div > div > div{{ background:var(--accent) !important; }}
.stProgress > div > div > div{{ background:rgba(0,0,0,.07) !important; }}

/* Alerts. */
[data-testid="stAlert"]{{ border-radius:var(--r-sm); border:1px solid var(--line); }}

/* Sidebar. */
[data-testid="stSidebar"]{{
  background:var(--surface) !important;
  border-right:1px solid var(--line);
}}
.sb-brand{{ font-weight:600; font-size:15px; letter-spacing:-.01em; color:var(--ink); }}
.sb-sub{{ color:var(--faint); font-size:11px; margin-top:2px;
  letter-spacing:.08em; text-transform:uppercase; font-weight:500; }}
.learner{{
  background:var(--accent-soft); border:1px solid var(--accent-line);
  border-radius:var(--r-sm); padding:12px 14px; margin:8px 0 12px;
}}
.learner .rl{{ font-size:10px; color:var(--muted); text-transform:uppercase;
  letter-spacing:.08em; font-weight:600; }}
.learner .nm{{ font-weight:600; color:var(--ink); font-size:15px; margin-top:2px; }}

/* Footnotes. */
.tiny{{ font-size:12px; color:var(--faint); text-align:center; }}
.divider{{ height:1px; background:var(--line); margin:28px 0; }}

@media (max-width:640px){{
  .kannada-word{{ font-size:clamp(52px,20vw,80px); }}
  .stButton > button, .stFormSubmitButton > button{{ min-height:46px; }}
}}

/* Respect a user who has asked the OS for less motion. */
@media (prefers-reduced-motion:reduce){{
  *{{ transition:none !important; animation:none !important; }}
}}
</style>
"""


def inject():
    """Install the stylesheet. Call once, first thing, on every rerun."""
    st.markdown(_CSS, unsafe_allow_html=True)


def card(html, extra=""):
    """Wrap markup in a card."""
    st.markdown(f'<div class="card {extra}">{html}</div>', unsafe_allow_html=True)


def narrow(px=880):
    """
    Constrain this view to a reading measure, centred in the full-bleed page.

    This has to be done by styling Streamlit's own block container: emitting a
    <div> from st.markdown and hoping the next widgets land inside it does not
    work — Streamlit renders every element as a sibling, so the div closes
    immediately and wraps nothing. A flashcard stretched across a 1440px projector
    is unreadable; the teacher's tables want the whole width, so they simply do
    not call this.
    """
    st.markdown(
        f"<style>.stMainBlockContainer,.block-container"
        f"{{max-width:{px}px !important;margin:0 auto !important;}}</style>",
        unsafe_allow_html=True,
    )


def divider():
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)


def spacer(px=14):
    st.markdown(f'<div style="height:{px}px"></div>', unsafe_allow_html=True)
