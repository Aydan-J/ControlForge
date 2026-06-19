import serial.tools.list_ports

ports = serial.tools.list_ports.comports()

print("Available serial ports:")

if not ports:
    print("No ports found.")
else:
    for port in ports:
        print(f"{port.device} - {port.description}")