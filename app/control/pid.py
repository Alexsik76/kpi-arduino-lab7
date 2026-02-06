# app/control/pid.py
import time

class PIDController:
    def __init__(self, kp, ki, kd, min_val, max_val):
        self.kp = kp  # Пропорційність (сила реакції)
        self.ki = ki  # Інтеграл (накопичення помилки - тут не знадобиться)
        self.kd = kd  # Похідна (гальмо при наближенні)
        
        self.min_val = min_val
        self.max_val = max_val
        
        self.prev_error = 0
        self.last_time = time.time()

    def compute(self, current_val, target_val):
        now = time.time()
        dt = now - self.last_time if (now - self.last_time) > 0 else 1e-3
        
        error = target_val - current_val
        
        # Proportional
        p_out = self.kp * error
        
        # Derivative (швидкість зміни помилки)
        # Це "гальмо": якщо ми швидко наближаємось, воно зменшує тягу
        derivative = (error - self.prev_error) / dt
        d_out = self.kd * derivative
        
        output = p_out + d_out
        
        # Save state
        self.prev_error = error
        self.last_time = now
        
        # Обмежуємо крок, щоб серво не зійшли з розуму
        # Наприклад, не більше 10 градусів за раз
        output = max(-3, min(3, output))
        
        return output