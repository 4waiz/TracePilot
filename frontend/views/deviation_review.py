"""Deviation review page — EDGE Group design."""

import streamlit as st
from frontend.api_client import api
from frontend.ui import C, chip, page_header, section_number, section_title


def render():
    """Render the deviation review interface."""
    token = st.session_state["token"]
    user = st.session_state.get("user", {})
    role = user.get("role", "operator")

    st.markdown(section_number("02"), unsafe_allow_html=True)
    page_header(
        "Deviation Review",
        "Review and disposition out-of-tolerance measurements",
    )

    jobs = api.list_jobs(token)
    if not jobs:
        st.info("No jobs found.")
        return

    if isinstance(jobs, dict):
        jobs = jobs.get("items", [])

    all_deviations = []
    for job in jobs:
        jid = job.get("id")
        devs = api.get_deviations(token, jid)
        if devs:
            dev_list = devs if isinstance(devs, list) else []
            for d in dev_list:
                d["_job_title"] = job.get("title", f"Job {jid}")
                d["_job_id"] = jid
            all_deviations.extend(dev_list)

    open_devs = [d for d in all_deviations if d.get("status") == "open"]
    resolved_devs = [d for d in all_deviations if d.get("status") != "open"]

    # KPIs
    k1, k2, k3 = st.columns(3)
    k1.metric("Open", len(open_devs))
    k2.metric("Resolved", len(resolved_devs))
    k3.metric("Total", len(all_deviations))

    if not all_deviations:
        st.markdown(
            f"<div style='text-align:center; padding:3rem; color:{C.TEXT_MUTED}'>"
            f"<div style='font-size:0.9rem; font-weight:700; text-transform:uppercase; "
            f"letter-spacing:0.08em; color:{C.SUCCESS}'>All Clear</div>"
            f"<div style='font-size:0.82rem; margin-top:4px; font-weight:300'>"
            f"No deviations found. All inspections are passing.</div></div>",
            unsafe_allow_html=True,
        )
        return

    # Open
    if open_devs:
        st.markdown(
            f"<div style='background:{C.DANGER_DIM}; border-left:3px solid {C.DANGER}; "
            f"border-radius:0 4px 4px 0; padding:12px 18px; margin:16px 0; font-size:0.88rem'>"
            f"<strong style='color:{C.DANGER}'>{len(open_devs)} open deviation(s)</strong>"
            f"<span style='color:{C.TEXT_MUTED}; margin-left:8px'>require review</span></div>",
            unsafe_allow_html=True,
        )

        can_approve = role in ("supervisor", "admin")

        for dev in open_devs:
            dev_id = dev.get("id")
            with st.container():
                c1, c2, c3, c4 = st.columns([2.5, 1, 1, 0.5])
                with c1:
                    st.markdown(
                        f"**{dev.get('_job_title', 'N/A')}** "
                        f"<span style='color:{C.TEXT_MUTED}; font-size:0.78rem'>"
                        f"Deviation #{dev_id}</span>",
                        unsafe_allow_html=True,
                    )
                with c2:
                    st.metric("Expected", f"{dev.get('expected_value', 'N/A')}")
                with c3:
                    st.metric("Actual", f"{dev.get('actual_value', 'N/A')}")
                with c4:
                    st.markdown(chip("open", C.DANGER), unsafe_allow_html=True)

                if can_approve:
                    with st.expander(f"Take Action -- Deviation #{dev_id}", expanded=False):
                        action = st.radio(
                            "Disposition",
                            options=["Approve (use-as-is)", "Reject (rework)", "Conditional Accept"],
                            key=f"action_{dev_id}", horizontal=True,
                        )
                        notes = st.text_area(
                            "Notes / Justification", key=f"notes_{dev_id}",
                            placeholder="Explain your decision (required)...",
                        )
                        if st.button("Submit Decision", key=f"decide_{dev_id}", type="primary"):
                            if not notes.strip():
                                st.warning("Please add notes to justify your decision.")
                            else:
                                action_map = {
                                    "Approve (use-as-is)": "approved",
                                    "Reject (rework)": "rejected",
                                    "Conditional Accept": "conditional",
                                }
                                result = api.approve_deviation(token, dev_id, {
                                    "disposition": action_map.get(action, "approved"),
                                    "notes": notes.strip(),
                                })
                                if result:
                                    st.success(f"Deviation #{dev_id} -- decision recorded.")
                                    st.rerun()
                else:
                    st.caption("Awaiting supervisor review.")

                st.markdown("---")
    else:
        st.success("No open deviations -- all resolved.")

    # Resolved
    if resolved_devs:
        with st.expander(f"Resolved Deviations ({len(resolved_devs)})", expanded=False):
            for dev in resolved_devs:
                dev_status = dev.get("status", "unknown")
                color = (
                    C.SUCCESS if dev_status == "approved"
                    else C.WARNING if dev_status == "conditional"
                    else C.DANGER if dev_status == "rejected"
                    else C.TEXT_MUTED
                )
                st.markdown(
                    f"<div style='display:flex; align-items:center; gap:12px; padding:8px 0; "
                    f"border-bottom:1px solid {C.BORDER}; font-size:0.82rem'>"
                    f"<span style='font-weight:700; color:{C.TEXT}'>#{dev.get('id')}</span>"
                    f"<span style='color:{C.TEXT_MUTED}'>{dev.get('_job_title', '')}</span>"
                    f"<span style='color:{C.TEXT_LIGHT}'>Exp: {dev.get('expected_value', '?')}</span>"
                    f"<span>Actual: {dev.get('actual_value', '?')}</span>"
                    f"<span style='margin-left:auto'>{chip(dev_status, color)}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
