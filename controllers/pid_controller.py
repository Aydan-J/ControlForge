"""
pid_controller.py

Simple software-only PID controller for ControlForge.

This file does NOT directly control hardware.
It only calculates a control output.
"""

import time
from dataclasses import dataclass


@dataclass
class PIDConfig:
    kp: float = 0.0
    ki: float = 0.0
    kd: float = 0.0

    output_min: float = -1.0
    output_max: float = 1.0

    integral_min: float = -10.0
    integral_max: float = 10.0


class PIDController:
    def __init__(self, config=None):
        if config is None:
            config = PIDConfig()

        self.config = config
        self.setpoint = 0.0
        self.integral = 0.0
        self.previous_error = None
        self.previous_time = None
        self.last_output = 0.0

    def set_gains(self, kp, ki, kd):
        self.config.kp = float(kp)
        self.config.ki = float(ki)
        self.config.kd = float(kd)

    def set_target(self, setpoint):
        self.setpoint = float(setpoint)

    def reset(self):
        self.integral = 0.0
        self.previous_error = None
        self.previous_time = None
        self.last_output = 0.0

    def compute(self, measured_value, current_time=None):
        measured_value = float(measured_value)

        if current_time is None:
            current_time = time.time()

        error = self.setpoint - measured_value

        if self.previous_time is None:
            dt = 0.0
        else:
            dt = current_time - self.previous_time

        if dt < 0:
            dt = 0.0

        proportional = self.config.kp * error

        if dt > 0:
            self.integral += error * dt

        self.integral = self._clamp(
            self.integral,
            self.config.integral_min,
            self.config.integral_max,
        )

        integral_term = self.config.ki * self.integral

        if self.previous_error is None or dt <= 0:
            derivative = 0.0
        else:
            derivative = (error - self.previous_error) / dt

        derivative_term = self.config.kd * derivative

        output = proportional + integral_term + derivative_term

        output = self._clamp(
            output,
            self.config.output_min,
            self.config.output_max,
        )

        self.previous_error = error
        self.previous_time = current_time
        self.last_output = output

        return output

    def get_status(self):
        return {
            "kp": self.config.kp,
            "ki": self.config.ki,
            "kd": self.config.kd,
            "setpoint": self.setpoint,
            "integral": self.integral,
            "previous_error": self.previous_error,
            "last_output": self.last_output,
            "output_min": self.config.output_min,
            "output_max": self.config.output_max,
        }

    def _clamp(self, value, minimum, maximum):
        return max(minimum, min(maximum, value))


if __name__ == "__main__":
    print("PID software test")
    print("-----------------")

    pid = PIDController(
        PIDConfig(
            kp=0.5,
            ki=0.1,
            kd=0.05,
            output_min=-1.0,
            output_max=1.0,
        )
    )

    pid.set_target(10.0)

    fake_measurements = [0, 2, 4, 6, 8, 9, 9.5, 10, 10.2]

    start_time = time.time()

    for index, measurement in enumerate(fake_measurements):
        fake_time = start_time + index * 0.1
        output = pid.compute(measurement, current_time=fake_time)

        print(
            f"target={pid.setpoint:.2f} | "
            f"measured={measurement:.2f} | "
            f"output={output:.4f}"
        )

    print("\nStatus:")
    print(pid.get_status())