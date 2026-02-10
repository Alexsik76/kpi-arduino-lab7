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

        self.current_frame = None
        self.jpeg_bytes = None

        self.width = 640
        self.height = 480
        self.center_x = self.width // 2
        self.center_y = self.height // 2

        self._init_hardware()
        self._init_ai()
        self._init_control()

        if enable_logging:
            self.logger = DataLogger()
        else:
            self.logger = None

        # --- SAFETY: COMMAND RATE LIMITING ---
        self.last_command_time = 0
        self.command_interval = 0.03  # Max 10 Hz for servos (100ms)
        self.last_sent_pan = -1
        self.last_sent_tilt = -1

        # --- MOTOR CONTROL: SMOOTH RAMPING ---
        self.target_l = 0
        self.target_r = 0
        self.current_l = 0.0
        self.current_r = 0.0
        self.motor_max_speed = 85  # Limited to ~85%
        self.ramp_step = 6.0  # Speed change per loop iteration (~60ms to full speed)

    def _init_hardware(self):
        self.pico = PicoController(port="/dev/serial0")
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.pan_angle = 90
        self.tilt_angle = 90
        # Do not send command immediately at start to avoid current spike
        # self.pico.send_cmd(self.pan_angle, self.tilt_angle)

    def _init_ai(self):
        self.detector = FaceDetector(score_threshold=0.7)

    def _init_control(self):
        self.pid_pan = PIDController(kp=0.035, ki=0.0, kd=0.02, min_val=0, max_val=180)
        self.pid_tilt = PIDController(
            kp=0.035, ki=0.0, kd=0.02, min_val=45, max_val=135
        )
        self.invert_pan = True
        self.invert_tilt = False

    def set_manual_mode(self, enabled: bool):
        self.manual_mode = enabled
        logger.info(f"Manual mode set to {enabled}")

    def set_motor_speed(self, left: int, right: int):
        if self.manual_mode:
            # Clamp and scale input (assumed -100 to 100)
            def scale_speed(val):
                clamped = max(-100, min(100, val))
                return int(clamped * (self.motor_max_speed / 100.0))

            self.target_l = scale_speed(left)
            self.target_r = scale_speed(right)

    def set_servo_angle(self, pan: int, tilt: int):
        if self.manual_mode:
            self.pan_angle = pan
            self.tilt_angle = tilt
            self.pico.send_cmd(pan, tilt)

    def start(self):
        if self.running:
            return
        self.running = True
        thread = threading.Thread(target=self._loop, daemon=True)
        thread.start()
        logger.info("System started")

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
        if self.pico:
            self.pico.close()
        if self.logger:
            self.logger.close()
        logger.info("System stopped")

    def get_jpg(self):
        with self.lock:
            return self.jpeg_bytes

    def _loop(self):
        while self.running:
            # start_time = time.time()

            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            # 1. Face Tracking (Only in Auto Mode)
            if not self.manual_mode:
                face_box, landmarks = self.detector.find_face(frame)

                log_error_x = 0
                log_error_y = 0
                delta_pan = 0
                delta_tilt = 0

                if face_box is not None and landmarks is not None:
                    x, y, w, h = face_box
                    nose_x, nose_y = landmarks[4], landmarks[5]

                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.circle(frame, (nose_x, nose_y), 5, (0, 0, 255), -1)

                    error_x = nose_x - self.center_x
                    error_y = nose_y - self.center_y

                    # Dead zone (slightly increased)
                    if abs(error_x) < 25:
                        error_x = 0
                    if abs(error_y) < 25:
                        error_y = 0

                    log_error_x = error_x
                    log_error_y = error_y

                    # PID calculation
                    if error_x != 0 or error_y != 0:
                        if error_x != 0:
                            delta_pan = self.pid_pan.compute(0, error_x)
                        else:
                            delta_pan = 0

                        if error_y != 0:
                            delta_tilt = self.pid_tilt.compute(0, error_y)
                        else:
                            delta_tilt = 0

                        if self.invert_pan:
                            delta_pan *= -1
                        if self.invert_tilt:
                            delta_tilt *= -1

                        self.pan_angle += delta_pan
                        self.tilt_angle += delta_tilt

                        # Angle limits
                        self.pan_angle = max(0, min(180, self.pan_angle))
                        self.tilt_angle = max(50, min(130, self.tilt_angle))

                        # --- SAFETY: Rate Limiting ---
                        current_time = time.time()

                        # Send command ONLY if 0.1s passed OR angle changed significantly (>2 degrees)
                        time_ok = (
                            current_time - self.last_command_time
                        ) > self.command_interval
                        angle_changed_significantly = (
                            abs(self.pan_angle - self.last_sent_pan) > 1.0
                            or abs(self.tilt_angle - self.last_sent_tilt) > 1.0
                        )

                        if time_ok and angle_changed_significantly:
                            self.pico.send_cmd(
                                int(self.pan_angle), int(self.tilt_angle)
                            )
                            self.last_command_time = current_time
                            self.last_sent_pan = self.pan_angle
                            self.last_sent_tilt = self.tilt_angle

            # 2. Motor Control (Smooth Ramping - Always Active)
            # This allows smooth stop even if switching modes
            changed_l = False
            changed_r = False

            # Left Motor Ramp
            if self.current_l < self.target_l:
                self.current_l = min(self.target_l, self.current_l + self.ramp_step)
                changed_l = True
            elif self.current_l > self.target_l:
                self.current_l = max(self.target_l, self.current_l - self.ramp_step)
                changed_l = True

            # Right Motor Ramp
            if self.current_r < self.target_r:
                self.current_r = min(self.target_r, self.current_r + self.ramp_step)
                changed_r = True
            elif self.current_r > self.target_r:
                self.current_r = max(self.target_r, self.current_r - self.ramp_step)
                changed_r = True

            if changed_l or changed_r:
                self.pico.send_motor_cmd(int(self.current_l), int(self.current_r))

            # Logging can remain per frame, low overhead
            if self.logger:
                self.logger.log(
                    log_error_x,
                    log_error_y,
                    self.pan_angle,
                    self.tilt_angle,
                    delta_pan,
                    delta_tilt,
                )

            (flag, encoded) = cv2.imencode(
                ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80]
            )
            with self.lock:
                self.current_frame = frame
                if flag:
                    self.jpeg_bytes = encoded.tobytes()

            # Maximum speed, no artificial delays
            time.sleep(0.001)
