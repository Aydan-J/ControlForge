import math
import re
import sys
import time
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    import serial
except ImportError:
    serial = None


# Make backend imports work when running this page directly
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


st.set_page_config(
    page_title="ControlForge Live Hardware",
    page_icon="🔌",
    layout="wide",
)

st.title("🔌 ControlForge Live Hardware Telemetry")
st.caption("Reads real Teensy serial data and displays live pendulum/cart measurements.")

st.warning(
    "Close Arduino Serial Monitor before using this page. "
    "Only one program can use the Teensy COM port at a time."
)


# ============================================================
# Session state
# ============================================================

if "hardware_history" not in st.session_state:
    st.session_state.hardware_history = []

if "hardware_last_raw" not in st.session_state:
    st.session_state.hardware_last_raw = ""

if "hardware_status" not in st.session_state:
    st.session_state.hardware_status = "Waiting for data."

if "previous_packet" not in st.session_state:
    st.session_state.previous_packet = None


# ============================================================
# Parser
# ============================================================

def angle_difference(current_angle, previous_angle):
    diff = current_angle - previous_angle

    while diff > math.pi:
        diff -= 2 * math.pi

    while diff < -math.pi:
        diff += 2 * math.pi

    return diff


def parse_arduino_line(raw_line: str):
    """
    Supports BOTH formats:

    1. Clean CSV:
       timestamp,theta1,theta2,theta1_dot,theta2_dot,cart_pos,cart_vel

    2. Human-readable Arduino output:
       Upper: 348.09 deg | Lower: 255.72 deg | CartTicks: -1856 | MotorPWM: 0 | Safety: FAULT
    """

    raw_line = raw_line.strip()

    if not raw_line:
        raise ValueError("Empty line.")

    # Format 1: CSV packet
    if "," in raw_line:
        parts = [p.strip() for p in raw_line.split(",")]

        if len(parts) != 7:
            raise ValueError(f"Expected 7 CSV values, got {len(parts)}.")

        values = [float(p) for p in parts]

        return {
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

    # Format 2: your Arduino human-readable line
    pattern = (
        r"Upper:\s*([-+]?\d*\.?\d+)\s*deg\s*\|\s*"
        r"Lower:\s*([-+]?\d*\.?\d+)\s*deg\s*\|\s*"
        r"CartTicks:\s*([-+]?\d+)\s*\|\s*"
        r"MotorPWM:\s*([-+]?\d+)\s*\|\s*"
        r"Safety:\s*(\w+)"
    )

    match = re.search(pattern, raw_line)

    if not match:
        raise ValueError(f"Unrecognized line format: {raw_line}")

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


# ============================================================
# Serial reader
# ============================================================

def read_one_serial_line(port: str, baud_rate: int, timeout: float):
    if serial is None:
        raise ImportError("pyserial is not installed. Run: python -m pip install pyserial")

    with serial.Serial(port=port, baudrate=baud_rate, timeout=timeout) as ser:
        raw_bytes = ser.readline()

    return raw_bytes.decode(errors="ignore").strip()


def add_packet(packet):
    st.session_state.hardware_history.append(packet)

    max_rows = 1000
    if len(st.session_state.hardware_history) > max_rows:
        st.session_state.hardware_history = st.session_state.hardware_history[-max_rows:]


# ============================================================
# Sidebar controls
# ============================================================

st.sidebar.header("Serial Settings")

port = st.sidebar.text_input("COM Port", value="COM3")
baud_rate = st.sidebar.number_input(
    "Baud Rate",
    min_value=9600,
    max_value=1000000,
    value=115200,
    step=9600,
)
timeout = st.sidebar.number_input(
    "Timeout",
    min_value=0.05,
    max_value=5.0,
    value=1.0,
    step=0.05,
)

auto_read = st.sidebar.checkbox("Auto-read live hardware", value=False)

refresh_delay = st.sidebar.slider(
    "Refresh delay",
    min_value=0.05,
    max_value=1.00,
    value=0.20,
    step=0.05,
)

read_button = st.sidebar.button("Read One Packet")
clear_button = st.sidebar.button("Clear History")

if clear_button:
    st.session_state.hardware_history = []
    st.session_state.hardware_last_raw = ""
    st.session_state.hardware_status = "History cleared."
    st.session_state.previous_packet = None
    st.rerun()


# ============================================================
# Read serial data
# ============================================================

if read_button or auto_read:
    try:
        raw_line = read_one_serial_line(port, int(baud_rate), float(timeout))
        st.session_state.hardware_last_raw = raw_line

        packet = parse_arduino_line(raw_line)
        add_packet(packet)

        st.session_state.hardware_status = "Valid hardware packet received."

    except Exception as e:
        st.session_state.hardware_status = f"Read error: {e}"


# ============================================================
# Display latest values
# ============================================================

history = st.session_state.hardware_history

if history:
    latest = history[-1]
else:
    latest = {
        "timestamp_ms": 0,
        "theta1": 0,
        "theta2": 0,
        "theta1_dot": 0,
        "theta2_dot": 0,
        "cart_pos": 0,
        "cart_vel": 0,
        "motor_pwm": 0,
        "safety": "UNKNOWN",
        "raw": "",
    }

status_col1, status_col2, status_col3, status_col4 = st.columns(4)

status_col1.metric("Packets Read", len(history))
status_col2.metric("Safety", latest["safety"])
status_col3.metric("Motor PWM", latest["motor_pwm"])
status_col4.metric("Cart Position", f"{latest['cart_pos']:.2f}")

st.caption(st.session_state.hardware_status)

st.subheader("Live Values")

c1, c2, c3 = st.columns(3)

with c1:
    st.metric("Theta 1 / Upper", f"{latest['theta1']:.4f} rad")
    st.metric("Theta 1 Velocity", f"{latest['theta1_dot']:.4f} rad/s")

with c2:
    st.metric("Theta 2 / Lower", f"{latest['theta2']:.4f} rad")
    st.metric("Theta 2 Velocity", f"{latest['theta2_dot']:.4f} rad/s")

with c3:
    st.metric("Cart Position", f"{latest['cart_pos']:.2f} ticks")
    st.metric("Cart Velocity", f"{latest['cart_vel']:.2f} ticks/s")

st.subheader("Latest Raw Serial Line")
st.code(st.session_state.hardware_last_raw or "No serial data read yet.")


# ============================================================
# Graphs
# ============================================================

st.subheader("Live Hardware Graphs")

if not history:
    st.info("Click 'Read One Packet' or enable auto-read to start receiving hardware data.")
else:
    df = pd.DataFrame(history)
    df["time_s"] = (df["timestamp_ms"] - df["timestamp_ms"].iloc[0]) / 1000.0

    selected_signals = st.multiselect(
        "Choose signals to graph",
        ["theta1", "theta2", "theta1_dot", "theta2_dot", "cart_pos", "cart_vel"],
        default=["theta1", "theta2", "cart_pos"],
    )

    if selected_signals:
        fig = go.Figure()

        for signal in selected_signals:
            fig.add_trace(
                go.Scatter(
                    x=df["time_s"],
                    y=df[signal],
                    mode="lines",
                    name=signal,
                )
            )

        fig.update_layout(
            height=420,
            xaxis_title="Time (s)",
            yaxis_title="Value",
            margin=dict(l=10, r=10, t=30, b=10),
        )

        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Recent hardware data table"):
        st.dataframe(df.tail(50), use_container_width=True)

    csv_data = df.to_csv(index=False)

    st.download_button(
        label="Download Hardware Data CSV",
        data=csv_data,
        file_name="controlforge_hardware_data.csv",
        mime="text/csv",
    )


# ============================================================
# Auto refresh
# ============================================================

if auto_read:
    time.sleep(refresh_delay)
    st.rerun()