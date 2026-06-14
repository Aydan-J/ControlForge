"""
double_pendulum.py

Simplified double pendulum/cart simulation for ControlForge.

Purpose:
- Generate fake/simulated state data when real hardware is unavailable
- Help test the dashboard and digital twin pipeline
- Provide the same 6-state format used by the Teensy serial stream

State format:
    [theta1, theta2, theta1_dot, theta2_dot, cart_pos, cart_vel]

Important:
This is a simplified simulation placeholder.
It is NOT a fully accurate double pendulum physics engine.
"""

import math
import time
from dataclasses import dataclass


@dataclass
class DoublePendulumState:
    theta1: float
    theta2: float
    theta1_dot: float
    theta2_dot: float
    cart_pos: float
    cart_vel: float

    def to_list(self):
        """
        Convert state object into generic ControlForge state list.
        """
        return [
            self.theta1,
            self.theta2,
            self.theta1_dot,
            self.theta2_dot,
            self.cart_pos,
            self.cart_vel,
        ]

    def to_packet_string(self, timestamp):
        """
        Convert simulated state into the same format as Teensy serial output.

        Format:
            timestamp,state1,state2,state3,state4,state5,state6
        """

        states = self.to_list()

        values = [timestamp] + states

        return ",".join(str(round(value, 4)) for value in values)


class DoublePendulumSimulator:
    def __init__(self):
        self.time_elapsed = 0.0

        self.state = DoublePendulumState(
            theta1=0.2,
            theta2=-0.3,
            theta1_dot=0.0,
            theta2_dot=0.0,
            cart_pos=0.0,
            cart_vel=0.0,
        )

    def reset(self):
        """
        Reset the simulation to a starting condition.
        """

        self.time_elapsed = 0.0

        self.state = DoublePendulumState(
            theta1=0.2,
            theta2=-0.3,
            theta1_dot=0.0,
            theta2_dot=0.0,
            cart_pos=0.0,
            cart_vel=0.0,
        )

    def step(self, dt=0.02, control_output=0.0):
        """
        Advance simulation by one time step.

        dt:
            Time step in seconds.

        control_output:
            Fake motor/control signal between -1 and 1.

        Returns:
            Updated DoublePendulumState.
        """

        control_output = self._clamp(control_output, -1.0, 1.0)

        self.time_elapsed += dt

        # Simplified fake cart dynamics.
        # This makes the cart respond smoothly to the control output.
        cart_acceleration = control_output * 0.8
        self.state.cart_vel += cart_acceleration * dt
        self.state.cart_vel *= 0.98
        self.state.cart_pos += self.state.cart_vel * dt

        # Keep fake cart inside a small visible range.
        if self.state.cart_pos > 1.0:
            self.state.cart_pos = 1.0
            self.state.cart_vel *= -0.3

        if self.state.cart_pos < -1.0:
            self.state.cart_pos = -1.0
            self.state.cart_vel *= -0.3

        # Simplified fake pendulum motion.
        # This creates chaotic-looking movement for dashboard testing.
        theta1_acc = (
            -0.7 * math.sin(self.state.theta1)
            + 0.15 * math.sin(self.state.theta2 - self.state.theta1)
            + 0.25 * control_output
        )

        theta2_acc = (
            -0.9 * math.sin(self.state.theta2)
            + 0.20 * math.sin(self.state.theta1 - self.state.theta2)
            - 0.15 * control_output
        )

        self.state.theta1_dot += theta1_acc * dt
        self.state.theta2_dot += theta2_acc * dt

        # Light damping so values do not explode.
        self.state.theta1_dot *= 0.995
        self.state.theta2_dot *= 0.995

        self.state.theta1 += self.state.theta1_dot * dt
        self.state.theta2 += self.state.theta2_dot * dt

        self.state.theta1 = self._wrap_angle(self.state.theta1)
        self.state.theta2 = self._wrap_angle(self.state.theta2)

        return self.state

    def get_state(self):
        """
        Return current simulation state.
        """

        return self.state

    def get_state_list(self):
        """
        Return current simulation state as generic list.
        """

        return self.state.to_list()

    def get_timestamp_ms(self):
        """
        Return simulation timestamp in milliseconds.
        """

        return int(self.time_elapsed * 1000)

    def get_packet_string(self):
        """
        Return current state in Teensy-like serial packet format.
        """

        return self.state.to_packet_string(self.get_timestamp_ms())

    def _wrap_angle(self, angle):
        """
        Wrap angle to range -pi to pi.
        """

        while angle > math.pi:
            angle -= 2 * math.pi

        while angle < -math.pi:
            angle += 2 * math.pi

        return angle

    def _clamp(self, value, minimum, maximum):
        """
        Clamp value between minimum and maximum.
        """

        return max(minimum, min(maximum, value))


if __name__ == "__main__":
    print("Double pendulum simulation test")
    print("-------------------------------")

    simulator = DoublePendulumSimulator()

    for step_number in range(20):
        # Fake changing control signal.
        control = math.sin(step_number * 0.2)

        state = simulator.step(dt=0.02, control_output=control)

        print(
            f"t={simulator.get_timestamp_ms()} ms | "
            f"theta1={state.theta1:.4f} | "
            f"theta2={state.theta2:.4f} | "
            f"cart_pos={state.cart_pos:.4f} | "
            f"packet={simulator.get_packet_string()}"
        )

        time.sleep(0.02)

    print("\nFinal state list:")
    print(simulator.get_state_list())