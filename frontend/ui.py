"""TracePilot UI — dark industrial design system.

All visual primitives, color tokens, and reusable render helpers.
Used across all pages for visual consistency.
"""

import streamlit as st


# ═══════════════════════════════════════════════════════════════════════════
# COLOR TOKENS
# ═══════════════════════════════════════════════════════════════════════════

class C:
    """Design tokens — single source of truth for all colors."""

    # Backgrounds
    BG_BASE = "#0b0f19"          # deepest background
    BG_SURFACE = "#111827"       # card / panel background
    BG_RAISED = "#1a2332"        # raised elements, hover states
    BG_OVERLAY = "#1e293b"       # modals, popovers

    # Borders
    BORDER = "#1e293b"           # default subtle border
    BORDER_STRONG = "#334155"    # emphasized border

    # Text
    TEXT = "#e2e8f0"             # primary text
    TEXT_DIM = "#94a3b8"         # secondary / caption text
    TEXT_MUTED = "#64748b"       # disabled / hint text

    # Accent
    ACCENT = "#0ea5e9"           # primary action blue
    ACCENT_HOVER = "#38bdf8"     # hover state
    ACCENT_DIM = "rgba(14,165,233,0.12)"  # subtle bg tint

    # Status
    SUCCESS = "#22c55e"
    SUCCESS_DIM = "rgba(34,197,94,0.10)"
    WARNING = "#f59e0b"
    WARNING_DIM = "rgba(245,158,11,0.10)"
    DANGER = "#ef4444"
    DANGER_DIM = "rgba(239,68,68,0.10)"
    INFO = "#38bdf8"
    INFO_DIM = "rgba(56,189,248,0.08)"

    # Job statuses
    STATUS = {
        "created": "#38bdf8",
        "uploading": "#64748b",
        "extracting": "#f59e0b",
        "review": "#f97316",
        "inspecting": "#a78bfa",
        "completed": "#22c55e",
        "deviation": "#ef4444",
    }

    SENSITIVITY = {
        "general": "#64748b",
        "confidential": "#f97316",
        "highly_confidential": "#ef4444",
    }


# ═══════════════════════════════════════════════════════════════════════════
# GLOBAL CSS — inject once from app.py
# ═══════════════════════════════════════════════════════════════════════════

GLOBAL_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* ── Reset & canvas ─────────────────────────────────────────── */
html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
}}

.stApp {{
    background-color: {C.BG_BASE};
}}

.block-container {{
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 1200px;
}}

/* ── Header ─────────────────────────────────────────────────── */
header[data-testid="stHeader"] {{
    background: {C.BG_BASE} !important;
    border-bottom: 1px solid {C.BORDER};
}}

/* ── Sidebar ────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {{
    background: {C.BG_SURFACE};
    border-right: 1px solid {C.BORDER};
}}
section[data-testid="stSidebar"] > div:first-child {{
    padding-top: 1rem;
}}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3,
section[data-testid="stSidebar"] .stMarkdown span,
section[data-testid="stSidebar"] .stMarkdown label {{
    color: {C.TEXT};
}}
section[data-testid="stSidebar"] hr {{
    border-color: {C.BORDER};
    margin: 0.6rem 0;
}}

/* Sidebar radio nav */
section[data-testid="stSidebar"] .stRadio > div {{
    gap: 1px;
}}
section[data-testid="stSidebar"] .stRadio label {{
    padding: 9px 14px !important;
    border-radius: 6px;
    font-size: 0.9rem;
    font-weight: 500;
    transition: background 0.12s;
}}
section[data-testid="stSidebar"] .stRadio label:hover {{
    background: {C.ACCENT_DIM};
}}
section[data-testid="stSidebar"] .stRadio label[data-checked="true"],
section[data-testid="stSidebar"] .stRadio [aria-checked="true"] {{
    background: {C.ACCENT_DIM} !important;
    border-left: 3px solid {C.ACCENT};
}}

/* ── Typography ─────────────────────────────────────────────── */
h1 {{ font-weight: 700; letter-spacing: -0.03em; font-size: 1.6rem !important; color: {C.TEXT} !important; }}
h2 {{ font-weight: 700; letter-spacing: -0.02em; font-size: 1.25rem !important; color: {C.TEXT} !important; }}
h3 {{ font-weight: 600; letter-spacing: -0.01em; font-size: 1.05rem !important; color: {C.TEXT} !important; }}

/* ── Metric cards ───────────────────────────────────────────── */
[data-testid="stMetric"] {{
    background: {C.BG_SURFACE};
    border: 1px solid {C.BORDER};
    border-radius: 8px;
    padding: 12px 14px;
}}
[data-testid="stMetricValue"] {{
    font-size: 1.6rem;
    font-weight: 700;
}}
[data-testid="stMetricLabel"] {{
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: {C.TEXT_DIM} !important;
}}

/* ── Buttons ────────────────────────────────────────────────── */
.stButton > button {{
    border-radius: 6px;
    font-weight: 600;
    font-size: 0.85rem;
    padding: 0.4rem 1rem;
    transition: all 0.12s ease;
    border: 1px solid {C.BORDER_STRONG};
    background: {C.BG_RAISED};
    color: {C.TEXT};
}}
.stButton > button:hover {{
    background: {C.BG_OVERLAY};
    border-color: {C.ACCENT};
    color: {C.ACCENT_HOVER};
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(0,0,0,0.4);
}}
.stButton > button[kind="primary"] {{
    background: {C.ACCENT};
    border: none;
    color: #fff;
}}
.stButton > button[kind="primary"]:hover {{
    background: {C.ACCENT_HOVER};
    box-shadow: 0 4px 16px rgba(14,165,233,0.3);
}}

/* ── Inputs ─────────────────────────────────────────────────── */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {{
    background: {C.BG_BASE} !important;
    border-color: {C.BORDER_STRONG} !important;
    color: {C.TEXT} !important;
    border-radius: 6px;
}}

/* ── Expanders ──────────────────────────────────────────────── */
details[data-testid="stExpander"] {{
    border: 1px solid {C.BORDER};
    border-radius: 8px;
    background: {C.BG_SURFACE};
}}
details[data-testid="stExpander"] summary {{
    font-weight: 600;
    font-size: 0.88rem;
}}

/* ── Progress bar ───────────────────────────────────────────── */
.stProgress > div > div > div {{
    background: linear-gradient(90deg, {C.SUCCESS}, #16a34a);
    border-radius: 3px;
}}

/* ── Horizontal radio (phase selector) ──────────────────────── */
.stRadio[data-testid="stRadio"] > div[role="radiogroup"] {{
    gap: 2px;
    background: {C.BG_SURFACE};
    padding: 4px;
    border-radius: 8px;
    border: 1px solid {C.BORDER};
}}

/* ── Alerts ─────────────────────────────────────────────────── */
.stAlert {{
    border-radius: 6px;
    font-size: 0.88rem;
}}

/* ── File uploader ──────────────────────────────────────────── */
[data-testid="stFileUploader"] {{
    border-radius: 8px;
}}
[data-testid="stFileUploader"] section {{
    border-color: {C.BORDER_STRONG} !important;
    background: {C.BG_SURFACE};
}}

/* ── Dividers ───────────────────────────────────────────────── */
hr {{
    border-color: {C.BORDER} !important;
    margin: 0.75rem 0 !important;
}}

/* ── Hide branding ──────────────────────────────────────────── */
#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}
</style>
"""


# ═══════════════════════════════════════════════════════════════════════════
# RENDER HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def inject_css():
    """Call once from app.py to inject the entire design system."""
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def chip(text: str, color: str, filled: bool = True) -> str:
    """Inline status chip. `filled`=True for solid bg, False for outline."""
    if filled:
        return (
            f"<span style='display:inline-block; background:{color}; color:#fff; "
            f"padding:2px 10px; border-radius:4px; font-size:0.72rem; "
            f"font-weight:600; letter-spacing:0.04em; text-transform:uppercase; "
            f"line-height:1.6'>{text}</span>"
        )
    return (
        f"<span style='display:inline-block; border:1px solid {color}; color:{color}; "
        f"padding:2px 10px; border-radius:4px; font-size:0.72rem; "
        f"font-weight:600; letter-spacing:0.04em; text-transform:uppercase; "
        f"line-height:1.6'>{text}</span>"
    )


def panel_start():
    """Open a dark panel container."""
    st.markdown(
        f"<div style='background:{C.BG_SURFACE}; border:1px solid {C.BORDER}; "
        f"border-radius:8px; padding:16px 20px; margin-bottom:12px'>",
        unsafe_allow_html=True,
    )


def panel_end():
    """Close a panel container."""
    st.markdown("</div>", unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "", extra_html: str = ""):
    """Full-width page header."""
    html = (
        f"<div style='margin-bottom:16px'>"
        f"<h1 style='margin:0; font-size:1.5rem !important'>{title}</h1>"
    )
    if subtitle:
        html += f"<p style='margin:2px 0 0; color:{C.TEXT_DIM}; font-size:0.88rem'>{subtitle}</p>"
    if extra_html:
        html += extra_html
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def section_title(title: str, count: str = ""):
    """Section header inside a page."""
    count_html = (
        f" <span style='color:{C.TEXT_MUTED}; font-weight:400; font-size:0.82rem'>"
        f"({count})</span>" if count else ""
    )
    st.markdown(
        f"<h3 style='margin:0 0 8px; padding-bottom:6px; "
        f"border-bottom:1px solid {C.BORDER}'>{title}{count_html}</h3>",
        unsafe_allow_html=True,
    )


def guidance(icon: str, message: str, kind: str = "info"):
    """Styled guidance block. kind: info|success|warning|danger."""
    color_map = {
        "info": (C.INFO, C.INFO_DIM),
        "success": (C.SUCCESS, C.SUCCESS_DIM),
        "warning": (C.WARNING, C.WARNING_DIM),
        "danger": (C.DANGER, C.DANGER_DIM),
    }
    accent, bg = color_map.get(kind, color_map["info"])
    st.markdown(
        f"<div style='background:{bg}; border-left:3px solid {accent}; "
        f"padding:10px 14px; border-radius:0 6px 6px 0; margin-bottom:12px; "
        f"font-size:0.88rem; color:{C.TEXT}; line-height:1.5'>"
        f"<span style='margin-right:6px'>{icon}</span>{message}</div>",
        unsafe_allow_html=True,
    )


def kpi_row(items: list[tuple[str, str, str]]):
    """Tight KPI row. items: [(label, value, accent_color), ...]"""
    cols = st.columns(len(items))
    for col, (label, value, accent) in zip(cols, items):
        with col:
            st.markdown(
                f"<div style='background:{C.BG_SURFACE}; border:1px solid {C.BORDER}; "
                f"border-top:2px solid {accent}; border-radius:6px; padding:10px 12px; "
                f"text-align:center'>"
                f"<div style='font-size:1.5rem; font-weight:700; color:{accent}; "
                f"line-height:1.2'>{value}</div>"
                f"<div style='font-size:0.68rem; color:{C.TEXT_MUTED}; text-transform:uppercase; "
                f"letter-spacing:0.07em; margin-top:3px'>{label}</div></div>",
                unsafe_allow_html=True,
            )


def empty_state(icon: str, title: str, subtitle: str = ""):
    """Centered empty state placeholder."""
    html = (
        f"<div style='text-align:center; padding:2.5rem 1rem; color:{C.TEXT_MUTED}'>"
        f"<div style='font-size:2rem; margin-bottom:6px; opacity:0.5'>{icon}</div>"
        f"<div style='font-size:0.95rem; font-weight:600; color:{C.TEXT_DIM}'>{title}</div>"
    )
    if subtitle:
        html += f"<div style='font-size:0.82rem; margin-top:4px'>{subtitle}</div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def progress_track(phases: list[str], completion: dict, current: str):
    """Horizontal phase tracker with completion states."""
    pills = []
    for p in phases:
        done = completion.get(p, False)
        active = (p == current)

        if done:
            bg = C.SUCCESS
            fg = "#fff"
            border = C.SUCCESS
            label = f"✓ {p}"
        elif active:
            bg = C.ACCENT
            fg = "#fff"
            border = C.ACCENT
            label = p
        else:
            bg = "transparent"
            fg = C.TEXT_MUTED
            border = C.BORDER
            label = p

        pills.append(
            f"<span style='display:inline-block; padding:4px 12px; margin:2px; "
            f"border-radius:4px; font-size:0.72rem; font-weight:600; "
            f"background:{bg}; color:{fg}; border:1px solid {border}; "
            f"letter-spacing:0.03em'>{label}</span>"
        )

    completed_count = sum(1 for p in phases if completion.get(p, False))
    st.markdown(
        f"<div style='display:flex; align-items:center; flex-wrap:wrap; gap:2px; margin-bottom:4px'>"
        f"{''.join(pills)}"
        f"<span style='margin-left:auto; font-size:0.72rem; color:{C.TEXT_MUTED}; "
        f"font-weight:600'>{completed_count}/{len(phases)}</span></div>",
        unsafe_allow_html=True,
    )
