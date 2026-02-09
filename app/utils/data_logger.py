import csv
import time
import os
import logging
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)

class DataLogger:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        # Create unique filename based on timestamp
        filename = f"track_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self.filepath = os.path.join(self.log_dir, filename)
        
        self.file = open(self.filepath, mode='w', newline='', encoding='utf-8')
        self.writer = csv.writer(self.file)
        
        # CSV Header
        self.writer.writerow([
            "timestamp", 
            "error_x", "error_y", 
            "pan_angle", "tilt_angle",
            "delta_pan", "delta_tilt" # Useful to see PID output
        ])
        logger.info(f"Logging telemetry to: {self.filepath}")

    def log(self, error_x, error_y, pan, tilt, d_pan, d_tilt):
        """Writes a single data frame to CSV."""
        try:
            row = [
                time.time(),
                error_x, error_y,
                round(pan, 2), round(tilt, 2),
                round(d_pan, 4), round(d_tilt, 4)
            ]
            self.writer.writerow(row)
        except Exception as e:
            logger.error(f"CSV Write Error: {e}")

    def close(self):
        if self.file:
            self.file.flush()
            self.file.close()
            logger.info("Telemetry log closed")