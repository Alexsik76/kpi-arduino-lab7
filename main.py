import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.types import ASGIApp, Receive, Scope, Send

from core import TrackingSystem


# --- LOGGING CONFIGURATION (Suppress Noise) ---
class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Filter out annoying cancellation errors during shutdown
        msg = record.getMessage()
        if "Exception in ASGI application" in msg or "CancelledError" in msg:
            return False
        return True


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("API")
# Apply filter to uvicorn error log to eat the traceback on Ctrl+C
logging.getLogger("uvicorn.error").addFilter(EndpointFilter())


# Global system instance
system: Optional[TrackingSystem] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the lifecycle of the application.
    Initializes hardware on startup and cleans up on shutdown.
    """
    global system

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
        # Give async tasks a moment to realize we are shutting down
        await asyncio.sleep(0.1)


app = FastAPI(lifespan=lifespan, title="Robot Eye v2")


# --- PURE ASGI MIDDLEWARE (Fixes Stream Errors) ---


class PrivateNetworkAccessMiddleware:
    """
    Pure ASGI middleware to handle Private Network Access headers.
    Replaces @app.middleware("http") to avoid BaseHTTPMiddleware streaming bugs.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Wrapper to inject headers into the response start message
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                # Add PNA header
                headers.append((b"access-control-allow-private-network", b"true"))

                # Handle OPTIONS preflight manually if needed,
                # but usually we just append headers to all responses.
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)


app.add_middleware(PrivateNetworkAccessMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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


# --- VIDEO STREAM GENERATOR ---


async def generate_mjpeg(request: Request):
    """
    Async generator that checks for client disconnection
    to avoid 'Exception in ASGI application' logs.
    """
    try:
        while system and system.running:
            # Critical: Check if client disconnected explicitly
            if await request.is_disconnected():
                break

            jpg_data = system.get_jpg()

            if jpg_data:
                yield (
                    b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg_data + b"\r\n"
                )
                await asyncio.sleep(0.033)
            else:
                await asyncio.sleep(0.05)

    except (asyncio.CancelledError, OSError):
        # Normal exit on shutdown
        pass
    except Exception as e:
        logger.error(f"Stream error: {e}")


# --- ENDPOINTS ---


@app.get("/health")
async def health_check():
    """Returns the current system status."""
    status = "online" if system and system.running else "offline"
    return {"status": status}


@app.get("/video_feed")
async def video_feed(request: Request):
    """Stream video feed to the client."""
    return StreamingResponse(
        generate_mjpeg(request), media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.post("/control/mode")
async def set_manual_mode(request: ManualModeRequest):
    if system:
        system.set_manual_mode(request.enabled)
        return {"status": "ok", "manual_mode": request.enabled}
    return {"status": "error", "message": "System not ready"}


@app.get("/control/mode")
async def get_manual_mode():
    mode = system.manual_mode if system else False
    return {"manual_mode": mode}


@app.post("/control/move")
async def control_move(request: MotorControlRequest):
    if not system or not system.manual_mode:
        return {"status": "error", "message": "Manual mode disabled"}

    system.set_motor_speed(request.left, request.right)
    return {"status": "ok", "left": request.left, "right": request.right}


@app.post("/control/servo")
async def control_servo(request: ServoControlRequest):
    if not system or not system.manual_mode:
        return {"status": "error", "message": "Manual mode disabled"}

    system.set_servo_angle(request.pan, request.tilt)
    return {"status": "ok", "pan": request.pan, "tilt": request.tilt}


if __name__ == "__main__":
    # Force log level to critical for uvicorn error during shutdown if needed,
    # but the Filter above is better.
    uvicorn.run(
        app, host="0.0.0.0", port=8000, loop="asyncio", timeout_graceful_shutdown=1
    )
