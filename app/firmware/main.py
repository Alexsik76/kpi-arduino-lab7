from machine import UART, Pin, Timer
import json
import time
from servo import Servo180
from motor import TB6612Motor

# --- 1. SETUP LED ---
led = Pin("LED", Pin.OUT)

# --- 2. UART CONFIGURATION ---
# GP0=TX, GP1=RX
uart = UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1), timeout=100)

# --- 3. HARDWARE INIT ---
try:
    # Servos
    pan_servo = Servo180(pin_id=8)
    tilt_servo = Servo180(pin_id=9)
    
    # Motors
    motor_l = TB6612Motor(pwm_pin=16, in1_pin=17, in2_pin=18, invert=True)
    motor_r = TB6612Motor(pwm_pin=21, in1_pin=19, in2_pin=20, invert=False)
    
    # Physics Timer (Smooth movement)
    timer = Timer()
    def physics_loop(t):
        motor_l.update()
        motor_r.update()
        
    timer.init(freq=50, mode=Timer.PERIODIC, callback=physics_loop)
    
except Exception as e:
    print(f"Init Error: {e}")
    # Error signal: fast blink
    while True:
        led.toggle()
        time.sleep(0.1)

def stop_all():
    motor_l.stop()
    motor_r.stop()

# --- 4. STARTUP ANIMATION (THE "WIGGLE") ---
def startup_wiggle():
    """Moves the camera head to indicate power-on status."""
    # 1. Center
    pan_servo.set_angle(90)
    tilt_servo.set_angle(90)
    time.sleep(0.3)
    
    # 2. Look Right-Up
    pan_servo.set_angle(110)
    tilt_servo.set_angle(70)
    time.sleep(0.2)
    
    # 3. Look Left-Down
    pan_servo.set_angle(70)
    tilt_servo.set_angle(110)
    time.sleep(0.2)
    
    # 4. Back to Center
    pan_servo.set_angle(90)
    tilt_servo.set_angle(90)
    
    # Visual confirmation with LED
    for _ in range(3):
        led.on(); time.sleep(0.05); led.off(); time.sleep(0.05)

# Run animation once on boot
startup_wiggle()

# --- 5. MAIN LOOP ---
print("System Ready")

while True:
    if uart.any():
        # Turn LED ON when receiving data
        led.on()
        
        try:
            line = uart.readline()
            if line:
                line_str = line.decode('utf-8').strip()
                if line_str:
                    data = json.loads(line_str)
                    
                    # Servo Control
                    if "pan" in data: pan_servo.set_angle(data["pan"])
                    if "tilt" in data: tilt_servo.set_angle(data["tilt"])
                    
                    # Motor Control
                    if "l" in data: motor_l.set_target(data["l"])
                    if "r" in data: motor_r.set_target(data["r"])
                    
                    if "stop" in data: stop_all()

        except ValueError:
            pass 
        except Exception as e:
            stop_all()
            print(f"Error: {e}")
        
        # Turn LED OFF after processing
        led.off()
