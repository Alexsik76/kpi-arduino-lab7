import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core import TrackingSystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("API")

# Global system instance
system: Optional[TrackingSystem] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the lifecycle of the application.
    Initializes hardware on startup and cleans up on shutdown.
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

# --- DATA MODELS ---


class ManualModeRequest(BaseModel):
    enabled: bool


class MotorControlRequest(BaseModel):
    left: int
    right: int


class ServoControlRequest(BaseModel):
    pan: int
    tilt: int


# --- MIDDLEWARE ---


@app.middleware("http")
async def private_network_access_middleware(request: Request, call_next):
    """
    Adds 'Access-Control-Allow-Private-Network: true' header to all responses.
    Required by Chrome for requests from public origins to private/local networks.
    """
    if request.method == "OPTIONS":
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": request.headers.get("Origin", "*"),
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Private-Network": "true",
                "Access-Control-Max-Age": "86400",
            },
        )
    response = await call_next(request)
    response.headers["Access-Control-Allow-Private-Network"] = "true"
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- VIDEO STREAM GENERATOR ---


async def generate_mjpeg():
    """
    Async generator for the MJPEG video stream.
    Yields JPEG frames with multipart boundaries.
    Handles client disconnection gracefully to avoid console errors.
    """
    try:
        while system and system.running:
            jpg_data = system.get_jpg()

            if jpg_data:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + jpg_data + b"\r\n"
                )
                # Sleep ~33ms for approx 30 FPS and to yield control
                await asyncio.sleep(0.033)
            else:
                # No frame yet, wait a bit longer to avoid CPU spinning
                await asyncio.sleep(0.05)

    except (asyncio.CancelledError, OSError, ConnectionResetError):
        # Graceful exit when client disconnects or server shuts down
        pass
    except Exception as e:
        logger.error(f"Stream generation error: {e}")


# --- ENDPOINTS ---


@app.get("/health")
async def health_check():
    """Returns the current system status."""
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
    """Control wheel motors (Manual mode only)."""
    if not system or not system.manual_mode:
        return {"status": "error", "message": "Manual mode disabled"}

    system.set_motor_speed(request.left, request.right)
    return {"status": "ok", "left": request.left, "right": request.right}


@app.post("/control/servo")
async def control_servo(request: ServoControlRequest):
    """Control pan/tilt servos (Manual mode only)."""
    if not system or not system.manual_mode:
        return {"status": "error", "message": "Manual mode disabled"}

    system.set_servo_angle(request.pan, request.tilt)
    return {"status": "ok", "pan": request.pan, "tilt": request.tilt}


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        loop="asyncio",
        timeout_graceful_shutdown=2
    )