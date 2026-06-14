"""
controller_manager.py

Controller manager for ControlForge.

Purpose:
- Store available controllers
- Select active controller
- Update PID gains
- Update LQR gains
- Compute software-only controller output

This file does NOT directly control hardware.
It only manages controller calculations.
"""

from dataclasses import dataclass

try:
    from controllers.pid_controller import PIDController, PIDConfig
    from controllers.lqr_controller import LQRController, LQRConfig
except ModuleNotFoundError:
    # Allows direct running from inside the controllers folder if needed.
    from pid_controller import PIDController, PIDConfig
    from lqr_controller import LQRController, LQRConfig


@dataclass
class ControllerOutput:
    controller_name: str
    output: float
    measured_value: float | None
    states: list | None
    setpoint: float | None


class ControllerManager:
    def __init__(self):
        self.controllers = {
            "PID": PIDController(
                PIDConfig(
                    kp=0.0,
                    ki=0.0,
                    kd=0.0,
                    output_min=-1.0,
                    output_max=1.0,
                )
            ),
            "LQR": LQRController(
                LQRConfig(
                    gains=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                    output_min=-1.0,
                    output_max=1.0,
                )
            ),
        }

        # Safe default: PID selected, but controller disabled.
        self.active_controller_name = "PID"
        self.enabled = False

    def enable(self):
        """
        Enable controller calculations.
        """
        self.enabled = True

    def disable(self):
        """
        Disable controller calculations and reset active controller.
        """
        self.enabled = False
        self.get_active_controller().reset()

    def is_enabled(self):
        """
        Return True if controller calculations are enabled.
        """
        return self.enabled

    def get_available_controllers(self):
        """
        Return available controller names.
        """
        return list(self.controllers.keys())

    def set_active_controller(self, controller_name):
        """
        Select which controller is active.
        """
        if controller_name not in self.controllers:
            raise ValueError(f"Unknown controller: {controller_name}")

        self.active_controller_name = controller_name
        self.controllers[controller_name].reset()

    def get_active_controller(self):
        """
        Return active controller object.
        """
        return self.controllers[self.active_controller_name]

    def get_active_controller_name(self):
        """
        Return active controller name.
        """
        return self.active_controller_name

    def set_target(self, setpoint):
        """
        Set target for PID.

        LQR does not use a simple setpoint in this placeholder version.
        """
        if self.active_controller_name != "PID":
            print("Warning: set_target only applies to PID in this version.")
            return

        pid = self.controllers["PID"]
        pid.set_target(setpoint)

    def update_pid_gains(self, kp, ki, kd):
        """
        Update PID gains.
        """
        pid = self.controllers["PID"]
        pid.set_gains(kp, ki, kd)

    def update_lqr_gains(self, gains):
        """
        Update LQR gain vector.

        Example:
            gains = [0.8, 0.8, 0.2, 0.2, 0.1, 0.1]
        """
        lqr = self.controllers["LQR"]
        lqr.set_gains(gains)

    def set_output_limits(self, output_min, output_max):
        """
        Set output limits for the active controller.
        """
        controller = self.get_active_controller()
        controller.set_output_limits(output_min, output_max)

    def compute_pid(self, measured_value, current_time=None):
        """
        Compute PID output using one measured value.
        """
        pid = self.controllers["PID"]

        if not self.enabled:
            return ControllerOutput(
                controller_name="PID",
                output=0.0,
                measured_value=float(measured_value),
                states=None,
                setpoint=pid.setpoint,
            )

        output = pid.compute(
            measured_value=measured_value,
            current_time=current_time,
        )

        return ControllerOutput(
            controller_name="PID",
            output=output,
            measured_value=float(measured_value),
            states=None,
            setpoint=pid.setpoint,
        )

    def compute_lqr(self, states):
        """
        Compute LQR output using a full state vector.
        """
        lqr = self.controllers["LQR"]

        if not self.enabled:
            return ControllerOutput(
                controller_name="LQR",
                output=0.0,
                measured_value=None,
                states=states,
                setpoint=None,
            )

        output = lqr.compute(states)

        return ControllerOutput(
            controller_name="LQR",
            output=output,
            measured_value=None,
            states=states,
            setpoint=None,
        )

    def compute(self, measured_value=None, states=None, current_time=None):
        """
        Compute output from the active controller.

        PID requires:
            measured_value

        LQR requires:
            states
        """

        if self.active_controller_name == "PID":
            if measured_value is None:
                raise ValueError("PID requires measured_value.")

            return self.compute_pid(
                measured_value=measured_value,
                current_time=current_time,
            )

        if self.active_controller_name == "LQR":
            if states is None:
                raise ValueError("LQR requires states.")

            return self.compute_lqr(states=states)

        raise ValueError(f"Unsupported controller: {self.active_controller_name}")

    def reset_active_controller(self):
        """
        Reset memory of active controller.
        """
        self.get_active_controller().reset()

    def get_status(self):
        """
        Return manager status for debugging/dashboard.
        """
        active_controller = self.get_active_controller()

        return {
            "enabled": self.enabled,
            "active_controller": self.active_controller_name,
            "available_controllers": self.get_available_controllers(),
            "controller_status": active_controller.get_status(),
        }


if __name__ == "__main__":
    print("Controller manager software test")
    print("--------------------------------")

    manager = ControllerManager()

    print("Available controllers:", manager.get_available_controllers())
    print("Active controller:", manager.get_active_controller_name())

    # -----------------------------
    # PID test
    # -----------------------------

    print("\nPID disabled test:")

    manager.set_active_controller("PID")
    manager.update_pid_gains(kp=0.5, ki=0.1, kd=0.05)
    manager.set_target(10.0)

    output = manager.compute(measured_value=0)
    print(output)

    print("\nPID enabled test:")

    manager.enable()

    fake_measurements = [0, 2, 4, 6, 8, 9, 9.5, 10, 10.2]

    for index, measurement in enumerate(fake_measurements):
        fake_time = index * 0.1

        output = manager.compute(
            measured_value=measurement,
            current_time=fake_time,
        )

        print(
            f"controller={output.controller_name} | "
            f"target={output.setpoint:.2f} | "
            f"measured={output.measured_value:.2f} | "
            f"output={output.output:.4f}"
        )

    print("\nPID status:")
    print(manager.get_status())

    # -----------------------------
    # LQR test
    # -----------------------------

    print("\nSwitching to LQR demo test:")

    manager.disable()
    manager.set_active_controller("LQR")
    manager.update_lqr_gains([0.8, 0.8, 0.2, 0.2, 0.1, 0.1])
    manager.enable()

    fake_states_list = [
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [0.2, -0.1, 0.05, -0.02, 0.0, 0.0],
        [0.5, -0.3, 0.10, -0.05, 0.1, 0.0],
        [1.0, -0.8, 0.20, -0.10, 0.2, 0.1],
        [2.0, -1.5, 0.50, -0.30, 0.4, 0.2],
    ]

    for states in fake_states_list:
        output = manager.compute(states=states)

        print(
            f"controller={output.controller_name} | "
            f"states={output.states} | "
            f"output={output.output:.4f}"
        )

    print("\nLQR status:")
    print(manager.get_status())