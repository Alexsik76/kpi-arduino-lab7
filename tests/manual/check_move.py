import json
import time

import serial

# Налаштування порту
ser = serial.Serial('/dev/serial0', 115200, timeout=1)

def send_command(data):
    # Формуємо JSON і обов'язково додаємо \n (Enter)
    msg = json.dumps(data) + '\n'
    ser.write(msg.encode('utf-8'))
    print(f"Відправлено: {msg.strip()}")

try:
    print("--- ТЕСТ МОТОРІВ І СЕРВО ---")
    
    # 1. Рухаємо головою (Серво)
    print("1. Голова в центр...")
    send_command({"pan": 90, "tilt": 90})
    time.sleep(1)
    
    print("2. Голова вліво-вправо...")
    send_command({"pan": 45})
    time.sleep(0.5)
    send_command({"pan": 135})
    time.sleep(0.5)
    send_command({"pan": 90})
    time.sleep(1)

    # 2. Рухаємо колесами (Мотори)
    # Значення від -100 (назад) до 100 (вперед)
    print("3. Двигуни: ВПЕРЕД (50%)")
    send_command({"l": 50, "r": 50}) 
    time.sleep(2) # Їдемо 2 секунди
    
    print("4. Двигуни: СТОП")
    send_command({"l": 0, "r": 0, "stop": True})
    
    print("--- ТЕСТ ЗАВЕРШЕНО ---")

except KeyboardInterrupt:
    send_command({"stop": True})
    print("\nЗупинка.")
finally:
    ser.close()
