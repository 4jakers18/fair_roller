# server_test.py

from fastapi import FastAPI, WebSocket, Request, Query, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from PIL import Image
import io

app = FastAPI()

# ─── Serve UI and uploads ─────────────────────────────────────────────────────

# Static assets (your HTML/JS/CSS) live in ./static
app.mount("/static", StaticFiles(directory="static"), name="static")
# Saved images in ./uploads
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Root serves the UI shell
@app.get("/", response_class=FileResponse)
async def serve_index():
    return FileResponse("static/index.html")

# ─── In-memory state ──────────────────────────────────────────────────────────

clients: set[WebSocket] = set()  # active WS clients

config: Dict[str, Any] = {       # dynamic run configuration
    "sides":        6,           # number of die faces
    "rolls":       10,           # how many rolls to do
    "settle_ms":  100,           # settle time between spin & photo
    "frame_size": "VGA",         # e.g. 'QVGA','VGA','UXGA'
    "jpeg_quality": 12           # 0–63 lower = better
}

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

CROP_RATIO = 0.75  # fraction of short edge to keep for center-square crop

# ─── WebSocket endpoint ──────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    print("🔌 WS client connected")
    try:
        while True:
            msg = await ws.receive_text()
            print(f"← WS recv: {msg}")
            # Only handle the initial handshake
            if msg == "ws_hello":
                await ws.send_json({"evt": "ready"})
            # otherwise ignore – we broadcast events separately
    except Exception as ex:
        print("⚠️ WS disconnected:", ex)
    finally:
        clients.discard(ws)


# ─── Broadcast helper ─────────────────────────────────────────────────────────

async def broadcast(cmd: Dict[str, Any]):
    dead = []
    for ws in clients:
        try:
            await ws.send_json(cmd)
        except:
            dead.append(ws)
    for ws in dead:
        clients.discard(ws)

# ─── Upload endpoint with center‐crop ─────────────────────────────────────────

# server_test.py

@app.post("/upload")
async def upload_image(request: Request, seq: int = Query(...)):
    data = await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="No data received")

    # decode and crop (as before)
    img = Image.open(io.BytesIO(data))
    w, h = img.size
    side = int(min(w, h) * CROP_RATIO)
    left = (w - side) // 2
    top  = (h - side) // 2
    cropped = img.crop((left, top, left + side, top + side))

    # 1) save the timestamped archive
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    fn = UPLOAD_DIR / f"{ts}_seq{seq}_{side}x{side}.jpg"
    with open(fn, "wb") as f:
        cropped.save(f, format="JPEG", quality=config["jpeg_quality"])
    print(f"← Saved cropped seq={seq} → {fn} ({side}×{side})")

    # 2) also save a simple preview file named <seq>.jpg
    preview_fn = UPLOAD_DIR / f"{seq}.jpg"
    with open(preview_fn, "wb") as f2:
        cropped.save(f2, format="JPEG", quality=config["jpeg_quality"])

    # 3) broadcast the step_ok to all WS clients
    await broadcast({"evt": "step_ok", "seq": seq})

    return {"status": "ok", "filename": str(fn)}

# ─── Config endpoints ─────────────────────────────────────────────────────────

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

# ─── Control endpoints ────────────────────────────────────────────────────────

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

# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("server_test:app", host="0.0.0.0", port=80)
