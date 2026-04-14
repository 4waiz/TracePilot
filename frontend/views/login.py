"""Login page for TracePilot."""

import streamlit as st
from frontend.api_client import api


def render():
    """Render the login page."""
    st.markdown("<div style='height: 60px'></div>", unsafe_allow_html=True)

    col_left, col_center, col_right = st.columns([1, 2, 1])

    with col_center:
        logo_col1, logo_col2, logo_col3 = st.columns([1, 1, 1])
        with logo_col2:
            st.image("logo.png", width=300)

        st.markdown(
            "<h1 style='text-align:center; margin-bottom:0; margin-top:4px; padding: 0; color: #8B0000;'>TracePilot</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align:center; color:#6c757d; margin-bottom:3rem; margin-top:0.5rem'>"
            "Secure First-Piece Inspection &amp; Traceability</p>",
            unsafe_allow_html=True,
        )

        # Custom login form styling
        st.markdown(
            """
            <style>
            .stForm {
                background: linear-gradient(135deg, #771b2a 0%, #5a1420 100%) !important;
                border-radius: 28px !important;
                padding: 48px 40px !important;
                box-shadow: 0 12px 32px rgba(0,0,0,0.3) !important;
                width: 400px !important;
                margin: 0 auto !important;
            }
            .stForm > div {
                background: transparent !important;
                box-shadow: none !important;
                padding: 0 !important;
                margin: 0 !important;
            }
            .stImage img {
                max-width: none !important;
            }
            .stImage {
                display: flex !important;
                justify-content: center !important;
                margin-top: 20px !important;
            }
            .login-field {
                margin-bottom: 32px;
            }
            .login-field label {
                color: #ffffff;
                font-size: 22px;
                font-weight: 600;
                display: block;
                margin-bottom: 16px;
                letter-spacing: 0.3px;
            }
            .stTextInput > div > div > input {
                width: 100% !important;
                padding: 16px 24px !important;
                border-radius: 24px !important;
                background: #c9a876 !important;
                border: none !important;
                font-size: 16px !important;
                color: #333 !important;
                transition: all 0.3s ease !important;
                height: 50px !important;
                box-sizing: border-box !important;
            }
            .stTextInput > div > div > input::placeholder {
                color: #999 !important;
            }
            .stTextInput > div > div > input:focus {
                background: #d4b896 !important;
                box-shadow: 0 4px 12px rgba(201, 168, 118, 0.3) !important;
                outline: none !important;
            }
            .login-button {
                margin-top: 32px;
            }
            .login-button button {
                background: #c9a876 !important;
                color: #ffffff !important;
                font-size: 16px !important;
                font-weight: 700 !important;
                padding: 14px 32px !important;
                border-radius: 24px !important;
                border: none !important;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
                transition: all 0.3s ease !important;
                cursor: pointer !important;
                width: 100% !important;
            }
            .login-button button:hover {
                background: #d4b896 !important;
                box-shadow: 0 6px 16px rgba(0,0,0,0.3) !important;
                transform: translateY(-1px) !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        with st.form("login_form"):
            st.markdown(
                "<div class='login-field'><label>username:</label></div>",
                unsafe_allow_html=True,
            )
            username = st.text_input(
                "",
                placeholder="Enter username",
                label_visibility="collapsed",
                key="username_input",
            )

            st.markdown(
                "<div class='login-field'><label>Password:</label></div>",
                unsafe_allow_html=True,
            )
            password = st.text_input(
                "",
                type="password",
                placeholder="Enter password",
                label_visibility="collapsed",
                key="password_input",
            )

            st.markdown("<div class='login-button'>", unsafe_allow_html=True)
            submitted = st.form_submit_button(
                "Login",
                use_container_width=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

        if submitted:
            username = username.strip()
            password = password.strip()
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
