"""Login page — EDGE Group design language."""

import streamlit as st
from frontend.api_client import api


def render():
    """Render the login page."""

    st.markdown(
        """
        <style>
        /* Login form override */
        [data-testid="stForm"] {
            background: #FFFFFF !important;
            border: 1px solid #E5E3E0 !important;
            border-radius: 4px !important;
            padding: 2.5rem 2.5rem 2rem !important;
            box-shadow: 0 2px 12px rgba(0,0,0,0.04) !important;
        }
        .edge-login-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .edge-login-title {
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            color: #C65D3D;
            margin-bottom: 4px;
        }
        .edge-login-subtitle {
            font-size: 1.4rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #1A1A1A;
            margin: 0;
        }
        .edge-login-desc {
            font-size: 0.85rem;
            color: #8A8A8A;
            margin-top: 8px;
            font-weight: 300;
        }
        .edge-divider {
            border: none;
            border-top: 2px solid #C65D3D;
            width: 40px;
            margin: 16px auto;
        }
        .edge-roles {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-top: 16px;
        }
        .edge-role {
            background: #F5F4F2;
            border: 1px solid #E5E3E0;
            border-radius: 4px;
            padding: 18px 14px;
            text-align: center;
            transition: box-shadow 0.15s ease;
        }
        .edge-role:hover {
            box-shadow: 0 2px 10px rgba(0,0,0,0.06);
        }
        .edge-role-title {
            font-size: 0.68rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.10em;
            color: #1A1A1A;
            margin-bottom: 6px;
        }
        .edge-role-cred {
            font-size: 0.72rem;
            color: #C65D3D;
            font-family: 'Inter', monospace;
            font-weight: 600;
        }
        .edge-role-desc {
            font-size: 0.70rem;
            color: #8A8A8A;
            margin-top: 8px;
            line-height: 1.5;
            font-weight: 300;
        }
        .edge-workflow {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        .edge-workflow-step {
            background: #FFFFFF;
            border: 1px solid #E5E3E0;
            color: #4A4A4A;
            padding: 6px 14px;
            border-radius: 3px;
            font-size: 0.65rem;
            font-weight: 600;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }
        .edge-workflow-arrow {
            color: #B0ADAA;
            font-size: 0.8rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height: 30px'></div>", unsafe_allow_html=True)

    _, col_center, _ = st.columns([1.3, 2, 1.3])

    with col_center:
        # Logo
        logo_l, logo_c, logo_r = st.columns([1, 1, 1])
        with logo_c:
            st.image("iconn.png", width=260)

        st.markdown(
            "<div class='edge-login-header'>"
            "<hr class='edge-divider'>"
            "<div class='edge-login-title'>Secure Platform</div>"
            "<div class='edge-login-subtitle'>TracePilot</div>"
            "<div class='edge-login-desc'>First-Piece Inspection &amp; Traceability</div>"
            "</div>",
            unsafe_allow_html=True,
        )

        # Login form
        with st.form("login_form"):
            username = st.text_input(
                "Username",
                placeholder="Enter your username",
                key="username_input",
            )
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password",
                key="password_input",
            )
            submitted = st.form_submit_button("Sign In", use_container_width=True)

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

        # Role cards
        st.markdown("---")
        st.markdown(
            "<div class='edge-roles'>"
            "<div class='edge-role'>"
            "<div class='edge-role-title'>Operator</div>"
            "<div class='edge-role-cred'>operator / operator123</div>"
            "<div class='edge-role-desc'>Create jobs, upload drawings, run AI extraction, record measurements</div>"
            "</div>"
            "<div class='edge-role'>"
            "<div class='edge-role-title'>Supervisor</div>"
            "<div class='edge-role-cred'>supervisor / supervisor123</div>"
            "<div class='edge-role-desc'>All operator capabilities plus review &amp; approve deviations</div>"
            "</div>"
            "<div class='edge-role'>"
            "<div class='edge-role-title'>Admin</div>"
            "<div class='edge-role-cred'>admin / admin123</div>"
            "<div class='edge-role-desc'>Full access including audit logs and system management</div>"
            "</div>"
            "</div>",
            unsafe_allow_html=True,
        )

        # Workflow
        st.markdown(
            "<div class='edge-workflow'>"
            "<span class='edge-workflow-step'>Upload</span>"
            "<span class='edge-workflow-arrow'>&#8594;</span>"
            "<span class='edge-workflow-step'>Extract</span>"
            "<span class='edge-workflow-arrow'>&#8594;</span>"
            "<span class='edge-workflow-step'>Review</span>"
            "<span class='edge-workflow-arrow'>&#8594;</span>"
            "<span class='edge-workflow-step'>Inspect</span>"
            "<span class='edge-workflow-arrow'>&#8594;</span>"
            "<span class='edge-workflow-step'>Report</span>"
            "</div>",
            unsafe_allow_html=True,
        )
