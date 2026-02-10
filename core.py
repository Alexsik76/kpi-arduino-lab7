import cv2
import threading
import time
import logging
from app.utils.data_logger import DataLogger
from app.hardware.servo_pico import PicoController
from app.tracking.face_utils import FaceDetector
from app.control.pid import PIDController

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
        self._init_control()

        # Logging
        self.logger = DataLogger() if enable_logging else None

        # State / Safety
        self.last_command_time = 0
        self.command_interval = 0.03  # Max servo rate
        self.last_sent_pan = -1
        self.last_sent_tilt = -1

        # Motor State
        self.target_l = 0
        self.target_r = 0
        # No ramping logic here anymore, physics is on Pico

    def _init_hardware(self):
        self.pico = PicoController(port="/dev/serial0")
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.pan_angle = 90
        self.tilt_angle = 90

    def _init_ai(self):
        self.detector = FaceDetector(score_threshold=0.7)

    def _init_control(self):
        self.pid_pan = PIDController(kp=0.035, ki=0.0, kd=0.02, min_val=0, max_val=180)
        self.pid_tilt = PIDController(kp=0.035, ki=0.0, kd=0.02, min_val=45, max_val=135)
        self.invert_pan = True
        self.invert_tilt = False

    # --- PUBLIC API ---

    def set_manual_mode(self, enabled: bool):
        self.manual_mode = enabled
        logger.info(f"Manual mode set to {enabled}")

    def set_motor_speed(self, left: int, right: int):
        if self.manual_mode:
            # Simple mapping logic, simply creating target values
            def map_speed(val):
                if val == 0: return 0
                sign = 1 if val > 0 else -1
                abs_val = abs(val)
                # Input range 1..100 maps to 45..85 (min_moving to max)
                min_s, max_s = 45, 85
                ratio = (abs_val - 1) / 99.0 if abs_val > 1 else 0.0
                pwm_out = min_s + (ratio * (max_s - min_s))
                return int(pwm_out * sign)

            self.target_l = map_speed(left)
            self.target_r = map_speed(right)
            # Immediate send could be added here for lower latency,
            # but _loop handles it cleanly too.

    def set_servo_angle(self, pan: int, tilt: int):
        if self.manual_mode:
            self.pan_angle = pan
            self.tilt_angle = tilt
            self.pico.send_cmd(pan, tilt)

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

    # --- INTERNAL LOGIC (Refactored) ---

    def _capture_frame(self):
        """Reads a frame from the camera."""
        ret, frame = self.cap.read()
        if not ret:
            time.sleep(0.1)
            return None
        return frame

    def _run_auto_tracking(self, frame):
        """Handles face detection, PID calculation, and servo movement."""
        # Default stats for logging
        stats = {
            "err_x": 0, "err_y": 0,
            "d_pan": 0, "d_tilt": 0
        }

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

        # Dead zone
        if abs(error_x) < 25: error_x = 0
        if abs(error_y) < 25: error_y = 0

        stats["err_x"] = error_x
        stats["err_y"] = error_y

        if error_x == 0 and error_y == 0:
            return stats

        # PID Compute
        delta_pan = self.pid_pan.compute(0, error_x) if error_x != 0 else 0
        delta_tilt = self.pid_tilt.compute(0, error_y) if error_y != 0 else 0

        if self.invert_pan: delta_pan *= -1
        if self.invert_tilt: delta_tilt *= -1

        stats["d_pan"] = delta_pan
        stats["d_tilt"] = delta_tilt

        # Apply changes
        self.pan_angle = max(0, min(180, self.pan_angle + delta_pan))
        self.tilt_angle = max(50, min(130, self.tilt_angle + delta_tilt))

        # Send to Hardware (with rate limit)
        self._send_servo_safe()
        
        return stats

    def _send_servo_safe(self):
        """Sends servo commands respecting rate limits."""
        current_time = time.time()
        time_ok = (current_time - self.last_command_time) > self.command_interval
        
        angle_changed = (
            abs(self.pan_angle - self.last_sent_pan) > 1.0 or 
            abs(self.tilt_angle - self.last_sent_tilt) > 1.0
        )

        if time_ok and angle_changed:
            self.pico.send_cmd(int(self.pan_angle), int(self.tilt_angle))
            self.last_command_time = current_time
            self.last_sent_pan = self.pan_angle
            self.last_sent_tilt = self.tilt_angle

    def _update_motors(self, last_sent_l, last_sent_r):
        """Sends motor commands ONLY if targets changed."""
        if (self.target_l != last_sent_l) or (self.target_r != last_sent_r):
            self.pico.send_motor_cmd(int(self.target_l), int(self.target_r))
            return self.target_l, self.target_r
        return last_sent_l, last_sent_r

    def _update_stream(self, frame):
        """Encodes frame to JPEG for the web server."""
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
                    log_stats["err_x"], log_stats["err_y"],
                    self.pan_angle, self.tilt_angle,
                    log_stats["d_pan"], log_stats["d_tilt"]
                )

            # 5. Stream
            self._update_stream(frame)

            # 6. Throttle
            time.sleep(0.001)