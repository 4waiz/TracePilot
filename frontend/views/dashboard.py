"""Dashboard page -- job listing inbox."""

import streamlit as st
from frontend.api_client import api
from frontend.ui import C, chip, page_header, kpi_row, section_title, empty_state


def render():
    """Render the dashboard job list."""
    token = st.session_state["token"]
    user = st.session_state.get("user", {})
    role = user.get("role", "user")

    # ── Header ───────────────────────────────────────────────────────
    role_color = C.ACCENT if role == "admin" else C.SUCCESS if role == "supervisor" else C.TEXT_DIM
    page_header(
        "Dashboard",
        f"Welcome back, {user.get('username', 'User')}",
        f" <span style='margin-left:8px'>{chip(role, role_color)}</span>",
    )

    data = api.list_jobs(token)
    if data is None:
        return

    jobs = data if isinstance(data, list) else []

    # ── KPIs ─────────────────────────────────────────────────────────
    total = len(jobs)
    in_progress = sum(1 for j in jobs if j.get("status") in ("extracting", "review", "inspecting"))
    completed = sum(1 for j in jobs if j.get("status") == "completed")
    deviations = sum(1 for j in jobs if j.get("status") == "deviation")

    kpi_row([
        ("Total", str(total), C.TEXT),
        ("In Progress", str(in_progress), C.INFO),
        ("Completed", str(completed), C.SUCCESS),
        ("Deviations", str(deviations), C.DANGER if deviations else C.TEXT_MUTED),
    ])

    st.markdown("")  # spacer

    # ── Job list ─────────────────────────────────────────────────────
    if not jobs:
        empty_state("📋", "No inspection jobs yet", "Create one using + New Job in the sidebar")
        return

    section_title("Jobs", str(len(jobs)))

    # Table header
    st.markdown(
        f"<div style='display:flex; align-items:center; padding:6px 14px; "
        f"font-size:0.68rem; text-transform:uppercase; letter-spacing:0.07em; "
        f"color:{C.TEXT_MUTED}; font-weight:600; border-bottom:1px solid {C.BORDER}'>"
        f"<span style='width:48px'>ID</span>"
        f"<span style='flex:1'>Title</span>"
        f"<span style='width:110px; text-align:center'>Status</span>"
        f"<span style='width:130px; text-align:center'>Sensitivity</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    for job in jobs:
        jid = job.get("id")
        status = job.get("status", "created")
        sensitivity = job.get("sensitivity_label", "general")
        status_color = C.STATUS.get(status, C.TEXT_MUTED)
        sens_color = C.SENSITIVITY.get(sensitivity, C.TEXT_MUTED)

        # Data row
        st.markdown(
            f"<div style='display:flex; align-items:center; padding:9px 14px; "
            f"border-bottom:1px solid {C.BORDER}; transition:background 0.1s'>"
            f"<span style='width:48px; color:{C.TEXT_MUTED}; font-weight:600; "
            f"font-size:0.82rem'>#{jid}</span>"
            f"<span style='flex:1; font-weight:500; color:{C.TEXT}; "
            f"font-size:0.9rem'>{job.get('title', 'Untitled')}</span>"
            f"<span style='width:110px; text-align:center'>"
            f"{chip(status, status_color)}</span>"
            f"<span style='width:130px; text-align:center'>"
            f"{chip(sensitivity.replace('_', ' ').title(), sens_color, filled=False)}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Button row — tight, right-aligned
        _, btn_col = st.columns([6, 1])
        with btn_col:
            if st.button("Open →", key=f"open_{jid}", use_container_width=True):
                st.session_state["selected_job_id"] = jid
                st.session_state["workspace_phase"] = "Setup"
                st.session_state["nav"] = "Job Workspace"
                st.rerun()

    st.markdown(
        f"<div style='text-align:right; padding:8px 14px; font-size:0.72rem; "
        f"color:{C.TEXT_MUTED}'>{len(jobs)} job(s)</div>",
        unsafe_allow_html=True,
    )
