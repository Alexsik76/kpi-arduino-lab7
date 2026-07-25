from machine import PWM, Pin


class Servo180:
    """
    Driver for standard 180-degree servo motors using PWM.
    """

    def __init__(self, pin_id, min_us=500, max_us=2500, freq=50):
        self._pwm = PWM(Pin(pin_id))
        self._pwm.freq(freq)
        self._min_ns = min_us * 1000
        self._max_ns = max_us * 1000
        self.set_angle(90)  # Default position: Center

    def set_angle(self, angle):
        """
        Sets the servo angle.
        :param angle: Angle in degrees (0-180)
        """
        if angle < 0:
            angle = 0
        if angle > 180:
            angle = 180

        # Calculate pulse width in nanoseconds
        pulse_ns = self._min_ns + (angle / 180) * (self._max_ns - self._min_ns)
        self._pwm.duty_ns(int(pulse_ns))

    def deinit(self):
        """Releases the PWM resource."""
        self._pwm.deinit()
