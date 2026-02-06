# app/hardware/servo_pico.py
import serial
import json
import time
import logging

logger = logging.getLogger(__name__)

class PicoController:
    def __init__(self, port='/dev/ttyACM0', baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self._connect()

    def _connect(self):
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(2)  # Чекаємо на ресет Pico
            logger.info(f"Connected to Pico on {self.port}")
        except serial.SerialException as e:
            logger.error(f"Pico connection failed: {e}")
            self.serial = None

    def send_cmd(self, pan=None, tilt=None):
        """Відправляє JSON команду на Pico"""
        if not self.serial:
            # Спроба перепідключитись "на льоту"
            self._connect()
            if not self.serial: return

        data = {}
        if pan is not None: data['pan'] = int(pan)
        if tilt is not None: data['tilt'] = int(tilt)

        if not data: return

        try:
            # Формуємо JSON + перехід рядка
            json_cmd = json.dumps(data) + '\n'
            self.serial.write(json_cmd.encode('utf-8'))
        except Exception as e:
            logger.error(f"Error writing to Pico: {e}")
            self.serial = None # Скидаємо, щоб перепідключитись

    def close(self):
        if self.serial:
            self.serial.close()