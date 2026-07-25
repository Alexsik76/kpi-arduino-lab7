import os

import cv2
import numpy as np

print("1. Checking OpenCV version...")
print(f"   Version: {cv2.__version__}")

# Шлях до моделі (перевір, щоб він був правильним відносно запуску)
model_path = "app/tracking/face_detection_yunet_2023mar.onnx" 

if not os.path.exists(model_path):
    print(f"❌ Model file not found at: {model_path}")
    exit()

print("2. Loading YuNet model...")
try:
    detector = cv2.FaceDetectorYN.create(
        model=model_path,
        config="",
        input_size=(320, 320),
        score_threshold=0.8,
        nms_threshold=0.3,
        top_k=5000,
        backend_id=cv2.dnn.DNN_BACKEND_OPENCV,
        target_id=cv2.dnn.DNN_TARGET_CPU
    )
    print("✅ Model loaded successfully.")
except Exception as e:
    print(f"❌ Crash loading model: {e}")
    exit()

print("3. Creating dummy image (black)...")
# Створюємо чорний квадрат 640x480
dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

print("4. Running detection on dummy image...")
detector.setInputSize((640, 480))
faces = detector.detect(dummy_frame)

print(f"✅ Detection finished. Result: {faces[1] if faces[1] is not None else 'None'}")