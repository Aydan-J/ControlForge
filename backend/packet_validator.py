"""
packet_validator.py

Validates ControlForge serial telemetry packets.

Expected format:
timestamp,state1,state2,state3,state4,state5,state6
"""

from dataclasses import dataclass


EXPECTED_STATE_COUNT = 6


@dataclass
class ValidationResult:
    is_valid: bool
    error_message: str | None = None


class PacketValidator:
    def __init__(self, expected_state_count: int = EXPECTED_STATE_COUNT):
        self.expected_state_count = expected_state_count

    def validate_raw_packet(self, raw_line: str) -> ValidationResult:
        if raw_line is None:
            return ValidationResult(False, "Packet is None.")

        raw_line = raw_line.strip()

        if raw_line == "":
            return ValidationResult(False, "Packet is empty.")

        parts = raw_line.split(",")

        expected_total_values = 1 + self.expected_state_count

        if len(parts) != expected_total_values:
            return ValidationResult(
                False,
                f"Expected {expected_total_values} values, got {len(parts)}.",
            )

        for value in parts:
            try:
                float(value)
            except ValueError:
                return ValidationResult(False, f"Non-numeric value found: {value}")

        return ValidationResult(True)

    def parse_raw_packet(self, raw_line: str) -> tuple[float, list[float]]:
        parts = raw_line.strip().split(",")

        timestamp = float(parts[0])
        states = [float(value) for value in parts[1:]]

        return timestamp, states


if __name__ == "__main__":
    validator = PacketValidator()

    test_packet = "123,1,2,3,4,5,6"
    result = validator.validate_raw_packet(test_packet)

    print(result)

    if result.is_valid:
        timestamp, states = validator.parse_raw_packet(test_packet)
        print("timestamp:", timestamp)
        print("states:", states)