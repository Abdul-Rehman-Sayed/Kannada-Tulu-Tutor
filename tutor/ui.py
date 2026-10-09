import html

import streamlit as st

INK = "#17150F"
CORRECT = "#1B5E20"
WRONG = "#8E2C1E"
CAUTION = "#7A5A16"

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Kannada:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&family=Inter:wght@400;500;600;700&display=swap');

@font-face{{
  font-family:'Tulu Mallige';
  src:url('app/static/fonts/Mallige-v1.4.ttf') format('truetype');
  unicode-range:U+11380-113FF;
  font-display:swap;
}}

:root{{

  --ink:#17150F;
  --body:#3A362C;
  --muted:#6B6558;
  --faint:#928B7C;

  --paper:#FBFAF6;
  --surface:#FFFFFF;
  --wash:#F4F2EC;
  --rule:#E4E0D6;
  --rule-strong:#CFC9BB;

  --ring:rgba(23,21,15,.14);

  --r:4px;
  --r-sm:3px;
  --ease:cubic-bezier(.22,.61,.36,1);
  --dur:.14s;

  --ok:{CORRECT};   --ok-bg:#F1F6F1;   --ok-brd:#C3D8C4;
  --no:{WRONG};     --no-bg:#FBF2F0;   --no-brd:#E5C6BF;
  --warn:{CAUTION}; --warn-bg:#FAF6EA; --warn-brd:#E0D3AE;

  --serif:'Source Serif 4',Georgia,'Times New Roman',serif;
  --sans:'Inter',system-ui,-apple-system,'Segoe UI','Tulu Mallige','Noto Sans Kannada','Nirmala UI',sans-serif;
  --kannada:'Noto Sans Kannada','Nirmala UI','Tunga','Tulu Mallige',sans-serif;
  --tulu:'Tulu Mallige','Noto Sans Kannada',sans-serif;
}}

.stApp{{ background:var(--paper); }}

html,body,[class*="css"],.stMarkdown,button,input,textarea,select{{
  font-family:var(--sans);
  color:var(--body);
  -webkit-font-smoothing:antialiased;
}}

.kn{{ font-family:var(--kannada); }}
.tu{{ font-family:var(--tulu); }}

h1,h2,h3,h4,.serif{{
  font-family:var(--serif);
  color:var(--ink);
  font-weight:600;
  letter-spacing:-.008em;
}}

.stMainBlockContainer,.block-container{{
  padding:2.2rem 2.2rem 5rem !important;
  max-width:none !important;
}}
@media (max-width:900px){{
  .stMainBlockContainer,.block-container{{ padding:1.5rem 1.1rem 4.5rem !important; }}
}}
@media (max-width:640px){{
  .stMainBlockContainer,.block-container{{ padding:1.1rem .8rem 4rem !important; }}
}}

@media (max-width:760px){{
  [data-testid="stHorizontalBlock"]{{ flex-wrap:wrap !important; gap:.6rem !important; }}
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]{{
    flex:1 1 100% !important; width:100% !important; min-width:100% !important;
  }}
}}

[data-testid="stDataFrame"],[data-testid="stTable"],.scroll-x{{
  max-width:100%; overflow-x:auto;
}}
[data-testid="stImage"] img{{ max-width:100%; height:auto; }}

.card{{
  background:var(--surface);
  border:1px solid var(--rule);
  border-radius:var(--r);
}}
.panel{{ padding:clamp(16px,2.4vw,26px); }}
.panel-tight{{ padding:clamp(12px,2vw,18px); }}

[data-testid="stHorizontalBlock"]:has(.lang-card){{ align-items:stretch; }}
[data-testid="stColumn"]:has(.lang-card){{ display:flex; flex-direction:column; }}
[data-testid="stColumn"]:has(.lang-card) > [data-testid="stVerticalBlock"]{{
  flex:1 1 auto; width:100%;
}}
[data-testid="stElementContainer"]:has(.lang-card){{
  display:flex; flex:1 1 auto;
}}
[data-testid="stElementContainer"]:has(.lang-card) [data-testid="stMarkdown"]{{
  display:flex; width:100%;
}}
[data-testid="stElementContainer"]:has(.lang-card) [data-testid="stMarkdownContainer"]{{
  display:flex; width:100%;
}}
.lang-card{{ display:flex; width:100%; }}
.lang-card > .panel{{ display:flex; flex-direction:column; width:100%; }}

.masthead{{ padding:clamp(24px,4vw,40px) clamp(18px,3.5vw,34px); }}
.masthead h1{{
  font-family:var(--serif);
  font-size:clamp(30px,5.2vw,46px); font-weight:600; line-height:1.12;
  margin:0 0 12px; letter-spacing:-.015em; color:var(--ink);
}}
.masthead .lede{{
  font-size:clamp(15px,1.7vw,17px); line-height:1.6; color:var(--muted);
  max-width:60ch; margin:0;
}}
.masthead .rule{{
  height:2px; background:var(--ink); width:44px; margin:0 0 20px;
}}
.masthead .script{{
  font-size:clamp(24px,4vw,32px); margin:22px 0 0; color:var(--ink);
  font-weight:400; letter-spacing:.16em; opacity:.82;
}}

.centred{{ text-align:center; }}

.points{{ padding:clamp(16px,2.4vw,26px); }}
.point{{ display:flex; gap:16px; padding:16px 0; border-top:1px solid var(--rule); }}
.point:first-child{{ border-top:none; padding-top:0; }}
.point .num{{
  font-family:var(--serif); font-size:15px; font-weight:600; color:var(--faint);
  min-width:22px; padding-top:1px;
}}
.point h3{{ font-family:var(--serif); font-size:16.5px; margin:0 0 4px; font-weight:600; }}
.point p{{ font-size:14px; line-height:1.6; color:var(--muted); margin:0; }}

.facts{{
  font-size:13px; color:var(--muted); padding:14px 18px;
  border-top:1px solid var(--rule); border-bottom:1px solid var(--rule);
}}
.facts b{{ color:var(--ink); font-weight:600; }}

.pic{{
  max-width:420px; margin:0 auto 14px; border:1px solid var(--rule);
  border-radius:var(--r-sm); overflow:hidden; background:var(--surface);
}}
.pic svg{{ display:block; width:100%; height:auto; }}
.pic img{{ display:block; width:100%; height:auto; aspect-ratio:4/3; object-fit:cover; }}
.pic figcaption{{
  padding:5px 10px 6px; font-size:10.5px; line-height:1.35; color:var(--faint);
  text-align:right; border-top:1px solid var(--rule);
}}

.lw{{
  background:var(--surface); border:1px solid var(--rule);
  border-radius:var(--r-sm); overflow:hidden; position:sticky; top:12px;
}}
.lw-hd{{
  display:flex; align-items:center; gap:10px; padding:13px 16px;
  border-bottom:1px solid var(--rule); background:var(--wash);
  font-size:13.5px; font-weight:600; color:var(--ink);
}}
.lw-hd .kn,.lw-hd .tu{{ font-size:24px; line-height:1; font-weight:500; }}
.lw-hd .tu{{ line-height:1.2; }}
.lw-hd .n{{
  margin-left:auto; font-size:11px; font-weight:700; letter-spacing:.08em;
  color:var(--muted); background:var(--paper); border:1px solid var(--rule);
  border-radius:999px; padding:3px 9px;
}}
.lw-list{{
  list-style:none; margin:0; padding:0; max-height:60vh; overflow-y:auto;
}}
.lw .lw-list > li{{ margin:0; list-style:none; }}
.lw .lw-item{{
  display:grid; grid-template-columns:auto 1fr auto; gap:2px 12px;
  align-items:baseline; padding:11px 16px; position:relative;
  border-top:1px solid var(--rule);
}}
.lw .lw-item:first-child{{ border-top:none; }}
.lw-n{{
  min-width:2ch; text-align:right;
  font-family:var(--serif); font-size:12px; color:var(--faint);
  font-variant-numeric:tabular-nums;
}}
.lw-list .w{{ font-size:23px; line-height:1.4; color:var(--ink); font-weight:500;
  min-width:0; overflow-wrap:anywhere; }}
.lw-list .t{{ font-size:12.5px; color:var(--body); font-weight:600; text-align:right; }}
.lw-list .m{{ grid-column:2/-1; font-size:12.5px; color:var(--muted); }}

.lw-now{{ background:var(--wash); }}
.lw-now::before{{
  content:""; position:absolute; left:0; top:0; bottom:0; width:3px;
  background:var(--ink);
}}
.lw-now .w{{ font-weight:600; }}
.lw-mark{{
  margin-left:8px; font-size:10px; font-weight:700; letter-spacing:.08em;
  text-transform:uppercase; color:var(--ink);
}}

.lw .lw-split{{
  padding:8px 16px; border-top:1px solid var(--rule); line-height:1.45;
  background:var(--paper); font-size:10.5px; font-weight:700;
  letter-spacing:.08em; text-transform:uppercase; color:var(--faint);
}}
.lw-ft{{
  margin:0; padding:9px 16px; border-top:1px solid var(--rule);
  background:var(--wash); font-size:11.5px; color:var(--muted);
}}

.letter-tile{{
  max-width:260px; margin:0 auto 16px; padding:22px 16px;
  border:1px solid var(--rule-strong); border-radius:var(--r-sm);
  background:var(--wash);
}}
.letter-tile .kn,.letter-tile .tu{{
  display:block; font-size:clamp(84px,18vw,132px); line-height:1;
  font-weight:500; color:var(--ink);
}}
.letter-tile .tu{{ line-height:1.2; }}
.letter-tile .also{{
  display:block; margin-top:10px; font-size:13px; color:var(--muted);
}}
.letter-tile .also .kn{{ display:inline; font-size:22px; font-weight:600; color:var(--body); }}
.isfor .line .l.tu{{ font-family:var(--tulu); }}
.cell .g.tu{{ font-family:var(--tulu); }}

.stages{{
  display:flex; gap:0; background:var(--surface); border:1px solid var(--rule);
  border-radius:var(--r); overflow:hidden; margin-bottom:14px;
}}
.stg{{
  flex:1 1 0; min-width:0; padding:11px 12px 12px;
  border-left:1px solid var(--rule); position:relative;
}}
.stg:first-child{{ border-left:none; }}
.stg .n{{
  font-size:10px; font-weight:700; letter-spacing:.1em; text-transform:uppercase;
  color:var(--faint);
}}
.stg .t{{
  font-family:var(--serif); font-size:15px; font-weight:600; color:var(--faint);
  margin-top:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}}
.stg .c{{ font-size:11.5px; color:var(--faint); margin-top:2px; }}
.stg-done .t,.stg-done .n{{ color:var(--muted); }}
.stg-done .c{{ color:var(--ok); font-weight:600; }}
.stg-done .m > i{{ background:var(--ok); }}
.stg-now{{ background:var(--wash); }}
.stg-now::before{{
  content:""; position:absolute; left:0; right:0; top:0; height:2px;
  background:var(--ink);
}}
.stg-now .n{{ color:var(--ink); }}
.stg-now .t{{ color:var(--ink); }}
.stg-now .c{{ color:var(--body); }}
.stg .m{{ height:3px; background:#E8E4DA; margin-top:7px; border-radius:2px;
  overflow:hidden; }}
.stg .m > i{{ display:block; height:100%; background:var(--ink); }}
.stg-locked .m{{ visibility:hidden; }}

.classcode{{ padding:20px 24px 18px; }}
.classcode .lbl{{
  font-size:11px; font-weight:700; letter-spacing:.11em; text-transform:uppercase;
  color:var(--muted); margin-bottom:8px;
}}
.classcode .code{{
  font-family:var(--serif); font-size:clamp(34px,6.4vw,52px); font-weight:700;
  letter-spacing:.08em; color:var(--ink); line-height:1.1; margin-bottom:10px;
}}
.classcode p{{ margin:0 0 6px; font-size:13px; color:var(--muted);
  line-height:1.6; max-width:60ch; }}
.classcode .tiny{{ font-size:11.5px; color:var(--faint); }}

.sb-class{{
  margin:0 0 14px; padding:10px 12px; border-radius:var(--r-sm);
  background:var(--wash); border:1px solid var(--rule);
}}
.sb-class .lbl{{
  font-size:10px; font-weight:700; letter-spacing:.11em; text-transform:uppercase;
  color:var(--faint);
}}
.sb-class .nm{{ font-size:14px; font-weight:600; color:var(--ink); margin-top:2px; }}

@media (max-width:640px){{
  .stg{{ padding:8px 7px 9px; }}
  .stg .t{{ font-size:12.5px; }}
  .stg .c{{ font-size:10.5px; }}
  .stg .n{{ font-size:9px; }}
}}

.stage-now{{ padding:14px 18px; }}
.stage-now h4{{ font-family:var(--serif); font-size:16px; margin:0 0 3px;
  color:var(--ink); font-weight:600; }}
.stage-now p{{ margin:0; font-size:13px; color:var(--muted); line-height:1.55; }}

.isfor{{
  margin-top:16px; padding:14px 18px; border-radius:var(--r-sm);
  background:var(--wash); border:1px solid var(--rule); text-align:center;
}}
.isfor .lead{{ font-size:12px; font-weight:700; letter-spacing:.1em;
  text-transform:uppercase; color:var(--muted); margin:0 0 9px; }}
.isfor .line{{ font-size:clamp(20px,4.2vw,27px); color:var(--ink);
  line-height:1.35; }}
.isfor .line .l{{ font-family:var(--kannada); font-weight:600; }}
.isfor .line .j{{ font-family:var(--serif); font-size:.66em; color:var(--muted);
  margin:0 .34em; }}
.isfor .line .a{{ font-family:var(--kannada); font-weight:500; }}
.isfor .gloss{{ font-size:13px; color:var(--muted); margin-top:6px; }}
.isfor .both{{
  font-size:13px; color:var(--body); margin-top:11px; padding-top:10px;
  border-top:1px solid var(--rule);
}}
.isfor .both b{{ color:var(--ink); font-weight:600; font-size:1.22em; }}

.word-card{{ padding:clamp(20px,3.4vw,34px); text-align:center; }}
.word{{
  font-size:clamp(54px,13vw,100px); font-weight:500; line-height:1.16;
  color:var(--ink); margin:0 0 10px; word-break:break-word;
  font-family:var(--kannada);
}}

.word.long{{ font-size:clamp(28px,7vw,50px); line-height:1.4; }}

.word.solo{{ line-height:.88; margin-bottom:2px; }}
.translit{{
  font-size:clamp(15px,2.6vw,19px); color:var(--body); font-weight:600;
  margin:0; letter-spacing:.01em;
}}
.meaning{{ font-size:clamp(14px,2.4vw,16px); color:var(--muted); margin:6px 0 0; }}

.tags{{ margin-top:18px; display:flex; gap:14px; justify-content:center;
  flex-wrap:wrap; font-size:11.5px; color:var(--faint);
  text-transform:uppercase; letter-spacing:.1em; font-weight:600; }}

.say{{
  margin-top:20px; padding:16px 18px; border-radius:var(--r-sm); text-align:center;
  background:var(--wash); border:1px solid var(--rule);
}}
.say .lbl{{
  font-size:11px; font-weight:700; letter-spacing:.12em; text-transform:uppercase;
  color:var(--muted); margin:0 0 8px;
}}
.say .val{{ font-size:clamp(21px,4.4vw,28px); font-weight:500; color:var(--ink);
  font-family:var(--kannada); line-height:1.35; }}
.say .hint{{ font-size:12.5px; color:var(--muted); margin-top:8px; }}

.fb{{ padding:14px 18px; border-radius:var(--r-sm); margin-bottom:10px;
  text-align:center; }}
.fb .hd{{ font-size:clamp(15px,2.6vw,17.5px); font-weight:600; font-family:var(--serif); }}
.fb .sub{{ font-size:12.5px; font-weight:400; margin-top:5px; opacity:.92; }}
.fb-ok{{ background:var(--ok-bg); border:1px solid var(--ok-brd); color:var(--ok); }}
.fb-no{{ background:var(--no-bg); border:1px solid var(--no-brd); color:var(--no); }}
.fb-warn{{ background:var(--warn-bg); border:1px solid var(--warn-brd); color:var(--warn); }}
.meter{{ height:3px; background:rgba(0,0,0,.09); margin-top:12px; overflow:hidden; }}
.meter > i{{ display:block; height:100%; background:currentColor; }}

.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button{{
  border-radius:var(--r-sm) !important;
  font-weight:500 !important; font-size:15px !important;
  min-height:48px;
  background:var(--surface) !important;
  border:1px solid var(--rule-strong) !important;
  color:var(--ink) !important;
  box-shadow:none !important;
  transition:background var(--dur) var(--ease), border-color var(--dur) var(--ease) !important;
}}
.stButton > button:hover, .stDownloadButton > button:hover,
.stFormSubmitButton > button:hover{{
  background:var(--wash) !important; border-color:var(--faint) !important;
  color:var(--ink) !important;
}}
.stButton > button:focus-visible, .stDownloadButton > button:focus-visible,
.stFormSubmitButton > button:focus-visible{{
  outline:none !important; border-color:var(--ink) !important;
  box-shadow:0 0 0 3px var(--ring) !important;
}}

.stButton > button[kind^="primary"],
.stFormSubmitButton > button[kind^="primary"]{{
  background:var(--ink) !important;
  border:1px solid var(--ink) !important;
  color:#FFFDF8 !important;
}}
.stButton > button[kind^="primary"]:hover,
.stFormSubmitButton > button[kind^="primary"]:hover{{
  background:#000 !important; border-color:#000 !important; color:#FFFDF8 !important;
}}
.stButton > button[kind^="primary"] p,
.stFormSubmitButton > button[kind^="primary"] p{{ color:#FFFDF8 !important; }}

div[data-baseweb="input"],
.stSelectbox div[data-baseweb="select"] > div{{
  background:var(--surface) !important;
  border:1px solid var(--rule-strong) !important;
  border-radius:var(--r-sm) !important;
  box-shadow:none !important;
  min-height:48px;
  overflow:hidden;
  transition:border-color var(--dur) var(--ease), box-shadow var(--dur) var(--ease);
}}
.stSelectbox div[data-baseweb="select"],
.stSelectbox div[data-baseweb="select"] *:not([data-testid="stIconMaterial"]),
div[data-baseweb="popover"] li,
div[data-baseweb="popover"] li *:not([data-testid="stIconMaterial"]){{
  font-family:var(--sans) !important;
}}

div[data-baseweb="input"]:focus-within,
.stSelectbox div[data-baseweb="select"] > div:focus-within{{
  border-color:var(--ink) !important;
  box-shadow:0 0 0 3px var(--ring) !important;
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
  font-size:16px !important;
}}
div[data-baseweb="input"] button{{
  background:transparent !important; border:none !important; box-shadow:none !important;
  color:var(--muted) !important;
}}

[data-testid="InputInstructions"]{{ display:none !important; }}

[data-testid="stForm"]{{
  background:transparent !important; border:none !important; padding:0 !important;
}}

[data-testid="stAudioInput"]{{
  background:var(--surface) !important;
  border:1px solid var(--rule-strong) !important;
  border-radius:var(--r-sm) !important;
  box-shadow:none !important;
}}
[data-testid="stAudio"] audio{{ width:100%; }}
[data-testid="stImage"] img{{ border-radius:var(--r-sm); }}

.stTabs [data-baseweb="tab-list"]{{
  gap:22px; background:transparent; padding:0;
  border-bottom:1px solid var(--rule); flex-wrap:wrap;
}}
.stTabs [data-baseweb="tab"]{{
  background:transparent !important; padding:11px 2px; font-weight:500;
  color:var(--muted); border-bottom:2px solid transparent; margin-bottom:-1px;
  transition:color var(--dur) var(--ease), border-color var(--dur) var(--ease);
}}
.stTabs [aria-selected="true"]{{
  color:var(--ink) !important; border-bottom-color:var(--ink);
}}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"]{{ display:none; }}

[data-testid="stMetric"]{{
  background:var(--surface); border:1px solid var(--rule);
  border-radius:var(--r); padding:14px 16px;
}}
[data-testid="stMetricValue"]{{ color:var(--ink); font-weight:600;
  font-family:var(--serif); }}
[data-testid="stDataFrame"]{{
  border-radius:var(--r-sm); overflow:hidden; border:1px solid var(--rule);
}}
[data-testid="stExpander"] details{{
  background:var(--surface); border:1px solid var(--rule) !important;
  border-radius:var(--r-sm) !important;
}}

.stProgress > div > div > div > div{{ background:var(--ink) !important; }}
.stProgress > div > div > div{{ background:rgba(0,0,0,.08) !important; }}

[data-testid="stAlert"]{{ border-radius:var(--r-sm); border:1px solid var(--rule); }}

[data-testid="stSidebar"]{{
  background:var(--surface) !important;
  border-right:1px solid var(--rule);
}}
.sb-brand{{ font-family:var(--serif); font-weight:600; font-size:16px; color:var(--ink); }}
.sb-sub{{ color:var(--faint); font-size:11px; margin-top:3px;
  letter-spacing:.1em; text-transform:uppercase; font-weight:600; }}
.learner{{
  border-top:1px solid var(--rule); border-bottom:1px solid var(--rule);
  padding:12px 0; margin:10px 0 12px;
}}
.learner .rl{{ font-size:10px; color:var(--faint); text-transform:uppercase;
  letter-spacing:.1em; font-weight:700; }}
.learner .nm{{ font-family:var(--serif); font-weight:600; color:var(--ink);
  font-size:16px; margin-top:3px; }}
.learner .lang{{ font-size:12px; color:var(--muted); margin-top:2px; }}

.chart{{ display:flex; flex-wrap:wrap; gap:6px; }}
.cell{{
  min-width:52px; flex:0 0 auto; padding:9px 6px 7px; text-align:center;
  border:1px solid var(--rule); border-radius:var(--r-sm); background:var(--surface);
}}
.cell .g{{ font-family:var(--kannada); font-size:23px; line-height:1.25; color:var(--ink); }}
.cell .r{{ font-size:10px; color:var(--faint); margin-top:1px;
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.cell-ok{{ background:var(--ok-bg); border-color:var(--ok-brd); }}
.cell-ok .g{{ color:var(--ok); }}
.cell-try{{ background:var(--warn-bg); border-color:var(--warn-brd); }}
.cell-try .g{{ color:var(--warn); }}
.cell-stuck{{ background:var(--no-bg); border-color:var(--no-brd); }}
.cell-stuck .g{{ color:var(--no); }}
.cell-mute{{ background:var(--wash); border-style:dashed;
  border-color:var(--rule-strong); }}
.cell-mute .g{{ color:var(--faint); }}
@media (max-width:640px){{
  .cell{{ min-width:44px; padding:7px 4px 5px; }}
  .cell .g{{ font-size:20px; }}
}}

.cogmap{{ overflow-x:auto; padding:4px 0 8px; }}
.cogmap svg{{ display:block; }}
.cogmap .edge{{ stroke:var(--rule-strong); stroke-width:1; opacity:.5; }}
.cogmap .node{{ stroke-width:1.5; }}
.cogmap .tier{{ fill:var(--faint); font-family:var(--sans); font-size:9px; }}

.legend{{ display:flex; align-items:center; gap:14px; flex-wrap:wrap;
  font-size:12px; color:var(--muted); margin:12px 0 0; }}
.legend .legend-title{{ font-size:11px; font-weight:600; letter-spacing:.08em;
  text-transform:uppercase; color:var(--faint); }}
.legend span{{ display:inline-flex; align-items:center; gap:7px; }}
.legend i{{ width:13px; height:13px; border-radius:3px; display:inline-block;
  flex:0 0 auto; background:var(--surface); border:1px solid var(--rule-strong); }}
.legend i.cell-ok{{ background:var(--ok); border-color:var(--ok); }}
.legend i.cell-try{{ background:var(--warn); border-color:var(--warn); }}
.legend i.cell-stuck{{ background:var(--no); border-color:var(--no); }}
.legend i.cell-mute{{ background:var(--wash); border-style:dashed;
  border-color:var(--rule-strong); }}

.bars{{ padding:clamp(14px,2vw,20px); }}
.bar-row{{ padding:11px 0; border-top:1px solid var(--rule); }}
.bar-row:first-child{{ border-top:none; padding-top:0; }}
.bar-head{{ display:flex; justify-content:space-between; gap:12px;
  font-size:13.5px; margin-bottom:7px; }}
.bar-head .nm{{ color:var(--ink); font-weight:500; }}
.bar-head .ct{{ color:var(--muted); white-space:nowrap; }}
.bar{{ height:7px; background:#EDEAE1; border-radius:2px; overflow:hidden; }}
.bar > i{{ display:block; height:100%; background:var(--ink); }}
.bar > i.low{{ background:var(--no); }}

.findings{{ padding:clamp(14px,2vw,22px); }}
.finding{{ display:flex; gap:12px; padding:11px 0; border-top:1px solid var(--rule);
  font-size:14.5px; line-height:1.55; color:var(--body); }}
.finding:first-child{{ border-top:none; padding-top:2px; }}
.finding .mk{{ font-weight:700; color:var(--ink); min-width:14px; }}
.finding b{{ color:var(--ink); font-weight:600; }}
.finding .kn{{ font-size:1.08em; }}
.finding-do{{ color:var(--ink); }}

.tiny{{ font-size:12px; color:var(--faint); }}
.divider{{ height:1px; background:var(--rule); margin:26px 0; }}
.section-note{{ font-size:13px; color:var(--muted); line-height:1.55;
  margin:0 0 12px; max-width:74ch; }}

@media (max-width:640px){{
  .word{{ font-size:clamp(50px,19vw,78px); }}
  .word.long{{ font-size:clamp(26px,8vw,40px); }}
}}

@media (prefers-reduced-motion:reduce){{
  *{{ transition:none !important; animation:none !important; }}
}}
</style>
"""


def inject():
    st.markdown(_CSS, unsafe_allow_html=True)


def loading(message="Loading…"):
    return st.spinner(message, show_time=True)


def esc(value):
    return html.escape(str(value))


def card(html_body, extra=""):
    st.markdown(f'<div class="card {extra}">{html_body}</div>', unsafe_allow_html=True)


def narrow(px=860):
    st.markdown(
        f"<style>.stMainBlockContainer,.block-container"
        f"{{max-width:{px}px !important;margin:0 auto !important;}}</style>",
        unsafe_allow_html=True,
    )


def divider():
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)


def spacer(px=14):
    st.markdown(f'<div style="height:{px}px"></div>', unsafe_allow_html=True)


def note(text):
    st.markdown(f'<p class="section-note">{text}</p>', unsafe_allow_html=True)


def bars(rows):
    parts = []
    for label, done, total, caption in rows:
        pct = (done / total * 100) if total else 0.0
        cls = " low" if pct < 34 else ""
        parts.append(
            f'<div class="bar-row"><div class="bar-head">'
            f'<span class="nm">{esc(label)}</span>'
            f'<span class="ct">{esc(caption)}</span></div>'
            f'<div class="bar"><i class="{cls.strip()}" style="width:{pct:.1f}%"></i></div>'
            f"</div>"
        )
    card(f'<div class="bars">{"".join(parts)}</div>')


def legend(items, title="What the colours mean"):
    parts = [
        f'<span><i class="{cls}"></i>{esc(label)}</span>' for cls, label in items
    ]
    head = f'<span class="legend-title">{esc(title)}</span>' if title else ""
    st.markdown(
        f'<div class="legend">{head}{"".join(parts)}</div>', unsafe_allow_html=True
    )
