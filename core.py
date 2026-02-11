import cv2
import numpy as np
import threading
import time
import logging
from app.utils.data_logger import DataLogger
from app.hardware.servo_pico import PicoController
from app.tracking.face_utils import FaceDetector
from app.control.servo_actor import PanTiltHead  # New import

logger = logging.getLogger("Core")

class TrackingSystem:
    def __init__(self, enable_logging=False):
        self.running = False
        self.manual_mode = False
        self.lock = threading.Lock()

        # Stream Data
        self.current_frame = None
        self.jpeg_bytes = None

        # Camera Config
        self.width = 640
        self.height = 480
        self.center_x = self.width // 2
        self.center_y = self.height // 2

        # Subsystems
        self._init_hardware()
        self._init_ai()
        
        # Control System (The Actor)
        self.head = PanTiltHead(self.pico)  # Inject Pico into Head

        # Logging
        self.logger = DataLogger() if enable_logging else None

        # Motor State
        self.target_l = 0
        self.target_r = 0

    def _init_hardware(self):
        self.pico = PicoController(port="/dev/serial0")
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def _init_ai(self):
        self.detector = FaceDetector(score_threshold=0.7)

    # --- PUBLIC API ---

    def set_manual_mode(self, enabled: bool):
        self.manual_mode = enabled
        logger.info(f"Manual mode set to {enabled}")

    def set_motor_speed(self, left: int, right: int):
        if self.manual_mode:
            # Mapping logic can be moved to a util later if needed
            def map_speed(val):
                if val == 0: return 0
                sign = 1 if val > 0 else -1
                abs_val = abs(val)
                min_s, max_s = 45, 85
                ratio = (abs_val - 1) / 99.0 if abs_val > 1 else 0.0
                pwm_out = min_s + (ratio * (max_s - min_s))
                return int(pwm_out * sign)

            self.target_l = map_speed(left)
            self.target_r = map_speed(right)

    def set_servo_angle(self, pan: int, tilt: int):
        if self.manual_mode:
            self.head.manual_move(pan, tilt)

    def start(self):
        if self.running: return
        self.running = True
        thread = threading.Thread(target=self._loop, daemon=True)
        thread.start()
        logger.info("System started")

    def stop(self):
        self.running = False
        if self.cap: self.cap.release()
        if self.pico: self.pico.close()
        if self.logger: self.logger.close()
        logger.info("System stopped")

    def get_jpg(self):
        with self.lock:
            return self.jpeg_bytes

    # --- INTERNAL LOGIC ---
    def _adjust_gamma(self, image, gamma=1.5):
        """
        gamma > 1.0 робить зображення світлішим (витягує тіні).
        gamma < 1.0 робить темнішим.
        """
        invGamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** invGamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
        
        return cv2.LUT(image, table)

    def _capture_frame(self):
        """Reads a frame from the camera."""
        ret, frame = self.cap.read()
        if not ret:
            time.sleep(0.1)
            return None
        frame = self._adjust_gamma(frame, gamma=1.8)
        return frame

    def _run_auto_tracking(self, frame):
        """Delegates tracking logic to the Head Actor."""
        # Default stats
        stats = {"err_x": 0, "err_y": 0, "d_pan": 0, "d_tilt": 0}

        face_box, landmarks = self.detector.find_face(frame)
        if face_box is None or landmarks is None:
            return stats

        # Visuals
        x, y, w, h = face_box
        nose_x, nose_y = landmarks[4], landmarks[5]
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.circle(frame, (nose_x, nose_y), 5, (0, 0, 255), -1)

        # Error Calculation
        error_x = nose_x - self.center_x
        error_y = nose_y - self.center_y

        # Dead zone logic
        if abs(error_x) < 25: error_x = 0
        if abs(error_y) < 25: error_y = 0

        stats["err_x"] = error_x
        stats["err_y"] = error_y

        if error_x == 0 and error_y == 0:
            return stats

        # DELEGATION: Ask the head to move
        move_stats = self.head.track_target(error_x, error_y)
        
        # Merge stats for logging
        stats.update(move_stats)
        
        return stats

    def _update_motors(self, last_sent_l, last_sent_r):
        """Sends motor commands ONLY if targets changed."""
        if (self.target_l != last_sent_l) or (self.target_r != last_sent_r):
            self.pico.send_motor_cmd(int(self.target_l), int(self.target_r))
            return self.target_l, self.target_r
        return last_sent_l, last_sent_r

    def _update_stream(self, frame):
        """Encodes frame to JPEG."""
        flag, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if flag:
            with self.lock:
                self.current_frame = frame
                self.jpeg_bytes = encoded.tobytes()

    # --- THE CONDUCTOR ---
    def _loop(self):
        last_sent_l = -999
        last_sent_r = -999

        while self.running:
            # 1. Capture
            frame = self._capture_frame()
            if frame is None: continue

            # 2. Logic (Auto Tracking)
            log_stats = None
            if not self.manual_mode:
                log_stats = self._run_auto_tracking(frame)

            # 3. Hardware (Motors)
            last_sent_l, last_sent_r = self._update_motors(last_sent_l, last_sent_r)

            # 4. Logging
            if self.logger and log_stats:
                self.logger.log(
                    log_stats.get("err_x", 0), log_stats.get("err_y", 0),
                    self.head.pan_angle, self.head.tilt_angle,
                    log_stats.get("d_pan", 0), log_stats.get("d_tilt", 0)
                )

            # 5. Stream
            self._update_stream(frame)

            # 6. Throttle
            time.sleep(0.001)