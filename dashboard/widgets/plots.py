"""
ControlForge Plot Widgets

Purpose:
Reusable Streamlit plot components for telemetry history, controller output,
and digital twin comparison.

Safety:
This file only displays data.
It does not send commands to hardware.
"""

from dataclasses import dataclass
import pandas as pd
import streamlit as st


@dataclass
class PlotState:
    timestamp: float
    states: list[float]
    controller_output: float | None = None


def build_history_dataframe(history: list[PlotState]) -> pd.DataFrame:
    """
    Convert PlotState history into a pandas DataFrame.

    Expected state order:
    state1, state2, state3, state4, state5, state6
    """

    rows = []

    for item in history:
        row = {
            "timestamp": item.timestamp,
            "state1": item.states[0] if len(item.states) > 0 else None,
            "state2": item.states[1] if len(item.states) > 1 else None,
            "state3": item.states[2] if len(item.states) > 2 else None,
            "state4": item.states[3] if len(item.states) > 3 else None,
            "state5": item.states[4] if len(item.states) > 4 else None,
            "state6": item.states[5] if len(item.states) > 5 else None,
            "controller_output": item.controller_output,
        }
        rows.append(row)

    return pd.DataFrame(rows)


def render_state_plot(
    history: list[PlotState],
    selected_states: list[str] | None = None,
) -> None:
    """
    Render line plot for selected telemetry states.
    """

    st.subheader("Telemetry State Plot")

    if not history:
        st.info("No telemetry history available yet.")
        return

    dataframe = build_history_dataframe(history)

    available_states = ["state1", "state2", "state3", "state4", "state5", "state6"]

    if selected_states is None:
        selected_states = ["state1", "state2"]

    selected_states = st.multiselect(
        "Select states to plot",
        available_states,
        default=selected_states,
    )

    if not selected_states:
        st.warning("Select at least one state to display.")
        return

    plot_data = dataframe.set_index("timestamp")[selected_states]

    st.line_chart(plot_data)


def render_controller_output_plot(history: list[PlotState]) -> None:
    """
    Render controller output over time.
    """

    st.subheader("Controller Output Plot")

    if not history:
        st.info("No controller output history available yet.")
        return

    dataframe = build_history_dataframe(history)

    if "controller_output" not in dataframe.columns:
        st.info("Controller output data is not available.")
        return

    output_data = dataframe[["timestamp", "controller_output"]].dropna()

    if output_data.empty:
        st.info("Controller output data is empty.")
        return

    st.line_chart(output_data.set_index("timestamp"))


def render_digital_twin_error_plot(
    timestamps: list[float],
    mean_absolute_errors: list[float],
    max_absolute_errors: list[float],
) -> None:
    """
    Render digital twin error plot.
    """

    st.subheader("Digital Twin Error Plot")

    if not timestamps or not mean_absolute_errors or not max_absolute_errors:
        st.info("No digital twin error history available yet.")
        return

    min_length = min(
        len(timestamps),
        len(mean_absolute_errors),
        len(max_absolute_errors),
    )

    dataframe = pd.DataFrame(
        {
            "timestamp": timestamps[:min_length],
            "mean_absolute_error": mean_absolute_errors[:min_length],
            "max_absolute_error": max_absolute_errors[:min_length],
        }
    )

    st.line_chart(dataframe.set_index("timestamp"))


def render_latest_state_bar_chart(states: list[float]) -> None:
    """
    Render a simple bar chart of the latest state vector.
    """

    st.subheader("Latest State Vector")

    if not states:
        st.info("No latest state data available.")
        return

    labels = [f"state{i + 1}" for i in range(len(states))]

    dataframe = pd.DataFrame(
        {
            "state": labels,
            "value": states,
        }
    )

    st.bar_chart(dataframe.set_index("state"))


def render_plots_test_page() -> None:
    """
    Standalone Streamlit test page for this widget file.
    """

    st.set_page_config(
        page_title="ControlForge Plot Widgets Test",
        layout="wide",
    )

    st.title("ControlForge Plot Widgets Test")

    fake_history = []

    for i in range(100):
        timestamp = i * 20

        states = [
            0.2 + i * 0.001,
            -0.3 + i * 0.002,
            0.05,
            -0.04,
            i * 0.0005,
            0.01,
        ]

        controller_output = 0.1 if i % 2 == 0 else -0.1

        fake_history.append(
            PlotState(
                timestamp=timestamp,
                states=states,
                controller_output=controller_output,
            )
        )

    latest_states = fake_history[-1].states

    render_latest_state_bar_chart(latest_states)

    st.divider()

    render_state_plot(fake_history)

    st.divider()

    render_controller_output_plot(fake_history)

    st.divider()

    fake_timestamps = [i * 20 for i in range(50)]
    fake_mean_errors = [0.05 + i * 0.001 for i in range(50)]
    fake_max_errors = [0.09 + i * 0.002 for i in range(50)]

    render_digital_twin_error_plot(
        timestamps=fake_timestamps,
        mean_absolute_errors=fake_mean_errors,
        max_absolute_errors=fake_max_errors,
    )


if __name__ == "__main__":
    render_plots_test_page()