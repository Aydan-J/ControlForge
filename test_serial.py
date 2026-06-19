import time
import serial

PORT = "COM3"
BAUD = 115200

print(f"Opening {PORT} at {BAUD} baud...")

ser = serial.Serial(PORT, BAUD, timeout=2)

# Teensy may reset when Python opens serial.
# Wait a bit so it starts printing again.
time.sleep(2)

print("Reading 20 lines...")

for i in range(20):
    line = ser.readline().decode(errors="ignore").strip()
    print(f"{i + 1}: {line}")

ser.close()
print("Done.")