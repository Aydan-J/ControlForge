"""
judge_demo.py

ControlForge Judge Demo page.

This version supports the CURRENT Arduino format:

Upper: 178.48 deg | Lower: 136.54 deg | CartTicks: 5 | MotorPWM: 0 | Safety: FAULT

It also supports CSV format if you switch Arduino back later:

timestamp,theta1,theta2,theta1_dot,theta2_dot,cart_pos,cart_vel
"""

import math
import re
import time

import pandas as pd
import streamlit as st

try:
    import serial
except ImportError:
    serial = None


def render_judge_demo_page():
    st.title("🏆 ControlForge Judge Demo")
    st.caption("Live hardware telemetry, variables, parameters, zeroing, graphs, and judge summary.")

    st.info(
        "Demo focus: ControlForge connects a physical double inverted pendulum "
        "to a real-time software dashboard using Teensy serial telemetry."
    )

    st.warning(
        "Close Arduino Serial Monitor and Serial Plotter before using this page. "
        "Only one program can use COM3 at a time."
    )

    # ============================================================
    # Session state
    # ============================================================

    defaults = {
        "judge_history": [],
        "judge_last_raw": "",
        "judge_status": "Waiting for hardware packets.",
        "judge_valid_packets": 0,
        "judge_invalid_packets": 0,
        "theta1_zero": 0.0,
        "theta2_zero": 0.0,
        "cart_zero": 0.0,
        "theta1_flip": False,
        "theta2_flip": False,
        "previous_packet": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # ============================================================
    # Helper functions
    # ============================================================

    def wrap_to_pi(angle):
        while angle > math.pi:
            angle -= 2.0 * math.pi
        while angle < -math.pi:
            angle += 2.0 * math.pi
        return angle

    def angle_difference(current_angle, previous_angle):
        return wrap_to_pi(current_angle - previous_angle)

    def parse_packet(raw_line):
        """
        Supports two formats:

        1. Human-readable Arduino format:
           Upper: 178.48 deg | Lower: 136.54 deg | CartTicks: 5 | MotorPWM: 0 | Safety: FAULT

        2. CSV format:
           timestamp,theta1,theta2,theta1_dot,theta2_dot,cart_pos,cart_vel
        """

        raw_line = raw_line.strip()

        if raw_line == "":
            raise ValueError("Empty serial line.")

        # ========================================================
        # Format 1: CSV
        # ========================================================

        if "," in raw_line:
            parts = [part.strip() for part in raw_line.split(",")]

            if len(parts) != 7:
                raise ValueError(
                    f"CSV packet found, but expected 7 values and got {len(parts)}. Raw: {raw_line}"
                )

            values = [float(part) for part in parts]

            packet = {
                "timestamp_ms": values[0],
                "theta1": values[1],
                "theta2": values[2],
                "theta1_dot": values[3],
                "theta2_dot": values[4],
                "cart_pos": values[5],
                "cart_vel": values[6],
                "motor_pwm": 0,
                "safety": "UNKNOWN",
                "raw": raw_line,
            }

            st.session_state.previous_packet = packet
            return packet

        # ========================================================
        # Format 2: Human-readable Arduino line
        # ========================================================

        pattern = (
            r"Upper:\s*([-+]?\d*\.?\d+)\s*deg\s*\|\s*"
            r"Lower:\s*([-+]?\d*\.?\d+)\s*deg\s*\|\s*"
            r"CartTicks:\s*([-+]?\d+)\s*\|\s*"
            r"MotorPWM:\s*([-+]?\d+)\s*\|\s*"
            r"Safety:\s*([A-Za-z]+)"
        )

        match = re.search(pattern, raw_line)

        if not match:
            raise ValueError(f"Could not parse Arduino line: {raw_line}")

        upper_deg = float(match.group(1))
        lower_deg = float(match.group(2))
        cart_ticks = float(match.group(3))
        motor_pwm = int(match.group(4))
        safety = match.group(5)

        now_ms = time.time() * 1000.0

        theta1 = math.radians(upper_deg)
        theta2 = math.radians(lower_deg)
        cart_pos = cart_ticks

        theta1_dot = 0.0
        theta2_dot = 0.0
        cart_vel = 0.0

        previous = st.session_state.previous_packet

        if previous is not None:
            dt = (now_ms - previous["timestamp_ms"]) / 1000.0

            if dt > 0:
                theta1_dot = angle_difference(theta1, previous["theta1"]) / dt
                theta2_dot = angle_difference(theta2, previous["theta2"]) / dt
                cart_vel = (cart_pos - previous["cart_pos"]) / dt

        packet = {
            "timestamp_ms": now_ms,
            "theta1": theta1,
            "theta2": theta2,
            "theta1_dot": theta1_dot,
            "theta2_dot": theta2_dot,
            "cart_pos": cart_pos,
            "cart_vel": cart_vel,
            "motor_pwm": motor_pwm,
            "safety": safety,
            "raw": raw_line,
        }

        st.session_state.previous_packet = packet
        return packet

    def close_serial_connections():
        for key in list(st.session_state.keys()):
            if key.startswith("judge_serial_"):
                try:
                    st.session_state[key].close()
                except Exception:
                    pass
                del st.session_state[key]

    def read_one_serial_line(port, baud_rate, timeout):
        if serial is None:
            raise ImportError("pyserial is not installed. Run: python -m pip install pyserial")

        serial_key = f"judge_serial_{port}_{baud_rate}"

        if serial_key not in st.session_state:
            try:
                st.session_state[serial_key] = serial.Serial(
                    port=port,
                    baudrate=baud_rate,
                    timeout=timeout,
                )
            except Exception as error:
                raise RuntimeError(
                    f"Could not open {port}. Close Arduino Serial Monitor, stop other Python processes, "
                    f"then click Reconnect Serial. Details: {error}"
                )

            time.sleep(2.0)

            try:
                st.session_state[serial_key].reset_input_buffer()
            except Exception:
                pass

        ser = st.session_state[serial_key]

        for _ in range(50):
            raw_bytes = ser.readline()
            raw_line = raw_bytes.decode(errors="ignore").strip()

            if raw_line:
                return raw_line

        raise ValueError("No serial data received from Teensy.")

    def add_packet(packet, max_history_rows):
        st.session_state.judge_history.append(packet)
        st.session_state.judge_valid_packets += 1

        if len(st.session_state.judge_history) > max_history_rows:
            st.session_state.judge_history = st.session_state.judge_history[-max_history_rows:]

    def get_zeroed_values(latest):
        theta1_zeroed = wrap_to_pi(latest["theta1"] - st.session_state.theta1_zero)
        theta2_zeroed = wrap_to_pi(latest["theta2"] - st.session_state.theta2_zero)
        cart_zeroed = latest["cart_pos"] - st.session_state.cart_zero

        if st.session_state.theta1_flip:
            theta1_zeroed = -theta1_zeroed

        if st.session_state.theta2_flip:
            theta2_zeroed = -theta2_zeroed

        return theta1_zeroed, theta2_zeroed, cart_zeroed

    def classify_health(latest, theta_limit_rad, velocity_limit_rad_s, cart_limit_ticks):
        if len(st.session_state.judge_history) == 0:
            return "Waiting", "Low", "Waiting for live hardware packets."

        if latest["safety"].upper() == "FAULT":
            return "Safety Fault", "High", "Arduino reported Safety: FAULT."

        warnings = []

        if abs(latest["theta1"]) > theta_limit_rad:
            warnings.append("Upper angle is outside selected range.")

        if abs(latest["theta2"]) > theta_limit_rad:
            warnings.append("Lower angle is outside selected range.")

        if abs(latest["theta1_dot"]) > velocity_limit_rad_s:
            warnings.append("Upper angular velocity is high.")

        if abs(latest["theta2_dot"]) > velocity_limit_rad_s:
            warnings.append("Lower angular velocity is high.")

        if abs(latest["cart_pos"]) > cart_limit_ticks:
            warnings.append("Cart position is outside selected range.")

        if warnings:
            return "Caution", "Medium", " ".join(warnings)

        return "Stable", "Low", "Live telemetry is being received."

    def make_summary(df):
        total_packets = st.session_state.judge_valid_packets + st.session_state.judge_invalid_packets

        telemetry_health = 0.0
        if total_packets > 0:
            telemetry_health = (st.session_state.judge_valid_packets / total_packets) * 100.0

        if df.empty:
            return {
                "duration_s": 0.0,
                "max_theta1": 0.0,
                "max_theta2": 0.0,
                "max_theta1_dot": 0.0,
                "max_theta2_dot": 0.0,
                "max_cart_pos": 0.0,
                "max_cart_vel": 0.0,
                "avg_theta1": 0.0,
                "avg_theta2": 0.0,
                "telemetry_health": telemetry_health,
            }

        duration_s = (df["timestamp_ms"].max() - df["timestamp_ms"].min()) / 1000.0

        return {
            "duration_s": duration_s,
            "max_theta1": df["theta1"].abs().max(),
            "max_theta2": df["theta2"].abs().max(),
            "max_theta1_dot": df["theta1_dot"].abs().max(),
            "max_theta2_dot": df["theta2_dot"].abs().max(),
            "max_cart_pos": df["cart_pos"].abs().max(),
            "max_cart_vel": df["cart_vel"].abs().max(),
            "avg_theta1": df["theta1"].mean(),
            "avg_theta2": df["theta2"].mean(),
            "telemetry_health": telemetry_health,
        }

    # ============================================================
    # Sidebar controls
    # ============================================================

    st.sidebar.header("Serial Parameters")

    port = st.sidebar.text_input("COM Port", value="COM3")

    baud_rate = st.sidebar.number_input(
        "Baud Rate",
        min_value=9600,
        max_value=1000000,
        value=115200,
        step=9600,
    )

    timeout = st.sidebar.number_input(
        "Serial Timeout",
        min_value=0.05,
        max_value=5.0,
        value=1.0,
        step=0.05,
    )

    read_attempts = st.sidebar.number_input(
        "Read Attempts Per Refresh",
        min_value=1,
        max_value=20,
        value=5,
        step=1,
    )

    max_history_rows = st.sidebar.number_input(
        "Max Stored Packets",
        min_value=50,
        max_value=10000,
        value=2000,
        step=50,
    )

    st.sidebar.divider()
    st.sidebar.header("Live Read Controls")

    read_button = st.sidebar.button("Read One Packet", type="primary")
    auto_read = st.sidebar.checkbox("Auto-read live hardware", value=False)

    refresh_delay = st.sidebar.slider(
        "Auto-read Delay",
        min_value=0.10,
        max_value=2.00,
        value=0.25,
        step=0.05,
    )

    reconnect_button = st.sidebar.button("Reconnect Serial")
    clear_button = st.sidebar.button("Clear Demo Run")

    st.sidebar.divider()
    st.sidebar.header("Zeroing / Calibration")

    zero_button = st.sidebar.button("Zero Current Position")

    st.session_state.theta1_flip = st.sidebar.checkbox(
        "Flip θ1 Direction",
        value=st.session_state.theta1_flip,
    )

    st.session_state.theta2_flip = st.sidebar.checkbox(
        "Flip θ2 Direction",
        value=st.session_state.theta2_flip,
    )

    st.sidebar.caption(
        f"θ1 zero: {st.session_state.theta1_zero:.4f} rad\n\n"
        f"θ2 zero: {st.session_state.theta2_zero:.4f} rad\n\n"
        f"Cart zero: {st.session_state.cart_zero:.2f} ticks"
    )

    st.sidebar.divider()
    st.sidebar.header("Safety Parameters")

    theta_limit_rad = st.sidebar.number_input(
        "Angle Warning Limit (rad)",
        min_value=0.1,
        max_value=10.0,
        value=3.2,
        step=0.1,
    )

    velocity_limit_rad_s = st.sidebar.number_input(
        "Velocity Warning Limit (rad/s)",
        min_value=0.1,
        max_value=100.0,
        value=10.0,
        step=0.5,
    )

    cart_limit_ticks = st.sidebar.number_input(
        "Cart Warning Limit (ticks)",
        min_value=10.0,
        max_value=100000.0,
        value=5000.0,
        step=100.0,
    )

    # ============================================================
    # Button actions
    # ============================================================

    if reconnect_button:
        close_serial_connections()
        st.session_state.judge_status = "Serial connection reset. Click Read One Packet."
        st.rerun()

    if clear_button:
        st.session_state.judge_history = []
        st.session_state.judge_last_raw = ""
        st.session_state.judge_status = "Demo run cleared."
        st.session_state.judge_valid_packets = 0
        st.session_state.judge_invalid_packets = 0
        st.session_state.previous_packet = None
        close_serial_connections()
        st.rerun()

    # ============================================================
    # Serial read
    # ============================================================

    if read_button or auto_read:
        packet = None
        last_error = None

        try:
            for _ in range(int(read_attempts)):
                raw_line = read_one_serial_line(port, int(baud_rate), float(timeout))
                st.session_state.judge_last_raw = raw_line

                try:
                    packet = parse_packet(raw_line)
                    break
                except Exception as parse_error:
                    last_error = parse_error
                    st.session_state.judge_invalid_packets += 1

            if packet is None:
                raise ValueError(f"No valid packet found. Last error: {last_error}")

            add_packet(packet, int(max_history_rows))
            st.session_state.judge_status = "Live hardware packet received."

        except Exception as read_error:
            st.session_state.judge_invalid_packets += 1
            st.session_state.judge_status = f"Read error: {read_error}"

    # ============================================================
    # Latest packet
    # ============================================================

    if st.session_state.judge_history:
        latest = st.session_state.judge_history[-1]
    else:
        latest = {
            "timestamp_ms": 0.0,
            "theta1": 0.0,
            "theta2": 0.0,
            "theta1_dot": 0.0,
            "theta2_dot": 0.0,
            "cart_pos": 0.0,
            "cart_vel": 0.0,
            "motor_pwm": 0,
            "safety": "UNKNOWN",
            "raw": "",
        }

    if zero_button:
        st.session_state.theta1_zero = latest["theta1"]
        st.session_state.theta2_zero = latest["theta2"]
        st.session_state.cart_zero = latest["cart_pos"]
        st.session_state.judge_status = "Current state saved as zero reference."
        st.rerun()

    theta1_zeroed, theta2_zeroed, cart_zeroed = get_zeroed_values(latest)

    df = pd.DataFrame(st.session_state.judge_history) if st.session_state.judge_history else pd.DataFrame()
    summary = make_summary(df)

    health_status, risk_level, health_message = classify_health(
        latest,
        theta_limit_rad,
        velocity_limit_rad_s,
        cart_limit_ticks,
    )

    # ============================================================
    # Dashboard display
    # ============================================================

    top1, top2, top3, top4, top5 = st.columns(5)

    top1.metric("System Health", health_status)
    top2.metric("Risk Level", risk_level)
    top3.metric("Safety", latest["safety"])
    top4.metric("Packets", len(st.session_state.judge_history))
    top5.metric("Motor PWM", latest["motor_pwm"])

    if health_status == "Stable":
        st.success(health_message)
    elif health_status == "Waiting":
        st.info(health_message)
    else:
        st.warning(health_message)

    st.caption(st.session_state.judge_status)

    st.divider()
    st.header("Live Hardware Measurements")

    raw_col, zero_col, velocity_col = st.columns(3)

    with raw_col:
        st.subheader("Raw Variables")
        st.metric("Upper Angle / θ1", f"{latest['theta1']:.4f} rad")
        st.metric("Lower Angle / θ2", f"{latest['theta2']:.4f} rad")
        st.metric("Cart Position", f"{latest['cart_pos']:.2f} ticks")

    with zero_col:
        st.subheader("Zeroed Variables")
        st.metric("θ1 Zeroed", f"{theta1_zeroed:.4f} rad")
        st.metric("θ2 Zeroed", f"{theta2_zeroed:.4f} rad")
        st.metric("Cart Zeroed", f"{cart_zeroed:.2f} ticks")

    with velocity_col:
        st.subheader("Velocity Variables")
        st.metric("θ1 Velocity", f"{latest['theta1_dot']:.4f} rad/s")
        st.metric("θ2 Velocity", f"{latest['theta2_dot']:.4f} rad/s")
        st.metric("Cart Velocity", f"{latest['cart_vel']:.2f} ticks/s")

    st.subheader("Latest Raw Serial")
    st.code(st.session_state.judge_last_raw or "No serial data yet.")

    st.divider()
    st.header("Current Parameters")

    parameters_df = pd.DataFrame(
        [
            {"Parameter": "COM Port", "Value": port},
            {"Parameter": "Baud Rate", "Value": int(baud_rate)},
            {"Parameter": "Timeout", "Value": float(timeout)},
            {"Parameter": "Read Attempts", "Value": int(read_attempts)},
            {"Parameter": "Max Stored Packets", "Value": int(max_history_rows)},
            {"Parameter": "θ1 Zero Offset", "Value": st.session_state.theta1_zero},
            {"Parameter": "θ2 Zero Offset", "Value": st.session_state.theta2_zero},
            {"Parameter": "Cart Zero Offset", "Value": st.session_state.cart_zero},
            {"Parameter": "Flip θ1", "Value": st.session_state.theta1_flip},
            {"Parameter": "Flip θ2", "Value": st.session_state.theta2_flip},
            {"Parameter": "Angle Warning Limit", "Value": theta_limit_rad},
            {"Parameter": "Velocity Warning Limit", "Value": velocity_limit_rad_s},
            {"Parameter": "Cart Warning Limit", "Value": cart_limit_ticks},
        ]
    )

    st.dataframe(parameters_df, use_container_width=True)

    st.divider()
    st.header("Demo Run Summary")

    s1, s2, s3, s4, s5 = st.columns(5)

    s1.metric("Duration", f"{summary['duration_s']:.2f} s")
    s2.metric("Max |θ1|", f"{summary['max_theta1']:.4f} rad")
    s3.metric("Max |θ2|", f"{summary['max_theta2']:.4f} rad")
    s4.metric("Max |Cart|", f"{summary['max_cart_pos']:.2f} ticks")
    s5.metric("Telemetry Health", f"{summary['telemetry_health']:.1f}%")

    report_text = f"""
ControlForge Judge Demo Report

System Health: {health_status}
Risk Level: {risk_level}
Status Message: {health_message}

Duration: {summary['duration_s']:.2f} seconds
Valid Packets: {st.session_state.judge_valid_packets}
Invalid Packets: {st.session_state.judge_invalid_packets}
Telemetry Health: {summary['telemetry_health']:.1f}%

Current Raw Variables:
theta1 = {latest['theta1']:.4f} rad
theta2 = {latest['theta2']:.4f} rad
theta1_dot = {latest['theta1_dot']:.4f} rad/s
theta2_dot = {latest['theta2_dot']:.4f} rad/s
cart_pos = {latest['cart_pos']:.2f} ticks
cart_vel = {latest['cart_vel']:.2f} ticks/s
motor_pwm = {latest['motor_pwm']}
safety = {latest['safety']}

Current Zeroed Variables:
theta1_zeroed = {theta1_zeroed:.4f} rad
theta2_zeroed = {theta2_zeroed:.4f} rad
cart_zeroed = {cart_zeroed:.2f} ticks

Maximum Values:
max |theta1| = {summary['max_theta1']:.4f} rad
max |theta2| = {summary['max_theta2']:.4f} rad
max |theta1_dot| = {summary['max_theta1_dot']:.4f} rad/s
max |theta2_dot| = {summary['max_theta2_dot']:.4f} rad/s
max |cart_pos| = {summary['max_cart_pos']:.2f} ticks
max |cart_vel| = {summary['max_cart_vel']:.2f} ticks/s
""".strip()

    with st.expander("View Generated Judge Report"):
        st.text(report_text)

    st.download_button(
        label="Download Judge Report",
        data=report_text,
        file_name="controlforge_judge_report.txt",
        mime="text/plain",
    )

    st.divider()
    st.header("Long-Scale Run Analytics")

    if df.empty:
        st.info("Click Read One Packet or turn on Auto-read to begin collecting hardware data.")
    else:
        graph_df = df.copy()

        graph_df["time_s"] = (
            graph_df["timestamp_ms"] - graph_df["timestamp_ms"].iloc[0]
        ) / 1000.0

        graph_df["theta1_zeroed"] = graph_df["theta1"].apply(
            lambda value: -wrap_to_pi(value - st.session_state.theta1_zero)
            if st.session_state.theta1_flip
            else wrap_to_pi(value - st.session_state.theta1_zero)
        )

        graph_df["theta2_zeroed"] = graph_df["theta2"].apply(
            lambda value: -wrap_to_pi(value - st.session_state.theta2_zero)
            if st.session_state.theta2_flip
            else wrap_to_pi(value - st.session_state.theta2_zero)
        )

        graph_df["cart_zeroed"] = graph_df["cart_pos"] - st.session_state.cart_zero

        selected_signals = st.multiselect(
            "Choose variables to graph",
            [
                "theta1",
                "theta2",
                "theta1_zeroed",
                "theta2_zeroed",
                "theta1_dot",
                "theta2_dot",
                "cart_pos",
                "cart_zeroed",
                "cart_vel",
                "motor_pwm",
            ],
            default=["theta1_zeroed", "theta2_zeroed", "cart_zeroed"],
        )

        if selected_signals:
            chart_df = graph_df.set_index("time_s")[selected_signals]
            st.line_chart(chart_df)

        with st.expander("Recent Data Table"):
            st.dataframe(graph_df.tail(100), use_container_width=True)

        st.download_button(
            label="Download Hardware Data CSV",
            data=graph_df.to_csv(index=False),
            file_name="controlforge_hardware_data.csv",
            mime="text/csv",
        )

    st.divider()
    st.header("What Judges Should Notice")

    j1, j2, j3 = st.columns(3)

    with j1:
        st.subheader("1. Real Hardware Data")
        st.write("The dashboard is receiving live encoder data from the Teensy.")

    with j2:
        st.subheader("2. Useful Parameters")
        st.write("Serial settings, safety limits, zero offsets, and direction flips can be adjusted live.")

    with j3:
        st.subheader("3. Analysis Ready")
        st.write("Runs are graphed, summarized, and downloadable as CSV/text reports.")

    st.markdown(
        "**Pitch line:** ControlForge makes a difficult physical control system measurable, debuggable, and safer to test."
    )

    if auto_read:
        time.sleep(float(refresh_delay))
        st.rerun()


if __name__ == "__main__":
    render_judge_demo_page()