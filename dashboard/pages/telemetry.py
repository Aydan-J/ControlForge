"""
ControlForge Telemetry Page

Purpose:
Telemetry dashboard page for live/simulated state monitoring.

Current status:
- Simulation/demo mode works.
- Hardware Serial mode is read-only.
- No motor commands are sent from this page.
"""

from dataclasses import dataclass
import math
import time

import pandas as pd
import streamlit as st


# ------------------------------------------------------------
# Optional pyserial import
# ------------------------------------------------------------
try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    serial = None
    SERIAL_AVAILABLE = False


# ------------------------------------------------------------
# Data structure
# ------------------------------------------------------------
@dataclass
class TelemetryPagePacket:
    timestamp: float
    states: list[float]
    raw: str


# ------------------------------------------------------------
# Packet parsing
# ------------------------------------------------------------
def parse_serial_packet(raw_line: str) -> tuple[TelemetryPagePacket | None, str | None]:
    """
    Parse one serial line using the universal 6-state packet format.
    """

    raw_line = raw_line.strip()

    if not raw_line:
        return None, "Empty packet."

    parts = raw_line.split(",")

    if len(parts) != 7:
        return None, f"Expected 7 comma-separated values, got {len(parts)}."

    try:
        values = [float(part.strip()) for part in parts]
    except ValueError:
        return None, "Packet contains a value that is not a number."

    timestamp = values[0]
    states = values[1:]

    packet = TelemetryPagePacket(
        timestamp=timestamp,
        states=states,
        raw=raw_line,
    )

    return packet, None


# ------------------------------------------------------------
# Cached fake telemetry generation
# ------------------------------------------------------------
def generate_fake_packet(sample_index: int) -> TelemetryPagePacket:
    """
    Generate one fake telemetry packet.
    """

    timestamp = sample_index * 20

    theta1 = 0.25 * math.sin(sample_index / 15)
    theta2 = -0.35 * math.cos(sample_index / 18)
    theta1_dot = 0.05 * math.sin(sample_index / 8)
    theta2_dot = 0.05 * math.cos(sample_index / 10)
    cart_pos = 0.01 * math.sin(sample_index / 20)
    cart_vel = 0.02 * math.cos(sample_index / 20)

    states = [theta1, theta2, theta1_dot, theta2_dot, cart_pos, cart_vel]

    raw = (
        f"{timestamp},"
        f"{theta1:.4f},"
        f"{theta2:.4f},"
        f"{theta1_dot:.4f},"
        f"{theta2_dot:.4f},"
        f"{cart_pos:.4f},"
        f"{cart_vel:.4f}"
    )

    return TelemetryPagePacket(timestamp=timestamp, states=states, raw=raw)


@st.cache_data
def build_fake_history(sample_count: int = 100) -> list[dict]:
    """
    Build fake telemetry history. Cached so it is only computed once
    per sample_count value.
    Returns list of dicts (serializable for caching).
    """

    packets = []
    for i in range(sample_count):
        p = generate_fake_packet(i)
        packets.append({"timestamp": p.timestamp, "states": p.states, "raw": p.raw})
    return packets


def _packets_from_cache(cached: list[dict]) -> list[TelemetryPagePacket]:
    """Convert cached dicts back to TelemetryPagePacket objects."""
    return [TelemetryPagePacket(**d) for d in cached]


# ------------------------------------------------------------
# Hardware serial reading
# ------------------------------------------------------------
def get_serial_reader(port: str, baud_rate: int, timeout_seconds: float) -> tuple[object | None, str | None]:
    """
    Get or create a persistent SerialReader stored in session state.
    Avoids closing/reopening the connection on every Streamlit rerun.
    """
    if not SERIAL_AVAILABLE:
        return None, "pyserial is not installed. Run: .\\.venv\\Scripts\\python.exe -m pip install pyserial"

    if not port.strip():
        return None, "Enter a COM port first, such as COM3 or COM5."

    reader = st.session_state.get("serial_reader", None)

    # Recreate the connection if parameters change
    if reader is not None:
        if reader.port != port.strip() or reader.baud_rate != baud_rate or reader.timeout != timeout_seconds:
            try:
                reader.disconnect()
            except Exception:
                pass
            reader = None

    if reader is None or not reader.is_connected():
        try:
            from backend.serial_reader import SerialReader
            reader = SerialReader(port=port.strip(), baud_rate=baud_rate, timeout=timeout_seconds)
            reader.connect()
            st.session_state.serial_reader = reader
        except Exception as error:
            return None, f"Could not connect to {port}: {error}"

    return reader, None


# ------------------------------------------------------------
# Cached DataFrame conversion
# ------------------------------------------------------------
@st.cache_data
def build_telemetry_dataframe_from_dicts(rows_data: list[dict]) -> pd.DataFrame:
    """
    Build DataFrame from list of row dicts. Cached for performance.
    """
    rows = []
    for d in rows_data:
        states = d["states"]
        if len(states) != 6:
            continue
        rows.append({
            "timestamp": d["timestamp"],
            "theta1": states[0],
            "theta2": states[1],
            "theta1_dot": states[2],
            "theta2_dot": states[3],
            "cart_pos": states[4],
            "cart_vel": states[5],
            "raw": d["raw"],
        })
    return pd.DataFrame(rows)


def build_telemetry_dataframe(history: list[TelemetryPagePacket]) -> pd.DataFrame:
    """
    Convert telemetry packets into a table.
    """
    rows_data = [{"timestamp": p.timestamp, "states": p.states, "raw": p.raw} for p in history]
    return build_telemetry_dataframe_from_dicts(tuple(str(r) for r in rows_data) if len(rows_data) > 200 else rows_data)


# Simple non-cached version for hardware mode where data changes every read
def build_telemetry_dataframe_direct(history: list[TelemetryPagePacket]) -> pd.DataFrame:
    rows = []
    for packet in history:
        if len(packet.states) != 6:
            continue
        rows.append({
            "timestamp": packet.timestamp,
            "theta1": packet.states[0],
            "theta2": packet.states[1],
            "theta1_dot": packet.states[2],
            "theta2_dot": packet.states[3],
            "cart_pos": packet.states[4],
            "cart_vel": packet.states[5],
            "raw": packet.raw,
        })
    return pd.DataFrame(rows)


# ------------------------------------------------------------
# UI rendering helpers
# ------------------------------------------------------------
def render_connection_status(mode: str, serial_status: str | None = None) -> None:
    """
    Show connection mode and safety status.
    """

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Mode", mode)
    with col2:
        st.metric("Packet Format", "6-State Universal")
    with col3:
        st.metric("Hardware Output", "Disabled")

    if serial_status:
        st.info(serial_status)


def render_latest_telemetry(packet: TelemetryPagePacket | None) -> None:
    """
    Show latest telemetry values.
    """

    st.subheader("Latest Telemetry")

    if packet is None:
        st.info("No valid telemetry packet available yet.")
        return

    labels = ["Theta 1", "Theta 2", "Theta 1 Velocity", "Theta 2 Velocity", "Cart Position", "Cart Velocity"]
    units = ["rad", "rad", "rad/s", "rad/s", "m", "m/s"]

    cols = st.columns(3)

    for index, value in enumerate(packet.states):
        with cols[index % 3]:
            st.metric(label=labels[index], value=f"{value:.4f} {units[index]}")

    with st.expander("Raw serial packet"):
        st.code(packet.raw)


def render_telemetry_plots(dataframe: pd.DataFrame) -> None:
    """
    Show telemetry plots.
    """

    st.subheader("Telemetry Plots")

    if dataframe.empty:
        st.info("No telemetry history available to plot yet.")
        return

    selected_signals = st.multiselect(
        "Select signals",
        ["theta1", "theta2", "theta1_dot", "theta2_dot", "cart_pos", "cart_vel"],
        default=["theta1", "theta2"],
    )

    if selected_signals:
        plot_data = dataframe.set_index("timestamp")[selected_signals]
        st.line_chart(plot_data)
    else:
        st.info("Select at least one signal to plot.")


def render_recent_packets(dataframe: pd.DataFrame) -> None:
    """
    Show recent telemetry table.
    """

    with st.expander("Recent Packets"):
        if dataframe.empty:
            st.info("No recent packets available yet.")
            return

        packet_count = st.slider(
            "Rows to show",
            min_value=5,
            max_value=50,
            value=10,
            step=5,
        )

        st.dataframe(
            dataframe.tail(packet_count),
            use_container_width=True,
            hide_index=True,
        )


# ------------------------------------------------------------
# Main page
# ------------------------------------------------------------
def render_telemetry_page() -> None:
    """
    Main telemetry page.
    """

    st.title("ControlForge Telemetry")

    st.caption(
        "Live/simulated telemetry monitoring for the universal 6-state ControlForge packet format."
    )

    # Store hardware packets across Streamlit reruns.
    if "hardware_history" not in st.session_state:
        st.session_state.hardware_history = []

    mode = st.radio(
        "Telemetry Source",
        ["Simulation Demo", "Hardware Serial Read-Only"],
        horizontal=True,
    )

    latest_packet = None
    history = []
    serial_status = None

    # --------------------------------------------------------
    # Simulation demo mode
    # --------------------------------------------------------
    if mode == "Simulation Demo":
        sample_index = int(time.time() * 10) % 1000

        cached = build_fake_history(sample_count=120)
        history = _packets_from_cache(cached)
        latest_packet = generate_fake_packet(sample_index)

        serial_status = "Using simulated demo telemetry. No hardware is required."

    # --------------------------------------------------------
    # Hardware serial mode
    # --------------------------------------------------------
    else:
        st.subheader("Hardware Serial Settings")

        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            port = st.text_input("COM Port", value="COM3")

        with col2:
            baud_rate = st.number_input("Baud Rate", min_value=9600, max_value=1000000, value=115200, step=9600)

        with col3:
            timeout_seconds = st.number_input("Timeout Seconds", min_value=0.1, max_value=10.0, value=2.0, step=0.1)

        col_a, col_b, col_c = st.columns([1, 1, 2])

        with col_a:
            read_button = st.button("Read One Packet")

        with col_b:
            clear_button = st.button("Clear Hardware History")

        with col_c:
            auto_read = st.checkbox("Auto-read read-only serial", value=False)

        if clear_button:
            st.session_state.hardware_history = []
            if "serial_reader" in st.session_state and st.session_state.serial_reader is not None:
                try:
                    st.session_state.serial_reader.disconnect()
                except Exception:
                    pass
                st.session_state.serial_reader = None
            st.success("Hardware packet history cleared and serial disconnected.")

        if read_button or auto_read:
            reader, error = get_serial_reader(
                port=port,
                baud_rate=int(baud_rate),
                timeout_seconds=float(timeout_seconds),
            )

            if reader is not None:
                try:
                    packet_raw = reader.read_packet()
                    if packet_raw is not None:
                        packet = TelemetryPagePacket(
                            timestamp=packet_raw.timestamp,
                            states=packet_raw.states,
                            raw=packet_raw.raw,
                        )
                        st.session_state.hardware_history.append(packet)
                        # Cap history to prevent memory/rendering lag
                        if len(st.session_state.hardware_history) > 300:
                            st.session_state.hardware_history = st.session_state.hardware_history[-300:]
                        latest_packet = packet
                        serial_status = f"Received valid packet from {port} at {baud_rate} baud."
                    else:
                        serial_status = "No serial packet received (timeout)."
                except Exception as error:
                    serial_status = f"Serial read error: {error}"
                    # Disconnect on error to force reconnect
                    try:
                        reader.disconnect()
                    except Exception:
                        pass
                    st.session_state.serial_reader = None
            else:
                serial_status = error

        if st.session_state.hardware_history:
            history = st.session_state.hardware_history
            latest_packet = st.session_state.hardware_history[-1]
        else:
            history = []
            if serial_status is None:
                serial_status = (
                    "Hardware Serial mode selected. Enter the COM port and click "
                    "'Read One Packet' after the Teensy is connected."
                )

    dataframe = build_telemetry_dataframe_direct(history)

    render_connection_status(mode=mode, serial_status=serial_status)

    st.divider()

    render_latest_telemetry(latest_packet)

    st.divider()

    render_telemetry_plots(dataframe)

    st.divider()

    render_recent_packets(dataframe)

    # Auto-read loop.
    if mode == "Hardware Serial Read-Only" and "auto_read" in locals() and auto_read:
        time.sleep(0.5)
        st.rerun()


if __name__ == "__main__":
    st.set_page_config(page_title="ControlForge Telemetry", layout="wide")
    render_telemetry_page()