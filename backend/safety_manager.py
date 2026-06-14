"""
safety_manager.py

Safety Watchdog and Emergency Stop (ESTOP) Manager for ControlForge.
Monitors system states (position, velocity, angle velocities) and handles
automatic shutoffs when physical limits are exceeded, or when a manual
ESTOP is triggered.
"""

from enum import Enum
from typing import Optional, Tuple


class SafetyStatus(Enum):
    SAFE = "SAFE"
    ESTOP_LIMIT_EXCEEDED = "ESTOP_LIMIT_EXCEEDED"
    ESTOP_MANUAL = "ESTOP_MANUAL"


class SafetyManager:
    """
    Enforces mechanical and operational safety constraints on the cart double pendulum.
    """

    def __init__(
        self,
        cart_pos_min: float = -1.5,
        cart_pos_max: float = 1.5,
        cart_vel_max: float = 3.0,
        theta1_vel_max: float = 12.0,
        theta2_vel_max: float = 15.0,
    ):
        self.cart_pos_min = cart_pos_min
        self.cart_pos_max = cart_pos_max
        self.cart_vel_max = cart_vel_max
        self.theta1_vel_max = theta1_vel_max
        self.theta2_vel_max = theta2_vel_max

        self.status = SafetyStatus.SAFE
        self.trigger_cause: Optional[str] = None

    def check_safety(self, states: list[float]) -> Tuple[SafetyStatus, Optional[str]]:
        """
        Evaluate current telemetry states against safety boundaries.
        Expected double pendulum states:
        [theta1, theta2, theta1_dot, theta2_dot, cart_pos, cart_vel]
        
        Returns:
            Tuple of (SafetyStatus, optional descriptive cause string)
        """
        # If already in manual ESTOP, stay there until reset
        if self.status == SafetyStatus.ESTOP_MANUAL:
            return self.status, self.trigger_cause

        if len(states) < 6:
            self._trigger_estop(
                SafetyStatus.ESTOP_LIMIT_EXCEEDED,
                f"Invalid state count: expected 6, got {len(states)}",
            )
            return self.status, self.trigger_cause

        theta1_vel = states[2]
        theta2_vel = states[3]
        cart_pos = states[4]
        cart_vel = states[5]

        # 1. Cart position boundary check
        if cart_pos < self.cart_pos_min or cart_pos > self.cart_pos_max:
            self._trigger_estop(
                SafetyStatus.ESTOP_LIMIT_EXCEEDED,
                f"Cart position boundary exceeded: {cart_pos:.4f} m (Limits: {self.cart_pos_min} to {self.cart_pos_max})",
            )

        # 2. Cart velocity boundary check
        elif abs(cart_vel) > self.cart_vel_max:
            self._trigger_estop(
                SafetyStatus.ESTOP_LIMIT_EXCEEDED,
                f"Cart velocity limit exceeded: {cart_vel:.4f} m/s (Limit: {self.cart_vel_max})",
            )

        # 3. First pendulum joint velocity boundary check
        elif abs(theta1_vel) > self.theta1_vel_max:
            self._trigger_estop(
                SafetyStatus.ESTOP_LIMIT_EXCEEDED,
                f"Theta 1 velocity limit exceeded: {theta1_vel:.4f} rad/s (Limit: {self.theta1_vel_max})",
            )

        # 4. Second pendulum joint velocity boundary check
        elif abs(theta2_vel) > self.theta2_vel_max:
            self._trigger_estop(
                SafetyStatus.ESTOP_LIMIT_EXCEEDED,
                f"Theta 2 velocity limit exceeded: {theta2_vel:.4f} rad/s (Limit: {self.theta2_vel_max})",
            )

        return self.status, self.trigger_cause

    def trigger_manual_estop(self) -> None:
        """
        Manually trigger an Emergency Stop.
        """
        self._trigger_estop(SafetyStatus.ESTOP_MANUAL, "Manual emergency stop triggered by operator.")

    def reset_estop(self) -> None:
        """
        Reset the emergency stop state to SAFE.
        """
        self.status = SafetyStatus.SAFE
        self.trigger_cause = None
        print("[SafetyManager] Safety status reset to SAFE.")

    def _trigger_estop(self, status: SafetyStatus, cause: str) -> None:
        """
        Lock system in ESTOP and record cause.
        """
        self.status = status
        self.trigger_cause = cause
        print(f"[SafetyManager] ESTOP ACTIVE! Status={status.value} | Cause: {cause}")


if __name__ == "__main__":
    print("Running safety manager test...")
    manager = SafetyManager()
    
    # Safe test
    safe_state = [0.1, -0.1, 1.0, -2.0, 0.0, 0.5]
    status, cause = manager.check_safety(safe_state)
    print(f"Safe check: {status.value} (Cause: {cause})")

    # Exceed position limit
    unsafe_state = [0.1, -0.1, 1.0, -2.0, 2.0, 0.5]
    status, cause = manager.check_safety(unsafe_state)
    print(f"Unsafe check (position): {status.value} (Cause: {cause})")

    # Reset
    manager.reset_estop()

    # Manual estop
    manager.trigger_manual_estop()
    status, cause = manager.check_safety(safe_state)
    print(f"Manual check: {status.value} (Cause: {cause})")
