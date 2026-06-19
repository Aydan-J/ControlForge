"""
packet_validator.py

Validates and parses ControlForge serial telemetry packets.

Supported formats:

1. Clean CSV packet, preferred:
timestamp,theta1,theta2,theta1_dot,theta2_dot,cart_pos,cart_vel

Example:
12345,0.1200,-0.2500,0.0100,-0.0200,-1856.0000,0.0000

2. Human-readable Arduino packet, optional fallback:
Upper: 348.09 deg | Lower: 255.72 deg | CartTicks: -1856 | MotorPWM: 0 | Safety: FAULT

The parser always returns:
timestamp, [theta1, theta2, theta1_dot, theta2_dot, cart_pos, cart_vel]
"""

from dataclasses import dataclass
import math
import re
import time


EXPECTED_STATE_COUNT = 6


@dataclass
class ValidationResult:
    is_valid: bool
    error_message: str | None = None


class PacketValidator:
    def __init__(self, expected_state_count: int = EXPECTED_STATE_COUNT):
        self.expected_state_count = expected_state_count

        # Used only when parsing human-readable packets,
        # because those packets do not include angular velocity directly.
        self._previous_timestamp: float | None = None
        self._previous_theta1: float | None = None
        self._previous_theta2: float | None = None
        self._previous_cart_pos: float | None = None

    # ============================================================
    # Public validation function
    # ============================================================

    def validate_raw_packet(self, raw_line: str) -> ValidationResult:
        if raw_line is None:
            return ValidationResult(False, "Packet is None.")

        raw_line = raw_line.strip()

        if raw_line == "":
            return ValidationResult(False, "Packet is empty.")

        # Try CSV first
        if self._looks_like_csv_packet(raw_line):
            return self._validate_csv_packet(raw_line)

        # Then try human-readable Arduino format
        if self._parse_human_readable_packet(raw_line) is not None:
            return ValidationResult(True)

        return ValidationResult(
            False,
            f"Unrecognized packet format: {raw_line}",
        )

    # ============================================================
    # Public parse function
    # ============================================================

    def parse_raw_packet(self, raw_line: str) -> tuple[float, list[float]]:
        """
        Returns:
        timestamp, states

        states order:
        [
            theta1,
            theta2,
            theta1_dot,
            theta2_dot,
            cart_pos,
            cart_vel,
        ]
        """

        raw_line = raw_line.strip()

        if self._looks_like_csv_packet(raw_line):
            return self._parse_csv_packet(raw_line)

        parsed = self._parse_human_readable_packet(raw_line)

        if parsed is not None:
            return parsed

        raise ValueError(f"Cannot parse packet: {raw_line}")

    # ============================================================
    # CSV packet handling
    # ============================================================

    def _looks_like_csv_packet(self, raw_line: str) -> bool:
        return "," in raw_line

    def _validate_csv_packet(self, raw_line: str) -> ValidationResult:
        parts = raw_line.split(",")

        expected_total_values = 1 + self.expected_state_count

        if len(parts) != expected_total_values:
            return ValidationResult(
                False,
                f"Expected {expected_total_values} values, got {len(parts)}.",
            )

        for value in parts:
            try:
                float(value.strip())
            except ValueError:
                return ValidationResult(False, f"Non-numeric value found: {value}")

        return ValidationResult(True)

    def _parse_csv_packet(self, raw_line: str) -> tuple[float, list[float]]:
        parts = raw_line.strip().split(",")

        timestamp = float(parts[0].strip())
        states = [float(value.strip()) for value in parts[1:]]

        if len(states) != self.expected_state_count:
            raise ValueError(
                f"Expected {self.expected_state_count} states, got {len(states)}."
            )

        return timestamp, states

    # ============================================================
    # Human-readable Arduino packet handling
    # ============================================================

    def _parse_human_readable_packet(
        self,
        raw_line: str,
    ) -> tuple[float, list[float]] | None:
        """
        Parses Arduino output like:

        Upper: 348.09 deg | Lower: 255.72 deg | CartTicks: -1856 | MotorPWM: 0 | Safety: FAULT

        Converts:
        Upper deg -> theta1 radians
        Lower deg -> theta2 radians
        CartTicks -> cart_pos

        Calculates:
        theta1_dot
        theta2_dot
        cart_vel
        """

        pattern = (
            r"Upper:\s*([-+]?\d*\.?\d+)\s*deg\s*\|\s*"
            r"Lower:\s*([-+]?\d*\.?\d+)\s*deg\s*\|\s*"
            r"CartTicks:\s*([-+]?\d+)\s*\|\s*"
            r"MotorPWM:\s*([-+]?\d+)\s*\|\s*"
            r"Safety:\s*(\w+)"
        )

        match = re.search(pattern, raw_line)

        if not match:
            return None

        upper_deg = float(match.group(1))
        lower_deg = float(match.group(2))
        cart_ticks = float(match.group(3))

        timestamp = time.time() * 1000.0

        theta1 = math.radians(upper_deg)
        theta2 = math.radians(lower_deg)
        cart_pos = cart_ticks

        theta1_dot = 0.0
        theta2_dot = 0.0
        cart_vel = 0.0

        if (
            self._previous_timestamp is not None
            and self._previous_theta1 is not None
            and self._previous_theta2 is not None
            and self._previous_cart_pos is not None
        ):
            dt = (timestamp - self._previous_timestamp) / 1000.0

            if dt > 0:
                theta1_dot = self._angle_difference(theta1, self._previous_theta1) / dt
                theta2_dot = self._angle_difference(theta2, self._previous_theta2) / dt
                cart_vel = (cart_pos - self._previous_cart_pos) / dt

        self._previous_timestamp = timestamp
        self._previous_theta1 = theta1
        self._previous_theta2 = theta2
        self._previous_cart_pos = cart_pos

        states = [
            theta1,
            theta2,
            theta1_dot,
            theta2_dot,
            cart_pos,
            cart_vel,
        ]

        return timestamp, states

    # ============================================================
    # Angle helper
    # ============================================================

    def _angle_difference(self, current_angle: float, previous_angle: float) -> float:
        """
        Returns wrapped angle difference in radians.
        Prevents huge velocity spikes when crossing 0/360 degrees.
        """

        difference = current_angle - previous_angle

        while difference > math.pi:
            difference -= 2 * math.pi

        while difference < -math.pi:
            difference += 2 * math.pi

        return difference


if __name__ == "__main__":
    validator = PacketValidator()

    test_packets = [
        "123,1,2,3,4,5,6",
        "Upper: 348.09 deg | Lower: 255.72 deg | CartTicks: -1856 | MotorPWM: 0 | Safety: FAULT",
    ]

    for test_packet in test_packets:
        print("\nTesting:", test_packet)

        result = validator.validate_raw_packet(test_packet)
        print(result)

        if result.is_valid:
            timestamp, states = validator.parse_raw_packet(test_packet)
            print("timestamp:", timestamp)
            print("states:", states)