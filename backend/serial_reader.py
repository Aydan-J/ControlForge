"""
serial_reader.py

Reads live telemetry from a Teensy over USB Serial.

Expected packet format:
    timestamp,state1,state2,state3,state4,state5,state6

Example:
    12345,1.23,4.56,0.12,0.34,0,0

This file ONLY reads and validates telemetry.
It does NOT send motor commands.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import serial
from serial import SerialException


# -----------------------------
# Safety / configuration limits
# -----------------------------

EXPECTED_STATE_COUNT = 6
DEFAULT_BAUD_RATE = 115200
DEFAULT_TIMEOUT = 1.0


@dataclass
class TelemetryPacket:
    """
    Clean structured telemetry packet.

    timestamp:
        Time value sent by Teensy.

    states:
        List of state values.
        For double pendulum, this may eventually mean:
        [theta1, theta2, theta1_dot, theta2_dot, cart_pos, cart_vel]

    raw:
        Original raw serial line.
    """

    timestamp: float
    states: list[float]
    raw: str


class SerialReader:
    """
    Handles USB serial communication from Teensy to Python.
    """

    def __init__(
        self,
        port: str,
        baud_rate: int = DEFAULT_BAUD_RATE,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.serial_connection: Optional[serial.Serial] = None

    def connect(self) -> None:
        """
        Connect to the Teensy over USB Serial.
        """

        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=self.timeout,
            )

            # Give the Teensy time to reset after serial connection opens.
            time.sleep(2)

            print(f"[SerialReader] Connected to {self.port} at {self.baud_rate} baud.")

        except SerialException as error:
            raise ConnectionError(
                f"Could not connect to serial port {self.port}. "
                f"Check that the Teensy is plugged in and the COM port is correct."
            ) from error

    def disconnect(self) -> None:
        """
        Safely close the serial connection.
        """

        if self.serial_connection is not None and self.serial_connection.is_open:
            self.serial_connection.close()
            print("[SerialReader] Serial connection closed.")

    def is_connected(self) -> bool:
        """
        Return True if the serial connection is currently open.
        """

        return (
            self.serial_connection is not None
            and self.serial_connection.is_open
        )

    def read_raw_line(self) -> Optional[str]:
        """
        Read one raw line from the Teensy.

        Returns:
            A decoded string if a line is received.
            None if no data is available.
        """

        if not self.is_connected():
            raise ConnectionError("Serial connection is not open.")

        assert self.serial_connection is not None

        try:
            raw_bytes = self.serial_connection.readline()

            if not raw_bytes:
                return None

            raw_line = raw_bytes.decode("utf-8", errors="replace").strip()

            if raw_line == "":
                return None

            return raw_line

        except SerialException as error:
            raise ConnectionError("Serial connection lost while reading data.") from error

    def parse_packet(self, raw_line: str) -> Optional[TelemetryPacket]:
        """
        Parse and validate one telemetry line.

        Expected format:
            timestamp,state1,state2,state3,state4,state5,state6

        Returns:
            TelemetryPacket if valid.
            None if invalid.
        """

        parts = raw_line.split(",")

        expected_total_values = 1 + EXPECTED_STATE_COUNT

        if len(parts) != expected_total_values:
            print(
                f"[SerialReader] Invalid packet length: expected "
                f"{expected_total_values} values, got {len(parts)} | raw: {raw_line}"
            )
            return None

        try:
            timestamp = float(parts[0])
            states = [float(value) for value in parts[1:]]

        except ValueError:
            print(f"[SerialReader] Invalid numeric data | raw: {raw_line}")
            return None

        return TelemetryPacket(
            timestamp=timestamp,
            states=states,
            raw=raw_line,
        )

    def read_packet(self) -> Optional[TelemetryPacket]:
        """
        Read and parse one telemetry packet.

        Returns:
            TelemetryPacket if a valid packet is received.
            None if no data or invalid data is received.
        """

        raw_line = self.read_raw_line()

        if raw_line is None:
            return None

        return self.parse_packet(raw_line)


# -----------------------------
# Manual test
# -----------------------------

if __name__ == "__main__":
    """
    Manual test command:

        python backend/serial_reader.py

    Before running:
        1. Plug in Teensy.
        2. Check the correct COM port in Device Manager.
        3. Change PORT below if needed.

    Common Windows examples:
        COM3
        COM4
        COM5
    """

    PORT = "COM3"

    reader = SerialReader(port=PORT)

    try:
        reader.connect()

        while True:
            packet = reader.read_packet()

            if packet is not None:
                print(packet)

    except KeyboardInterrupt:
        print("\n[SerialReader] Stopped by user.")

    finally:
        reader.disconnect()