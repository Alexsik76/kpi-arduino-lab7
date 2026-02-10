import serial
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class PicoController:
    def __init__(self, port="/dev/serial0", baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.serial: Optional[serial.Serial] = None
        self._connect()

    def _connect(self):
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.1,  # Short timeout for non-blocking feel
                xonxoff=False,
                rtscts=False,  # RPi 5 UART typically doesn't use hardware flow control
                dsrdtr=False,
            )
            logger.info(f"UART Connected: {self.port}")
        except serial.SerialException as e:
            logger.critical(f"UART Connection failed: {e}")
            self.serial = None

    def send_cmd(self, pan: int, tilt: int):
        """
        Sends pan/tilt coordinates to Pico via UART.
        Protocol: JSON string terminated by newline.
        """
        if not self.serial:
            return

        command = {"pan": int(pan), "tilt": int(tilt)}

        try:
            # Prepare payload: JSON + \n
            payload = json.dumps(command) + "\n"
            self.serial.write(payload.encode("utf-8"))
        except Exception as e:
            logger.error(f"UART Write Error: {e}")
            # Optional: logic to attempt reconnection could go here

    def send_motor_cmd(self, left: int, right: int):
        """
        Sends motor speed commands to Pico via UART.
        Protocol: JSON string terminated by newline.
        Example: {"left": 100, "right": 100}
        """
        if not self.serial:
            return

        command = {"left": int(left), "right": int(right)}

        try:
            # Prepare payload: JSON + \n
            payload = json.dumps(command) + "\n"
            self.serial.write(payload.encode("utf-8"))
        except Exception as e:
            logger.error(f"UART Write Error (Motor): {e}")

    def close(self):
        if self.serial and self.serial.is_open:
            # Try to stop the robot before closing
            try:
                self.serial.write(b'{"stop":true}\n')
            except Exception:
                pass
            self.serial.close()
            logger.info("UART closed")
