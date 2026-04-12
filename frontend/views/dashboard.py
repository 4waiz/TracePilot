"""Dashboard page -- job listing and job detail view."""

import streamlit as st
from frontend.api_client import api
from frontend.views.inspection import render as render_inspection


STATUS_COLORS = {
    "created": "#17a2b8",
    "uploading": "#6c757d",
    "extracting": "#ffc107",
    "review": "#fd7e14",
    "inspecting": "#6f42c1",
    "completed": "#28a745",
    "deviation": "#dc3545",
}

SENSITIVITY_COLORS = {
    "general": "#6c757d",
    "confidential": "#fd7e14",
    "highly_confidential": "#dc3545",
}


def _badge(text: str, color: str) -> str:
    return (
        f"<span style='background:{color}; color:#fff; padding:2px 10px; "
        f"border-radius:12px; font-size:0.85em; font-weight:600'>{text}</span>"
    )


# =========================================================================
# JOB LIST VIEW
# =========================================================================

def _render_job_list():
    token = st.session_state["token"]
    user = st.session_state.get("user", {})

    role = user.get("role", "user")
    st.markdown(
        f"### Welcome, {user.get('username', 'User')} "
        f"{_badge(role, '#17a2b8')}",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    data = api.list_jobs(token)
    if data is None:
        return

    jobs = data if isinstance(data, list) else []

    # KPI cards
    total = len(jobs)
    in_progress = sum(1 for j in jobs if j.get("status") in ("extracting", "review", "inspecting"))
    completed = sum(1 for j in jobs if j.get("status") == "completed")
    deviations = sum(1 for j in jobs if j.get("status") == "deviation")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Jobs", total)
    k2.metric("In Progress", in_progress)
    k3.metric("Completed", completed)
    k4.metric("Deviations", deviations)

    st.markdown("---")

    if not jobs:
        st.info("No inspection jobs yet. Create one from the sidebar.")
        return

    for job in jobs:
        jid = job.get("id")
        status = job.get("status", "created")
        sensitivity = job.get("sensitivity_label", "general")
        color = STATUS_COLORS.get(status, "#6c757d")
        sens_color = SENSITIVITY_COLORS.get(sensitivity, "#6c757d")

        c1, c2, c3, c4, c5 = st.columns([0.5, 2.5, 1.2, 1.2, 1])
        with c1:
            st.markdown(f"**#{jid}**")
        with c2:
            st.markdown(f"**{job.get('title', 'Untitled')}**")
        with c3:
            st.markdown(_badge(status, color), unsafe_allow_html=True)
        with c4:
            st.markdown(_badge(sensitivity.replace("_", " ").title(), sens_color), unsafe_allow_html=True)
        with c5:
            if st.button("Open", key=f"open_{jid}"):
                st.session_state["selected_job_id"] = jid
                st.rerun()

    st.caption(f"Showing {len(jobs)} job(s)")


# =========================================================================
# JOB DETAIL VIEW
# =========================================================================

def _render_job_detail(job_id: int):
    token = st.session_state["token"]

    job = api.get_job(token, job_id)
    if not job:
        st.error("Job not found.")
        if st.button("Back to Dashboard"):
            del st.session_state["selected_job_id"]
            st.rerun()
        return

    status = job.get("status", "created")
    col_back, col_title, col_status = st.columns([0.5, 3, 1])
    with col_back:
        if st.button("< Back"):
            del st.session_state["selected_job_id"]
            st.rerun()
    with col_title:
        st.subheader(job.get("title", "Untitled Job"))
    with col_status:
        color = STATUS_COLORS.get(status, "#6c757d")
        st.markdown(_badge(status.upper(), color), unsafe_allow_html=True)

    st.markdown("---")

    tab_docs, tab_specs, tab_inspect, tab_devs, tab_report = st.tabs(
        ["Documents", "Specs & Steps", "Inspection", "Deviations", "Report"]
    )

    with tab_docs:
        _render_documents_tab(token, job_id)
    with tab_specs:
        _render_specs_tab(token, job_id, status)
    with tab_inspect:
        render_inspection(job_id)
    with tab_devs:
        _render_deviations_tab(token, job_id)
    with tab_report:
        _render_report_tab(token, job_id)


def _render_documents_tab(token: str, job_id: int):
    docs = api.get_documents(token, job_id)

    if docs:
        doc_list = docs if isinstance(docs, list) else []
        if doc_list:
            for doc in doc_list:
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**{doc.get('original_filename', doc.get('filename', 'document'))}**")
                with c2:
                    size_kb = doc.get("file_size", 0) / 1024
                    st.caption(f"{size_kb:.1f} KB")
        else:
            st.info("No documents uploaded yet.")
    else:
        st.info("No documents uploaded yet.")

    st.markdown("---")
    uploaded = st.file_uploader(
        "Upload documents (PDF)", type=["pdf"],
        accept_multiple_files=True, key=f"doc_upload_{job_id}",
    )
    if uploaded and st.button("Upload", key=f"do_upload_{job_id}"):
        with st.spinner("Uploading..."):
            result = api.upload_documents(token, job_id, uploaded[:3])
        if result:
            st.success("Documents uploaded.")
            st.rerun()


def _render_specs_tab(token: str, job_id: int, status: str):
    specs = api.get_specs(token, job_id)
    steps = api.get_steps(token, job_id)

    spec_list = specs if isinstance(specs, list) else [] if specs is None else []
    step_list = steps if isinstance(steps, list) else [] if steps is None else []

    if not spec_list and status in ("created", "uploading"):
        st.info("Upload documents first, then click below to run AI extraction.")
        if st.button("Extract Specs & Steps", type="primary"):
            with st.spinner("Running AI extraction... this may take a moment."):
                result = api.trigger_extraction(token, job_id)
            if result:
                st.success(
                    f"Extraction complete! Found {result.get('specs_count', 0)} specs "
                    f"and {result.get('steps_count', 0)} steps (method: {result.get('method', 'unknown')})"
                )
                st.rerun()
        return

    if not spec_list:
        if status in ("extracting",):
            st.info("Extraction in progress...")
        else:
            st.info("No specifications found. Try running extraction again.")
            if st.button("Re-extract", type="primary"):
                with st.spinner("Running AI extraction..."):
                    result = api.trigger_extraction(token, job_id)
                if result:
                    st.success("Extraction complete!")
                    st.rerun()
        return

    st.markdown("#### Specifications")
    all_confirmed = all(s.get("confirmed_by_user", False) for s in spec_list)

    for i, spec in enumerate(spec_list):
        spec_id = spec.get("id")
        confirmed = spec.get("confirmed_by_user", False)

        with st.expander(
            f"{spec.get('characteristic', f'Spec {i+1}')} -- "
            f"{'Confirmed' if confirmed else 'Pending'}",
            expanded=not confirmed,
        ):
            if not confirmed:
                ec1, ec2 = st.columns(2)
                with ec1:
                    char_val = st.text_input("Characteristic", value=spec.get("characteristic", ""), key=f"char_{spec_id}")
                    nominal = st.number_input("Nominal", value=float(spec.get("nominal", 0)), format="%.4f", key=f"nom_{spec_id}")
                    unit = st.text_input("Unit", value=spec.get("unit", "mm"), key=f"unit_{spec_id}")
                with ec2:
                    usl = st.number_input("Upper Limit", value=float(spec.get("upper_limit", 0)), format="%.4f", key=f"usl_{spec_id}")
                    lsl = st.number_input("Lower Limit", value=float(spec.get("lower_limit", 0)), format="%.4f", key=f"lsl_{spec_id}")
                    tool = st.text_input("Tool Required", value=spec.get("tool_required", "") or "", key=f"tool_{spec_id}")

                confidence = spec.get("confidence", 0)
                if confidence:
                    st.caption(f"AI Confidence: {confidence:.0%}")

                bc1, bc2 = st.columns(2)
                with bc1:
                    if st.button("Save", key=f"save_{spec_id}"):
                        result = api.update_spec(token, spec_id, {
                            "characteristic": char_val,
                            "nominal": nominal,
                            "upper_limit": usl,
                            "lower_limit": lsl,
                            "unit": unit,
                            "tool_required": tool,
                        })
                        if result:
                            st.success("Spec updated.")
                            st.rerun()
                with bc2:
                    if st.button("Delete", key=f"del_{spec_id}"):
                        if api.delete_spec(token, spec_id):
                            st.success("Spec deleted.")
                            st.rerun()
            else:
                c1, c2, c3, c4 = st.columns(4)
                c1.markdown(f"**Nominal:** {spec.get('nominal', 'N/A')} {spec.get('unit', '')}")
                c2.markdown(f"**USL:** {spec.get('upper_limit', 'N/A')}")
                c3.markdown(f"**LSL:** {spec.get('lower_limit', 'N/A')}")
                c4.markdown(f"**Tool:** {spec.get('tool_required', 'N/A')}")

    # Add new spec
    st.markdown("---")
    with st.expander("Add New Specification"):
        ac1, ac2 = st.columns(2)
        with ac1:
            new_char = st.text_input("Characteristic Name", key="new_char")
            new_nominal = st.number_input("Nominal Value", format="%.4f", key="new_nom")
            new_unit = st.text_input("Unit", value="mm", key="new_unit")
        with ac2:
            new_usl = st.number_input("Upper Limit", format="%.4f", key="new_usl")
            new_lsl = st.number_input("Lower Limit", format="%.4f", key="new_lsl")
            new_tool = st.text_input("Measurement Tool", key="new_tool")

        if st.button("Add Spec"):
            if not new_char.strip():
                st.warning("Characteristic name is required.")
            else:
                result = api.add_spec(token, job_id, {
                    "characteristic": new_char.strip(),
                    "nominal": new_nominal,
                    "upper_limit": new_usl,
                    "lower_limit": new_lsl,
                    "unit": new_unit,
                    "tool_required": new_tool,
                })
                if result:
                    st.success("Spec added.")
                    st.rerun()

    # Confirm button
    if not all_confirmed and spec_list:
        st.markdown("---")
        if st.button("Confirm All Specifications", type="primary"):
            result = api.confirm_specs(token, job_id)
            if result:
                st.success("All specs confirmed. Ready for inspection.")
                st.rerun()

    # Steps display
    if step_list:
        st.markdown("---")
        st.markdown("#### Inspection Steps")
        for step in step_list:
            st.markdown(
                f"**Step {step.get('step_number', '?')}:** "
                f"{step.get('title', '')} -- {step.get('description', '')}"
            )


def _render_deviations_tab(token: str, job_id: int):
    devs = api.get_deviations(token, job_id)
    if not devs:
        st.success("No deviations recorded for this job.")
        return

    dev_list = devs if isinstance(devs, list) else []
    if not dev_list:
        st.success("No deviations recorded for this job.")
        return

    for dev in dev_list:
        dev_id = dev.get("id")
        dev_status = dev.get("status", "open")
        status_color = "#dc3545" if dev_status == "open" else "#28a745" if dev_status in ("approved", "accepted") else "#ffc107"

        with st.container():
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            with c1:
                st.markdown(f"**Deviation #{dev_id}** (Spec {dev.get('spec_id', 'N/A')})")
            with c2:
                st.markdown(f"Expected: {dev.get('expected_value', 'N/A')}")
            with c3:
                st.markdown(f"Actual: {dev.get('actual_value', 'N/A')}")
            with c4:
                st.markdown(_badge(dev_status.upper(), status_color), unsafe_allow_html=True)

        user = st.session_state.get("user", {})
        if user.get("role") in ("supervisor", "admin") and dev_status == "open":
            with st.expander(f"Review Deviation #{dev_id}"):
                action = st.radio(
                    "Decision",
                    ["Approve (use-as-is)", "Reject (rework)", "Conditional Accept"],
                    key=f"dev_action_{dev_id}",
                    horizontal=True,
                )
                notes = st.text_area("Notes", key=f"dev_notes_{dev_id}")
                if st.button("Submit", key=f"dev_submit_{dev_id}"):
                    action_map = {
                        "Approve (use-as-is)": "approved",
                        "Reject (rework)": "rejected",
                        "Conditional Accept": "conditional",
                    }
                    result = api.approve_deviation(token, dev_id, {
                        "disposition": action_map.get(action, "approved"),
                        "notes": notes,
                    })
                    if result:
                        st.success("Decision recorded.")
                        st.rerun()


def _render_report_tab(token: str, job_id: int):
    st.markdown("#### Inspection Report")
    st.info("Generate a full inspection report including all measurements, deviations, and approvals.")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Generate Report", type="primary"):
            with st.spinner("Generating report..."):
                result = api.generate_report(token, job_id)
            if result:
                st.session_state[f"report_{job_id}"] = result
                st.success("Report generated successfully!")
                st.rerun()

    report = st.session_state.get(f"report_{job_id}")
    if report:
        with c2:
            pdf_url = api.get_report_pdf_url(job_id)
            json_url = api.get_report_json_url(job_id)
            st.markdown(f"[Download PDF Report]({pdf_url})")
            st.markdown(f"[Download JSON Report]({json_url})")

        st.markdown("---")
        st.json(report)


# =========================================================================

def render():
    if "selected_job_id" in st.session_state:
        _render_job_detail(st.session_state["selected_job_id"])
    else:
        _render_job_list()
