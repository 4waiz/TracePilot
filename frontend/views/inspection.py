"""Guided inspection workflow page."""

import streamlit as st
from frontend.api_client import api


def render(job_id: int):
    """Render the guided inspection workflow for a job."""
    token = st.session_state.get("token")
    if not token:
        st.warning("Please log in first.")
        return

    job = api.get_job(token, job_id)
    if not job:
        st.error("Job not found.")
        return

    if job.get("status") not in ("inspecting", "deviation", "completed"):
        st.info("Please confirm all specs before starting inspection.")
        return

    specs = api.get_specs(token, job_id)
    steps = api.get_steps(token, job_id)
    measurements = api.get_measurements(token, job_id)
    progress = api.get_progress(token, job_id)

    spec_list = specs if isinstance(specs, list) else []
    step_list = steps if isinstance(steps, list) else []
    measurement_list = measurements if isinstance(measurements, list) else []

    confirmed_specs = [s for s in spec_list if s.get("confirmed_by_user", False)]

    if not confirmed_specs:
        st.info("No confirmed specs to inspect.")
        return

    # Progress
    if progress:
        total = progress.get("total_specs", 0)
        measured = progress.get("measured", 0)
        passed = progress.get("passed", 0)
        failed = progress.get("failed", 0)

        if total > 0:
            st.progress(min(measured / total, 1.0), text=f"Progress: {measured}/{total} measured")
        p1, p2, p3 = st.columns(3)
        p1.metric("Measured", measured)
        p2.metric("Passed", passed)
        p3.metric("Failed", failed)
    st.markdown("---")

    measured_spec_ids = {m.get("spec_id") for m in measurement_list}

    step_key = f"current_step_{job_id}"
    if step_key not in st.session_state:
        st.session_state[step_key] = 0

    if step_list:
        current_idx = min(st.session_state.get(step_key, 0), len(step_list) - 1)
        step = step_list[current_idx]

        st.markdown(f"### Step {step.get('step_number', current_idx + 1)}: {step.get('title', '')}")
        st.markdown(step.get("description", ""))

        if step.get("source_document") or step.get("source_snippet"):
            with st.expander("Source Reference"):
                if step.get("source_document"):
                    st.caption(f"Document: {step['source_document']}, Page: {step.get('source_page', '?')}")
                if step.get("source_snippet"):
                    st.text(step["source_snippet"])

        spec_char = step.get("spec_characteristic", "")
        linked_specs = [s for s in confirmed_specs if s.get("characteristic") == spec_char] if spec_char else []
        if not linked_specs:
            linked_specs = [s for s in confirmed_specs if s.get("id") not in measured_spec_ids]

        for spec in linked_specs[:3]:
            _render_spec_measurement(token, job_id, spec, measurement_list, measured_spec_ids)

        # Navigation
        nav1, _, nav3 = st.columns(3)
        with nav1:
            if current_idx > 0 and st.button("Previous Step"):
                st.session_state[step_key] = current_idx - 1
                st.rerun()
        with nav3:
            if current_idx < len(step_list) - 1 and st.button("Next Step"):
                st.session_state[step_key] = current_idx + 1
                st.rerun()
    else:
        st.markdown("### Measure All Specifications")
        for spec in confirmed_specs:
            _render_spec_measurement(token, job_id, spec, measurement_list, measured_spec_ids)

    # Complete inspection
    if progress and progress.get("measured", 0) >= progress.get("total_specs", 0) and progress.get("total_specs", 0) > 0:
        if progress.get("failed", 0) == 0 or job.get("status") != "deviation":
            st.markdown("---")
            if st.button("Complete Inspection", type="primary"):
                api.update_job_status(token, job_id, "completed")
                st.success("Inspection completed!")
                st.rerun()


def _render_spec_measurement(token, job_id, spec, measurement_list, measured_spec_ids):
    spec_id = spec.get("id")
    already_measured = spec_id in measured_spec_ids

    st.markdown(f"**{spec.get('characteristic', 'Unknown')}**")
    st.caption(
        f"Nominal: {spec.get('nominal', 0):.4f} {spec.get('unit', 'mm')} | "
        f"Limits: [{spec.get('lower_limit', 0):.4f}, {spec.get('upper_limit', 0):.4f}]"
    )
    if spec.get("tool_required"):
        st.caption(f"Tool: {spec['tool_required']}")

    if already_measured:
        prev = [m for m in measurement_list if m.get("spec_id") == spec_id]
        if prev:
            m = prev[-1]
            result_text = "PASS" if m.get("passed") else "FAIL"
            result_color = "#28a745" if m.get("passed") else "#dc3545"
            st.markdown(
                f"Measured: **{m.get('actual_value', 0):.4f}** -- "
                f"<span style='color:{result_color}; font-weight:bold'>{result_text}</span>",
                unsafe_allow_html=True,
            )
    else:
        value = st.number_input(
            f"Enter measurement for {spec.get('characteristic', '')}",
            format="%.4f", key=f"meas_{spec_id}",
        )
        if st.button("Submit Measurement", key=f"submit_meas_{spec_id}"):
            result = api.submit_measurement(token, job_id, spec_id, value)
            if result:
                if result.get("passed"):
                    st.success(f"PASS - Value {value:.4f} is within tolerance.")
                else:
                    dev_info = result.get("deviation", {})
                    st.error(
                        f"FAIL - Value {value:.4f} is out of tolerance! "
                        f"Deviation created (#{dev_info.get('id', '?')})"
                    )
                st.rerun()
    st.markdown("---")
