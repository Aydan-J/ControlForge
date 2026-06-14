"""
system_models.py

Generic system model definitions for ControlForge.

Purpose:
- Define supported system types
- Define state names and units
- Help dashboard map generic state1, state2, ... into readable labels

Example serial packet:
    timestamp,state1,state2,state3,state4,state5,state6

For the double pendulum demo:
    state1 = theta1
    state2 = theta2
    state3 = theta1_dot
    state4 = theta2_dot
    state5 = cart_pos
    state6 = cart_vel
"""

from dataclasses import dataclass


@dataclass
class StateInfo:
    index: int
    name: str
    label: str
    unit: str
    description: str


@dataclass
class SystemModel:
    name: str
    display_name: str
    description: str
    states: list


class SystemModelRegistry:
    def __init__(self):
        self.models = {}

        self._register_default_models()

    def _register_default_models(self):
        """
        Register built-in ControlForge system models.
        """

        self.register_model(
            SystemModel(
                name="double_pendulum_cart",
                display_name="Cart Double Pendulum",
                description=(
                    "A cart-driven double pendulum system. "
                    "The cart is actuated by a motor, and the pendulum angles "
                    "are measured by encoders."
                ),
                states=[
                    StateInfo(
                        index=0,
                        name="theta1",
                        label="Theta 1",
                        unit="rad",
                        description="First pendulum joint angle.",
                    ),
                    StateInfo(
                        index=1,
                        name="theta2",
                        label="Theta 2",
                        unit="rad",
                        description="Second pendulum joint angle.",
                    ),
                    StateInfo(
                        index=2,
                        name="theta1_dot",
                        label="Theta 1 velocity",
                        unit="rad/s",
                        description="Angular velocity of first pendulum joint.",
                    ),
                    StateInfo(
                        index=3,
                        name="theta2_dot",
                        label="Theta 2 velocity",
                        unit="rad/s",
                        description="Angular velocity of second pendulum joint.",
                    ),
                    StateInfo(
                        index=4,
                        name="cart_pos",
                        label="Cart position",
                        unit="m",
                        description="Horizontal position of the cart.",
                    ),
                    StateInfo(
                        index=5,
                        name="cart_vel",
                        label="Cart velocity",
                        unit="m/s",
                        description="Horizontal velocity of the cart.",
                    ),
                ],
            )
        )

        self.register_model(
            SystemModel(
                name="generic_6_state",
                display_name="Generic 6-State System",
                description=(
                    "A generic system using six unnamed state values. "
                    "Useful when hardware-specific labels are not defined yet."
                ),
                states=[
                    StateInfo(0, "state1", "State 1", "", "Generic state value 1."),
                    StateInfo(1, "state2", "State 2", "", "Generic state value 2."),
                    StateInfo(2, "state3", "State 3", "", "Generic state value 3."),
                    StateInfo(3, "state4", "State 4", "", "Generic state value 4."),
                    StateInfo(4, "state5", "State 5", "", "Generic state value 5."),
                    StateInfo(5, "state6", "State 6", "", "Generic state value 6."),
                ],
            )
        )

    def register_model(self, model):
        """
        Add a system model to the registry.
        """

        self.models[model.name] = model

    def get_model(self, name):
        """
        Get one system model by name.
        """

        if name not in self.models:
            raise ValueError(f"Unknown system model: {name}")

        return self.models[name]

    def get_model_names(self):
        """
        Return internal model names.
        """

        return list(self.models.keys())

    def get_display_names(self):
        """
        Return human-readable model names.
        """

        return [model.display_name for model in self.models.values()]

    def get_state_info(self, model_name, state_index):
        """
        Get label/unit information for one state.
        """

        model = self.get_model(model_name)

        for state in model.states:
            if state.index == state_index:
                return state

        raise ValueError(
            f"State index {state_index} not found in model {model_name}."
        )

    def map_states_to_labels(self, model_name, states):
        """
        Convert a raw state list into labeled values.

        Example:
            [0.1, 0.2, 0, 0, 0, 0]

        Becomes:
            {
                "theta1": {
                    "label": "Theta 1",
                    "value": 0.1,
                    "unit": "rad"
                },
                ...
            }
        """

        model = self.get_model(model_name)

        mapped = {}

        for state_info in model.states:
            if state_info.index < len(states):
                value = states[state_info.index]
            else:
                value = None

            mapped[state_info.name] = {
                "label": state_info.label,
                "value": value,
                "unit": state_info.unit,
                "description": state_info.description,
            }

        return mapped


if __name__ == "__main__":
    print("System model registry test")
    print("--------------------------")

    registry = SystemModelRegistry()

    print("Available models:")
    for model_name in registry.get_model_names():
        model = registry.get_model(model_name)
        print(f"- {model.name}: {model.display_name}")

    print("\nDouble pendulum state labels:")

    model = registry.get_model("double_pendulum_cart")

    for state in model.states:
        print(
            f"state{state.index + 1} -> "
            f"{state.name} | "
            f"{state.label} | "
            f"unit={state.unit}"
        )

    print("\nMapped fake telemetry:")

    fake_states = [0.25, -0.5, 0.1, -0.2, 0.0, 0.0]

    mapped = registry.map_states_to_labels(
        model_name="double_pendulum_cart",
        states=fake_states,
    )

    for name, info in mapped.items():
        print(
            f"{name}: {info['value']} {info['unit']} "
            f"({info['label']})"
        )