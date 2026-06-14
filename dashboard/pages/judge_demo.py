import time
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    import serial
except ImportError:
    serial = None


# ============================================================
# Page setup
# ============================================================

st.set_page_config(
    page_title="ControlForge Judge Demo",
    page_icon="🏆",
    layout="wide"
)

STATE_COLUMNS = [
    "timestamp_ms",
    "theta1",
    "theta2",
    "theta1_dot",
    "theta2_dot",
    "cart_pos",
    "cart_vel",
]

DISPLAY_NAMES = {
    "theta1": "Theta 1",
    "theta2": "Theta 2",
    "theta1_dot": "Theta 1 Velocity",
    "theta2_dot": "Theta 2 Velocity",
    "cart_pos": "Cart Position",
    "cart_vel": "Cart Velocity",
}


# ============================================================
# Session state
# ============================================================

if "judge_history" not in st.session_state:
    st.session_state.judge_history = []

if "judge_start_time" not in st.session_state:
    st.session_state.judge_start_time = time.time()

if "judge_packet_count" not in st.session_state:
    st.session_state.judge_packet_count = 0

if "judge_invalid_count" not in st.session_state:
    st.session_state.judge_invalid_count = 0

if "judge_last_raw_packet" not in st.session_state:
    st.session_state.judge_last_raw_packet = ""

if "judge_status_message" not in st.session_state:
    st.session_state.judge_status_message = "Demo ready."


# ============================================================
# Packet helpers
# ============================================================

def parse_packet(raw_line: str):
    """
    Expected packet format:
    timestamp,theta1,theta2,theta1_dot,theta2_dot,cart_pos,cart_vel
    """

    if not raw_line:
        raise ValueError("Empty packet.")

    parts = raw_line.strip().split(",")

    if len(parts) != 7:
        raise ValueError(f"Expected 7 values, got {len(parts)}.")

    values = [float(part) for part in parts]

    return {
        "timestamp_ms": values[0],
        "theta1": values[1],
        "theta2": values[2],
        "theta1_dot": values[3],
        "theta2_dot": values[4],
        "cart_pos": values[5],
        "cart_vel": values[6],
    }


def generate_demo_packet():
    """
    Generates fake judge-demo telemetry.
    This matches the same 7-value format the Teensy sends.
    """

    timestamp_ms = int((time.time() - st.session_state.judge_start_time) * 1000)
    t = timestamp_ms / 1000.0

    theta1 = 0.25 * np.sin(t)
    theta2 = -0.35 * np.cos(t * 0.8)
    theta1_dot = 0.05 * np.cos(t)
    theta2_dot = 0.05 * np.sin(t * 0.8)
    cart_pos = 0.10 * np.sin(t * 0.5)
    cart_vel = 0.06 * np.cos(t * 0.5)

    raw_packet = (
        f"{timestamp_ms},"
        f"{theta1:.4f},"
        f"{theta2:.4f},"
        f"{theta1_dot:.4f},"
        f"{theta2_dot:.4f},"
        f"{cart_pos:.4f},"
        f"{cart_vel:.4f}"
    )

    return raw_packet


def read_serial_packet(port: str, baud_rate: int, timeout: float):
    """
    Reads one packet from the Teensy.
    This is read-only. It does not send anything back.
    """

    if serial is None:
        raise ImportError("pyserial is not installed. Run: pip install pyserial")

    with serial.Serial(port=port, baudrate=baud_rate, timeout=timeout) as ser:
        raw_bytes = ser.readline()

    return raw_bytes.decode(errors="ignore").strip()


def add_packet_to_history(packet_dict):
    st.session_state.judge_history.append(packet_dict)
    st.session_state.judge_packet_count += 1

    max_history = 500
    if len(st.session_state.judge_history) > max_history:
        st.session_state.judge_history = st.session_state.judge_history[-max_history:]


def get_history_df():
    if not st.session_state.judge_history:
        return pd.DataFrame(columns=STATE_COLUMNS)

    return pd.DataFrame(st.session_state.judge_history)


# ============================================================
# Visualization helpers
# ============================================================

def make_pendulum_figure(theta1, theta2, cart_pos, theta2_mode="Relative angle"):
    """
    Draws a cart double pendulum.

    theta1: first arm angle
    theta2: second arm angle
    cart_pos: cart x-position
    theta2_mode:
        - Relative angle: theta2 is measured from first arm
        - Absolute angle: theta2 is measured from vertical
    """

    l1 = 1.0
    l2 = 0.8

    cart_width = 0.45
    cart_height = 0.22
    wheel_radius = 0.06

    cart_x = cart_pos
    cart_y = 0.0

    joint1_x = cart_x
    joint1_y = cart_y + cart_height / 2

    # First arm: angle from vertical
    x1 = joint1_x + l1 * np.sin(theta1)
    y1 = joint1_y - l1 * np.cos(theta1)

    if theta2_mode == "Relative angle":
        theta2_absolute = theta1 + theta2
    else:
        theta2_absolute = theta2

    x2 = x1 + l2 * np.sin(theta2_absolute)
    y2 = y1 - l2 * np.cos(theta2_absolute)

    fig = go.Figure()

    # Track
    fig.add_trace(go.Scatter(
        x=[-1.5, 1.5],
        y=[-0.18, -0.18],
        mode="lines",
        line=dict(width=6),
        name="Track"
    ))

    # Cart body
    fig.add_shape(
        type="rect",
        x0=cart_x - cart_width / 2,
        y0=cart_y - cart_height / 2,
        x1=cart_x + cart_width / 2,
        y1=cart_y + cart_height / 2,
        line=dict(width=2),
        fillcolor="rgba(120,120,120,0.25)",
    )

    # Wheels
    for wx in [cart_x - 0.14, cart_x + 0.14]:
        fig.add_shape(
            type="circle",
            x0=wx - wheel_radius,
            y0=-0.18 - wheel_radius,
            x1=wx + wheel_radius,
            y1=-0.18 + wheel_radius,
            line=dict(width=2),
            fillcolor="rgba(80,80,80,0.25)",
        )

    # Pendulum arms
    fig.add_trace(go.Scatter(
        x=[joint1_x, x1, x2],
        y=[joint1_y, y1, y2],
        mode="lines+markers",
        line=dict(width=6),
        marker=dict(size=[12, 14, 18]),
        name="Double Pendulum"
    ))

    # Labels
    fig.add_annotation(
        x=cart_x,
        y=0.32,
        text=f"cart_pos = {cart_pos:.3f}",
        showarrow=False
    )

    fig.add_annotation(
        x=x1,
        y=y1 + 0.15,
        text=f"θ1 = {theta1:.3f}",
        showarrow=False
    )

    fig.add_annotation(
        x=x2,
        y=y2 - 0.15,
        text=f"θ2 = {theta2:.3f}",
        showarrow=False
    )

    fig.update_layout(
        height=520,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(range=[-1.7, 1.7], zeroline=False, showgrid=True),
        yaxis=dict(range=[-2.1, 0.7], zeroline=False, showgrid=True, scaleanchor="x", scaleratio=1),
        showlegend=False,
        title="Live Cart Double Pendulum Visualization"
    )

    return fig


# ============================================================
# Analysis helpers
# ============================================================

def analyze_system_health(latest_packet, df):
    """
    Simple judge-facing health monitor.
    This is not motor control. It only analyzes incoming data.
    """

    warnings = []

    theta1 = abs(latest_packet["theta1"])
    theta2 = abs(latest_packet["theta2"])
    theta1_dot = abs(latest_packet["theta1_dot"])
    theta2_dot = abs(latest_packet["theta2_dot"])
    cart_pos = abs(latest_packet["cart_pos"])

    if theta1 > 0.75:
        warnings.append("Theta 1 angle is large.")

    if theta2 > 0.75:
        warnings.append("Theta 2 angle is large.")

    if theta1_dot > 1.5:
        warnings.append("Theta 1 velocity is high.")

    if theta2_dot > 1.5:
        warnings.append("Theta 2 velocity is high.")

    if cart_pos > 0.8:
        warnings.append("Cart position is near the safety range limit.")

    if len(df) >= 2:
        latest_time = df["timestamp_ms"].iloc[-1]
        previous_time = df["timestamp_ms"].iloc[-2]
        delta = latest_time - previous_time

        if delta > 1000:
            warnings.append("Telemetry update delay detected.")

    if not warnings:
        return "Stable", "Low", "No anomalies detected."

    if len(warnings) <= 2:
        return "Caution", "Medium", " ".join(warnings)

    return "Unstable", "High", " ".join(warnings)


def make_run_summary(df):
    if df.empty:
        return {
            "duration_s": 0,
            "packets": 0,
            "max_theta1": 0,
            "max_theta2": 0,
            "max_cart_pos": 0,
            "avg_theta1": 0,
            "avg_theta2": 0,
            "avg_cart_pos": 0,
            "telemetry_health": 0,
        }

    duration_s = (df["timestamp_ms"].max() - df["timestamp_ms"].min()) / 1000
    packets = len(df)

    total_packets = st.session_state.judge_packet_count + st.session_state.judge_invalid_count

    if total_packets == 0:
        telemetry_health = 0
    else:
        telemetry_health = (st.session_state.judge_packet_count / total_packets) * 100

    return {
        "duration_s": duration_s,
        "packets": packets,
        "max_theta1": df["theta1"].abs().max(),
        "max_theta2": df["theta2"].abs().max(),
        "max_cart_pos": df["cart_pos"].abs().max(),
        "avg_theta1": df["theta1"].mean(),
        "avg_theta2": df["theta2"].mean(),
        "avg_cart_pos": df["cart_pos"].mean(),
        "telemetry_health": telemetry_health,
    }


def make_summary_text(summary, health_status, risk_level, health_message):
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    text = f"""
ControlForge Demo Run Summary
Generated: {created_at}

Experiment Duration: {summary["duration_s"]:.2f} seconds
Valid Packets Received: {summary["packets"]}
Invalid Packets: {st.session_state.judge_invalid_count}
Telemetry Health: {summary["telemetry_health"]:.1f}%

Maximum Theta 1: {summary["max_theta1"]:.4f} rad
Maximum Theta 2: {summary["max_theta2"]:.4f} rad
Maximum Cart Position: {summary["max_cart_pos"]:.4f} m

Average Theta 1: {summary["avg_theta1"]:.4f} rad
Average Theta 2: {summary["avg_theta2"]:.4f} rad
Average Cart Position: {summary["avg_cart_pos"]:.4f} m

System Health: {health_status}
Risk Level: {risk_level}
Health Notes: {health_message}

Safety Mode:
Read-only telemetry is enabled. No motor commands were sent.
"""
    return text.strip()


# ============================================================
# Header
# ============================================================

st.title("🏆 ControlForge Judge Demo")
st.caption(
    "A polished live demo page combining telemetry, visualization, system health, "
    "and an automatic run summary report."
)

st.info(
    "Safety status: ControlForge is currently in read-only mode. "
    "This page reads telemetry and visualizes it, but it does not send motor commands."
)


# ============================================================
# Sidebar controls
# ============================================================

st.sidebar.header("Demo Controls")

data_source = st.sidebar.radio(
    "Data Source",
    ["Built-in Demo Telemetry", "Hardware Serial Read-Only"],
)

theta2_mode = st.sidebar.selectbox(
    "Theta 2 Interpretation",
    ["Relative angle", "Absolute angle"],
)

auto_update = st.sidebar.checkbox("Auto-update demo", value=True)

refresh_delay = st.sidebar.slider(
    "Refresh delay",
    min_value=0.05,
    max_value=1.00,
    value=0.20,
    step=0.05,
)

if data_source == "Hardware Serial Read-Only":
    st.sidebar.subheader("Serial Settings")

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
else:
    port = "COM3"
    baud_rate = 115200
    timeout = 1.0

read_button = st.sidebar.button("Read One Packet")

clear_button = st.sidebar.button("Clear Demo Run")

if clear_button:
    st.session_state.judge_history = []
    st.session_state.judge_packet_count = 0
    st.session_state.judge_invalid_count = 0
    st.session_state.judge_last_raw_packet = ""
    st.session_state.judge_start_time = time.time()
    st.session_state.judge_status_message = "Demo run cleared."
    st.rerun()


# ============================================================
# Read packet
# ============================================================

should_read = read_button or auto_update

if should_read:
    try:
        if data_source == "Built-in Demo Telemetry":
            raw_packet = generate_demo_packet()
        else:
            raw_packet = read_serial_packet(port, int(baud_rate), float(timeout))

        st.session_state.judge_last_raw_packet = raw_packet
        packet = parse_packet(raw_packet)
        add_packet_to_history(packet)

        st.session_state.judge_status_message = "Valid packet received."

    except Exception as e:
        st.session_state.judge_invalid_count += 1
        st.session_state.judge_status_message = f"Packet error: {e}"


df = get_history_df()

if df.empty:
    latest = {
        "timestamp_ms": 0,
        "theta1": 0,
        "theta2": 0,
        "theta1_dot": 0,
        "theta2_dot": 0,
        "cart_pos": 0,
        "cart_vel": 0,
    }
else:
    latest = df.iloc[-1].to_dict()


health_status, risk_level, health_message = analyze_system_health(latest, df)
summary = make_run_summary(df)
summary_text = make_summary_text(summary, health_status, risk_level, health_message)


# ============================================================
# Main dashboard layout
# ============================================================

top1, top2, top3, top4 = st.columns(4)

top1.metric("System Health", health_status)
top2.metric("Risk Level", risk_level)
top3.metric("Valid Packets", st.session_state.judge_packet_count)
top4.metric("Telemetry Health", f"{summary['telemetry_health']:.1f}%")

st.caption(st.session_state.judge_status_message)

left_col, right_col = st.columns([1.35, 1])

with left_col:
    fig = make_pendulum_figure(
        latest["theta1"],
        latest["theta2"],
        latest["cart_pos"],
        theta2_mode=theta2_mode,
    )
    st.plotly_chart(fig, use_container_width=True)

with right_col:
    st.subheader("Live Telemetry")

    c1, c2 = st.columns(2)

    with c1:
        st.metric("Theta 1", f"{latest['theta1']:.4f} rad")
        st.metric("Theta 1 Velocity", f"{latest['theta1_dot']:.4f} rad/s")
        st.metric("Cart Position", f"{latest['cart_pos']:.4f} m")

    with c2:
        st.metric("Theta 2", f"{latest['theta2']:.4f} rad")
        st.metric("Theta 2 Velocity", f"{latest['theta2_dot']:.4f} rad/s")
        st.metric("Cart Velocity", f"{latest['cart_vel']:.4f} m/s")

    st.subheader("Health Notes")
    if health_status == "Stable":
        st.success(health_message)
    elif health_status == "Caution":
        st.warning(health_message)
    else:
        st.error(health_message)

    st.subheader("Latest Raw Packet")
    st.code(st.session_state.judge_last_raw_packet or "No packet yet.")


# ============================================================
# Run summary report
# ============================================================

st.divider()
st.header("📄 Demo Run Summary Report")

r1, r2, r3, r4 = st.columns(4)

r1.metric("Duration", f"{summary['duration_s']:.2f} s")
r2.metric("Max θ1", f"{summary['max_theta1']:.4f} rad")
r3.metric("Max θ2", f"{summary['max_theta2']:.4f} rad")
r4.metric("Max Cart Pos", f"{summary['max_cart_pos']:.4f} m")

r5, r6, r7, r8 = st.columns(4)

r5.metric("Average θ1", f"{summary['avg_theta1']:.4f} rad")
r6.metric("Average θ2", f"{summary['avg_theta2']:.4f} rad")
r7.metric("Average Cart Pos", f"{summary['avg_cart_pos']:.4f} m")
r8.metric("Invalid Packets", st.session_state.judge_invalid_count)

with st.expander("View full generated report"):
    st.text(summary_text)

st.download_button(
    label="Download Run Summary as TXT",
    data=summary_text,
    file_name="controlforge_demo_run_summary.txt",
    mime="text/plain",
)

if not df.empty:
    csv_data = df.to_csv(index=False)

    st.download_button(
        label="Download Telemetry Data as CSV",
        data=csv_data,
        file_name="controlforge_demo_telemetry.csv",
        mime="text/csv",
    )


# ============================================================
# Charts and table
# ============================================================

st.divider()
st.header("Telemetry Trends")

if df.empty:
    st.write("No telemetry data yet.")
else:
    plot_df = df.copy()
    plot_df["time_s"] = plot_df["timestamp_ms"] / 1000

    selected_signals = st.multiselect(
        "Choose signals to graph",
        ["theta1", "theta2", "theta1_dot", "theta2_dot", "cart_pos", "cart_vel"],
        default=["theta1", "theta2", "cart_pos"],
    )

    if selected_signals:
        trend_fig = go.Figure()

        for signal in selected_signals:
            trend_fig.add_trace(go.Scatter(
                x=plot_df["time_s"],
                y=plot_df[signal],
                mode="lines",
                name=DISPLAY_NAMES[signal],
            ))

        trend_fig.update_layout(
            height=400,
            xaxis_title="Time (s)",
            yaxis_title="Value",
            margin=dict(l=10, r=10, t=30, b=10),
        )

        st.plotly_chart(trend_fig, use_container_width=True)

    with st.expander("View recent telemetry table"):
        st.dataframe(df.tail(25), use_container_width=True)


# ============================================================
# Architecture explanation
# ============================================================

st.divider()
st.header("Why This Demo Matters")

a1, a2, a3 = st.columns(3)

with a1:
    st.subheader("1. Hardware Pipeline")
    st.write(
        "The Teensy sends telemetry packets through USB Serial. "
        "The dashboard reads the packets and converts them into live state values."
    )

with a2:
    st.subheader("2. Live Visualization")
    st.write(
        "The pendulum animation turns raw numbers into a physical-looking system, "
        "so judges can understand what the data means."
    )

with a3:
    st.subheader("3. Run Report")
    st.write(
        "After a demo run, ControlForge summarizes system behavior, packet health, "
        "maximum angles, cart movement, and safety status."
    )


# ============================================================
# Auto refresh
# ============================================================

if auto_update:
    time.sleep(refresh_delay)
    st.rerun()