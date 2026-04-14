"""Job Workspace -- dedicated workflow page for a single inspection job."""

import streamlit as st
from frontend.api_client import api
from frontend.views.inspection import render as render_inspection
from frontend.ui import C, chip, guidance, page_header, section_title, progress_track, empty_state


PHASES = ["Setup", "Extraction", "Spec Review", "Inspection", "Deviations", "Report"]


def _compute_phase_status(token: str, job_id: int, job: dict) -> dict:
    """Compute completion status for each phase."""
    status = job.get("status", "created")

    docs = api.get_documents(token, job_id)
    doc_list = docs if isinstance(docs, list) else []
    has_docs = len(doc_list) > 0

    specs = api.get_specs(token, job_id)
    spec_list = specs if isinstance(specs, list) else []
    has_specs = len(spec_list) > 0

    all_confirmed = has_specs and all(s.get("confirmed_by_user", False) for s in spec_list)

    progress = api.get_progress(token, job_id) if all_confirmed else None
    all_measured = False
    if progress:
        total = progress.get("total_specs", 0)
        measured = progress.get("measured", 0)
        all_measured = total > 0 and measured >= total

    devs = api.get_deviations(token, job_id) if all_confirmed else None
    dev_list = devs if isinstance(devs, list) else []
    open_devs = [d for d in dev_list if d.get("status") == "open"]
    devs_clear = len(open_devs) == 0

    report_generated = st.session_state.get(f"ws_report_{job_id}") is not None

    return {
        "docs": doc_list,
        "specs": spec_list,
        "progress": progress,
        "dev_list": dev_list,
        "open_devs": open_devs,
        "status": status,
        "Setup": has_docs,
        "Extraction": has_specs,
        "Spec Review": all_confirmed,
        "Inspection": all_measured,
        "Deviations": devs_clear and all_measured,
        "Report": report_generated,
    }


def render():
    """Render the job workspace page."""
    job_id = st.session_state.get("selected_job_id")

    if job_id is None:
        st.warning("No job selected. Returning to Dashboard.")
        st.session_state["nav"] = "Dashboard"
        st.rerun()
        return

    if "workspace_phase" not in st.session_state:
        st.session_state["workspace_phase"] = "Setup"

    token = st.session_state["token"]
    job = api.get_job(token, job_id)
    if not job:
        st.error("Job not found.")
        if st.button("← Back to Dashboard"):
            st.session_state["selected_job_id"] = None
            st.session_state.pop("workspace_phase", None)
            st.session_state["nav"] = "Dashboard"
            st.rerun()
        return

    ps = _compute_phase_status(token, job_id, job)
    status = ps["status"]
    status_color = C.STATUS.get(status, C.TEXT_MUTED)

    # ── Header ───────────────────────────────────────────────────────
    col_title, col_close = st.columns([5, 1])
    with col_title:
        st.markdown(
            f"<div>"
            f"<h1 style='margin:0; font-size:1.4rem !important; color:#434b51'>"
            f"{job.get('title', 'Untitled Job')}</h1>"
            f"<span style='color:#8a9199; font-size:0.82rem'>Job #{job_id}</span>"
            f"  {chip(status, status_color)}"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col_close:
        if st.button("✕ Close", use_container_width=True):
            st.session_state["selected_job_id"] = None
            st.session_state.pop("workspace_phase", None)
            st.session_state["nav"] = "Dashboard"
            st.rerun()

    # ── Progress track ───────────────────────────────────────────────
    progress_track(PHASES, ps, st.session_state["workspace_phase"])

    # ── Phase selector ───────────────────────────────────────────────
    phase = st.radio(
        "Phase",
        PHASES,
        index=PHASES.index(st.session_state["workspace_phase"]),
        horizontal=True,
        label_visibility="collapsed",
    )
    st.session_state["workspace_phase"] = phase

    st.markdown("")

    # ── Phase dispatch ───────────────────────────────────────────────
    if phase == "Setup":
        _render_setup(token, job_id, ps)
    elif phase == "Extraction":
        _render_extraction(token, job_id, ps)
    elif phase == "Spec Review":
        _render_spec_review(token, job_id, ps)
    elif phase == "Inspection":
        _render_inspection(job_id, ps)
    elif phase == "Deviations":
        _render_deviations(token, job_id, ps)
    elif phase == "Report":
        _render_report(token, job_id, ps)


# ═════════════════════════════════════════════════════════════════════════
# SETUP
# ═════════════════════════════════════════════════════════════════════════

def _render_setup(token, job_id, ps):
    doc_list = ps["docs"]

    if doc_list:
        guidance("✓", f"<strong>{len(doc_list)}</strong> document(s) uploaded — proceed to <strong>Extraction</strong>", "success")
    else:
        guidance("1", "Upload job documents (drawings, job cards, SOPs) to begin the workflow.", "info")

    section_title("Documents", str(len(doc_list)) if doc_list else "0")

    if doc_list:
        for doc in doc_list:
            fname = doc.get("original_filename", doc.get("filename", "document"))
            size_kb = doc.get("file_size", 0) / 1024
            st.markdown(
                f"<div style='display:flex; justify-content:space-between; align-items:center; "
                f"padding:8px 12px; background:{C.BG_RAISED}; border:1px solid {C.BORDER}; "
                f"border-radius:6px; margin-bottom:4px; font-size:0.88rem'>"
                f"<span style='color:{C.TEXT}'>📄 {fname}</span>"
                f"<span style='color:{C.TEXT_MUTED}; font-size:0.78rem'>{size_kb:.1f} KB</span></div>",
                unsafe_allow_html=True,
            )
    else:
        empty_state("📂", "No documents uploaded", "Upload PDFs below to get started")

    st.markdown("")
    uploaded = st.file_uploader(
        "Upload documents (PDF)", type=["pdf"],
        accept_multiple_files=True, key=f"ws_doc_upload_{job_id}",
    )
    if uploaded and len(uploaded) > 3:
        st.warning("Maximum 3 files. Only the first 3 will be uploaded.")
    if uploaded and st.button("Upload Documents", key=f"ws_do_upload_{job_id}", type="primary"):
        with st.spinner("Uploading..."):
            result = api.upload_documents(token, job_id, uploaded[:3])
        if result:
            st.success("Documents uploaded.")
            st.rerun()
        else:
            st.error("Upload failed. Please try again.")


# ═════════════════════════════════════════════════════════════════════════
# EXTRACTION
# ═════════════════════════════════════════════════════════════════════════

def _render_extraction(token, job_id, ps):
    spec_list = ps["specs"]
    status = ps["status"]
    has_docs = ps["Setup"]

    if spec_list:
        guidance("✓", f"Extraction complete — <strong>{len(spec_list)}</strong> spec(s) found. Proceed to <strong>Spec Review</strong>.", "success")
        steps = api.get_steps(token, job_id)
        step_list = steps if isinstance(steps, list) else []
        if step_list:
            st.caption(f"{len(step_list)} inspection step(s) extracted.")
        with st.expander("Re-run extraction (overwrites existing)"):
            if st.button("Re-extract", key="ws_re_extract"):
                with st.spinner("Running AI extraction..."):
                    result = api.trigger_extraction(token, job_id)
                if result:
                    st.success(f"Found {result.get('specs_count', 0)} specs, {result.get('steps_count', 0)} steps.")
                    st.rerun()
                else:
                    st.error("Extraction failed. Check documents and backend.")
        return

    if status == "extracting":
        guidance("⏳", "Extraction is in progress...", "warning")
        return

    if not has_docs:
        guidance("!", "No documents uploaded. Go to <strong>Setup</strong> first.", "warning")
        return

    guidance("2", "Run AI extraction to detect specifications from uploaded documents.", "info")

    section_title("AI Extraction")
    if st.button("Extract Specs & Steps", type="primary", key="ws_extract"):
        with st.spinner("Running AI extraction..."):
            result = api.trigger_extraction(token, job_id)
        if result:
            st.success(f"Found {result.get('specs_count', 0)} specs, {result.get('steps_count', 0)} steps.")
            st.rerun()
        else:
            st.error("Extraction failed. Check documents and backend.")


# ═════════════════════════════════════════════════════════════════════════
# SPEC REVIEW
# ═════════════════════════════════════════════════════════════════════════

def _render_spec_review(token, job_id, ps):
    spec_list = ps["specs"]

    if not spec_list:
        guidance("!", "No specs found. Run <strong>Extraction</strong> first.", "warning")
        return

    all_confirmed = all(s.get("confirmed_by_user", False) for s in spec_list)
    pending = sum(1 for s in spec_list if not s.get("confirmed_by_user", False))

    if all_confirmed:
        guidance("✓", f"All <strong>{len(spec_list)}</strong> spec(s) confirmed — proceed to <strong>Inspection</strong>.", "success")
    else:
        guidance("3", f"<strong>{pending}</strong> spec(s) pending review. Edit if needed, then confirm all.", "info")

    section_title("Specifications", str(len(spec_list)))

    steps = api.get_steps(token, job_id)
    step_list = steps if isinstance(steps, list) else []

    for i, spec in enumerate(spec_list):
        spec_id = spec.get("id")
        confirmed = spec.get("confirmed_by_user", False)
        icon = "✓" if confirmed else "·"
        label = "Confirmed" if confirmed else "Pending"
        label_color = C.SUCCESS if confirmed else C.WARNING

        with st.expander(
            f"{icon}  {spec.get('characteristic', f'Spec {i+1}')}  —  {label}",
            expanded=not confirmed,
        ):
            if not confirmed:
                ec1, ec2 = st.columns(2)
                with ec1:
                    char_val = st.text_input("Characteristic", value=spec.get("characteristic", ""), key=f"ws_char_{spec_id}")
                    nominal = st.number_input("Nominal", value=float(spec.get("nominal", 0)), format="%.4f", key=f"ws_nom_{spec_id}")
                    unit = st.text_input("Unit", value=spec.get("unit", "mm"), key=f"ws_unit_{spec_id}")
                with ec2:
                    usl = st.number_input("Upper Limit", value=float(spec.get("upper_limit", 0)), format="%.4f", key=f"ws_usl_{spec_id}")
                    lsl = st.number_input("Lower Limit", value=float(spec.get("lower_limit", 0)), format="%.4f", key=f"ws_lsl_{spec_id}")
                    tool = st.text_input("Tool Required", value=spec.get("tool_required", "") or "", key=f"ws_tool_{spec_id}")

                confidence = spec.get("confidence", 0)
                if confidence:
                    st.caption(f"AI Confidence: {confidence:.0%}")

                bc1, bc2 = st.columns(2)
                with bc1:
                    if st.button("Save", key=f"ws_save_{spec_id}"):
                        result = api.update_spec(token, spec_id, {
                            "characteristic": char_val, "nominal": nominal,
                            "upper_limit": usl, "lower_limit": lsl,
                            "unit": unit, "tool_required": tool,
                        })
                        if result:
                            st.success("Saved."); st.rerun()
                        else:
                            st.error("Failed to save.")
                with bc2:
                    if st.button("Delete", key=f"ws_del_{spec_id}"):
                        if api.delete_spec(token, spec_id):
                            st.success("Deleted."); st.rerun()
                        else:
                            st.error("Failed to delete.")
            else:
                c1, c2, c3, c4 = st.columns(4)
                c1.markdown(f"**Nominal:** {spec.get('nominal', 'N/A')} {spec.get('unit', '')}")
                c2.markdown(f"**USL:** {spec.get('upper_limit', 'N/A')}")
                c3.markdown(f"**LSL:** {spec.get('lower_limit', 'N/A')}")
                c4.markdown(f"**Tool:** {spec.get('tool_required', 'N/A')}")

    # Add new spec
    st.markdown("---")
    with st.expander("+ Add New Specification"):
        ac1, ac2 = st.columns(2)
        with ac1:
            new_char = st.text_input("Characteristic", key="ws_new_char")
            new_nominal = st.number_input("Nominal", format="%.4f", key="ws_new_nom")
            new_unit = st.text_input("Unit", value="mm", key="ws_new_unit")
        with ac2:
            new_usl = st.number_input("Upper Limit", format="%.4f", key="ws_new_usl")
            new_lsl = st.number_input("Lower Limit", format="%.4f", key="ws_new_lsl")
            new_tool = st.text_input("Tool", key="ws_new_tool")

        if st.button("Add Spec", key="ws_add_spec"):
            if not new_char.strip():
                st.warning("Characteristic name required.")
            else:
                result = api.add_spec(token, job_id, {
                    "characteristic": new_char.strip(), "nominal": new_nominal,
                    "upper_limit": new_usl, "lower_limit": new_lsl,
                    "unit": new_unit, "tool_required": new_tool,
                })
                if result:
                    st.success("Added."); st.rerun()
                else:
                    st.error("Failed to add.")

    # Confirm all
    if not all_confirmed and spec_list:
        st.markdown("---")
        if st.button("Confirm All Specifications", type="primary", key="ws_confirm_all"):
            result = api.confirm_specs(token, job_id)
            if result:
                st.success("All specs confirmed."); st.rerun()
            else:
                st.error("Failed to confirm.")

    # Steps
    if step_list:
        st.markdown("---")
        section_title("Inspection Steps", str(len(step_list)))
        for step in step_list:
            st.markdown(
                f"**Step {step.get('step_number', '?')}:** "
                f"{step.get('title', '')} — {step.get('description', '')}"
            )


# ═════════════════════════════════════════════════════════════════════════
# INSPECTION
# ═════════════════════════════════════════════════════════════════════════

def _render_inspection(job_id, ps):
    status = ps["status"]

    if not ps["Spec Review"] or status not in ("inspecting", "deviation", "completed"):
        guidance("🔒", "Confirm all specs in <strong>Spec Review</strong> to unlock inspection.", "warning")
        return

    if ps["Inspection"]:
        guidance("✓", "All measurements submitted.", "success")
    else:
        guidance("4", "Enter measurements for each spec. Pass/fail is automatic.", "info")

    render_inspection(job_id)


# ═════════════════════════════════════════════════════════════════════════
# DEVIATIONS
# ═════════════════════════════════════════════════════════════════════════

def _render_deviations(token, job_id, ps):
    dev_list = ps["dev_list"]
    open_devs = ps["open_devs"]
    user = st.session_state.get("user", {})
    role = user.get("role", "operator")

    if not dev_list:
        guidance("✓", "No deviations — all measurements within tolerance.", "success")
        return

    if open_devs:
        guidance("!", f"<strong>{len(open_devs)}</strong> open deviation(s) need review.", "warning")
    else:
        guidance("✓", f"All <strong>{len(dev_list)}</strong> deviation(s) resolved.", "success")

    section_title("Deviations", f"{len(open_devs)} open / {len(dev_list)} total")

    for dev in dev_list:
        dev_id = dev.get("id")
        dev_status = dev.get("status", "open")
        color = C.DANGER if dev_status == "open" else C.SUCCESS if dev_status in ("approved", "accepted") else C.WARNING

        st.markdown(
            f"<div style='display:flex; align-items:center; gap:12px; padding:9px 14px; "
            f"border-bottom:1px solid {C.BORDER}; font-size:0.88rem'>"
            f"<span style='font-weight:600; color:{C.TEXT}'>#{dev_id}</span>"
            f"<span style='color:{C.TEXT_DIM}'>Spec {dev.get('spec_id', '?')}</span>"
            f"<span style='color:{C.TEXT_DIM}'>Exp: {dev.get('expected_value', 'N/A')}</span>"
            f"<span style='color:{C.TEXT}'>→ {dev.get('actual_value', 'N/A')}</span>"
            f"<span style='margin-left:auto'>{chip(dev_status, color)}</span></div>",
            unsafe_allow_html=True,
        )

        if role in ("supervisor", "admin") and dev_status == "open":
            with st.expander(f"Review #{dev_id}"):
                action = st.radio(
                    "Decision",
                    ["Approve (use-as-is)", "Reject (rework)", "Conditional Accept"],
                    key=f"ws_dev_action_{dev_id}", horizontal=True,
                )
                notes = st.text_area("Notes", key=f"ws_dev_notes_{dev_id}")
                if st.button("Submit", key=f"ws_dev_submit_{dev_id}", type="primary"):
                    if not notes.strip():
                        st.warning("Notes required.")
                    else:
                        action_map = {"Approve (use-as-is)": "approved", "Reject (rework)": "rejected", "Conditional Accept": "conditional"}
                        result = api.approve_deviation(token, dev_id, {"disposition": action_map.get(action, "approved"), "notes": notes.strip()})
                        if result:
                            st.success("Recorded."); st.rerun()

    if role == "operator" and open_devs:
        st.info("Open deviations require supervisor review.")


# ═════════════════════════════════════════════════════════════════════════
# REPORT
# ═════════════════════════════════════════════════════════════════════════

def _render_report(token, job_id, ps):
    report = st.session_state.get(f"ws_report_{job_id}")

    if report:
        guidance("✓", "Report ready — download below.", "success")
    else:
        guidance("6", "Generate the final inspection report (PDF + JSON traceability pack).", "info")

    section_title("Inspection Report")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Generate Report", type="primary", key="ws_gen_report"):
            with st.spinner("Generating..."):
                result = api.generate_report(token, job_id)
            if result:
                st.session_state[f"ws_report_{job_id}"] = result
                st.success("Report generated."); st.rerun()
            else:
                st.error("Generation failed.")

    if report:
        with c2:
            pdf_url = api.get_report_pdf_url(job_id)
            json_url = api.get_report_json_url(job_id)
            st.markdown(f"[📄 PDF Report]({pdf_url})")
            st.markdown(f"[📦 JSON Report]({json_url})")
        st.markdown("---")
        st.json(report)
