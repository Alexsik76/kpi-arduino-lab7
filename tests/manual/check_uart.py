import time

import serial

# Відкриваємо порт
try:
    ser = serial.Serial('/dev/serial0', 115200, timeout=1)
    print("Порт /dev/serial0 відкрито успішно!")
except Exception as e:
    print(f"Помилка відкриття порту: {e}")
    exit()

# Пробуємо щось відправити
print("Відправляю тестову команду...")
# Це залежить від твого протоколу на Pico. 
# Наприклад, якщо він чекає JSON, відправимо пустий JSON.
ser.write(b'{"test": 1}\n') 

time.sleep(1)
print("Слухаю відповідь...")
if ser.in_waiting > 0:
    response = ser.read(ser.in_waiting)
    print(f"Отримано відповідь від Pico: {response}")
else:
    print("Pico мовчить...")
