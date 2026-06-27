"""
Storytime Studio — design system (Path B reskin).

inject_theme() loads the Spectral + Hanken Grotesk fonts and a full CSS token
set so the WHOLE Streamlit app adopts the redesign (warm ivory paper, terracotta
pill buttons, rounded inputs, Spectral headings, hidden Streamlit chrome).

Helper functions build the typographic / image book covers and small UI atoms
used by the storefront.
"""
import base64
import pathlib
import streamlit as st

# Book cover palette (assign per book) + matching light text tints
COVER_BG = ["#C0573E", "#2F5D52", "#7A4A8C", "#B8843C", "#3E6B4F", "#34507A", "#A85A6B", "#C77F2E"]
COVER_FG = ["#FBF1E6", "#EAF1EC", "#F4ECF6", "#FBF1E6", "#EEF5EE", "#EAF0F7", "#FBEEF0", "#FBF1E6"]


def inject_theme():
    st.markdown(
        """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,500;0,600;0,700;0,800;1,400;1,500&family=Hanken+Grotesk:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
      :root{
        --paper:#FBF7F0; --paper2:#F7F0E6; --card:#FFFDF9; --ink:#2A2420;
        --muted:#6B6157; --muted2:#8A7C6C; --faint:#A38A6B; --border:#EBE2D4; --borderin:#E2D6C4;
        --terra:#C0573E; --terra-d:#A8472F; --teal:#2F5D52; --teal-t:#E7EFE9;
        --clay-t:#F4E7DC; --gold:#E2A24A;
      }
      html, body, [class*="css"], .stApp { font-family:"Hanken Grotesk", system-ui, sans-serif; }
      .stApp { background:var(--paper); color:var(--ink); }
      h1,h2,h3,h4 { font-family:"Spectral", Georgia, serif !important; letter-spacing:-0.01em; color:var(--ink); }
      h1 { font-weight:700; }
      p, span, label, li, div { color:var(--ink); }
      a { color:var(--terra); }

      /* hide default Streamlit chrome */
      #MainMenu, header[data-testid="stHeader"], footer { display:none !important; }
      [data-testid="stToolbar"]{ display:none !important; }
      .block-container { padding-top:1.4rem; padding-bottom:3rem; max-width:1180px; }

      /* primary buttons -> terracotta pill */
      .stButton > button, .stDownloadButton > button {
        font-family:"Hanken Grotesk",sans-serif; font-weight:700; border-radius:999px;
        border:1.5px solid transparent; background:var(--terra); color:#FBF7F0 !important;
        padding:.62rem 1.35rem; transition:transform .15s, box-shadow .15s;
        box-shadow:0 10px 26px rgba(192,87,62,.30);
      }
      .stButton > button:hover, .stDownloadButton > button:hover {
        transform:translateY(-1px); box-shadow:0 12px 30px rgba(192,87,62,.36); color:#FBF7F0 !important; border-color:transparent;
      }
      /* secondary buttons -> outline */
      .stButton > button[kind="secondary"]{
        background:transparent; color:var(--ink) !important; border:1.5px solid var(--borderin); box-shadow:none;
      }
      .stButton > button[kind="secondary"]:hover{ border-color:var(--ink); background:transparent; color:var(--ink) !important; }

      /* inputs */
      .stTextInput input, .stTextArea textarea,
      .stSelectbox div[data-baseweb="select"], .stNumberInput input {
        border-radius:12px !important; border:1.5px solid var(--borderin) !important;
        background:#fff !important; font-family:"Hanken Grotesk",sans-serif; color:var(--ink) !important;
      }
      .stTextInput input:focus, .stTextArea textarea:focus { border-color:var(--terra) !important; }

      /* tabs, radios, expanders, progress in brand colors */
      .stTabs [aria-selected="true"]{ color:var(--terra) !important; }
      .stTabs [data-baseweb="tab-highlight"]{ background:var(--terra) !important; }
      .stProgress > div > div > div { background:var(--terra) !important; }
      [data-testid="stExpander"]{ border-radius:14px; border:1px solid var(--border); }

      /* sidebar */
      [data-testid="stSidebar"]{ background:var(--card); border-right:1px solid var(--border); }

      /* ---- design atoms ---- */
      .ss-eyebrow{ font-size:13px; font-weight:800; letter-spacing:.18em; text-transform:uppercase; color:var(--terra); }
      .ss-eyebrow.teal{ color:var(--teal); } .ss-eyebrow.gold{ color:var(--gold); }
      .ss-pill{ display:inline-block; font-size:13px; font-weight:700; padding:6px 14px; border-radius:999px; }
      .ss-pill.clay{ background:var(--clay-t); color:var(--terra-d); }
      .ss-pill.teal{ background:var(--teal-t); color:var(--teal); }
      .ss-card{ background:var(--card); border:1px solid var(--border); border-radius:18px; padding:24px;
        box-shadow:0 14px 30px rgba(42,36,32,.06); }
      .ss-band{ background:var(--paper2); border-radius:24px; padding:30px clamp(18px,4vw,40px); }

      /* book covers (typographic) */
      .ss-cover{ position:relative; aspect-ratio:3/4; border-radius:8px 12px 12px 8px;
        box-shadow:0 14px 30px rgba(42,36,32,.15); overflow:hidden; }
      .ss-cover .spine{ position:absolute; left:0; top:0; bottom:0; width:9px; background:rgba(0,0,0,.16); }
      .ss-cover .pad{ padding:20px 16px 16px 24px; height:100%; display:flex; flex-direction:column; box-sizing:border-box; }
      .ss-cover .cat{ font-size:9.5px; letter-spacing:.2em; text-transform:uppercase; opacity:.8; font-weight:700; }
      .ss-cover .ttl{ font-family:"Spectral",serif; font-weight:700; font-size:22px; line-height:1.1; margin-top:auto; }
      .ss-cover .rule{ height:1px; background:currentColor; opacity:.32; margin:11px 0 8px; }
      .ss-cover .sub{ font-size:10.5px; opacity:.82; }
      .ss-cover-img{ aspect-ratio:3/4; border-radius:8px 12px 12px 8px; overflow:hidden;
        box-shadow:0 14px 30px rgba(42,36,32,.15); position:relative; }
      .ss-cover-img img{ width:100%; height:100%; object-fit:cover; display:block; }
      .ss-cover-img .spine{ position:absolute; left:0; top:0; bottom:0; width:9px; background:rgba(0,0,0,.18); z-index:2; }

      @keyframes floaty{ 0%,100%{ transform:var(--rot) translateY(0);} 50%{ transform:var(--rot) translateY(-10px);} }
      .ss-floaty{ animation:floaty 7.5s ease-in-out infinite; }
    </style>
    """,
        unsafe_allow_html=True,
    )


def cover_data_uri(path):
    try:
        b = pathlib.Path(path).read_bytes()
        ext = "png" if str(path).lower().endswith("png") else "jpeg"
        return f"data:image/{ext};base64,{base64.b64encode(b).decode()}"
    except Exception:
        return ""


def typo_cover_html(title, category, idx=0):
    bg = COVER_BG[idx % len(COVER_BG)]; fg = COVER_FG[idx % len(COVER_FG)]
    return (
        f'<div class="ss-cover" style="background:{bg}">'
        f'<div class="spine"></div>'
        f'<div class="pad" style="color:{fg}">'
        f'<div class="cat">{category}</div>'
        f'<div class="ttl">{title}</div>'
        f'<div class="rule"></div>'
        f'<div class="sub">Personalized edition</div>'
        f'</div></div>'
    )


def image_cover_html(src):
    return f'<div class="ss-cover-img"><div class="spine"></div><img src="{src}"/></div>'
