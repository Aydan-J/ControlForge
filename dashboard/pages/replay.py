"""
ControlForge Replay Page

Purpose:
Dashboard page for replaying old experiment logs.

Current status:
Supports demo replay data and optional CSV upload.
No hardware commands are sent from this page.
"""

from dataclasses import dataclass
import math
import pandas as pd
import streamlit as st


@dataclass
class ReplayFrame:
    timestamp: float
    theta1: float
    theta2: float
    theta1_dot: float
    theta2_dot: float
    cart_pos: float
    cart_vel: float
    controller_output: float


REQUIRED_COLUMNS = [
    "timestamp",
    "theta1",
    "theta2",
    "theta1_dot",
    "theta2_dot",
    "cart_pos",
    "cart_vel",
]


@st.cache_data
def generate_demo_replay_data(sample_count: int = 200) -> pd.DataFrame:
    """
    Generate fake replay data that looks like a saved experiment log.
    """

    rows = []

    for sample_index in range(sample_count):
        timestamp = sample_index * 20

        theta1 = 0.25 * math.sin(sample_index / 15)
        theta2 = -0.35 * math.cos(sample_index / 18)
        theta1_dot = 0.05 * math.sin(sample_index / 8)
        theta2_dot = 0.05 * math.cos(sample_index / 10)
        cart_pos = 0.01 * math.sin(sample_index / 20)
        cart_vel = 0.02 * math.cos(sample_index / 20)

        controller_output = -(
            0.4 * theta1
            + 0.2 * theta2
            + 0.1 * theta1_dot
            + 0.1 * theta2_dot
            + 0.05 * cart_pos
            + 0.05 * cart_vel
        )

        rows.append(
            {
                "timestamp": timestamp,
                "theta1": theta1,
                "theta2": theta2,
                "theta1_dot": theta1_dot,
                "theta2_dot": theta2_dot,
                "cart_pos": cart_pos,
                "cart_vel": cart_vel,
                "controller_output": controller_output,
            }
        )

    return pd.DataFrame(rows)


def validate_replay_dataframe(dataframe: pd.DataFrame) -> tuple[bool, list[str]]:
    """
    Check whether the uploaded replay file has the required columns.
    """

    missing_columns = []

    for column in REQUIRED_COLUMNS:
        if column not in dataframe.columns:
            missing_columns.append(column)

    return len(missing_columns) == 0, missing_columns


def load_uploaded_csv(uploaded_file) -> pd.DataFrame | None:
    """
    Load uploaded CSV file.
    """

    if uploaded_file is None:
        return None

    try:
        dataframe = pd.read_csv(uploaded_file)
        return dataframe
    except Exception as error:
        st.error(f"Could not read CSV file: {error}")
        return None


def render_replay_source_selector() -> pd.DataFrame:
    """
    Let the user choose demo replay data or upload CSV.
    """

    st.subheader("Replay Source")

    source = st.radio(
        "Choose replay source",
        ["Demo Log", "Upload CSV"],
        horizontal=True,
    )

    if source == "Demo Log":
        sample_count = st.slider(
            "Demo sample count",
            min_value=50,
            max_value=500,
            value=200,
            step=50,
        )

        dataframe = generate_demo_replay_data(sample_count=sample_count)
        st.info("Using generated demo replay data.")

        return dataframe

    uploaded_file = st.file_uploader(
        "Upload experiment CSV",
        type=["csv"],
    )

    uploaded_dataframe = load_uploaded_csv(uploaded_file)

    if uploaded_dataframe is None:
        st.warning("No CSV uploaded yet. Showing demo replay data instead.")
        return generate_demo_replay_data(sample_count=200)

    is_valid, missing_columns = validate_replay_dataframe(uploaded_dataframe)

    if not is_valid:
        st.error(
            "Uploaded CSV is missing required columns: "
            + ", ".join(missing_columns)
        )
        st.warning("Showing demo replay data instead.")
        return generate_demo_replay_data(sample_count=200)

    st.success("CSV loaded successfully.")
    return uploaded_dataframe


def render_replay_summary(dataframe: pd.DataFrame) -> None:
    """
    Show replay summary metrics.
    """

    st.subheader("Replay Summary")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Rows", len(dataframe))

    with col2:
        st.metric("Columns", len(dataframe.columns))

    with col3:
        if "timestamp" in dataframe.columns and not dataframe.empty:
            duration = dataframe["timestamp"].max() - dataframe["timestamp"].min()
            st.metric("Duration", f"{duration:.0f} ms")
        else:
            st.metric("Duration", "N/A")


def render_replay_frame_selector(dataframe: pd.DataFrame) -> int:
    """
    Let the user select a replay frame.
    """

    st.subheader("Replay Frame")

    max_index = max(0, len(dataframe) - 1)

    selected_index = st.slider(
        "Frame index",
        min_value=0,
        max_value=max_index,
        value=0,
        step=1,
    )

    return selected_index


def render_current_frame(dataframe: pd.DataFrame, selected_index: int) -> None:
    """
    Show values from selected replay frame.
    """

    st.subheader("Current Frame Values")

    if dataframe.empty:
        st.info("No replay data available.")
        return

    row = dataframe.iloc[selected_index]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Timestamp", f"{row.get('timestamp', 0):.0f} ms")
        st.metric("Theta 1", f"{row.get('theta1', 0):.4f} rad")

    with col2:
        st.metric("Theta 2", f"{row.get('theta2', 0):.4f} rad")
        st.metric("Cart Position", f"{row.get('cart_pos', 0):.4f} m")

    with col3:
        st.metric("Cart Velocity", f"{row.get('cart_vel', 0):.4f} m/s")

        if "controller_output" in dataframe.columns:
            st.metric("Controller Output", f"{row.get('controller_output', 0):.4f}")
        else:
            st.metric("Controller Output", "N/A")


def render_replay_plot(dataframe: pd.DataFrame) -> None:
    """
    Plot selected replay signals.
    """

    st.subheader("Replay Plot")

    possible_signals = [
        "theta1",
        "theta2",
        "theta1_dot",
        "theta2_dot",
        "cart_pos",
        "cart_vel",
        "controller_output",
    ]

    available_signals = [
        signal for signal in possible_signals if signal in dataframe.columns
    ]

    selected_signals = st.multiselect(
        "Select signals to plot",
        available_signals,
        default=available_signals[:2],
    )

    if not selected_signals:
        st.info("Select at least one signal.")
        return

    if "timestamp" in dataframe.columns:
        plot_data = dataframe.set_index("timestamp")[selected_signals]
    else:
        plot_data = dataframe[selected_signals]

    st.line_chart(plot_data)


def render_replay_table(dataframe: pd.DataFrame) -> None:
    """
    Show replay data table.
    """

    with st.expander("Replay Data Table"):
        rows_to_show = st.slider(
            "Rows to preview",
            min_value=5,
            max_value=100,
            value=20,
            step=5,
        )

        st.dataframe(
            dataframe.head(rows_to_show),
            use_container_width=True,
        )


def render_replay_page() -> None:
    """
    Main replay page.
    """

    st.title("ControlForge Replay")

    st.caption(
        "Replay saved telemetry logs from the cart double pendulum system."
    )

    st.warning(
        "Replay mode only. This page does not send commands to the motor or motor driver."
    )

    dataframe = render_replay_source_selector()

    st.divider()

    render_replay_summary(dataframe)

    st.divider()

    selected_index = render_replay_frame_selector(dataframe)

    render_current_frame(dataframe, selected_index)

    st.divider()

    render_replay_plot(dataframe)

    st.divider()

    render_replay_table(dataframe)


if __name__ == "__main__":
    st.set_page_config(page_title="ControlForge Replay", layout="wide")
    render_replay_page()