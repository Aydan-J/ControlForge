"""
digital_twin.py

Digital twin comparison module for ControlForge.

Purpose:
- Run a simulated system beside real hardware data
- Compare hardware states vs simulation states
- Calculate prediction/error values
- Help dashboard show real vs simulated behavior

This file does NOT control motors.
"""

from dataclasses import dataclass

try:
    from simulation.double_pendulum import DoublePendulumSimulator
except ModuleNotFoundError:
    # Allows direct running from inside the simulation folder if needed.
    from double_pendulum import DoublePendulumSimulator


@dataclass
class TwinComparison:
    hardware_states: list
    simulated_states: list
    errors: list
    mean_absolute_error: float
    max_absolute_error: float


class DigitalTwin:
    def __init__(self):
        self.simulator = DoublePendulumSimulator()
        self.latest_comparison = None

    def reset(self):
        """
        Reset the digital twin simulation and stored comparison.
        """

        self.simulator.reset()
        self.latest_comparison = None

    def step_simulation(self, dt=0.02, control_output=0.0):
        """
        Advance the simulated system by one step.
        """

        state = self.simulator.step(
            dt=dt,
            control_output=control_output,
        )

        return state.to_list()

    def compare(self, hardware_states, simulated_states=None):
        """
        Compare hardware states against simulated states.

        hardware_states:
            Real or fake hardware state list.

        simulated_states:
            Optional simulated state list.
            If not given, the current simulator state is used.

        Returns:
            TwinComparison
        """

        hardware_states = [float(value) for value in hardware_states]

        if simulated_states is None:
            simulated_states = self.simulator.get_state_list()

        simulated_states = [float(value) for value in simulated_states]

        if len(hardware_states) != len(simulated_states):
            raise ValueError(
                f"Hardware and simulation state lengths must match. "
                f"Got {len(hardware_states)} hardware states and "
                f"{len(simulated_states)} simulated states."
            )

        errors = []

        for hardware_value, simulated_value in zip(hardware_states, simulated_states):
            error = hardware_value - simulated_value
            errors.append(error)

        absolute_errors = [abs(error) for error in errors]

        if len(absolute_errors) == 0:
            mean_absolute_error = 0.0
            max_absolute_error = 0.0
        else:
            mean_absolute_error = sum(absolute_errors) / len(absolute_errors)
            max_absolute_error = max(absolute_errors)

        comparison = TwinComparison(
            hardware_states=hardware_states,
            simulated_states=simulated_states,
            errors=errors,
            mean_absolute_error=mean_absolute_error,
            max_absolute_error=max_absolute_error,
        )

        self.latest_comparison = comparison

        return comparison

    def update(self, hardware_states, dt=0.02, control_output=0.0):
        """
        Step the simulation, then compare it to hardware states.

        This is the main method the dashboard/backend can use later.
        """

        simulated_states = self.step_simulation(
            dt=dt,
            control_output=control_output,
        )

        comparison = self.compare(
            hardware_states=hardware_states,
            simulated_states=simulated_states,
        )

        return comparison

    def get_latest_comparison(self):
        """
        Return the most recent comparison result.
        """

        return self.latest_comparison

    def get_status(self):
        """
        Return dashboard-friendly status.
        """

        return {
            "has_comparison": self.latest_comparison is not None,
            "simulated_states": self.simulator.get_state_list(),
            "latest_comparison": self.latest_comparison,
        }


if __name__ == "__main__":
    print("Digital twin test")
    print("-----------------")

    twin = DigitalTwin()

    fake_hardware_states_list = [
        [0.20, -0.30, 0.00, 0.00, 0.00, 0.00],
        [0.21, -0.29, 0.02, 0.01, 0.01, 0.00],
        [0.23, -0.27, 0.04, 0.03, 0.02, 0.01],
        [0.25, -0.25, 0.06, 0.05, 0.03, 0.02],
        [0.28, -0.22, 0.08, 0.08, 0.04, 0.03],
    ]

    for index, hardware_states in enumerate(fake_hardware_states_list):
        control_output = 0.2

        comparison = twin.update(
            hardware_states=hardware_states,
            dt=0.02,
            control_output=control_output,
        )

        print(f"\nStep {index + 1}")
        print("Hardware states:", comparison.hardware_states)
        print("Simulated states:", [round(value, 4) for value in comparison.simulated_states])
        print("Errors:", [round(value, 4) for value in comparison.errors])
        print("Mean absolute error:", round(comparison.mean_absolute_error, 4))
        print("Max absolute error:", round(comparison.max_absolute_error, 4))

    print("\nStatus:")
    print(twin.get_status())