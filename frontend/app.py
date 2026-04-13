"""TracePilot -- Streamlit frontend entry point.

Run with:  streamlit run frontend/app.py
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path so "frontend.*" imports resolve
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

# -- Page config (must be first Streamlit call) ---------------------------
st.set_page_config(
    page_title="TracePilot",
    page_icon="icon.png",
    layout="wide",
)

# -- Inject design system CSS --------------------------------------------
from frontend.ui import inject_css, chip, C
inject_css()

# -- Session state defaults -----------------------------------------------

if "token" not in st.session_state:
    st.session_state["token"] = None
if "user" not in st.session_state:
    st.session_state["user"] = None
if "nav" not in st.session_state:
    st.session_state["nav"] = "Dashboard"
if "selected_job_id" not in st.session_state:
    st.session_state["selected_job_id"] = None


# -- Auth gate ------------------------------------------------------------

def _is_authenticated() -> bool:
    return st.session_state.get("token") is not None


# -- Routing --------------------------------------------------------------

if not _is_authenticated():
    from frontend.views.login import render as render_login
    render_login()
else:
    user_obj = st.session_state["user"]
    user_role = user_obj.get("role", "user")
    username = user_obj.get("username", "")

    # ── Sidebar ──────────────────────────────────────────────────────
    with st.sidebar:
        # Brand block
        st.markdown(
            f"<div style='text-align:center; padding:8px 0 4px'>"
            f"<div style='font-size:1.3rem; font-weight:700; color:{C.TEXT}; "
            f"letter-spacing:-0.03em'>TracePilot</div>"
            f"<div style='font-size:0.7rem; color:{C.TEXT_MUTED}; "
            f"text-transform:uppercase; letter-spacing:0.1em; margin-top:2px'>"
            f"Inspection & Traceability</div></div>",
            unsafe_allow_html=True,
        )
        st.markdown("---")

        # User block
        role_color = C.ACCENT if user_role == "admin" else C.SUCCESS if user_role == "supervisor" else C.TEXT_DIM
        st.markdown(
            f"<div style='padding:6px 0'>"
            f"<div style='font-size:0.88rem; font-weight:600; color:{C.TEXT}'>{username}</div>"
            f"<div style='margin-top:3px'>{chip(user_role, role_color)}</div></div>",
            unsafe_allow_html=True,
        )
        st.markdown("---")

        # Navigation
        nav_items = ["Dashboard", "New Job", "Deviation Review"]
        if st.session_state["selected_job_id"] is not None:
            nav_items.insert(1, "Job Workspace")
        if user_role == "admin":
            nav_items.append("Audit Log")

        nav_icons = {
            "Dashboard": "◻",
            "Job Workspace": "▸",
            "New Job": "+",
            "Deviation Review": "△",
            "Audit Log": "☰",
        }

        nav_labels = [f"{nav_icons.get(i, '·')}  {i}" for i in nav_items]
        current_nav = st.session_state.get("nav", "Dashboard")
        default_index = nav_items.index(current_nav) if current_nav in nav_items else 0

        nav_label = st.radio(
            "Navigation", nav_labels,
            index=default_index, label_visibility="collapsed",
        )
        nav = nav_items[nav_labels.index(nav_label)]

        st.markdown("---")

        # Logout
        if st.button("Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    st.session_state["nav"] = nav

    # ── Main area ────────────────────────────────────────────────────
    if nav == "Job Workspace":
        if st.session_state["selected_job_id"] is None:
            st.session_state["nav"] = "Dashboard"
            st.rerun()
        else:
            from frontend.views.job_workspace import render as render_workspace
            render_workspace()
    elif nav == "Dashboard":
        from frontend.views.dashboard import render as render_dashboard
        render_dashboard()
    elif nav == "New Job":
        from frontend.views.new_job import render as render_new_job
        render_new_job()
    elif nav == "Deviation Review":
        from frontend.views.deviation_review import render as render_deviation_review
        render_deviation_review()
    elif nav == "Audit Log":
        from frontend.views.audit_log import render as render_audit_log
        render_audit_log()
