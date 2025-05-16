# server_test.py

from fastapi import FastAPI, WebSocket, Request, Query, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from PIL import Image
import io

app = FastAPI()

# —————————————————————————————————————
# In-memory state
# —————————————————————————————————————

# Connected WS clients
clients: set[WebSocket] = set()

# Default run config
config: Dict[str, Any] = {
    "sides":        6,           # number of die faces
    "rolls":       10,           # how many rolls to do
    "settle_ms":  100,           # settle time between spin & photo
    "frame_size": "VGA",         # e.g. 'QVGA','VGA','UXGA'
    "jpeg_quality": 12           # 0–63 lower = better
}

# Ensure upload dir exists
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# crop fraction of the short edge to keep (0.0–1.0)
CROP_RATIO = 0.75

# —————————————————————————————————————
# WebSocket endpoint
# —————————————————————————————————————

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    print("🔌 WS client connected")
    try:
        while True:
            msg = await ws.receive_text()
            print(f"← WS recv: {msg}")
            if msg == "ws_hello":
                await ws.send_json({"evt": "ready"})
            else:
                await ws.send_text(f"echo: {msg}")
    except Exception as ex:
        print("⚠️ WS disconnected:", ex)
    finally:
        clients.remove(ws)

# —————————————————————————————————————
# Helper to broadcast a command to all clients
# —————————————————————————————————————

async def broadcast(cmd: Dict[str, Any]):
    dead = []
    for ws in clients:
        try:
            await ws.send_json(cmd)
        except:
            dead.append(ws)
    for ws in dead:
        clients.remove(ws)

# —————————————————————————————————————
# Upload endpoint with center‐crop
# —————————————————————————————————————

@app.post("/upload")
async def upload_image(request: Request, seq: int = Query(...)):
    data = await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="No data received")

    # decode JPEG
    try:
        img = Image.open(io.BytesIO(data))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image data: {e}")

    # compute center square crop
    w, h = img.size
    side = int(min(w, h) * CROP_RATIO)
    left   = (w - side) // 2
    top    = (h - side) // 2
    right  = left + side
    bottom = top + side
    cropped = img.crop((left, top, right, bottom))

    # save cropped JPEG
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    fn = UPLOAD_DIR / f"{ts}_seq{seq}_{side}x{side}.jpg"
    try:
        with open(fn, "wb") as f:
            cropped.save(f, format="JPEG", quality=config["jpeg_quality"])
    except Exception as ex:
        print(f"❌ Failed to save {fn}: {ex}")
        raise HTTPException(status_code=500, detail="Failed to save cropped image")

    print(f"← Saved cropped seq={seq} → {fn} ({side}×{side})")
    return {"status": "ok", "filename": str(fn)}

# —————————————————————————————————————
# REST: Read / update config
# —————————————————————————————————————

@app.get("/config")
def get_config():
    return config

@app.post("/config")
async def set_config(updates: Dict[str, Any]):
    for k in updates:
        if k not in config:
            return JSONResponse({"error": f"Unknown config field '{k}'"}, status_code=400)
        config[k] = updates[k]
    print("⚙️ Config updated:", config)
    return config

# —————————————————————————————————————
# REST: Control commands
# —————————————————————————————————————

@app.post("/start")
async def start_run():
    cmd = {"cmd": "start", **config}
    await broadcast(cmd)
    print("→ cmd_start sent:", cmd)
    return {"status": "started", "cmd": cmd}

@app.post("/pause")
async def pause_run():
    await broadcast({"cmd": "pause"})
    print("→ cmd_pause sent")
    return {"status": "paused"}

@app.post("/resume")
async def resume_run():
    await broadcast({"cmd": "resume"})
    print("→ cmd_resume sent")
    return {"status": "resumed"}

@app.post("/stop")
async def stop_run():
    await broadcast({"cmd": "stop"})
    print("→ cmd_stop sent")
    return {"status": "stopped"}

# —————————————————————————————————————
# Main
# —————————————————————————————————————

if __name__ == "__main__":
    uvicorn.run("server_test:app", host="0.0.0.0", port=80)
