# Firmware Documentation

This firmware runs on a **Raspberry Pi Pico** using **MicroPython**. It controls the robot's motors and servos based on JSON commands received via UART.

## Pinout

| Component       | Pin Function | GPIO Pin | Notes               |
| :-------------- | :----------- | :------- | :------------------ |
| **UART**        | TX           | `GP0`    | Connected to RPi RX |
|                 | RX           | `GP1`    | Connected to RPi TX |
| **Left Motor**  | PWM          | `GP16`   | Speed control       |
| (TB6612FNG)     | IN1          | `GP17`   | Direction A         |
|                 | IN2          | `GP18`   | Direction B         |
| **Right Motor** | PWM          | `GP21`   | Speed control       |
| (TB6612FNG)     | IN1          | `GP19`   | Direction A         |
|                 | IN2          | `GP20`   | Direction B         |
| **Servos**      | Pan          | `GP8`    | Horizontal (0-180°) |
|                 | Tilt         | `GP9`    | Vertical (0-180°)   |
| **Status**      | LED          | `LED`    | Onboard LED         |

## Communication Protocol

The firmware listens for **JSON strings** terminated by a newline character (`\n`) over UART at **115200 baud**.

### Command Format

**1. Servo Control**
Target angles in degrees (0-180).

```json
{ "pan": 90, "tilt": 90 }
```

**2. Motor Control**
Target speed (-100 to 100). Negative values reverse direction.

```json
{ "l": 100, "r": 100 }
```

**3. Emergency Stop**
Immediately stops all motors.

```json
{ "stop": true }
```

## Startup Behavior

On power-up, the robot performs a "wiggle" animation (Center -> Right-Up -> Left-Down -> Center) to indicate readiness.
