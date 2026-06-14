"""
ControlForge Pendulum Animation Widget

Purpose:
Reusable Streamlit visualization for a cart double pendulum.

Safety:
This file only visualizes simulated or measured states.
It does not control hardware.
"""

from dataclasses import dataclass
import math
import streamlit as st


@dataclass
class PendulumAnimationState:
    theta1: float
    theta2: float
    cart_pos: float = 0.0


def calculate_pendulum_points(
    animation_state: PendulumAnimationState,
    link1_length: float = 1.0,
    link2_length: float = 1.0,
) -> dict:
    """
    Convert cart position and pendulum angles into x/y points.

    Angle convention:
    theta = 0 means link points downward.
    """

    cart_x = animation_state.cart_pos
    cart_y = 0.0

    joint1_x = cart_x + link1_length * math.sin(animation_state.theta1)
    joint1_y = cart_y - link1_length * math.cos(animation_state.theta1)

    joint2_x = joint1_x + link2_length * math.sin(animation_state.theta1 + animation_state.theta2)
    joint2_y = joint1_y - link2_length * math.cos(animation_state.theta1 + animation_state.theta2)

    return {
        "cart": (cart_x, cart_y),
        "joint1": (joint1_x, joint1_y),
        "joint2": (joint2_x, joint2_y),
    }


def build_pendulum_dataframe(points: dict) -> pd.DataFrame:
    """
    Build a dataframe for plotting the pendulum links.
    """

    cart_x, cart_y = points["cart"]
    joint1_x, joint1_y = points["joint1"]
    joint2_x, joint2_y = points["joint2"]

    return pd.DataFrame(
        {
            "x": [cart_x, joint1_x, joint2_x],
            "y": [cart_y, joint1_y, joint2_y],
            "point": ["cart", "joint1", "joint2"],
        }
    )


def render_pendulum_animation(
    animation_state: PendulumAnimationState,
    link1_length: float = 1.0,
    link2_length: float = 1.0,
) -> None:
    """
    Render a simple cart double pendulum visualization.
    """

    st.subheader("Cart Double Pendulum Visualization")

    points = calculate_pendulum_points(
        animation_state=animation_state,
        link1_length=link1_length,
        link2_length=link2_length,
    )

    # Use lightweight dict for scatter chart instead of DataFrame
    chart_data = {
        "x": [points["cart"][0], points["joint1"][0], points["joint2"][0]],
        "y": [points["cart"][1], points["joint1"][1], points["joint2"][1]],
    }

    st.scatter_chart(
        chart_data,
        x="x",
        y="y",
        size=120,
    )

    st.caption(
        "This is a simplified point visualization. A polished animation can be added later."
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Theta 1", f"{animation_state.theta1:.4f} rad")

    with col2:
        st.metric("Theta 2", f"{animation_state.theta2:.4f} rad")

    with col3:
        st.metric("Cart Position", f"{animation_state.cart_pos:.4f} m")

    with st.expander("Pendulum point coordinates"):
        st.write({
            "cart": points["cart"],
            "joint1": points["joint1"],
            "joint2": points["joint2"],
        })


def render_pendulum_test_page() -> None:
    """
    Standalone Streamlit test page for this widget file.
    """

    st.set_page_config(
        page_title="ControlForge Pendulum Animation Test",
        layout="wide",
    )

    st.title("ControlForge Pendulum Animation Test")

    st.warning(
        "Visualization only. This does not send commands to the motor or motor driver."
    )

    theta1 = st.slider(
        "Theta 1",
        min_value=-3.14,
        max_value=3.14,
        value=0.4,
        step=0.01,
    )

    theta2 = st.slider(
        "Theta 2",
        min_value=-3.14,
        max_value=3.14,
        value=-0.7,
        step=0.01,
    )

    cart_pos = st.slider(
        "Cart Position",
        min_value=-2.0,
        max_value=2.0,
        value=0.0,
        step=0.01,
    )

    animation_state = PendulumAnimationState(
        theta1=theta1,
        theta2=theta2,
        cart_pos=cart_pos,
    )

    render_pendulum_animation(animation_state)


if __name__ == "__main__":
    render_pendulum_test_page()