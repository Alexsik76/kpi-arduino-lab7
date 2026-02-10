import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from core import TrackingSystem

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("API")

# Check for logging flag
enable_csv_logging = "--log-csv" in sys.argv
if enable_csv_logging:
    logger.info("CSV Logging ENABLED")

system = TrackingSystem(enable_logging=enable_csv_logging)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Face Tracking System...")
    try:
        system.start()
        yield
    finally:
        logger.info("Shutting down...")
        system.stop()


app = FastAPI(lifespan=lifespan, title="Robot Eye v2")

# --- CORS CONFIGURATION ---
# Allows external sites (e.g., GitHub Pages) to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify domains; "*" is OK for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def generate_mjpeg():
    """Async stream generator with robust error handling."""
    try:
        while True:
            if not system.running:
                break

            jpg_data = system.get_jpg()
            if jpg_data is None:
                await asyncio.sleep(0.1)
                continue

            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg_data + b"\r\n")
            await asyncio.sleep(0.03)

    except (asyncio.CancelledError, OSError, ConnectionResetError):
        pass


@app.get("/health")
async def health_check():
    """Combined health check endpoint."""
    return {"status": "online", "system": "ready"}


@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(
        generate_mjpeg(), media_type="multipart/x-mixed-replace; boundary=frame"
    )


# --- Manual Control Endpoints ---


class ManualModeRequest(BaseModel):
    enabled: bool


class MotorControlRequest(BaseModel):
    left: int
    right: int


class ServoControlRequest(BaseModel):
    pan: int
    tilt: int


@app.post("/control/mode")
async def set_manual_mode(request: ManualModeRequest):
    system.set_manual_mode(request.enabled)
    return {"status": "ok", "manual_mode": request.enabled}


@app.get("/control/mode")
async def get_manual_mode():
    return {"manual_mode": system.manual_mode}


@app.post("/control/move")
async def control_move(request: MotorControlRequest):
    if not system.manual_mode:
        return {"status": "error", "message": "Manual mode not enabled"}

    system.set_motor_speed(request.left, request.right)
    return {"status": "ok", "left": request.left, "right": request.right}


@app.post("/control/servo")
async def control_servo(request: ServoControlRequest):
    if not system.manual_mode:
        return {"status": "error", "message": "Manual mode not enabled"}

    system.set_servo_angle(request.pan, request.tilt)
    return {"status": "ok", "pan": request.pan, "tilt": request.tilt}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app, host="0.0.0.0", port=8000, loop="asyncio", timeout_graceful_shutdown=1
    )
