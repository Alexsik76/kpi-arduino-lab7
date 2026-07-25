# Manual Hardware Verification Scripts

The scripts in this directory are manual hardware verification tools designed to run directly on the physical robot (Raspberry Pi and Raspberry Pi Pico).

## Hardware Requirement

These scripts interact directly with physical hardware peripherals (camera modules, UART serial interfaces, DC motors, and servo actuators). They cannot be run in automated CI environments or standard unit test runners.

## Usage

Each script is executed manually on the robot hardware:

- `check_cam.py`: Basic camera initialization and frame capture check.
- `check_step1_cam.py`: Camera resolution and image saving test.
- `check_step2_ai.py`: Face detection model loading and inference test.
- `check_uart.py`: Pico UART communication check.
- `check_move.py`: Motor and servo control test sequence over UART.
- `calibrate.py`: Pan and tilt servo orientation calibration.
- `fast_test.py`: Fast movement and response test script.
- `simple_run.py`: Minimal end-to-end face tracking loop script.
