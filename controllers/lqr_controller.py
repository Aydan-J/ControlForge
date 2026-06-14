"""
lqr_controller.py

Safe placeholder/demo LQR controller for ControlForge.

Purpose:
- Provide an LQR-style controller interface
- Allow dashboard/controller manager integration
- Keep output clamped for safety
- Avoid real hardware control until the physical model is verified

Important:
This is NOT a full automatic LQR solver.
This uses manually provided gain values K.

LQR idea:
    output = -Kx

Where:
    x = current state vector
    K = gain vector

Example:
    states = [theta1, theta2, theta1_dot, theta2_dot, cart_pos, cart_vel]
    gains  = [k1,     k2,     k3,         k4,         k5,       k6]

This file does NOT directly control hardware.
"""


from dataclasses import dataclass


@dataclass
class LQRConfig:
    gains: list
    output_min: float = -1.0
    output_max: float = 1.0


class LQRController:
    def __init__(self, config=None):
        if config is None:
            config = LQRConfig(
                gains=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                output_min=-1.0,
                output_max=1.0,
            )

        self.config = config
        self.last_output = 0.0

    def set_gains(self, gains):
        """
        Update LQR gain vector.

        Example:
            gains = [1.2, 0.8, 0.3, 0.3, 0.1, 0.1]
        """

        if len(gains) == 0:
            raise ValueError("LQR gains cannot be empty.")

        self.config.gains = [float(value) for value in gains]

    def set_output_limits(self, output_min, output_max):
        """
        Set minimum and maximum output limits.
        """

        output_min = float(output_min)
        output_max = float(output_max)

        if output_min >= output_max:
            raise ValueError("output_min must be less than output_max.")

        self.config.output_min = output_min
        self.config.output_max = output_max

    def compute(self, states):
        """
        Compute LQR-style output.

        Formula:
            output = -Kx

        states:
            List of current system states.

        Returns:
            Clamped output value.
        """

        if len(states) != len(self.config.gains):
            raise ValueError(
                f"State length and gain length must match. "
                f"Got {len(states)} states and {len(self.config.gains)} gains."
            )

        output = 0.0

        for gain, state in zip(self.config.gains, states):
            output += gain * float(state)

        # LQR control law uses negative feedback.
        output = -output

        output = self._clamp(
            output,
            self.config.output_min,
            self.config.output_max,
        )

        self.last_output = output

        return output

    def reset(self):
        """
        Reset controller memory.
        """

        self.last_output = 0.0

    def get_status(self):
        """
        Return useful debugging/dashboard information.
        """

        return {
            "gains": self.config.gains,
            "last_output": self.last_output,
            "output_min": self.config.output_min,
            "output_max": self.config.output_max,
            "note": "Demo LQR placeholder. Not verified for hardware control.",
        }

    def _clamp(self, value, minimum, maximum):
        """
        Clamp value between minimum and maximum.
        """

        return max(minimum, min(maximum, value))


if __name__ == "__main__":
    print("LQR software demo test")
    print("----------------------")

    lqr = LQRController(
        LQRConfig(
            gains=[0.8, 0.8, 0.2, 0.2, 0.1, 0.1],
            output_min=-1.0,
            output_max=1.0,
        )
    )

    fake_states_list = [
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [0.2, -0.1, 0.05, -0.02, 0.0, 0.0],
        [0.5, -0.3, 0.10, -0.05, 0.1, 0.0],
        [1.0, -0.8, 0.20, -0.10, 0.2, 0.1],
        [2.0, -1.5, 0.50, -0.30, 0.4, 0.2],
    ]

    for states in fake_states_list:
        output = lqr.compute(states)

        print(
            f"states={states} | "
            f"output={output:.4f}"
        )

    print("\nStatus:")
    print(lqr.get_status())