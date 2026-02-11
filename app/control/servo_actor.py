import time
import logging
from app.control.pid import PIDController
from app.hardware.servo_pico import PicoController

logger = logging.getLogger("ServoActor")

class PanTiltHead:
    """
    High-level controller for the Pan/Tilt mechanism.
    Manages PID logic, physical angle limits, and UART communication rates.
    """

    def __init__(self, pico_controller: PicoController):
        self.pico = pico_controller
        
        # Current State
        self.pan_angle: float = 90.0
        self.tilt_angle: float = 90.0
        
        # Hardware Limits (Hard Stops)
        self.PAN_MIN, self.PAN_MAX = 0, 180
        self.TILT_MIN, self.TILT_MAX = 50, 130
        
        # PID Configuration (Output limit = max speed per tick)
        self.pid_pan = PIDController(kp=0.035, ki=0.0, kd=0.02, output_limit=15)
        self.pid_tilt = PIDController(kp=0.035, ki=0.0, kd=0.02, output_limit=10)
        
        # Configuration
        self.invert_pan = True
        self.invert_tilt = False
        
        # Rate Limiting (to avoid flooding UART)
        self.last_sent_time = 0.0
        self.send_interval = 0.03  # ~30Hz max update rate
        self.last_sent_pan = -1
        self.last_sent_tilt = -1

    def track_target(self, error_x: int, error_y: int) -> dict:
        """
        Calculates new angles based on error and moves servos if needed.
        Returns debug stats.
        """
        # 1. PID Calculation (Getting the correction)
        delta_pan = self.pid_pan.compute(0, error_x)
        delta_tilt = self.pid_tilt.compute(0, error_y)

        if self.invert_pan: delta_pan *= -1
        if self.invert_tilt: delta_tilt *= -1

        # 2. Apply Correction & Clamp (Physical Limits)
        self.pan_angle = self._clamp(self.pan_angle + delta_pan, self.PAN_MIN, self.PAN_MAX)
        self.tilt_angle = self._clamp(self.tilt_angle + delta_tilt, self.TILT_MIN, self.TILT_MAX)

        # 3. Send to Hardware (Rate Limited)
        self._sync_hardware()

        return {
            "d_pan": delta_pan,
            "d_tilt": delta_tilt,
            "pan": self.pan_angle,
            "tilt": self.tilt_angle
        }

    def manual_move(self, pan: int, tilt: int):
        """Directly sets angles in manual mode."""
        self.pan_angle = self._clamp(pan, self.PAN_MIN, self.PAN_MAX)
        self.tilt_angle = self._clamp(tilt, self.TILT_MIN, self.TILT_MAX)
        self._sync_hardware(force=True)

    def _sync_hardware(self, force=False):
        """Sends command to Pico via UART if interval passed or forced."""
        now = time.time()
        
        # Check time constraint
        if not force and (now - self.last_sent_time < self.send_interval):
            return

        # Check redundant data constraint (don't send if angle hasn't changed enough)
        pan_changed = abs(self.pan_angle - self.last_sent_pan) > 0.5
        tilt_changed = abs(self.tilt_angle - self.last_sent_tilt) > 0.5

        if force or pan_changed or tilt_changed:
            self.pico.send_cmd(int(self.pan_angle), int(self.tilt_angle))
            self.last_sent_time = now
            self.last_sent_pan = self.pan_angle
            self.last_sent_tilt = self.tilt_angle

    @staticmethod
    def _clamp(value, min_val, max_val):
        return max(min_val, min(max_val, value))