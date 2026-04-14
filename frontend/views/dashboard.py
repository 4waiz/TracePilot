"""Dashboard page — EDGE Group style with section numbers and role guidance."""

import streamlit as st
from frontend.api_client import api
from frontend.ui import C, chip, page_header, section_number


_ROLE_GUIDANCE = {
    "operator": {
        "welcome": "Your workspace for creating and running inspections.",
        "actions": [
            ("New Job", "Create a new inspection job, upload drawings, extract specs"),
            ("Job Workspace", "Open any job to continue measuring and recording results"),
        ],
    },
    "supervisor": {
        "welcome": "You can create jobs and review deviations that need approval.",
        "actions": [
            ("Deviation Review", "Approve, reject, or conditionally accept out-of-tolerance measurements"),
            ("New Job", "Create an inspection job or assist operators"),
        ],
    },
    "admin": {
        "welcome": "Full system access including audit trail and all jobs.",
        "actions": [
            ("Deviation Review", "Review and approve deviations across all jobs"),
            ("Audit Log", "View the full audit trail of all system actions"),
        ],
    },
}


def render():
    """Render the dashboard job list."""
    token = st.session_state["token"]
    user = st.session_state.get("user", {})
    role = user.get("role", "operator")
    username = user.get("username", "User")

    # ── Section number + header ──────────────────────────────────────
    st.markdown(section_number("01"), unsafe_allow_html=True)
    page_header(
        "Dashboard",
        f"Welcome back, {username}",
        f" {chip(role, C.STATUS.get('created') if role == 'operator' else C.SUCCESS if role == 'supervisor' else C.ACCENT)}",
    )

    # ── Role guidance ────────────────────────────────────────────────
    guide = _ROLE_GUIDANCE.get(role, _ROLE_GUIDANCE["operator"])
    st.markdown(
        f"<div style='background:{C.BG_SURFACE}; border:1px solid {C.BORDER}; border-radius:4px; "
        f"padding:16px 22px; margin-bottom:24px; font-size:0.88rem; color:{C.TEXT_DIM}'>"
        f"<strong style='color:{C.TEXT}'>{guide['welcome']}</strong>"
        f"<div style='display:flex; gap:10px; flex-wrap:wrap; margin-top:10px'>"
        + "".join(
            f"<span style='background:{C.BG_BASE}; border:1px solid {C.BORDER}; border-radius:3px; "
            f"padding:8px 14px; font-size:0.75rem; line-height:1.3'>"
            f"<strong style='color:{C.ACCENT}'>{name}</strong>"
            f"<span style='color:{C.TEXT_MUTED}; margin-left:4px'>-- {desc}</span></span>"
            for name, desc in guide["actions"]
        )
        + "</div></div>",
        unsafe_allow_html=True,
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
            "<div class='dashboard-empty-subtitle'>Create one using <strong>New Job</strong> in the sidebar</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        return

    # Filter
    _, filter_col = st.columns([3, 1])
    with filter_col:
        status_filter = st.selectbox(
            "Filter",
            ["All", "created", "extracting", "review", "inspecting", "deviation", "completed"],
            key="dash_status_filter",
            label_visibility="collapsed",
        )

    filtered_jobs = [j for j in jobs if j.get("status") == status_filter] if status_filter != "All" else jobs

    # Table
    st.markdown(
        f"<div class='dashboard-table-card'>"
        f"<div class='dashboard-table-card-header'>"
        f"<span class='dashboard-table-card-title'>Inspection Jobs</span>"
        f"<span class='dashboard-table-card-count'>{len(filtered_jobs)}</span>"
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

    for job in filtered_jobs:
        jid = job.get("id")
        status = job.get("status", "created")
        sensitivity = job.get("sensitivity_label", "general")
        status_color = C.STATUS.get(status, C.TEXT_MUTED)
        sens_color = C.SENSITIVITY.get(sensitivity, C.TEXT_MUTED)

        st.markdown(
            f"<div class='dashboard-row'>"
            f"<span class='dashboard-row-id'>#{jid}</span>"
            f"<span class='dashboard-row-title'>{job.get('title', 'Untitled')}</span>"
            f"<span class='dashboard-row-status'>{chip(status, status_color)}</span>"
            f"<span class='dashboard-row-sensitivity'>"
            f"{chip(sensitivity.replace('_', ' ').title(), sens_color, filled=False)}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        _, btn_col = st.columns([6, 1])
        with btn_col:
            if st.button("Open", key=f"open_{jid}", use_container_width=True):
                st.session_state["selected_job_id"] = jid
                st.session_state["workspace_phase"] = "Setup"
                st.session_state["nav"] = "Job Workspace"
                st.rerun()

    st.markdown(
        f"<div class='dashboard-footer'>{len(filtered_jobs)} job(s)"
        f"{' (filtered)' if status_filter != 'All' else ''}</div>",
        unsafe_allow_html=True,
    )
