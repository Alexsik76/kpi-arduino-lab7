import cv2
import threading
import time
import logging

from app.hardware.servo_pico import PicoController
from app.tracking.face_utils import FaceDetector
from app.control.servo_actor import PanTiltHead
from app.utils.data_logger import DataLogger

logger = logging.getLogger("Core")

# --- MOCK CLASS ---
class MockPicoController(PicoController):
    """
    Inherits from PicoController to satisfy type checkers.
    Overrides __init__ to avoid opening real serial ports.
    """
    def __init__(self, port=None):
        # We deliberately do NOT call super().__init__() 
        # to prevent hardware connection attempts.
        pass

    def send_motor_cmd(self, left: int, right: int):
        """Mock method with unambiguous variable names."""
        pass  # Do nothing

    def close(self):
        pass

class TrackingSystem:
    def __init__(self, enable_logging: bool = False):
        self.running = False
        self.manual_mode = False
        self.lock = threading.Lock()

        # Stream properties
        self.current_frame = None
        self.jpeg_bytes = None
        self.width, self.height = 640, 480
        self.center_x, self.center_y = self.width // 2, self.height // 2

        # Subsystems
        self.pico = self._init_pico()
        
        self.cap = self._init_camera()
        self.detector = FaceDetector(score_threshold=0.7)
        
        # Now valid because MockPicoController IS A PicoController
        self.head = PanTiltHead(self.pico)
        
        self.logger = DataLogger() if enable_logging else None

        # Motor targets
        self.target_l = 0
        self.target_r = 0

    def _init_pico(self) -> PicoController:
        """Initialize real hardware or fallback to Mock."""
        try:
            return PicoController(port="/dev/serial0")
        except Exception as e:
            logger.error(f"Pico init failed: {e}. Switching to Mock mode.")
            return MockPicoController()

    def _init_camera(self):
        gst_pipeline = (
            "libcamerasrc ! "
            "video/x-raw, format=NV12, width=640, height=480, framerate=30/1 ! "
            "videoconvert ! video/x-raw, format=BGR ! appsink drop=1 sync=0"
        )
        # Try GStreamer (for RPi Camera)
        cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
        
        # Fallback to standard V4L2 if GStreamer fails
        if not cap.isOpened():
            logger.warning("GStreamer failed, falling back to V4L2 (index 0)")
            cap = cv2.VideoCapture(0)
            
        return cap

    # --- API METHODS ---

    def set_manual_mode(self, enabled: bool):
        self.manual_mode = enabled
        if enabled:
            self.target_l, self.target_r = 0, 0
            self._update_motors(0, 0)
        logger.info(f"Mode: {'Manual' if enabled else 'Auto'}")

    def set_servo_angle(self, pan: int, tilt: int):
        """Manual control for camera servos."""
        if self.manual_mode:
            self.head.manual_move(pan, tilt)

    def set_motor_speed(self, left: int, right: int):
        """Manual control for platform motors."""
        if self.manual_mode:
            # Note: inputs might be swapped based on wiring
            self.target_l, self.target_r = right, left

    def start(self):
        if self.running: 
            return
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self.running = False
        if self.cap: 
            self.cap.release()
        if self.pico: 
            self.pico.close()

    # --- INTERNAL LOOP ---

    def _loop(self):
        last_l, last_r = -999, -999
        while self.running:
            ret, frame = self.cap.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue

            log_stats = None
            if not self.manual_mode:
                log_stats = self._process_auto_tracking(frame)
            else:
                last_l, last_r = self._update_motors(last_l, last_r)

            if self.logger and log_stats:
                self.logger.log(
                    log_stats.get("err_x", 0), log_stats.get("err_y", 0),
                    self.head.pan_angle, self.head.tilt_angle,
                    log_stats.get("d_pan", 0), log_stats.get("d_tilt", 0)
                )

            self._update_stream(frame)
            time.sleep(0.001)

    def _process_auto_tracking(self, frame):
        face_box, landmarks = self.detector.find_face(frame)
        
        if face_box is not None and landmarks is not None:
            nose_x, nose_y = landmarks[4], landmarks[5]
            error_x = nose_x - self.center_x
            error_y = nose_y - self.center_y
            
            move_stats = self.head.track_target(error_x, error_y)
            
            x, y, w, h = face_box
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.circle(frame, (nose_x, nose_y), 5, (0, 0, 255), -1)
            
            stats = {"err_x": error_x, "err_y": error_y}
            stats.update(move_stats)
            return stats
        
        return None

    def _update_motors(self, last_l, last_r):
        if self.target_l != last_l or self.target_r != last_r:
            self.pico.send_motor_cmd(int(self.target_l), int(self.target_r))
            return self.target_l, self.target_r
        return last_l, last_r

    def _update_stream(self, frame):
        _, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        with self.lock:
            self.jpeg_bytes = encoded.tobytes()

    def get_jpg(self):
        with self.lock:
            return self.jpeg_bytes