import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from core import TrackingSystem

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("API")

# Global system instance (initialized lazily)
system: Optional[TrackingSystem] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the lifecycle of the application.
    Initializes the hardware on startup and cleans up on shutdown.
    """
    global system

    # Check for CLI flag or environment variable
    enable_csv = "--log-csv" in sys.argv or os.getenv("LOG_CSV") == "1"

    logger.info("Initializing Hardware...")
    try:
        system = TrackingSystem(enable_logging=enable_csv)
        logger.info("Starting Face Tracking System...")
        system.start()
        yield
    except Exception as e:
        logger.critical(f"Failed to start system: {e}")
        raise
    finally:
        logger.info("Shutting down...")
        if system:
            system.stop()


app = FastAPI(lifespan=lifespan, title="Robot Eye v2")

# --- CORS CONFIGURATION ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- DATA MODELS ---

class ManualModeRequest(BaseModel):
    enabled: bool


class MotorControlRequest(BaseModel):
    left: int
    right: int


class ServoControlRequest(BaseModel):
    pan: int
    tilt: int


# --- VIDEO STREAM ---

async def generate_mjpeg():
    """
    Async generator for the MJPEG video stream.
    Yields JPEG frames with multipart boundaries.
    """
    try:
        while system and system.running:
            jpg_data = system.get_jpg()

            if jpg_data is None:
                # Wait briefly if the camera is not ready yet
                await asyncio.sleep(0.05)
                continue

            # Construct the multipart frame
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + jpg_data + b"\r\n"
            )

            # Cap at ~30 FPS
            await asyncio.sleep(0.033)

    except (asyncio.CancelledError, OSError, ConnectionResetError):
        logger.debug("Client disconnected from stream")


# --- ENDPOINTS ---

@app.get("/health")
async def health_check():
    """Returns the system status."""
    status = "online" if system and system.running else "offline"
    return {"status": status}


@app.get("/video_feed")
async def video_feed():
    """Stream video feed to the client."""
    return StreamingResponse(
        generate_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.post("/control/mode")
async def set_manual_mode(request: ManualModeRequest):
    """Enable or disable manual control mode."""
    if system:
        system.set_manual_mode(request.enabled)
        return {"status": "ok", "manual_mode": request.enabled}
    return {"status": "error", "message": "System not ready"}


@app.get("/control/mode")
async def get_manual_mode():
    """Get the current control mode."""
    mode = system.manual_mode if system else False
    return {"manual_mode": mode}


@app.post("/control/move")
async def control_move(request: MotorControlRequest):
    """Control the wheel motors (Manual mode only)."""
    if not system or not system.manual_mode:
        return {"status": "error", "message": "Manual mode not enabled or system offline"}

    system.set_motor_speed(request.left, request.right)
    return {"status": "ok", "left": request.left, "right": request.right}


@app.post("/control/servo")
async def control_servo(request: ServoControlRequest):
    """Control the pan/tilt servos (Manual mode only)."""
    if not system or not system.manual_mode:
        return {"status": "error", "message": "Manual mode not enabled or system offline"}

    system.set_servo_angle(request.pan, request.tilt)
    return {"status": "ok", "pan": request.pan, "tilt": request.tilt}


if __name__ == "__main__":
    # Host 0.0.0.0 allows access from other devices on the network
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        loop="asyncio",
        timeout_graceful_shutdown=2
    )