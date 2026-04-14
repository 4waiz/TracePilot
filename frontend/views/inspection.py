"""Guided inspection workflow page with re-measurement support."""

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

    # Build measurement lookup: spec_id -> list of measurements (latest last)
    measurements_by_spec: dict[int, list] = {}
    for m in measurement_list:
        sid = m.get("spec_id")
        measurements_by_spec.setdefault(sid, []).append(m)

    measured_spec_ids = set(measurements_by_spec.keys())

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
            _render_spec_measurement(token, job_id, spec, measurements_by_spec)

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
            _render_spec_measurement(token, job_id, spec, measurements_by_spec)

    # Complete inspection
    if progress and progress.get("measured", 0) >= progress.get("total_specs", 0) and progress.get("total_specs", 0) > 0:
        if progress.get("failed", 0) == 0 or job.get("status") != "deviation":
            st.markdown("---")
            if st.button("Complete Inspection", type="primary"):
                api.update_job_status(token, job_id, "completed")
                st.success("Inspection completed!")
                st.rerun()


def _render_spec_measurement(token, job_id, spec, measurements_by_spec):
    """Render a single spec with its measurement input or result, including re-measure option."""
    spec_id = spec.get("id")
    prev_measurements = measurements_by_spec.get(spec_id, [])
    already_measured = len(prev_measurements) > 0

    st.markdown(f"**{spec.get('characteristic', 'Unknown')}**")
    st.caption(
        f"Nominal: {spec.get('nominal', 0):.4f} {spec.get('unit', 'mm')}  |  "
        f"Limits: [{spec.get('lower_limit', 0):.4f}, {spec.get('upper_limit', 0):.4f}]"
    )
    if spec.get("tool_required"):
        st.caption(f"Tool: {spec['tool_required']}")

    if already_measured:
        m = prev_measurements[-1]  # latest measurement
        result_text = "PASS" if m.get("passed") else "FAIL"
        result_color = "#10b981" if m.get("passed") else "#ef4444"
        result_bg = "rgba(16,185,129,0.08)" if m.get("passed") else "rgba(239,68,68,0.08)"

        st.markdown(
            f"<div style='background:{result_bg}; border:1px solid {result_color}20; "
            f"border-radius:8px; padding:10px 16px; margin:4px 0 8px'>"
            f"<span style='font-size:0.92rem'>Measured: <strong>{m.get('actual_value', 0):.4f}</strong></span>"
            f"<span style='margin-left:12px; color:{result_color}; font-weight:700; "
            f"font-size:0.85rem'>{result_text}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Re-measure option (delete old + enter new)
        remeasure_key = f"remeasure_{spec_id}"
        if st.session_state.get(remeasure_key):
            st.caption("Enter the new measurement value:")
            new_val = st.number_input(
                f"New measurement for {spec.get('characteristic', '')}",
                format="%.4f", key=f"remeas_val_{spec_id}",
                label_visibility="collapsed",
            )
            col_submit, col_cancel = st.columns(2)
            with col_submit:
                if st.button("Submit", key=f"remeas_submit_{spec_id}", type="primary"):
                    # Delete old measurement, then record new
                    m_id = m.get("id")
                    api.delete_measurement(token, m_id)
                    result = api.submit_measurement(token, job_id, spec_id, new_val)
                    if result:
                        st.session_state[remeasure_key] = False
                        if result.get("passed"):
                            st.success(f"PASS -- {new_val:.4f} is within tolerance.")
                        else:
                            dev_info = result.get("deviation", {})
                            st.error(
                                f"FAIL -- {new_val:.4f} is out of tolerance! "
                                f"Deviation #{dev_info.get('id', '?')} created."
                            )
                        st.rerun()
            with col_cancel:
                if st.button("Cancel", key=f"remeas_cancel_{spec_id}"):
                    st.session_state[remeasure_key] = False
                    st.rerun()
        else:
            if st.button("Re-measure", key=f"remeas_btn_{spec_id}"):
                st.session_state[remeasure_key] = True
                st.rerun()
    else:
        value = st.number_input(
            f"Enter measurement for {spec.get('characteristic', '')}",
            format="%.4f", key=f"meas_{spec_id}",
        )
        if st.button("Submit Measurement", key=f"submit_meas_{spec_id}"):
            result = api.submit_measurement(token, job_id, spec_id, value)
            if result:
                if result.get("passed"):
                    st.success(f"PASS -- Value {value:.4f} is within tolerance.")
                else:
                    dev_info = result.get("deviation", {})
                    st.error(
                        f"FAIL -- Value {value:.4f} is out of tolerance! "
                        f"Deviation #{dev_info.get('id', '?')} created."
                    )
                st.rerun()
    st.markdown("---")
