"""Audit log viewer (admin only)."""

import csv
import io
from datetime import datetime, timedelta

import streamlit as st
from frontend.api_client import api


def render():
    """Render the audit log page."""
    token = st.session_state["token"]
    user = st.session_state.get("user", {})

    if user.get("role") not in ("admin",):
        st.error("Access denied. Admin privileges required.")
        return

    st.header("Audit Log")
    st.markdown("---")

    # -- filters ----------------------------------------------------------
    f1, f2, f3 = st.columns(3)
    with f1:
        date_from = st.date_input(
            "From",
            value=datetime.utcnow().date() - timedelta(days=30),
        )
    with f2:
        date_to = st.date_input("To", value=datetime.utcnow().date())
    with f3:
        action_filter = st.text_input(
            "Action type",
            placeholder="e.g. login, create_job, submit_measurement",
        )

    username_filter = st.text_input("Username", placeholder="Filter by username")

    filters: dict = {}
    if date_from:
        filters["date_from"] = str(date_from)
    if date_to:
        filters["date_to"] = str(date_to)
    if action_filter:
        filters["action"] = action_filter
    if username_filter:
        filters["username"] = username_filter

    # -- pagination -------------------------------------------------------
    page_key = "audit_page"
    if page_key not in st.session_state:
        st.session_state[page_key] = 1

    page_size = 25
    filters["page"] = st.session_state[page_key]
    filters["page_size"] = page_size

    # -- fetch ------------------------------------------------------------
    with st.spinner("Loading audit logs..."):
        data = api.get_audit_logs(token, filters)

    if data is None:
        return

    logs = data if isinstance(data, list) else data.get("items", data.get("logs", []))
    total = data.get("total", len(logs)) if isinstance(data, dict) else len(logs)

    if not logs:
        st.info("No audit log entries found for the selected filters.")
        return

    # -- table ------------------------------------------------------------
    rows = []
    for entry in logs:
        rows.append({
            "Timestamp": entry.get("timestamp", entry.get("created_at", "")),
            "User": entry.get("username", entry.get("user", "")),
            "Action": entry.get("action", ""),
            "Resource": entry.get("resource", entry.get("resource_type", "")),
            "Details": str(entry.get("details", entry.get("metadata", ""))),
        })

    st.dataframe(rows, use_container_width=True, hide_index=True)

    # -- pagination controls ----------------------------------------------
    total_pages = max(1, (total + page_size - 1) // page_size)
    p1, p2, p3 = st.columns([1, 2, 1])
    with p1:
        if st.button("Previous", disabled=(st.session_state[page_key] <= 1)):
            st.session_state[page_key] -= 1
            st.rerun()
    with p2:
        st.markdown(
            f"<p style='text-align:center'>Page {st.session_state[page_key]} of {total_pages}</p>",
            unsafe_allow_html=True,
        )
    with p3:
        if st.button("Next", disabled=(st.session_state[page_key] >= total_pages)):
            st.session_state[page_key] += 1
            st.rerun()

    # -- export -----------------------------------------------------------
    st.markdown("---")
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["Timestamp", "User", "Action", "Resource", "Details"])
    writer.writeheader()
    writer.writerows(rows)
    st.download_button(
        "Export CSV",
        data=buf.getvalue(),
        file_name="tracepilot_audit_log.csv",
        mime="text/csv",
    )
