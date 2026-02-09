import serial
import time

print("Init UART...")
# Спробуй тут вказати прямий шлях до пристрою, а не аліас serial0
# На RPi 5 GPIO 14/15 - це зазвичай /dev/ttyAMA0
try:
    ser = serial.Serial('/dev/ttyAMA0', 115200, timeout=1)
    print("UART Opened. Sending data...")
    ser.write(b'test\n')
    ser.close()
    print("Done.")
except Exception as e:
    print(f"UART Error: {e}")