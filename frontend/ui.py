"""TracePilot UI — dark industrial design system.

All visual primitives, color tokens, and reusable render helpers.
Used across all pages for visual consistency.
"""

import streamlit as st
import sass


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
# RENDER HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def inject_css():
    """Call once from app.py to inject the entire design system."""
    # Compile SASS to CSS
    css = sass.compile(filename="frontend/styles.scss")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


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
            bg = "#ff5622"
            fg = "#fff"
            border = "#ff5622"
            label = f"✓ {p}"
        elif active:
            bg = "#434b51"
            fg = "#fff"
            border = "#434b51"
            label = p
        else:
            bg = "transparent"
            fg = "#8a9199"
            border = "#d1d5db"
            label = p

        pills.append(
            f"<span style='display:inline-block; padding:6px 14px; margin:2px; "
            f"border-radius:6px; font-size:0.74rem; font-weight:600; "
            f"background:{bg}; color:{fg}; border:1px solid {border}; "
            f"letter-spacing:0.03em; transition:all 0.15s ease'>{label}</span>"
        )

    completed_count = sum(1 for p in phases if completion.get(p, False))
    st.markdown(
        f"<div style='display:flex; align-items:center; flex-wrap:wrap; gap:4px; margin-bottom:8px; "
        f"padding:10px 0'>"
        f"{''.join(pills)}"
        f"<span style='margin-left:auto; font-size:0.74rem; color:#434b51; "
        f"font-weight:700; background:#f0f1f3; padding:3px 10px; border-radius:12px'>"
        f"{completed_count}/{len(phases)}</span></div>",
        unsafe_allow_html=True,
    )
