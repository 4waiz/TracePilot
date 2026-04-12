"""TracePilot -- Streamlit frontend entry point.

Run with:  streamlit run frontend/app.py
"""

import streamlit as st

# -- Page config (must be first Streamlit call) ---------------------------
st.set_page_config(
    page_title="TracePilot",
    page_icon="icon.png",
    layout="wide",
)

# -- Custom CSS -----------------------------------------------------------
st.markdown(
    """
    <style>
    /* ---------- header bar ---------- */
    header[data-testid="stHeader"] {
        background-color: #1a1a2e !important;
    }

    /* ---------- sidebar ---------- */
    section[data-testid="stSidebar"] {
        background-color: #16213e;
    }
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #e0e0e0;
    }

    /* ---------- typography ---------- */
    html, body, [class*="css"] {
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }
    h1, h2, h3 {
        font-weight: 700;
        letter-spacing: -0.02em;
    }

    /* ---------- status / badge colors ---------- */
    .pass  { color: #28a745 !important; }
    .fail  { color: #dc3545 !important; }
    .warn  { color: #ffc107 !important; }
    .info  { color: #17a2b8 !important; }

    /* ---------- metric cards ---------- */
    [data-testid="stMetric"] {
        background: #0e1117;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 12px 16px;
    }
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
    }

    /* ---------- dataframe ---------- */
    .stDataFrame {
        border-radius: 8px;
    }

    /* ---------- buttons ---------- */
    .stButton > button {
        border-radius: 6px;
        font-weight: 600;
        transition: all 0.15s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
    .stButton > button[kind="primary"] {
        background-color: #17a2b8;
        border: none;
    }

    /* ---------- tabs ---------- */
    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
    }

    /* ---------- progress bar ---------- */
    .stProgress > div > div > div {
        background-color: #28a745;
    }

    /* ---------- expander ---------- */
    .streamlit-expanderHeader {
        font-weight: 600;
    }

    /* ---------- sensitivity badges ---------- */
    .sens-general { background: #6c757d; }
    .sens-confidential { background: #fd7e14; }
    .sens-highly-confidential { background: #dc3545; }

    /* ---------- hide streamlit branding ---------- */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -- Session state defaults -----------------------------------------------

if "token" not in st.session_state:
    st.session_state["token"] = None
if "user" not in st.session_state:
    st.session_state["user"] = None
if "nav" not in st.session_state:
    st.session_state["nav"] = "Dashboard"


# -- Auth gate ------------------------------------------------------------

def _is_authenticated() -> bool:
    return st.session_state.get("token") is not None


# -- Routing --------------------------------------------------------------

if not _is_authenticated():
    from frontend.pages.login import render as render_login
    render_login()
else:
    # Sidebar
    with st.sidebar:
        st.image("icon.png", width=60)
        st.markdown("## TracePilot")
        st.caption(f"Logged in as **{st.session_state['user'].get('username', '')}**")
        st.markdown("---")

        user_role = st.session_state["user"].get("role", "user")

        nav_items = ["Dashboard", "New Job", "Deviation Review"]
        if user_role == "admin":
            nav_items.append("Audit Log")

        nav = st.radio("Navigation", nav_items, label_visibility="collapsed")

        st.markdown("---")
        if st.button("Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    st.session_state["nav"] = nav

    # Main area
    if nav == "Dashboard":
        from frontend.pages.dashboard import render as render_dashboard
        render_dashboard()
    elif nav == "New Job":
        from frontend.pages.new_job import render as render_new_job
        render_new_job()
    elif nav == "Deviation Review":
        from frontend.pages.deviation_review import render as render_deviation_review
        render_deviation_review()
    elif nav == "Audit Log":
        from frontend.pages.audit_log import render as render_audit_log
        render_audit_log()
