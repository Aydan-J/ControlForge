"""
serial_writer.py

Safely writes control outputs (motor commands) to the Teensy over USB Serial.
Integrates with the SafetyManager to ensure motor output is shut down if any
safety limit is violated or if a manual E-stop is triggered.
"""

from typing import Optional
import serial

try:
    from backend.safety_manager import SafetyStatus
except ImportError:
    # Allow local testing import
    from safety_manager import SafetyStatus


class SerialWriter:
    """
    Handles sending motor commands (control voltages/PWM) to the physical Teensy board.
    Ensures ESTOP compliance in software before any message is sent.
    """

    def __init__(
        self,
        port: Optional[str] = None,
        baud_rate: int = 115200,
        timeout: float = 1.0,
        serial_connection: Optional[serial.Serial] = None,
        max_voltage: float = 12.0,  # Limits output range for the 775 motor driver
    ):
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.serial_connection = serial_connection
        self.max_voltage = max_voltage
        self.own_connection = False

    def connect(self) -> None:
        """
        Open the serial connection if not already provided.
        """
        if self.serial_connection is not None:
            return

        if not self.port:
            raise ValueError("Cannot connect: Port or active serial connection must be provided.")

        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=self.timeout,
            )
            self.own_connection = True
            print(f"[SerialWriter] Opened serial connection on port {self.port}.")
        except serial.SerialException as error:
            raise ConnectionError(f"Could not open serial port {self.port} for writing: {error}")

    def disconnect(self) -> None:
        """
        Close the serial connection if owned by this instance.
        """
        if self.own_connection and self.serial_connection is not None and self.serial_connection.is_open:
            self.serial_connection.close()
            print("[SerialWriter] Closed serial connection.")
            self.serial_connection = None
            self.own_connection = False

    def send_control_command(self, value: float, safety_status: SafetyStatus) -> str:
        """
        Sends a command to the motor.
        
        Args:
            value: Desired control value (e.g. -1.0 to 1.0 or voltage).
            safety_status: Current safety status from SafetyManager.
            
        Returns:
            The raw string command that was sent (or simulated).
        """
        # Clamp command to limits
        clamped_value = max(-self.max_voltage, min(self.max_voltage, value))

        # Enforce ESTOP: If safety status is not SAFE, force command to 0.0
        if safety_status != SafetyStatus.SAFE:
            clamped_value = 0.0
            print(f"[SerialWriter] SAFETY LOCKOUT: ESTOP active ({safety_status.value}). Command forced to 0.0.")

        # Command protocol: "CMD,value\n"
        command_str = f"CMD,{clamped_value:.4f}\n"
        command_bytes = command_str.encode("utf-8")

        if self.serial_connection is not None and self.serial_connection.is_open:
            try:
                self.serial_connection.write(command_bytes)
                self.serial_connection.flush()
            except serial.SerialException as error:
                raise ConnectionError(f"Serial connection lost while sending command: {error}")
        else:
            # Simulation/debug print
            pass

        return command_str.strip()


if __name__ == "__main__":
    print("Testing SerialWriter in simulation mode...")
    
    # Create writer without a real serial connection
    writer = SerialWriter(max_voltage=1.0)
    
    # Test safe output
    cmd = writer.send_control_command(0.75, SafetyStatus.SAFE)
    print(f"Sent (SAFE, 0.75): '{cmd}'")
    
    # Test clamping
    cmd = writer.send_control_command(2.5, SafetyStatus.SAFE)
    print(f"Sent (SAFE, 2.5): '{cmd}' (should clamp to 1.0)")

    # Test ESTOP lockout
    cmd = writer.send_control_command(0.5, SafetyStatus.ESTOP_LIMIT_EXCEEDED)
    print(f"Sent (ESTOP, 0.5): '{cmd}' (should force to 0.0)")
