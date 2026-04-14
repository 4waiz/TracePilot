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
    page_icon="logo2.png",
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

    # ── Top navbar with logo ─────────────────────────────────────────
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("logo2.png", width=250, use_container_width=False)

    # ── Sidebar ──────────────────────────────────────────────────────
    with st.sidebar:
        # Logo (centered)
        col_l, col_c, col_r = st.columns([1, 3, 1])
        with col_c:
            st.image("icon2.png", use_container_width=True)

        # Brand block
        st.markdown(
            "<div class='sidebar-brand'>"
            "<div class='sidebar-brand-name'>TracePilot</div>"
            "<div class='sidebar-brand-tagline'>Inspection &amp; Traceability</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown("---")

        # User block
        initial = username[0].upper() if username else "U"
        role_colors = {"admin": "#ff5622", "supervisor": "#22c55e", "operator": "#38bdf8"}
        rc = role_colors.get(user_role, "#64748b")
        st.markdown(
            f"<div class='sidebar-user'>"
            f"<div class='sidebar-avatar'>{initial}</div>"
            f"<div>"
            f"<div class='sidebar-user-name'>{username}</div>"
            f"<span class='sidebar-user-role' style='background:{rc}; color:#fff'>{user_role}</span>"
            f"</div></div>",
            unsafe_allow_html=True,
        )
        st.markdown("---")

        # Navigation
        nav_items = ["Dashboard", "New Job", "Deviation Review"]
        if st.session_state["selected_job_id"] is not None:
            nav_items.insert(1, "Job Workspace")
        if user_role == "admin":
            nav_items.append("Audit Log")

        current_nav = st.session_state.get("nav", "Dashboard")

        st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)
        for item in nav_items:
            is_active = (item == current_nav)
            if is_active:
                st.markdown(
                    f"<div style='padding:10px 16px; margin:2px 8px; border-radius:0 7px 7px 0; "
                    f"border-left:3px solid #ff5622; background:rgba(255,86,34,0.15); "
                    f"color:#ffffff; font-size:0.85rem; font-weight:600; cursor:pointer'>"
                    f"{item}</div>",
                    unsafe_allow_html=True,
                )
            if st.button(item, key=f"nav_{item}", use_container_width=True):
                st.session_state["nav"] = item
                st.rerun()

        nav = current_nav

        st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)

        # Logout
        if st.button("⏻  Sign Out", key="sidebar_logout", use_container_width=True):
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
