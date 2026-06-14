"""
logger.py

Simple CSV telemetry logger for ControlForge.

Saves packets to:
logs/controlforge_log_*.csv

This file does NOT control motors.
"""

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class FakePacket:
    """
    Fake packet used only for testing logger.py directly.
    """
    timestamp: float
    states: list
    raw: str


class TelemetryLogger:
    def __init__(self, log_directory="logs", filename=None):
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(parents=True, exist_ok=True)

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"controlforge_log_{timestamp}.csv"

        self.file_path = self.log_directory / filename

        self.file = None
        self.writer = None
        self.is_logging = False

    def start(self):
        """
        Start logging telemetry to a CSV file.
        """

        if self.is_logging:
            print("Logger is already running.")
            return

        self.file = open(self.file_path, "w", newline="", encoding="utf-8")
        self.writer = csv.writer(self.file)

        self.writer.writerow([
            "timestamp",
            "state1",
            "state2",
            "state3",
            "state4",
            "state5",
            "state6",
            "raw",
        ])

        self.file.flush()
        self.is_logging = True

        print("Logging started:", self.file_path)

    def log_packet(self, packet):
        """
        Log one telemetry packet.

        The packet must have:
        - packet.timestamp
        - packet.states
        - packet.raw
        """

        if not self.is_logging:
            return

        if self.writer is None or self.file is None:
            raise RuntimeError("Logger is active, but file is not open.")

        row = [
            packet.timestamp,
            *packet.states,
            packet.raw,
        ]

        self.writer.writerow(row)
        self.file.flush()

    def stop(self):
        """
        Stop logging and close the CSV file.
        """

        if not self.is_logging:
            print("Logger is not running.")
            return

        if self.file is not None:
            self.file.flush()
            self.file.close()

        self.file = None
        self.writer = None
        self.is_logging = False

        print("Logging stopped:", self.file_path)

    def get_log_path(self):
        """
        Return the path of the current log file.
        """

        return self.file_path


if __name__ == "__main__":
    logger = TelemetryLogger()
    logger.start()

    fake_packets = [
        FakePacket(1000, [1, 2, 3, 4, 5, 6], "1000,1,2,3,4,5,6"),
        FakePacket(1020, [2, 3, 4, 5, 6, 7], "1020,2,3,4,5,6,7"),
        FakePacket(1040, [3, 4, 5, 6, 7, 8], "1040,3,4,5,6,7,8"),
    ]

    for packet in fake_packets:
        logger.log_packet(packet)

    logger.stop()

    print("Created file:", logger.get_log_path())