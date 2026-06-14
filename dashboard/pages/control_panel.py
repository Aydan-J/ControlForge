"""
ControlForge Control Panel Page

Purpose:
Dashboard page for software-only controller selection and tuning.

Current status:
Simulation/demo mode only.
No motor commands are sent from this page.
"""

from dataclasses import dataclass
import math
import time
import streamlit as st


@dataclass
class ControlPanelState:
    controller_name: str
    enabled: bool
    output: float
    setpoint: float | None = None
    measured_value: float | None = None


def clamp(value: float, minimum: float, maximum: float) -> float:
    """
    Clamp a value between a minimum and maximum.
    """

    return max(minimum, min(maximum, value))


def calculate_demo_pid_output(
    kp: float,
    ki: float,
    kd: float,
    setpoint: float,
    measured_value: float,
) -> float:
    """
    Simple demo PID-style calculation.

    This is not the full backend PID controller.
    It is only for showing the UI working.
    """

    error = setpoint - measured_value

    proportional = kp * error
    integral_demo = ki * error * 0.1
    derivative_demo = kd * (-measured_value)

    output = proportional + integral_demo + derivative_demo

    return clamp(output, -1.0, 1.0)


def calculate_demo_lqr_output(gains: list[float], states: list[float]) -> float:
    """
    Simple demo LQR-style output.

    output = -Kx
    """

    output = 0.0

    for gain, state in zip(gains, states):
        output += gain * state

    return clamp(-output, -1.0, 1.0)


def generate_demo_states(sample_index: int) -> list[float]:
    """
    Generate fake 6-state double pendulum/cart values.
    """

    theta1 = 0.25 * math.sin(sample_index / 15)
    theta2 = -0.35 * math.cos(sample_index / 18)
    theta1_dot = 0.05 * math.sin(sample_index / 8)
    theta2_dot = 0.05 * math.cos(sample_index / 10)
    cart_pos = 0.01 * math.sin(sample_index / 20)
    cart_vel = 0.02 * math.cos(sample_index / 20)

    return [
        theta1,
        theta2,
        theta1_dot,
        theta2_dot,
        cart_pos,
        cart_vel,
    ]


def render_safety_panel() -> None:
    """
    Show safety information.
    """

    st.subheader("Safety Status")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Hardware Output", "Disabled")

    with col2:
        st.metric("Motor Driver", "Do Not Connect Yet")

    with col3:
        st.metric("Emergency Stop", "Not Implemented Yet")

    st.error(
        "Do not connect the 775 motor or motor driver yet. "
        "This control panel is simulation-only until safety limits and emergency stop behavior are finished."
    )


def render_controller_status(state: ControlPanelState) -> None:
    """
    Show controller status metrics.
    """

    st.subheader("Controller Status")

    status_text = "Enabled" if state.enabled else "Disabled"

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Status", status_text)

    with col2:
        st.metric("Controller", state.controller_name)

    with col3:
        st.metric("Software Output", f"{state.output:.4f}")

    col4, col5 = st.columns(2)

    with col4:
        if state.setpoint is None:
            st.metric("Setpoint", "N/A")
        else:
            st.metric("Setpoint", f"{state.setpoint:.4f}")

    with col5:
        if state.measured_value is None:
            st.metric("Measured Value", "N/A")
        else:
            st.metric("Measured Value", f"{state.measured_value:.4f}")


def render_pid_panel(enabled: bool, measured_value: float) -> ControlPanelState:
    """
    Render PID controls and calculate demo output.
    """

    st.subheader("PID Tuning")

    st.caption("Software-only PID tuning demo.")

    kp = st.slider("Kp", min_value=0.0, max_value=5.0, value=0.2, step=0.01)
    ki = st.slider("Ki", min_value=0.0, max_value=2.0, value=0.0, step=0.01)
    kd = st.slider("Kd", min_value=0.0, max_value=2.0, value=0.05, step=0.01)

    setpoint = st.number_input(
        "Setpoint",
        value=0.0,
        step=0.1,
        help="Target theta1 value for this demo.",
    )

    if enabled:
        output = calculate_demo_pid_output(
            kp=kp,
            ki=ki,
            kd=kd,
            setpoint=setpoint,
            measured_value=measured_value,
        )
    else:
        output = 0.0

    st.write("PID values:")
    st.json(
        {
            "kp": kp,
            "ki": ki,
            "kd": kd,
            "setpoint": setpoint,
            "measured_value": measured_value,
        }
    )

    return ControlPanelState(
        controller_name="PID",
        enabled=enabled,
        output=output,
        setpoint=setpoint,
        measured_value=measured_value,
    )


def render_lqr_panel(enabled: bool, states: list[float]) -> ControlPanelState:
    """
    Render LQR demo controls and calculate demo output.
    """

    st.subheader("LQR Demo Tuning")

    st.caption(
        "This is a manual gain-vector demo, not a full mathematically solved LQR controller yet."
    )

    default_gains = [0.4, 0.2, 0.1, 0.1, 0.05, 0.05]
    gains = []

    cols = st.columns(3)

    for index, default_gain in enumerate(default_gains):
        with cols[index % 3]:
            gain = st.slider(
                f"K{index + 1}",
                min_value=-5.0,
                max_value=5.0,
                value=float(default_gain),
                step=0.01,
            )
            gains.append(gain)

    if enabled:
        output = calculate_demo_lqr_output(gains=gains, states=states)
    else:
        output = 0.0

    st.write("LQR demo values:")
    st.json(
        {
            "gains": gains,
            "states": states,
        }
    )

    return ControlPanelState(
        controller_name="LQR",
        enabled=enabled,
        output=output,
        setpoint=None,
        measured_value=None,
    )


def render_current_state_vector(states: list[float]) -> None:
    """
    Show the current fake state vector.
    """

    st.subheader("Current Demo State Vector")

    labels = [
        "theta1",
        "theta2",
        "theta1_dot",
        "theta2_dot",
        "cart_pos",
        "cart_vel",
    ]

    cols = st.columns(3)

    for index, value in enumerate(states):
        with cols[index % 3]:
            st.metric(labels[index], f"{value:.4f}")


def render_control_panel_page() -> None:
    """
    Main control panel page.
    """

    st.title("ControlForge Control Panel")

    st.caption(
        "Simulation-only controller tuning for the cart double pendulum demo."
    )

    render_safety_panel()

    st.divider()

    sample_index = int(time.time() * 10) % 1000
    states = generate_demo_states(sample_index)

    render_current_state_vector(states)

    st.divider()

    selected_controller = st.radio(
        "Select Controller",
        ["PID", "LQR"],
        horizontal=True,
    )

    enabled = st.toggle(
        "Enable Software Controller",
        value=False,
        help="This only enables software output inside the dashboard.",
    )

    if enabled:
        st.warning("Software controller enabled. Hardware output is still disabled.")
    else:
        st.info("Controller disabled. Output remains 0.")

    st.divider()

    if selected_controller == "PID":
        control_state = render_pid_panel(
            enabled=enabled,
            measured_value=states[0],
        )
    else:
        control_state = render_lqr_panel(
            enabled=enabled,
            states=states,
        )

    st.divider()

    render_controller_status(control_state)


if __name__ == "__main__":
    st.set_page_config(page_title="ControlForge Control Panel", layout="wide")
    render_control_panel_page()