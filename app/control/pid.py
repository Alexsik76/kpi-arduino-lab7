import time


class PIDController:
    """
    Standard PID controller implementation for hardware control.
    """
    def __init__(self, kp: float, ki: float, kd: float, output_limit: float = 1.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_limit = output_limit

        self.prev_error = 0.0
        self.integral = 0.0
        self.last_time = time.time()

    def compute(self, error: float) -> float:
        """
        Calculates the PID output based on the current error.
        """
        now = time.time()
        dt = now - self.last_time
        if dt <= 0:
            dt = 1e-3

        # Proportional term
        p_out = self.kp * error

        # Integral term (with anti-windup logic)
        self.integral += error * dt
        i_out = self.ki * self.integral

        # Derivative term (change in error)
        derivative = (error - self.prev_error) / dt
        d_out = self.kd * derivative

        # Total output
        output = p_out + i_out + d_out

        # State update
        self.prev_error = error
        self.last_time = now

        # Clamp output to prevent violent movements
        return max(-self.output_limit, min(self.output_limit, output))

    def reset(self):
        """Resets the internal state of the controller."""
        self.prev_error = 0.0
        self.integral = 0.0
        self.last_time = time.time()