"""
ControlForge Analysis Page

Purpose:
Dashboard page for analyzing telemetry history, controller output,
and digital twin error metrics.

Current status:
Simulation/demo mode only.
No hardware commands are sent from this page.
"""

from dataclasses import dataclass
import math
import pandas as pd
import streamlit as st


@dataclass
class AnalysisSample:
    timestamp: float
    hardware_states: list[float]
    simulated_states: list[float]
    controller_output: float


@dataclass
class ErrorMetrics:
    errors: list[float]
    mean_absolute_error: float
    max_absolute_error: float


def clamp(value: float, minimum: float, maximum: float) -> float:
    """
    Clamp a value between a minimum and maximum.
    """

    return max(minimum, min(maximum, value))


def generate_hardware_states(sample_index: int) -> list[float]:
    """
    Generate fake hardware telemetry states.
    """

    theta1 = 0.25 * math.sin(sample_index / 15)
    theta2 = -0.35 * math.cos(sample_index / 18)
    theta1_dot = 0.05 * math.sin(sample_index / 8)
    theta2_dot = 0.05 * math.cos(sample_index / 10)
    cart_pos = 0.01 * math.sin(sample_index / 20)
    cart_vel = 0.02 * math.cos(sample_index / 20)

    return [theta1, theta2, theta1_dot, theta2_dot, cart_pos, cart_vel]


def generate_simulated_states(sample_index: int) -> list[float]:
    """
    Generate fake digital twin states.
    Intentionally close to hardware states but not identical.
    """

    theta1 = 0.24 * math.sin((sample_index + 2) / 15)
    theta2 = -0.33 * math.cos((sample_index + 3) / 18)
    theta1_dot = 0.048 * math.sin((sample_index + 1) / 8)
    theta2_dot = 0.052 * math.cos((sample_index + 2) / 10)
    cart_pos = 0.011 * math.sin((sample_index + 2) / 20)
    cart_vel = 0.019 * math.cos((sample_index + 1) / 20)

    return [theta1, theta2, theta1_dot, theta2_dot, cart_pos, cart_vel]


def calculate_controller_output(states: list[float]) -> float:
    """
    Generate a fake controller output from the state vector.
    """

    gains = [0.4, 0.2, 0.1, 0.1, 0.05, 0.05]
    output = sum(g * s for g, s in zip(gains, states))
    return clamp(-output, -1.0, 1.0)


def calculate_error_metrics(
    hardware_states: list[float],
    simulated_states: list[float],
) -> ErrorMetrics:
    """
    Compare hardware states against simulated states.
    """

    min_length = min(len(hardware_states), len(simulated_states))
    errors = [hardware_states[i] - simulated_states[i] for i in range(min_length)]
    absolute_errors = [abs(e) for e in errors]

    if absolute_errors:
        mean_absolute_error = sum(absolute_errors) / len(absolute_errors)
        max_absolute_error = max(absolute_errors)
    else:
        mean_absolute_error = 0.0
        max_absolute_error = 0.0

    return ErrorMetrics(
        errors=errors,
        mean_absolute_error=mean_absolute_error,
        max_absolute_error=max_absolute_error,
    )


@st.cache_data
def build_analysis_dataframe(sample_count: int = 150) -> pd.DataFrame:
    """
    Build the full analysis DataFrame in one pass.
    Cached so it only recomputes when sample_count changes.
    """

    rows = []

    for sample_index in range(sample_count):
        timestamp = sample_index * 20
        hw = generate_hardware_states(sample_index)
        sim = generate_simulated_states(sample_index)
        ctrl = calculate_controller_output(hw)
        metrics = calculate_error_metrics(hw, sim)

        rows.append({
            "timestamp": timestamp,
            "hardware_theta1": hw[0],
            "hardware_theta2": hw[1],
            "hardware_theta1_dot": hw[2],
            "hardware_theta2_dot": hw[3],
            "hardware_cart_pos": hw[4],
            "hardware_cart_vel": hw[5],
            "sim_theta1": sim[0],
            "sim_theta2": sim[1],
            "sim_theta1_dot": sim[2],
            "sim_theta2_dot": sim[3],
            "sim_cart_pos": sim[4],
            "sim_cart_vel": sim[5],
            "controller_output": ctrl,
            "mean_absolute_error": metrics.mean_absolute_error,
            "max_absolute_error": metrics.max_absolute_error,
        })

    return pd.DataFrame(rows)


def render_summary_metrics(dataframe: pd.DataFrame) -> None:
    """
    Show overall analysis metrics.
    """

    latest_row = dataframe.iloc[-1]

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Latest Mean Abs Error", f"{latest_row['mean_absolute_error']:.4f}")
    with col2:
        st.metric("Latest Max Abs Error", f"{latest_row['max_absolute_error']:.4f}")
    with col3:
        st.metric("Latest Ctrl Output", f"{latest_row['controller_output']:.4f}")
    with col4:
        st.metric("Samples", len(dataframe))


def render_hardware_vs_simulation_plot(dataframe: pd.DataFrame) -> None:
    """
    Plot hardware state against simulated state.
    """

    st.subheader("Hardware vs Digital Twin")

    signal_options = {
        "Theta 1": ("hardware_theta1", "sim_theta1"),
        "Theta 2": ("hardware_theta2", "sim_theta2"),
        "Theta 1 Velocity": ("hardware_theta1_dot", "sim_theta1_dot"),
        "Theta 2 Velocity": ("hardware_theta2_dot", "sim_theta2_dot"),
        "Cart Position": ("hardware_cart_pos", "sim_cart_pos"),
        "Cart Velocity": ("hardware_cart_vel", "sim_cart_vel"),
    }

    selected_signal = st.selectbox(
        "Select signal to compare",
        list(signal_options.keys()),
    )

    hardware_column, simulation_column = signal_options[selected_signal]
    plot_data = dataframe.set_index("timestamp")[[hardware_column, simulation_column]]
    st.line_chart(plot_data)


def render_error_plot(dataframe: pd.DataFrame) -> None:
    """
    Plot digital twin error metrics over time.
    """

    st.subheader("Digital Twin Error Metrics")
    plot_data = dataframe.set_index("timestamp")[["mean_absolute_error", "max_absolute_error"]]
    st.line_chart(plot_data)


def render_controller_output_plot(dataframe: pd.DataFrame) -> None:
    """
    Plot controller output over time.
    """

    st.subheader("Controller Output History")
    plot_data = dataframe.set_index("timestamp")[["controller_output"]]
    st.line_chart(plot_data)


def render_error_table(dataframe: pd.DataFrame) -> None:
    """
    Show recent analysis data inside an expander (lazy-loaded).
    """

    with st.expander("Recent Analysis Samples"):
        rows_to_show = st.slider(
            "Rows to show",
            min_value=5,
            max_value=50,
            value=10,
            step=5,
        )

        selected_columns = [
            "timestamp",
            "hardware_theta1",
            "sim_theta1",
            "hardware_theta2",
            "sim_theta2",
            "controller_output",
            "mean_absolute_error",
            "max_absolute_error",
        ]

        st.dataframe(
            dataframe[selected_columns].tail(rows_to_show),
            use_container_width=True,
        )


def render_analysis_page() -> None:
    """
    Main analysis page.
    """

    st.title("ControlForge Analysis")

    st.caption(
        "Analyze simulated telemetry, controller output, and digital twin comparison for the cart double pendulum demo."
    )

    st.warning(
        "Analysis mode only. This page does not send commands to the motor or motor driver."
    )

    sample_count = st.slider(
        "Number of demo samples",
        min_value=50,
        max_value=300,
        value=150,
        step=25,
    )

    dataframe = build_analysis_dataframe(sample_count=sample_count)

    render_summary_metrics(dataframe)

    st.divider()

    render_hardware_vs_simulation_plot(dataframe)

    st.divider()

    render_error_plot(dataframe)

    st.divider()

    render_controller_output_plot(dataframe)

    st.divider()

    render_error_table(dataframe)


if __name__ == "__main__":
    st.set_page_config(page_title="ControlForge Analysis", layout="wide")
    render_analysis_page()