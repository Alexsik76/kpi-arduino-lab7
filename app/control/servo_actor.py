import time
import logging
from app.control.pid import PIDController
from app.hardware.servo_pico import PicoController

logger = logging.getLogger("ServoActor")


class PanTiltHead:
    """
    Final corrected actor. Signs flipped to fix "running away"
    and Kd reduced to stop the "initial jump" away from the face.
    """

    def __init__(self, pico_controller: PicoController):
        self.pico = pico_controller
        self.pan_angle = 90.0
        self.tilt_angle = 90.0
        self.PAN_MIN, self.PAN_MAX = 0, 180
        self.TILT_MIN, self.TILT_MAX = 50, 130

        # --- PID TUNING (narrow FoV camera) ---
        # Narrower lens → face covers more pixels → error is ~2x larger.
        # Gains reduced ~40% from wide-angle values to compensate.
        self.pid_pan = PIDController(kp=-0.0012, ki=0.0, kd=-0.001, output_limit=0.4)
        self.pid_tilt = PIDController(kp=0.0006, ki=0.0, kd=0.0005, output_limit=0.3)

        self.dead_zone = 35  # Larger face → need wider dead zone to filter noise
        self.last_sent_time = 0.0
        self.send_interval = 0.04
        self.last_sent_pan = -1
        self.last_sent_tilt = -1

    def track_target(self, error_x: int, error_y: int) -> dict:
        """Calculates smooth tracking without the initial opposite kick."""
        adj_err_x = error_x if abs(error_x) > self.dead_zone else 0
        adj_err_y = error_y if abs(error_y) > self.dead_zone else 0

        # Compute PID outputs
        delta_pan = self.pid_pan.compute(adj_err_x)
        delta_tilt = self.pid_tilt.compute(adj_err_y)

        # Apply movement
        self.pan_angle = self._clamp(
            self.pan_angle + delta_pan, self.PAN_MIN, self.PAN_MAX
        )
        self.tilt_angle = self._clamp(
            self.tilt_angle + delta_tilt, self.TILT_MIN, self.TILT_MAX
        )

        self._sync_hardware()

        return {
            "d_pan": delta_pan,
            "d_tilt": delta_tilt,
            "pan": self.pan_angle,
            "tilt": self.tilt_angle,
        }

    def manual_move(self, pan: int, tilt: int):
        """Standard manual control used by the UI buttons."""
        self.pan_angle = self._clamp(pan, self.PAN_MIN, self.PAN_MAX)
        self.tilt_angle = self._clamp(tilt, self.TILT_MIN, self.TILT_MAX)
        self.pid_pan.reset()
        self.pid_tilt.reset()
        self._sync_hardware(force=True)

    def _sync_hardware(self, force: bool = False):
        """Sends commands to Pico via UART."""
        now = time.time()
        if not force and (now - self.last_sent_time < self.send_interval):
            return

        if force or abs(self.pan_angle - self.last_sent_pan) > 0.4:
            if self.pico:
                self.pico.send_cmd(int(self.pan_angle), int(self.tilt_angle))
                self.last_sent_time = now
                self.last_sent_pan = self.pan_angle
                self.last_sent_tilt = self.tilt_angle

    @staticmethod
    def _clamp(value, min_val, max_val):
        return max(min_val, min(max_val, value))
