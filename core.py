import cv2
import threading
import time
import logging
from app.hardware.servo_pico import PicoController
from app.tracking.face_utils import FaceDetector
from app.control.pid import PIDController

logger = logging.getLogger("Core")

class TrackingSystem:
    def __init__(self):
        self.running = False
        self.lock = threading.Lock()
        
        # Основні дані
        self.current_frame = None
        self.jpeg_bytes = None  # <--- НОВЕ: Зберігаємо готовий JPG тут
        
        # Конфігурація
        self.width = 640
        self.height = 480
        self.center_x = self.width // 2
        self.center_y = self.height // 2

        self._init_hardware()
        self._init_ai()
        self._init_control()

    def _init_hardware(self):
        self.pico = PicoController()
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        
        self.pan_angle = 90
        self.tilt_angle = 90
        self.pico.send_cmd(self.pan_angle, self.tilt_angle)

    def _init_ai(self):
        self.detector = FaceDetector(score_threshold=0.7)

    def _init_control(self):
        # PID: Плавний рух
        self.pid_pan = PIDController(kp=0.03, ki=0.0, kd=0.02, min_val=0, max_val=180)
        self.pid_tilt = PIDController(kp=0.03, ki=0.0, kd=0.02, min_val=45, max_val=135)
        self.invert_pan = True
        self.invert_tilt = False

    def start(self):
        if self.running: return
        self.running = True
        thread = threading.Thread(target=self._loop, daemon=True)
        thread.start()
        logger.info("System started")

    def stop(self):
        self.running = False
        self.cap.release()
        self.pico.close()
        logger.info("System stopped")

    def get_jpg(self):
        """Повертає готові байти JPG. Дуже швидко."""
        with self.lock:
            return self.jpeg_bytes

    def _loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            # 1. AI Analysis
            face_box, landmarks = self.detector.find_face(frame)

            if face_box is not None:
                x, y, w, h = face_box
                nose_x, nose_y = landmarks[4], landmarks[5]

                # Візуалізація
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.circle(frame, (nose_x, nose_y), 5, (0, 0, 255), -1)

                # 2. Control (PID)
                error_x = nose_x - self.center_x
                error_y = nose_y - self.center_y

                # Dead zone
                if abs(error_x) < 30: error_x = 0
                if abs(error_y) < 30: error_y = 0

                if error_x != 0 or error_y != 0:
                    delta_pan = self.pid_pan.compute(0, error_x)
                    delta_tilt = self.pid_tilt.compute(0, error_y)

                    if self.invert_pan: delta_pan *= -1
                    if self.invert_tilt: delta_tilt *= -1

                    self.pan_angle += delta_pan
                    self.tilt_angle += delta_tilt

                    # Hard Limits
                    self.pan_angle = max(0, min(180, self.pan_angle))
                    self.tilt_angle = max(50, min(130, self.tilt_angle))

                    self.pico.send_cmd(int(self.pan_angle), int(self.tilt_angle))

            # --- ОПТИМІЗАЦІЯ ---
            # Кодуємо один раз тут, а не в веб-сервері
            (flag, encoded) = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            
            with self.lock:
                self.current_frame = frame # На випадок якщо треба raw frame
                if flag:
                    self.jpeg_bytes = encoded.tobytes()
            
            time.sleep(0.03)