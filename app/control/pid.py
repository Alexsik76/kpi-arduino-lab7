import time

class PIDController:
    def __init__(self, kp, ki, kd, min_val, max_val):
        self.kp = kp  # Proportional gain
        self.ki = ki  # Integral gain
        self.kd = kd  # Derivative gain
        
        self.min_val = min_val
        self.max_val = max_val
        
        self.prev_error = 0
        self.last_time = time.time()

    def compute(self, current_val, target_val):
        now = time.time()
        # Prevent division by zero
        dt = now - self.last_time if (now - self.last_time) > 0 else 1e-3
        
        error = target_val - current_val
        
        # Proportional term
        p_out = self.kp * error
        
        # Derivative term (dampening)
        derivative = (error - self.prev_error) / dt
        d_out = self.kd * derivative
        
        output = p_out + d_out
        
        # Save state for next iteration
        self.prev_error = error
        self.last_time = now
        
        # Limit the output change (speed limit) to avoid jerky movements
        output = max(-15, min(15, output))
        
        return output