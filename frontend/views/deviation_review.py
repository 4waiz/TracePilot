"""Deviation review page (supervisor)."""

import streamlit as st
from frontend.api_client import api


def render():
    """Render the deviation review interface."""
    token = st.session_state["token"]

    st.header("Deviation Review")
    st.markdown("---")

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

    if not open_devs:
        st.success("No open deviations. All inspections are passing.")
        return

    st.warning(f"**{len(open_devs)}** open deviation(s) require review.")
    st.markdown("---")

    for dev in open_devs:
        dev_id = dev.get("id")
        with st.container():
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                st.markdown(f"**Job:** {dev.get('_job_title', 'N/A')}")
                st.markdown(f"**Spec ID:** {dev.get('spec_id', 'N/A')}")
            with c2:
                st.metric("Expected", f"{dev.get('expected_value', 'N/A')}")
            with c3:
                st.metric("Actual", f"{dev.get('actual_value', 'N/A')}")

            with st.expander(f"Take Action (Deviation #{dev_id})", expanded=False):
                action = st.radio(
                    "Disposition",
                    options=["Approve (use-as-is)", "Reject (rework)", "Conditional Accept"],
                    key=f"action_{dev_id}", horizontal=True,
                )
                notes = st.text_area(
                    "Notes / Justification", key=f"notes_{dev_id}",
                    placeholder="Enter your review notes...",
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

            st.markdown("---")
