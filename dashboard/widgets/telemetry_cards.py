"""
telemetry_cards.py

Reusable Streamlit telemetry display widgets for ControlForge.

Purpose:
- Display latest telemetry values
- Display state labels, units, and values
- Display raw packet information
- Keep dashboard/app.py cleaner

This file does NOT control hardware.
"""

import streamlit as st


def display_telemetry_metrics(mapped_states):
    """
    Display mapped telemetry states as metric cards.

    Expected mapped_states format:

    {
        "theta1": {
            "label": "Theta 1",
            "value": 0.25,
            "unit": "rad",
            "description": "First pendulum joint angle."
        },
        ...
    }
    """

    if mapped_states is None or len(mapped_states) == 0:
        st.warning("No mapped telemetry states available.")
        return

    columns = st.columns(3)

    for index, (state_name, info) in enumerate(mapped_states.items()):
        column = columns[index % 3]

        label = info.get("label", state_name)
        value = info.get("value", None)
        unit = info.get("unit", "")
        description = info.get("description", "")

        if value is None:
            display_value = "None"
        else:
            try:
                display_value = f"{float(value):.4f} {unit}"
            except ValueError:
                display_value = f"{value} {unit}"

        with column:
            st.metric(label=label, value=display_value)

            if description:
                st.caption(description)


def display_latest_snapshot(snapshot, is_stale=False):
    """
    Display latest raw telemetry snapshot.

    snapshot should have:
    - timestamp
    - states
    - raw
    """

    if snapshot is None:
        st.warning("No latest telemetry snapshot available.")
        return

    status_text = "STALE" if is_stale else "LIVE"

    if is_stale:
        st.error(f"Telemetry status: {status_text}")
    else:
        st.success(f"Telemetry status: {status_text}")

    st.json(
        {
            "timestamp": snapshot.timestamp,
            "states": snapshot.states,
            "raw": snapshot.raw,
            "is_stale": is_stale,
        }
    )


def display_raw_packet(raw_packet):
    """
    Display raw packet string in a code block.
    """

    if raw_packet is None or raw_packet == "":
        st.warning("No raw packet available.")
        return

    st.code(raw_packet)


def display_history_summary(history):
    """
    Display a small summary of telemetry history.
    """

    if history is None or len(history) == 0:
        st.info("No telemetry history yet.")
        return

    latest = history[-1]

    st.write(
        {
            "history_size": len(history),
            "latest_timestamp": latest.timestamp,
            "latest_raw": latest.raw,
        }
    )


def display_recent_history(history, count=10):
    """
    Display recent telemetry history entries.
    """

    if history is None or len(history) == 0:
        st.info("No telemetry history yet.")
        return

    recent_items = history[-count:]

    # Single JSON render instead of one st.write per item
    st.json([
        {
            "timestamp": item.timestamp,
            "states": item.states,
            "raw": item.raw,
        }
        for item in recent_items
    ])


if __name__ == "__main__":
    """
    Simple direct test.

    Run:
        streamlit run dashboard/widgets/telemetry_cards.py

    Or:
        python -m streamlit run dashboard/widgets/telemetry_cards.py
    """

    from dataclasses import dataclass

    st.title("Telemetry Cards Test")

    @dataclass
    class FakeSnapshot:
        timestamp: float
        states: list
        raw: str

    fake_mapped_states = {
        "theta1": {
            "label": "Theta 1",
            "value": 0.25,
            "unit": "rad",
            "description": "First pendulum joint angle.",
        },
        "theta2": {
            "label": "Theta 2",
            "value": -0.50,
            "unit": "rad",
            "description": "Second pendulum joint angle.",
        },
        "theta1_dot": {
            "label": "Theta 1 velocity",
            "value": 0.10,
            "unit": "rad/s",
            "description": "Angular velocity of first pendulum joint.",
        },
        "theta2_dot": {
            "label": "Theta 2 velocity",
            "value": -0.20,
            "unit": "rad/s",
            "description": "Angular velocity of second pendulum joint.",
        },
        "cart_pos": {
            "label": "Cart position",
            "value": 0.00,
            "unit": "m",
            "description": "Horizontal position of the cart.",
        },
        "cart_vel": {
            "label": "Cart velocity",
            "value": 0.00,
            "unit": "m/s",
            "description": "Horizontal velocity of the cart.",
        },
    }

    fake_snapshot = FakeSnapshot(
        timestamp=1000,
        states=[0.25, -0.50, 0.10, -0.20, 0.00, 0.00],
        raw="1000,0.25,-0.50,0.10,-0.20,0.00,0.00",
    )

    fake_history = [
        FakeSnapshot(1000, [0.1, -0.1, 0, 0, 0, 0], "1000,0.1,-0.1,0,0,0,0"),
        FakeSnapshot(1020, [0.2, -0.2, 0, 0, 0, 0], "1020,0.2,-0.2,0,0,0,0"),
        FakeSnapshot(1040, [0.3, -0.3, 0, 0, 0, 0], "1040,0.3,-0.3,0,0,0,0"),
    ]

    st.header("Metric cards")
    display_telemetry_metrics(fake_mapped_states)

    st.header("Latest snapshot")
    display_latest_snapshot(fake_snapshot, is_stale=False)

    st.header("Raw packet")
    display_raw_packet(fake_snapshot.raw)

    st.header("History summary")
    display_history_summary(fake_history)

    st.header("Recent history")
    display_recent_history(fake_history)