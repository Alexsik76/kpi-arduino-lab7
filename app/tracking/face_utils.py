import cv2
import numpy as np
import logging
import os

logger = logging.getLogger(__name__)

class FaceDetector:
    # Прибираємо model_path з аргументів, бо ми тепер знаємо, де він точно лежить
    def __init__(self, score_threshold=0.8):
        
        # 1. Визначаємо шлях до поточної папки (app/tracking/)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 2. Будуємо повний шлях до моделі
        model_path = os.path.join(current_dir, 'face_detection_yunet_2023mar.onnx')

        if not os.path.exists(model_path):
            logger.error(f"Model not found at: {model_path}")
            raise FileNotFoundError(f"Missing model: {model_path}")

        self.detector = cv2.FaceDetectorYN.create(
            model=model_path,
            config="",
            input_size=(320, 320),
            score_threshold=score_threshold,
            nms_threshold=0.3,
            top_k=5000,
            backend_id=cv2.dnn.DNN_BACKEND_OPENCV,
            target_id=cv2.dnn.DNN_TARGET_CPU
        )
        logger.info(f"YuNet loaded from {model_path}")

    def find_face(self, frame):
        h, w, _ = frame.shape
        self.detector.setInputSize((w, h))
        _, faces = self.detector.detect(frame)

        if faces is None:
            return None, None

        best_face = None
        best_landmarks = None
        max_area = 0

        for face in faces:
            box = face[:4].astype(int)
            landmarks = face[4:14].astype(int)
            x, y, w, h = box
            area = w * h
            if area > max_area:
                max_area = area
                best_face = (x, y, w, h)
                best_landmarks = landmarks

        return best_face, best_landmarks