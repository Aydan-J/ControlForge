"""
data_manager.py

Simple telemetry storage for ControlForge.

Stores:
- latest telemetry packet
- rolling telemetry history
- stale/live data status

This file does NOT control motors.
"""

from dataclasses import dataclass
from collections import deque
import time


@dataclass
class TelemetrySnapshot:
    timestamp: float
    states: list
    received_time: float
    raw: str


@dataclass
class FakePacket:
    """
    Fake packet used only for testing data_manager.py directly.
    """
    timestamp: float
    states: list
    raw: str


class DataManager:
    def __init__(self, max_history_size=1000, stale_timeout_seconds=1.0):
        self.history = deque(maxlen=max_history_size)
        self.latest_snapshot = None
        self.stale_timeout_seconds = stale_timeout_seconds

    def update(self, packet):
        """
        Store one telemetry packet.

        The packet must have:
        - packet.timestamp
        - packet.states
        - packet.raw
        """

        snapshot = TelemetrySnapshot(
            timestamp=packet.timestamp,
            states=packet.states,
            received_time=time.time(),
            raw=packet.raw,
        )

        self.latest_snapshot = snapshot
        self.history.append(snapshot)

        return snapshot

    def get_latest(self):
        """
        Return the latest telemetry snapshot.
        """

        return self.latest_snapshot

    def get_history(self):
        """
        Return the full stored telemetry history.
        """

        return list(self.history)

    def get_recent_history(self, count):
        """
        Return the most recent count snapshots.
        """

        if count <= 0:
            return []

        return list(self.history)[-count:]

    def has_data(self):
        """
        Return True if at least one packet has been stored.
        """

        return self.latest_snapshot is not None

    def is_data_stale(self):
        """
        Return True if the latest packet is too old.
        """

        if self.latest_snapshot is None:
            return True

        age = time.time() - self.latest_snapshot.received_time
        return age > self.stale_timeout_seconds

    def clear(self):
        """
        Clear latest telemetry and history.
        """

        self.history.clear()
        self.latest_snapshot = None


if __name__ == "__main__":
    manager = DataManager(max_history_size=3)

    fake_packets = [
        FakePacket(1000, [1, 2, 3, 4, 5, 6], "1000,1,2,3,4,5,6"),
        FakePacket(1020, [2, 3, 4, 5, 6, 7], "1020,2,3,4,5,6,7"),
        FakePacket(1040, [3, 4, 5, 6, 7, 8], "1040,3,4,5,6,7,8"),
        FakePacket(1060, [4, 5, 6, 7, 8, 9], "1060,4,5,6,7,8,9"),
    ]

    for packet in fake_packets:
        manager.update(packet)

    print("Latest packet:")
    print(manager.get_latest())

    print("\nHistory:")
    for item in manager.get_history():
        print(item)

    print("\nRecent 2 packets:")
    for item in manager.get_recent_history(2):
        print(item)

    print("\nHas data:", manager.has_data())
    print("Is stale:", manager.is_data_stale())