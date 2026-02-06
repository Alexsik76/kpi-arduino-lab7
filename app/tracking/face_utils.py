import cv2
import numpy as np
import logging
import os

logger = logging.getLogger(__name__)

class FaceDetector:
    def __init__(self, score_threshold=0.8):
        # Resolve the absolute path to the model file relative to this script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(current_dir, 'face_detection_yunet_2023mar.onnx')

        if not os.path.exists(model_path):
            logger.error(f"Model not found at: {model_path}")
            raise FileNotFoundError(f"Missing model: {model_path}")

        # Initialize YuNet detector
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
        """
        Detects faces in the frame.
        Returns: (box, landmarks) for the largest face found.
        """
        h, w, _ = frame.shape
        self.detector.setInputSize((w, h))
        
        _, faces = self.detector.detect(frame)

        if faces is None:
            return None, None

        best_face = None
        best_landmarks = None
        max_area = 0

        # Find the largest face in the frame
        for face in faces:
            # YuNet returns: [x, y, w, h, landmarks...]
            box = face[:4].astype(int)
            landmarks = face[4:14].astype(int)
            
            x, y, w, h = box
            area = w * h
            
            if area > max_area:
                max_area = area
                best_face = (x, y, w, h)
                best_landmarks = landmarks

        return best_face, best_landmarks