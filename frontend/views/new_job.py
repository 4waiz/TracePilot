"""New job creation page."""

import streamlit as st
from frontend.api_client import api
from frontend.ui import page_header, section_number


def render():
    """Render the new-job form."""
    token = st.session_state["token"]

    st.markdown(section_number("03"), unsafe_allow_html=True)
    page_header(
        "Create New Job",
        "Set up a first-piece inspection with document upload",
    )

    with st.form("new_job_form"):
        title = st.text_input(
            "Job Title",
            placeholder="e.g. Bracket Assembly FPI - PO 2024-0412",
            help="A descriptive name for this inspection job.",
        )

        description = st.text_area(
            "Description (optional)",
            placeholder="Any additional notes about this inspection...",
            height=80,
        )

        c1, c2 = st.columns(2)
        with c1:
            sensitivity = st.selectbox(
                "Sensitivity Label",
                options=["General", "Confidential", "Highly Confidential"],
                help=(
                    "**General** -- no restrictions.  \n"
                    "**Confidential** -- limited access, audit-logged.  \n"
                    "**Highly Confidential** -- encrypted at rest, strict RBAC."
                ),
            )

        uploaded_files = st.file_uploader(
            "Upload Inspection Documents (PDF)",
            type=["pdf"],
            accept_multiple_files=True,
            help="Upload PDF documents (drawings, specs, work instructions). Max 50MB per file.",
        )

        if uploaded_files and len(uploaded_files) > 3:
            st.warning("Maximum 3 files allowed. Only the first 3 will be uploaded.")

        submitted = st.form_submit_button(
            "Create Job", use_container_width=True
        )

    if submitted:
        if not title.strip():
            st.error("Job title is required.")
            return

        sens_map = {
            "General": "general",
            "Confidential": "confidential",
            "Highly Confidential": "highly_confidential",
        }
        with st.spinner("Creating job..."):
            job = api.create_job(token, title.strip(), sens_map.get(sensitivity, "general"))

        if not job:
            return

        job_id = job.get("id")
        st.success(f"Job **{title}** created (ID: {job_id}).")

        # Upload documents if provided
        files_to_upload = (uploaded_files or [])[:3]
        if files_to_upload:
            with st.spinner(f"Uploading {len(files_to_upload)} document(s)..."):
                result = api.upload_documents(token, job_id, files_to_upload)
            if result:
                st.success(f"{len(files_to_upload)} document(s) uploaded.")
            else:
                st.warning("Job created but document upload failed.")

        # Navigate to the new job workspace
        st.session_state["selected_job_id"] = job_id
        st.session_state["workspace_phase"] = "Setup"
        st.session_state["nav"] = "Job Workspace"
        st.rerun()
