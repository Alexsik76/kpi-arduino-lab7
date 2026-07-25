import json
import os
import time

import cv2
import serial

# --- НАЛАШТУВАННЯ ---
UART_PORT = '/dev/serial0'
BAUD_RATE = 115200
MODEL_PATH = "app/tracking/face_detection_yunet_2023mar.onnx"
FRAME_W = 640
FRAME_H = 480
CENTER_X = FRAME_W // 2
CENTER_Y = FRAME_H // 2

# Обмеження кутів
PAN_MIN, PAN_MAX = 0, 180
TILT_MIN, TILT_MAX = 50, 130

# Поточні кути
pan_angle = 90
tilt_angle = 90

# --- 1. ІНІЦІАЛІЗАЦІЯ UART ---
print(f"[Init] Connecting to UART {UART_PORT}...")
try:
    ser = serial.Serial(UART_PORT, BAUD_RATE, timeout=0.1, write_timeout=0.1)
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    print("[Init] UART OK")
except Exception as e:
    print(f"[Error] UART Failed: {e}")
    exit()

def send_servo(pan, tilt):
    """Проста функція відправки"""
    cmd = {"pan": int(pan), "tilt": int(tilt)}
    try:
        msg = json.dumps(cmd) + "\n"
        ser.write(msg.encode('utf-8'))
    except Exception as e:
        print(f"[UART Error] {e}")

# --- 2. ІНІЦІАЛІЗАЦІЯ AI ---
print(f"[Init] Loading Model {MODEL_PATH}...")
if not os.path.exists(MODEL_PATH):
    print("[Error] Model not found!")
    exit()

detector = cv2.FaceDetectorYN.create(
    model=MODEL_PATH,
    config="",
    input_size=(320, 320), # YuNet вхід
    score_threshold=0.7,
    nms_threshold=0.3,
    top_k=1,
    backend_id=cv2.dnn.DNN_BACKEND_OPENCV,
    target_id=cv2.dnn.DNN_TARGET_CPU
)
print("[Init] AI OK")

# --- 3. ІНІЦІАЛІЗАЦІЯ КАМЕРИ ---
print("[Init] Opening Camera...")
# Використовуємо V4L2 явно, як надійніший бекенд для RPi
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)

if not cap.isOpened():
    print("[Error] Camera failed")
    exit()
print("[Init] Camera OK")

# --- ГОЛОВНИЙ ЦИКЛ ---
print(">>> STARTING TRACKING LOOP (Ctrl+C to stop) <<<")
try:
    # Пропускаємо перші кадри для стабілізації камери
    for _ in range(5):
        cap.read()
    
    # Таймер для обмеження частоти UART (щоб не заспамити)
    last_sent_time = 0
    
    while True:
        # 1. Читаємо кадр
        ret, frame = cap.read()
        if not ret:
            print("Frame error")
            continue

        # 2. Детекція
        detector.setInputSize((FRAME_W, FRAME_H))
        _, faces = detector.detect(frame)

        # 3. Логіка трекінгу
        if faces is not None:
            # Беремо перше обличчя
            face = faces[0]
            # face = [x, y, w, h, landmarks...]
            box = face[:4].astype(int)
            landmarks = face[4:14].astype(int)
            
            # Центр обличчя (по носу або центру бокса)
            # landmarks[4], landmarks[5] - це ніс
            nose_x, nose_y = landmarks[4], landmarks[5]
            
            # Рахуємо помилку
            error_x = nose_x - CENTER_X
            error_y = nose_y - CENTER_Y
            
            # Простий "Bang-Bang" або P-контролер
            # Якщо помилка > 20 пікселів, рухаємо на 1-2 градуси
            step = 1.5 
            
            moved = False
            
            if abs(error_x) > 20:
                # Інверсія для Pan: якщо обличчя зліва (x < center), треба крутити вліво
                # (або вправо, залежить від мотора)
                # Спробуй змінити знак, якщо крутить не туди
                if error_x > 0:
                    pan_angle -= step 
                else:
                    pan_angle += step
                moved = True
                
            if abs(error_y) > 20:
                if error_y > 0:
                    tilt_angle += step
                else:
                    tilt_angle -= step
                moved = True

            # Обмеження
            pan_angle = max(PAN_MIN, min(PAN_MAX, pan_angle))
            tilt_angle = max(TILT_MIN, min(TILT_MAX, tilt_angle))

            # 4. Відправка (не частіше 15 разів на сек)
            if moved and (time.time() - last_sent_time > 0.06):
                send_servo(pan_angle, tilt_angle)
                last_sent_time = time.time()
                print(
                    f"[Track] Face at ({nose_x},{nose_y}) -> "
                    f"Servo ({int(pan_angle)}, {int(tilt_angle)})"
                )
        
        # Невелика пауза, щоб розвантажити CPU
        time.sleep(0.01)

except KeyboardInterrupt:
    print("\nStopping...")
    send_servo(90, 90) # Повернути в центр (опціонально)
    time.sleep(0.5)
    
finally:
    cap.release()
    ser.close()
    print("Closed.")