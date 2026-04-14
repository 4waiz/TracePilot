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

    kpi_data = [
        ("Total", str(total), "total"),
        ("In Progress", str(in_progress), "progress"),
        ("Completed", str(completed), "completed"),
        ("Deviations", str(deviations), "deviation"),
    ]

    st.markdown(
        "<div class='dashboard-kpi-strip'>"
        + "".join(
            f"<div class='dashboard-kpi-card dashboard-kpi-card--{kind}'>"
            f"<div class='dashboard-kpi-value'>{value}</div>"
            f"<div class='dashboard-kpi-label'>{label}</div>"
            f"</div>"
            for label, value, kind in kpi_data
        )
        + "</div>",
        unsafe_allow_html=True,
    )

    # ── Job list ─────────────────────────────────────────────────────
    if not jobs:
        st.markdown(
            "<div class='dashboard-empty'>"
            "<div class='dashboard-empty-title'>No inspection jobs yet</div>"
            "<div class='dashboard-empty-subtitle'>Create one using New Job in the sidebar</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        return

    # Table card wrapper
    st.markdown(
        f"<div class='dashboard-table-card'>"
        f"<div class='dashboard-table-card-header'>"
        f"<span class='dashboard-table-card-title'>Jobs</span>"
        f"<span class='dashboard-table-card-count'>{len(jobs)}</span>"
        f"</div>"
        f"<div class='dashboard-table-header'>"
        f"<span class='dashboard-row-id'>ID</span>"
        f"<span class='dashboard-row-title'>Title</span>"
        f"<span class='dashboard-row-status'>Status</span>"
        f"<span class='dashboard-row-sensitivity'>Sensitivity</span>"
        f"</div>"
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
            f"<div class='dashboard-row'>"
            f"<span class='dashboard-row-id'>#{jid}</span>"
            f"<span class='dashboard-row-title'>{job.get('title', 'Untitled')}</span>"
            f"<span class='dashboard-row-status'>"
            f"{chip(status, status_color)}</span>"
            f"<span class='dashboard-row-sensitivity'>"
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
        f"<div class='dashboard-footer'>{len(jobs)} job(s)</div>",
        unsafe_allow_html=True,
    )
