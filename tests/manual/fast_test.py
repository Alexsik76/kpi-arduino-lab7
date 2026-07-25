import json
import time

import serial

# Відкриваємо порт
ser = serial.Serial('/dev/serial0', 115200, timeout=1)

def send(cmd):
    # Формуємо JSON + перехід рядка
    msg = json.dumps(cmd) + "\n"
    # Кодуємо в байти
    ser.write(msg.encode('utf-8'))
    # !!! ГОЛОВНЕ: Примусово виштовхнути з буфера
    # ser.flush() 
    print(f"Sent: {cmd}")

print("Start...")
# time.sleep(2) # Час на ініціалізацію Pico після рестарту

# Тест реакції
try:
    print("Pan Left")
    send({"pan": 45})
    time.sleep(0.5) # Пауза лише пів секунди! Перевіряємо швидкість
    
    print("Pan Right")
    send({"pan": 135})
    time.sleep(0.5)
    
    print("Motors Forward")
    send({"l": 50, "r": 50})
    time.sleep(1)
    
    print("Stop")
    send({"stop": True})

finally:
    ser.close()