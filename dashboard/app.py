"""
ControlForge Main Dashboard

Purpose:
Main Streamlit dashboard for the ControlForge platform.

Pages:
- Overview
- Telemetry
- Visualization
- Control Panel
- Analysis
- Replay

Current status:
Simulation/demo mode only.
No motor commands are sent from this dashboard.
"""

import importlib.util
from pathlib import Path

import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
PAGES_DIR = BASE_DIR / "pages"

# Module cache — each page file is loaded only once per process
_MODULE_CACHE: dict = {}

def load_page_function(file_name: str, function_name: str):
    """
    Load a page function from a Python file.
    Modules are cached so they are only imported once, not on every Streamlit rerun.
    """

    # Return from cache if already loaded
    cache_key = f"{file_name}::{function_name}"
    if cache_key in _MODULE_CACHE:
        return _MODULE_CACHE[cache_key]

    page_path = PAGES_DIR / file_name

    if not page_path.exists():
        st.error(f"Missing page file: {page_path}")
        return None

    spec = importlib.util.spec_from_file_location(file_name, page_path)
    module = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(module)
    except Exception as error:
        st.error(f"Could not load {file_name}: {error}")
        return None

    if not hasattr(module, function_name):
        st.error(f"{file_name} is missing function: {function_name}")
        return None

    func = getattr(module, function_name)
    _MODULE_CACHE[cache_key] = func
    return func


def render_overview_page() -> None:
    """
    Render the dashboard overview page.
    """

    st.title("ControlForge")

    st.caption(
        "A real-time control systems dashboard for the cart double pendulum demo."
    )

    st.warning(
        "Hardware output is disabled. Do not connect the 775 motor or motor driver "
        "until safety limits and emergency stop behavior are finished."
    )

    st.subheader("What ControlForge Does")

    st.write(
        "ControlForge is a dashboard for testing and understanding control systems. "
        "The main demo is a cart double pendulum: a moving cart with two connected "
        "swinging arms. The system can track values like pendulum angles, angular "
        "velocity, cart position, and cart velocity."
    )

    st.write(
        "The dashboard helps users view telemetry, tune software controllers, compare "
        "hardware data to a simulation, visualize the pendulum, and replay saved logs. "
        "Right now, the dashboard uses simulation/demo data only, so it is safe to test "
        "without connecting the motor."
    )

    st.subheader("Dashboard Sections")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info(
            "**Telemetry**\n\n"
            "View live or simulated sensor values, raw packets, plots, and recent data."
        )

        st.info(
            "**Visualization**\n\n"
            "See a simple visual model of the cart double pendulum."
        )

    with col2:
        st.info(
            "**Control Panel**\n\n"
            "Tune PID or LQR demo settings in software-only mode."
        )

        st.info(
            "**Analysis**\n\n"
            "Compare hardware-style data with digital twin simulation data."
        )

    with col3:
        st.info(
            "**Replay**\n\n"
            "Replay old or demo experiment logs and inspect frame-by-frame values."
        )

    st.subheader("Current Project Status")

    st.success("Backend, controllers, simulation files, widgets, and pages are running in demo mode.")

    st.code(
        """
Completed:
✅ telemetry.py
✅ visualization.py
✅ control_panel.py
✅ analysis.py
✅ replay.py

Now integrated:
✅ dashboard/app.py

Still later:
- Polish UI
- Improve pendulum animation
- Add real serial mode inside dashboard
- Add hardware safety limits
- Add emergency stop behavior
- Add real motor output only after safety checks
        """.strip()
    )


def render_main_dashboard() -> None:
    """
    Render main app with tab/page navigation.
    """

    st.set_page_config(
        page_title="ControlForge Dashboard",
        layout="wide",
    )

    st.sidebar.title("ControlForge")
    st.sidebar.caption("Universal control systems platform")

    selected_page = st.sidebar.radio(
        "Navigation",
        [
            "Overview",
            "Telemetry",
            "Visualization",
            "Control Panel",
            "Analysis",
            "Replay",
            "Advanced Tools",
        ],
    )

    st.sidebar.divider()

    st.sidebar.warning(
        "Hardware output disabled. Simulation/demo mode only."
    )

    if selected_page == "Overview":
        render_overview_page()

    elif selected_page == "Telemetry":
        page_function = load_page_function(
            file_name="telemetry.py",
            function_name="render_telemetry_page",
        )

        if page_function:
            page_function()

    elif selected_page == "Visualization":
        page_function = load_page_function(
            file_name="visualization.py",
            function_name="render_visualization_page",
        )

        if page_function:
            page_function()

    elif selected_page == "Control Panel":
        page_function = load_page_function(
            file_name="control_panel.py",
            function_name="render_control_panel_page",
        )

        if page_function:
            page_function()

    elif selected_page == "Analysis":
        page_function = load_page_function(
            file_name="analysis.py",
            function_name="render_analysis_page",
        )

        if page_function:
            page_function()

    elif selected_page == "Replay":
        page_function = load_page_function(
            file_name="replay.py",
            function_name="render_replay_page",
        )

        if page_function:
            page_function()

    elif selected_page == "Advanced Tools":
        page_function = load_page_function(
            file_name="advanced_tools.py",
            function_name="render_advanced_tools_page",
        )

        if page_function:
            page_function()


if __name__ == "__main__":
    render_main_dashboard()