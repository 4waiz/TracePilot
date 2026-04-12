"""Login page for TracePilot."""

import streamlit as st
from frontend.api_client import api


def render():
    """Render the login page."""
    st.markdown("<div style='height: 60px'></div>", unsafe_allow_html=True)

    col_left, col_center, col_right = st.columns([1, 2, 1])

    with col_center:
        # Logo
        logo_col1, logo_col2, logo_col3 = st.columns([1, 1, 1])
        with logo_col2:
            st.image("icon.png", width=120)

        st.markdown(
            "<h1 style='text-align:center; margin-bottom:0'>TracePilot</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align:center; color:#6c757d; margin-bottom:2rem'>"
            "Secure First-Piece Inspection &amp; Traceability</p>",
            unsafe_allow_html=True,
        )

        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input(
                "Password", type="password", placeholder="Enter your password"
            )
            submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("Please enter both username and password.")
                return

            with st.spinner("Authenticating..."):
                result = api.login(username, password)

            if result and "access_token" in result:
                token = result["access_token"]
                user = api.get_me(token)
                if user:
                    st.session_state["token"] = token
                    st.session_state["user"] = user
                    st.rerun()
                else:
                    st.error("Failed to retrieve user profile.")
            elif result is not None:
                st.error("Invalid credentials. Please try again.")

        st.markdown("---")
        st.info(
            "**Demo credentials**  \n"
            "Operator: `operator` / `operator123`  \n"
            "Supervisor: `supervisor` / `supervisor123`  \n"
            "Admin: `admin` / `admin123`"
        )
