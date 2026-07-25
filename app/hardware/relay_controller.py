import logging
import time

from gpiozero import OutputDevice
from gpiozero.pins.lgpio import LGPIOFactory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Lab7_Variant14")

class SteamEngineController:
    """
    Controls the DC motor via a relay.
    Implementation for Variant 14 (GPIO 14, Duration 1.4s).
    """

    def __init__(self, pin_number: int = 14):
        """
        Initialize the relay controller.
        :param pin_number: GPIO pin number (BCM). Default is 14.
        """
        # LGPIOFactory is critical for Raspberry Pi 5 architecture
        self._factory = LGPIOFactory()
        self._pin_number = pin_number
        
        # Initialize GPIO as output
        # active_high=True for High Level Trigger relay
        self._device = OutputDevice(
            pin=self._pin_number,
            active_high=True,
            initial_value=False,
            pin_factory=self._factory
        )
        logger.info(f"Relay controller initialized on GPIO {self._pin_number}")

    def activate_load(self):
        """
        Executes the lab task algorithm:
        Activate load for n * 100 ms.
        n = 14 -> 1400 ms = 1.4 s.
        """
        variant_n = 14
        duration = (variant_n * 100) / 1000.0
        
        logger.info(f"Starting standard procedure for Variant {variant_n}...")
        logger.info(f"Engine RUN for {duration} seconds")
        
        self._device.on()  # Close relay (Start motor)
        time.sleep(duration)
        self._device.off() # Open relay (Stop motor)
        
        logger.info("Engine STOPPED. Task completed.")

    def cleanup(self):
        """Release resources."""
        self._device.close()

if __name__ == "__main__":
    try:
        # Create controller object
        engine = SteamEngineController(pin_number=14)
        
        print("--- Press CTRL+C to stop manually ---")
        
        # Main loop for manual activation
        while True:
            input("Press Enter to activate Variant 14 sequence...")
            engine.activate_load()
            
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        if 'engine' in locals():
            engine.cleanup()