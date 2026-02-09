import cv2

# import numpy as np
import logging
import os

logger = logging.getLogger(__name__)


class FaceDetector:
    def __init__(self, score_threshold=0.6):
        """
        Initializes the YuNet detector.
        """
        # 1. Optimization: Force 4 threads (RPi 5 CPU cores)
        cv2.setNumThreads(4)

        # 2. Determine model path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(current_dir, "face_detection_yunet_2023mar.onnx")

        if not os.path.exists(model_path):
            logger.error(f"Model not found at: {model_path}")
            raise FileNotFoundError(f"Missing model: {model_path}")

        # 3. Input size for NEURAL NETWORK (for speed)
        # YuNet trained on 320x320.
        # We will resize input frame to 320x240 (4:3) for speed.
        self.ai_width = 320
        self.ai_height = 240

        # Initialize YuNet
        self.detector = cv2.FaceDetectorYN.create(
            model=model_path,
            config="",
            input_size=(self.ai_width, self.ai_height),
            score_threshold=score_threshold,
            nms_threshold=0.3,
            top_k=5000,
            backend_id=cv2.dnn.DNN_BACKEND_OPENCV,
            target_id=cv2.dnn.DNN_TARGET_CPU,
        )
        logger.info(f"YuNet loaded. AI Resolution: {self.ai_width}x{self.ai_height}")

    def find_face(self, frame):
        """
        Detects a face in the frame.
        Returns coordinates scaled to original frame size.
        """
        # Get original frame dimensions (e.g., 640x480)
        orig_h, orig_w = frame.shape[:2]

        # 1. Downscale frame for speed (Resize)
        # LINEAR interpolation is fast enough for detection
        input_frame = cv2.resize(
            frame, (self.ai_width, self.ai_height), interpolation=cv2.INTER_LINEAR
        )

        # 2. Ensure detector knows input size
        self.detector.setInputSize((self.ai_width, self.ai_height))

        # 3. Detection
        _, faces = self.detector.detect(input_frame)

        if faces is None or len(faces) == 0:
            return None, None

        # 4. Find largest face
        best_face = None
        # best_landmarks = None
        max_area = 0

        for face in faces:
            # face = [x, y, w, h, x_re, y_re, x_le, y_le, x_nt, y_nt, x_rm, y_rm, x_lm, y_lm, confidence]
            box = face[:4]
            w, h = box[2], box[3]
            area = w * h

            if area > max_area:
                max_area = area
                best_face = face

        if best_face is not None:
            # 5. Scale coordinates back to original size
            # Calculate coefficients (e.g., 640/320 = 2.0)
            scale_x = orig_w / self.ai_width
            scale_y = orig_h / self.ai_height

            # Box coordinates (x, y, w, h)
            box = best_face[:4]
            x = int(box[0] * scale_x)
            y = int(box[1] * scale_y)
            w = int(box[2] * scale_x)
            h = int(box[3] * scale_y)

            # Landmark coordinates
            # best_face[4:14] is 10 numbers (x,y for 5 points)
            # Multiply X by scale_x, Y by scale_y
            landmarks = best_face[4:14].reshape(5, 2)
            landmarks[:, 0] *= scale_x
            landmarks[:, 1] *= scale_y
            landmarks = landmarks.astype(int).flatten()

            return (x, y, w, h), landmarks

        return None, None
