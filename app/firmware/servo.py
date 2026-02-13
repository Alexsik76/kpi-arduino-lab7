from machine import Pin, PWM

class TB6612Motor:
    """
    Driver for TB6612FNG with internal Smooth Ramping and Dead Zone compensation.
    """
    def __init__(self, pwm_pin, in1_pin, in2_pin, invert=False):
        self._pwm = PWM(Pin(pwm_pin))
        # 20kHz is above human hearing range (removes high-pitch whine)
        self._pwm.freq(20000)
        
        self._in1 = Pin(in1_pin, Pin.OUT)
        self._in2 = Pin(in2_pin, Pin.OUT)
        self._invert = invert
        
        # Physics state
        self.current_speed = 0.0
        self.target_speed = 0.0
        
        # Acceleration settings (step per update tick)
        # 3.0 = Smooth acceleration
        # 20.0 = Fast braking
        self.accel_step = 3.0
        self.decel_step = 20.0 
        
        # Minimum duty cycle to overcome static friction (Dead Zone)
        # Usually 30-40% for yellow TT motors
        self.min_duty_percent = 35 

        self._apply_hardware(0)

    def set_target(self, value):
        """Sets the target speed (-100 to 100)."""
        if value > 100: value = 100
        if value < -100: value = -100
        self.target_speed = float(value)

    def stop(self):
        """Immediate hard stop."""
        self.target_speed = 0.0
        self.current_speed = 0.0
        self._apply_hardware(0)

    def update(self):
        """
        Updates physics. Must be called periodically (e.g., every 20ms).
        """
        if self.current_speed == self.target_speed:
            return

        # Determine if we are accelerating or decelerating
        # Deceleration happens if:
        # 1. Target is 0 (stop)
        # 2. Target magnitude is less than current (slowing down)
        # 3. Signs are different (reversing)
        is_decelerating = (
            (self.target_speed == 0) or 
            (abs(self.target_speed) < abs(self.current_speed)) or 
            ((self.target_speed * self.current_speed) < 0)
        )

        step = self.decel_step if is_decelerating else self.accel_step

        if self.current_speed < self.target_speed:
            self.current_speed += step
            # Prevent overshoot
            if self.current_speed > self.target_speed:
                self.current_speed = self.target_speed
        else:
            self.current_speed -= step
            # Prevent overshoot
            if self.current_speed < self.target_speed:
                self.current_speed = self.target_speed

        self._apply_hardware(int(self.current_speed))

    def _apply_hardware(self, value):
        """Writes PWM and Direction pins."""
        # Handle inversion
        real_speed = -value if self._invert else value
        abs_speed = abs(real_speed)
        
        duty_val = 0
        
        # Dead Zone Mapping
        # If speed > 0, we map the range 1..100 to min_duty..100
        # This ensures the motor actually moves at low speeds
        if abs_speed > 0:
            # Normalize 1..100 to 0.0..1.0
            ratio = (abs_speed - 1) / 99.0 
            
            # Scale to min_duty..100
            pwm_percent = self.min_duty_percent + (ratio * (100 - self.min_duty_percent))
            
            # Convert percentage to u16 duty cycle
            duty_val = int(pwm_percent * 65535 / 100)
        
        self._pwm.duty_u16(duty_val)

        # Set H-Bridge direction
        if real_speed > 0:
            self._in1.value(1)
            self._in2.value(0)
        elif real_speed < 0:
            self._in1.value(0)
            self._in2.value(1)
        else:
            self._in1.value(0)
            self._in2.value(0)
