import time

class PIDController:
    """
    A simple PID controller for servo movement with output clamping.
    """
    def __init__(self, kp: float, ki: float, kd: float, output_limit: float = 15.0):
        """
        Initialize the PID controller.

        Args:
            kp (float): Proportional gain.
            ki (float): Integral gain.
            kd (float): Derivative gain.
            output_limit (float, optional): Maximum change per step (speed limit). Defaults to 15.0.
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_limit = output_limit
        
        self.prev_error = 0.0
        self.last_time = time.time()

    def compute(self, current_val: float, target_val: float) -> float:
        """
        Calculate the control output (correction value).
        """
        now = time.time()
        
        # Calculate time delta (dt) safely
        dt = now - self.last_time if (now - self.last_time) > 0 else 1e-3
        
        error = target_val - current_val
        
        # Proportional term
        p_out = self.kp * error
        
        # Derivative term
        derivative = (error - self.prev_error) / dt
        d_out = self.kd * derivative
        
        # Note: Integral term is omitted as per your previous logic (ki=0 usually),
        # but could be added here if needed.
        
        output = p_out + d_out
        
        # Save state for next iteration
        self.prev_error = error
        self.last_time = now
        
        # Clamp the output to the limit (e.g., between -15 and 15)
        # This prevents the servo from moving too violently
        output = max(-self.output_limit, min(self.output_limit, output))
        
        return output