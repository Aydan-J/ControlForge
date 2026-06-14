import math
import time

import plotly.graph_objects as go
import streamlit as st


# ------------------------------------------------------------
# Demo state generation
# ------------------------------------------------------------
def generate_demo_state(t: float) -> dict:
    """
    Generate fake/demo cart double-pendulum states.

    Important:
        This is only for visualization/demo mode.
        It is not real hardware data.
        It is not a physically accurate double-pendulum simulation.
    """

    theta1 = 0.70 * math.sin(1.35 * t)
    theta2 = 0.85 * math.sin(1.95 * t + 0.70)

    theta1_dot = 0.70 * 1.35 * math.cos(1.35 * t)
    theta2_dot = 0.85 * 1.95 * math.cos(1.95 * t + 0.70)

    cart_pos = 1.45 * math.sin(0.75 * t)
    cart_vel = 1.45 * 0.75 * math.cos(0.75 * t)

    return {
        "theta1": theta1,
        "theta2": theta2,
        "theta1_dot": theta1_dot,
        "theta2_dot": theta2_dot,
        "cart_pos": cart_pos,
        "cart_vel": cart_vel,
    }


# ------------------------------------------------------------
# Coordinate calculation
# ------------------------------------------------------------
def calculate_pendulum_points(
    theta1: float,
    theta2: float,
    cart_pos: float,
    link1_length: float = 1.3,
    link2_length: float = 1.1,
    theta2_mode: str = "Absolute angle",
) -> dict:
    """
    Convert cart position and pendulum angles into x/y coordinates.
    """

    cart_x = cart_pos
    cart_y = 0.0

    joint1_x = cart_x
    joint1_y = cart_y

    joint2_x = joint1_x + link1_length * math.sin(theta1)
    joint2_y = joint1_y - link1_length * math.cos(theta1)

    if theta2_mode == "Relative angle":
        second_arm_angle = theta1 + theta2
    else:
        second_arm_angle = theta2

    end_x = joint2_x + link2_length * math.sin(second_arm_angle)
    end_y = joint2_y - link2_length * math.cos(second_arm_angle)

    return {
        "cart": (cart_x, cart_y),
        "joint1": (joint1_x, joint1_y),
        "joint2": (joint2_x, joint2_y),
        "end": (end_x, end_y),
    }


# ------------------------------------------------------------
# Cached layout template — built once, reused every frame
# ------------------------------------------------------------
@st.cache_data
def _build_layout_template():
    """
    Build the static parts of the Plotly layout once.
    Reused every frame to avoid rebuilding the full layout dict.
    """
    return dict(
        height=550,
        margin=dict(l=10, r=10, t=30, b=10),
        title="Live Cart Double Pendulum View",
        transition_duration=0,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            range=[-3.0, 3.0],
            zeroline=False,
            showgrid=True,
            title="Cart position",
            gridcolor="rgba(128,128,128,0.15)",
        ),
        yaxis=dict(
            range=[-2.6, 0.7],
            zeroline=False,
            showgrid=True,
            scaleanchor="x",
            scaleratio=1,
            title="Height",
            gridcolor="rgba(128,128,128,0.15)",
        ),
        showlegend=False,
    )


# ------------------------------------------------------------
# Lightweight figure creation
# ------------------------------------------------------------
def create_pendulum_figure(
    state: dict,
    link1_length: float = 1.3,
    link2_length: float = 1.1,
    theta2_mode: str = "Absolute angle",
) -> go.Figure:
    """
    Create a minimal Plotly figure for the pendulum.
    Only 3 traces instead of the original 7 — much faster to render.
    """

    points = calculate_pendulum_points(
        theta1=state["theta1"],
        theta2=state["theta2"],
        cart_pos=state["cart_pos"],
        link1_length=link1_length,
        link2_length=link2_length,
        theta2_mode=theta2_mode,
    )

    cart_x, cart_y = points["cart"]
    joint2_x, joint2_y = points["joint2"]
    end_x, end_y = points["end"]

    cart_width = 0.70
    cart_height = 0.35

    fig = go.Figure()

    # Track line
    fig.add_trace(
        go.Scatter(
            x=[-3.0, 3.0],
            y=[0, 0],
            mode="lines",
            line=dict(width=4, color="rgba(128,128,128,0.5)"),
            hoverinfo="skip",
        )
    )

    # Cart body as a thick marker
    fig.add_shape(
        type="rect",
        x0=cart_x - cart_width / 2,
        y0=cart_y - cart_height / 2,
        x1=cart_x + cart_width / 2,
        y1=cart_y + cart_height / 2,
        line=dict(width=2),
        fillcolor="rgba(120, 120, 120, 0.35)",
    )

    # Pendulum arms + joints — single trace for speed
    fig.add_trace(
        go.Scatter(
            x=[cart_x, joint2_x, end_x],
            y=[cart_y, joint2_y, end_y],
            mode="lines+markers",
            line=dict(width=6),
            marker=dict(size=[12, 15, 20]),
            hoverinfo="skip",
        )
    )

    # Cart wheels
    wheel_y = cart_y - cart_height / 2 - 0.09
    fig.add_trace(
        go.Scatter(
            x=[cart_x - 0.22, cart_x + 0.22],
            y=[wheel_y, wheel_y],
            mode="markers",
            marker=dict(size=10),
            hoverinfo="skip",
        )
    )

    fig.update_layout(**_build_layout_template())

    return fig


# ------------------------------------------------------------
# Main page render function (called from app.py)
# ------------------------------------------------------------
def render_visualization_page() -> None:
    """
    Render the visualization page.
    Optimized: sidebar controls are outside the animation loop,
    and only the chart + metrics re-render on each tick.
    """

    st.title("ControlForge Visualization")
    st.caption("Cart double pendulum visualization in safe simulation mode.")

    st.warning(
        "Hardware output is disabled. Do not connect the 775 motor or motor driver yet."
    )

    # ---- Sidebar controls (rendered once) ----
    st.sidebar.header("Visualization Controls")

    mode = st.sidebar.radio(
        "Mode",
        ["Demo animation", "Manual control"],
    )

    auto_refresh = st.sidebar.checkbox(
        "Auto-refresh demo animation",
        value=True,
        disabled=(mode != "Demo animation"),
    )

    refresh_rate = st.sidebar.slider(
        "Refresh delay (seconds)",
        min_value=0.05,
        max_value=0.50,
        value=0.10,
        step=0.01,
        disabled=(mode != "Demo animation"),
    )

    st.sidebar.divider()

    link1_length = st.sidebar.slider(
        "Link 1 length",
        min_value=0.5,
        max_value=2.0,
        value=1.3,
        step=0.1,
    )

    link2_length = st.sidebar.slider(
        "Link 2 length",
        min_value=0.5,
        max_value=2.0,
        value=1.1,
        step=0.1,
    )

    theta2_mode = st.sidebar.radio(
        "Theta 2 interpretation",
        ["Absolute angle", "Relative angle"],
    )

    st.sidebar.divider()
    st.sidebar.caption("Current mode is visual-only. No motor output is sent.")

    # ---- State ----
    if mode == "Demo animation":
        t = time.time()
        state = generate_demo_state(t)
    else:
        st.sidebar.subheader("Manual State Inputs")

        theta1 = st.sidebar.slider("Theta 1", -math.pi, math.pi, 0.5, 0.01)
        theta2 = st.sidebar.slider("Theta 2", -math.pi, math.pi, -0.7, 0.01)
        cart_pos = st.sidebar.slider("Cart position", -2.5, 2.5, 0.0, 0.01)

        state = {
            "theta1": theta1,
            "theta2": theta2,
            "theta1_dot": 0.0,
            "theta2_dot": 0.0,
            "cart_pos": cart_pos,
            "cart_vel": 0.0,
        }

    # ---- Layout ----
    left_col, right_col = st.columns([2.2, 1.0])

    with left_col:
        figure = create_pendulum_figure(
            state=state,
            link1_length=link1_length,
            link2_length=link2_length,
            theta2_mode=theta2_mode,
        )
        st.plotly_chart(
            figure,
            use_container_width=True,
            config={
                "displayModeBar": False,
                "staticPlot": True,    # ← key optimization: disables all Plotly JS interactivity
                "scrollZoom": False,
            },
        )

    with right_col:
        st.subheader("Current State")
        st.metric("Theta 1", f"{state['theta1']:.3f} rad")
        st.metric("Theta 2", f"{state['theta2']:.3f} rad")
        st.metric("Cart Position", f"{state['cart_pos']:.3f} m")
        st.divider()
        st.metric("Theta 1 Velocity", f"{state['theta1_dot']:.3f} rad/s")
        st.metric("Theta 2 Velocity", f"{state['theta2_dot']:.3f} rad/s")
        st.metric("Cart Velocity", f"{state['cart_vel']:.3f} m/s")

    # ---- Explanation (collapsed by default, no cost when hidden) ----
    with st.expander("How this visualization works"):
        st.write(
            """
            The cart position controls the horizontal location of the cart.
            Theta 1 controls the first pendulum arm.
            Theta 2 controls the second pendulum arm.

            Right now, these values are generated in demo mode or controlled manually
            with sliders. Later, this same visualization can use real values from the
            Teensy serial packet.
            """
        )

    # ---- Auto-refresh ----
    if mode == "Demo animation" and auto_refresh:
        time.sleep(refresh_rate)
        st.rerun()


# Allow running standalone for testing
if __name__ == "__main__":
    st.set_page_config(
        page_title="ControlForge Visualization",
        page_icon="⚙️",
        layout="wide",
    )
    render_visualization_page()