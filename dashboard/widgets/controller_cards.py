"""
ControlForge Controller Cards

Purpose:
Reusable Streamlit UI components for controller selection, PID tuning,
LQR demo tuning, controller status display, and safety notices.

Safety:
This file does NOT send commands to motors.
This file is dashboard UI only.
All controller outputs are software-only unless hardware output is added later.
"""

from dataclasses import dataclass
import streamlit as st


@dataclass
class ControllerDisplayState:
    active_controller: str
    is_enabled: bool
    output: float
    setpoint: float | None = None
    measured_value: float | None = None


def render_safety_notice() -> None:
    """
    Display hardware safety reminder.
    """

    st.error(
        "Hardware output is disabled. Do not connect the 775 motor or motor driver "
        "until safety limits, emergency stop behavior, and output clamping are finished."
    )


def render_controller_selector(
    available_controllers: list[str],
    default_controller: str = "PID",
) -> str:
    """
    Let the user select the active controller.
    """

    if not available_controllers:
        st.error("No controllers available.")
        return "None"

    if default_controller not in available_controllers:
        default_controller = available_controllers[0]

    selected_controller = st.selectbox(
        "Select Controller",
        available_controllers,
        index=available_controllers.index(default_controller),
    )

    return selected_controller


def render_controller_enable_toggle(default_enabled: bool = False) -> bool:
    """
    Show an enable/disable toggle for software-only controller testing.
    """

    enabled = st.toggle(
        "Enable Software Controller",
        value=default_enabled,
        help="Simulation-only right now. This does not send motor commands.",
    )

    if enabled:
        st.warning("Software controller is enabled. Motor output is still disabled.")
    else:
        st.info("Controller is disabled. Output should remain 0.")

    return enabled


def render_pid_controls(
    default_kp: float = 0.2,
    default_ki: float = 0.0,
    default_kd: float = 0.05,
    default_setpoint: float = 0.0,
) -> dict:
    """
    Show PID tuning controls.

    Returns:
        Dictionary containing kp, ki, kd, and setpoint.
    """

    st.subheader("PID Controls")
    st.caption("These values affect software simulation only.")

    kp = st.slider(
        "Kp",
        min_value=0.0,
        max_value=5.0,
        value=float(default_kp),
        step=0.01,
    )

    ki = st.slider(
        "Ki",
        min_value=0.0,
        max_value=2.0,
        value=float(default_ki),
        step=0.01,
    )

    kd = st.slider(
        "Kd",
        min_value=0.0,
        max_value=2.0,
        value=float(default_kd),
        step=0.01,
    )

    setpoint = st.number_input(
        "Setpoint",
        value=float(default_setpoint),
        step=0.1,
        help="Target value for the PID controller.",
    )

    return {
        "kp": kp,
        "ki": ki,
        "kd": kd,
        "setpoint": setpoint,
    }


def render_lqr_controls(default_gains: list[float] | None = None) -> dict:
    """
    Show simple LQR demo gain controls.

    This is not a full LQR solver.
    It only edits a manual gain vector.
    """

    st.subheader("LQR Demo Controls")
    st.caption("Demo only. This is not a mathematically solved LQR controller yet.")

    if default_gains is None:
        default_gains = [0.4, 0.2, 0.1, 0.1, 0.05, 0.05]

    gains = []

    for index, gain in enumerate(default_gains):
        new_gain = st.slider(
            f"K{index + 1}",
            min_value=-5.0,
            max_value=5.0,
            value=float(gain),
            step=0.01,
        )
        gains.append(new_gain)

    return {
        "gains": gains,
    }


def render_controller_status_card(controller_state: ControllerDisplayState) -> None:
    """
    Display the current controller status.
    """

    st.subheader("Controller Status")

    col1, col2, col3 = st.columns(3)

    status_text = "Enabled" if controller_state.is_enabled else "Disabled"

    with col1:
        st.metric("Status", status_text)

    with col2:
        st.metric("Active Controller", controller_state.active_controller)

    with col3:
        st.metric("Controller Output", f"{controller_state.output:.4f}")

    col4, col5 = st.columns(2)

    with col4:
        if controller_state.setpoint is not None:
            st.metric("Setpoint", f"{controller_state.setpoint:.4f}")
        else:
            st.metric("Setpoint", "N/A")

    with col5:
        if controller_state.measured_value is not None:
            st.metric("Measured Value", f"{controller_state.measured_value:.4f}")
        else:
            st.metric("Measured Value", "N/A")


def render_controller_test_page() -> None:
    """
    Standalone Streamlit test page for this widget file.
    """

    st.set_page_config(
        page_title="ControlForge Controller Cards Test",
        layout="wide",
    )

    st.title("ControlForge Controller Cards Test")

    render_safety_notice()

    available_controllers = ["PID", "LQR"]

    selected_controller = render_controller_selector(
        available_controllers=available_controllers,
        default_controller="PID",
    )

    enabled = render_controller_enable_toggle(default_enabled=False)

    st.divider()

    if selected_controller == "PID":
        pid_values = render_pid_controls()

        fake_output = 0.25 if enabled else 0.0

        controller_state = ControllerDisplayState(
            active_controller="PID",
            is_enabled=enabled,
            output=fake_output,
            setpoint=pid_values["setpoint"],
            measured_value=0.15,
        )

    elif selected_controller == "LQR":
        lqr_values = render_lqr_controls()

        fake_output = -0.12 if enabled else 0.0

        controller_state = ControllerDisplayState(
            active_controller="LQR",
            is_enabled=enabled,
            output=fake_output,
            setpoint=None,
            measured_value=None,
        )

        st.write("Current LQR gain vector:")
        st.json(lqr_values)

    else:
        controller_state = ControllerDisplayState(
            active_controller="None",
            is_enabled=False,
            output=0.0,
        )

    st.divider()

    render_controller_status_card(controller_state)


if __name__ == "__main__":
    render_controller_test_page()