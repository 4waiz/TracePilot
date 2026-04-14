"""TracePilot UI — EDGE Group design system.

All visual primitives, color tokens, and reusable render helpers.
Used across all pages for visual consistency.
"""

import streamlit as st
import sass


# ═══════════════════════════════════════════════════════════════════════════
# COLOR TOKENS — EDGE Group palette
# ═══════════════════════════════════════════════════════════════════════════

class C:
    """Design tokens — single source of truth for all colors."""

    # Backgrounds
    BG_BASE = "#F5F4F2"
    BG_SURFACE = "#FFFFFF"
    BG_RAISED = "#EDECEB"
    BG_SECTION = "#ECEAE7"

    # Borders
    BORDER = "#E5E3E0"
    BORDER_STRONG = "#D0CCC7"

    # Text
    TEXT = "#1A1A1A"
    TEXT_DIM = "#4A4A4A"
    TEXT_MUTED = "#8A8A8A"
    TEXT_LIGHT = "#B0ADAA"

    # Accent — burnt orange
    ACCENT = "#C65D3D"
    ACCENT_HOVER = "#B34F31"
    ACCENT_DIM = "rgba(198,93,61,0.08)"

    # Status
    SUCCESS = "#2E8B57"
    SUCCESS_DIM = "rgba(46,139,87,0.08)"
    WARNING = "#D4952A"
    WARNING_DIM = "rgba(212,149,42,0.08)"
    DANGER = "#C0392B"
    DANGER_DIM = "rgba(192,57,43,0.08)"
    INFO = "#3B7DD8"
    INFO_DIM = "rgba(59,125,216,0.08)"

    # Job statuses
    STATUS = {
        "created": "#3B7DD8",
        "extracting": "#D4952A",
        "review": "#C65D3D",
        "inspecting": "#7C6BBF",
        "completed": "#2E8B57",
        "deviation": "#C0392B",
    }

    SENSITIVITY = {
        "general": "#8A8A8A",
        "confidential": "#D4952A",
        "highly_confidential": "#C0392B",
    }


# ═══════════════════════════════════════════════════════════════════════════
# RENDER HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def inject_css():
    """Call once from app.py to inject the entire design system."""
    css = sass.compile(filename="frontend/styles.scss")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def chip(text: str, color: str, filled: bool = True) -> str:
    """Inline status chip — EDGE style: flat, uppercase, tight."""
    if filled:
        return (
            f"<span style='display:inline-block; background:{color}; color:#fff; "
            f"padding:2px 10px; border-radius:3px; font-size:0.65rem; "
            f"font-weight:700; letter-spacing:0.08em; text-transform:uppercase; "
            f"line-height:1.6'>{text}</span>"
        )
    return (
        f"<span style='display:inline-block; border:1px solid {color}; color:{color}; "
        f"padding:2px 10px; border-radius:3px; font-size:0.65rem; "
        f"font-weight:700; letter-spacing:0.08em; text-transform:uppercase; "
        f"line-height:1.6'>{text}</span>"
    )


def section_number(num: str) -> str:
    """EDGE-style section number: '01/' in accent color."""
    return (
        f"<div style='color:{C.ACCENT}; font-size:0.85rem; font-weight:700; "
        f"letter-spacing:0.05em; margin-bottom:4px'>{num}/</div>"
    )


def panel_start():
    """Open a card panel."""
    st.markdown(
        f"<div style='background:{C.BG_SURFACE}; border:1px solid {C.BORDER}; "
        f"border-radius:4px; padding:20px 24px; margin-bottom:12px'>",
        unsafe_allow_html=True,
    )


def panel_end():
    st.markdown("</div>", unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "", extra_html: str = ""):
    """Full-width page header — EDGE uppercase style."""
    html = (
        f"<div style='margin-bottom:24px; padding-bottom:16px; "
        f"border-bottom:1px solid {C.BORDER}'>"
        f"<h1 style='margin:0; font-size:1.6rem !important; letter-spacing:0.08em; "
        f"text-transform:uppercase; font-weight:800; color:{C.TEXT}'>{title}</h1>"
    )
    if subtitle:
        html += (
            f"<p style='margin:6px 0 0; color:{C.TEXT_MUTED}; font-size:0.88rem; "
            f"font-weight:300; letter-spacing:0.02em'>{subtitle}{extra_html}</p>"
        )
    elif extra_html:
        html += extra_html
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def section_title(title: str, count: str = ""):
    """Section header — EDGE style with optional count."""
    count_html = (
        f" <span style='color:{C.TEXT_MUTED}; font-weight:400; font-size:0.78rem'>"
        f"({count})</span>" if count else ""
    )
    st.markdown(
        f"<h3 style='margin:0 0 12px; padding-bottom:8px; "
        f"border-bottom:1px solid {C.BORDER}; font-size:0.82rem !important; "
        f"text-transform:uppercase; letter-spacing:0.10em; font-weight:700; "
        f"color:{C.TEXT}'>{title}{count_html}</h3>",
        unsafe_allow_html=True,
    )


def guidance(icon: str, message: str, kind: str = "info"):
    """Styled guidance block — clean EDGE style."""
    color_map = {
        "info": (C.INFO, C.INFO_DIM),
        "success": (C.SUCCESS, C.SUCCESS_DIM),
        "warning": (C.WARNING, C.WARNING_DIM),
        "danger": (C.DANGER, C.DANGER_DIM),
    }
    accent, bg = color_map.get(kind, color_map["info"])
    st.markdown(
        f"<div style='background:{bg}; border-left:3px solid {accent}; "
        f"padding:12px 18px; border-radius:0 4px 4px 0; margin-bottom:16px; "
        f"font-size:0.88rem; color:{C.TEXT_DIM}; line-height:1.5'>"
        f"<span style='margin-right:8px; color:{accent}'>{icon}</span>{message}</div>",
        unsafe_allow_html=True,
    )


def kpi_row(items: list[tuple[str, str, str]]):
    """Tight KPI row."""
    cols = st.columns(len(items))
    for col, (label, value, accent) in zip(cols, items):
        with col:
            st.markdown(
                f"<div style='background:{C.BG_SURFACE}; border:1px solid {C.BORDER}; "
                f"border-top:3px solid {accent}; border-radius:4px; padding:14px 14px; "
                f"text-align:center'>"
                f"<div style='font-size:1.5rem; font-weight:800; color:{C.TEXT}; "
                f"line-height:1'>{value}</div>"
                f"<div style='font-size:0.60rem; color:{C.TEXT_MUTED}; text-transform:uppercase; "
                f"letter-spacing:0.12em; margin-top:6px; font-weight:700'>{label}</div></div>",
                unsafe_allow_html=True,
            )


def empty_state(icon: str, title: str, subtitle: str = ""):
    """Centered empty state placeholder."""
    html = (
        f"<div style='text-align:center; padding:3rem 1rem; color:{C.TEXT_MUTED}'>"
        f"<div style='font-size:2rem; margin-bottom:8px; opacity:0.4'>{icon}</div>"
        f"<div style='font-size:0.9rem; font-weight:700; color:{C.TEXT_DIM}; "
        f"text-transform:uppercase; letter-spacing:0.06em'>{title}</div>"
    )
    if subtitle:
        html += f"<div style='font-size:0.82rem; margin-top:6px; font-weight:300'>{subtitle}</div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def progress_track(phases: list[str], completion: dict, current: str):
    """Horizontal phase tracker — EDGE clean style."""
    pills = []
    for p in phases:
        done = completion.get(p, False)
        active = (p == current)

        if done:
            bg = C.ACCENT
            fg = "#fff"
            border = C.ACCENT
            label = f"&#10003; {p}"
        elif active:
            bg = C.TEXT
            fg = "#fff"
            border = C.TEXT
            label = p
        else:
            bg = "transparent"
            fg = C.TEXT_MUTED
            border = C.BORDER_STRONG
            label = p

        pills.append(
            f"<span style='display:inline-block; padding:6px 16px; margin:2px; "
            f"border-radius:3px; font-size:0.68rem; font-weight:700; "
            f"background:{bg}; color:{fg}; border:1px solid {border}; "
            f"letter-spacing:0.06em; text-transform:uppercase'>{label}</span>"
        )

    completed_count = sum(1 for p in phases if completion.get(p, False))
    st.markdown(
        f"<div style='display:flex; align-items:center; flex-wrap:wrap; gap:4px; margin-bottom:12px; "
        f"padding:12px 0'>"
        f"{''.join(pills)}"
        f"<span style='margin-left:auto; font-size:0.68rem; color:{C.ACCENT}; "
        f"font-weight:700; background:{C.ACCENT_DIM}; padding:4px 12px; border-radius:3px; "
        f"letter-spacing:0.06em'>{completed_count}/{len(phases)}</span></div>",
        unsafe_allow_html=True,
    )
