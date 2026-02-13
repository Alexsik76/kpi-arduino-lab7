# Frontend Documentation

The frontend is a static web application hosted on GitHub Pages. It connects to the robot's backend to provide video streaming and control controls.

## 🔗 Links

- **Live Interface**: [alexsik76.github.io/kpi-arduino-lab7](https://alexsik76.github.io/kpi-arduino-lab7/)
- **Source Code**: `/docs` directory in the repository.

## Configuration

The application connects to the backend defined in `js/config.js`.

| Environment | URL                       | Note                                                     |
| :---------- | :------------------------ | :------------------------------------------------------- |
| **Global**  | `https://robot.lab.vn.ua` | Accessible from anywhere. **Requires Robot ON.**         |
| **Local**   | `https://robo.lan`        | Accessible only on local network. **Requires Robot ON.** |

_Note: The backend is not always online. The interface will show a "Signal Lost" status if the robot is offline._

## Control Modes

### 1. Connection Modes

- **Global**: Default mode. Connects via the public URL.
- **Local**: Toggle via the "Local Mode" switch in the UI. Reduces video latency but requires proximity.

### 2. Operation Modes

- **Manual Mode**: Full manual control via buttons/keyboard.
- **Auto Mode**: Robot autonomously tracks faces.

## Features

### Center Camera Button

- **Function**: Resets the camera head to the center (90°, 90°).
- **Requirement**: Only works in **Manual Mode**.

### Keyboard Controls

| Key       | Action                  |
| :-------- | :---------------------- |
| `W` / `S` | Move Forward / Backward |
| `A` / `D` | Turn Left / Right       |
| `Arrows`  | Pan/Tilt Camera         |
