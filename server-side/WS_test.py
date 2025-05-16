# server_test.py

from fastapi import FastAPI, WebSocket, Request, Query, HTTPException
import uvicorn
from pathlib import Path
from datetime import datetime
from PIL import Image
import io

app = FastAPI()

# where we save the cropped images
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# fraction of the short edge to keep (0.0–1.0)
CROP_RATIO = 0.75

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    print("🔌 WS client connected")
    try:
        while True:
            msg = await ws.receive_text()
            print(f"← WS recv: {msg}")
            if msg == "ws_hello":
                await ws.send_json({"evt": "ready"})
            else:
                await ws.send_text(f"echo: {msg}")
    except Exception as e:
        print("⚠️ WS connection closed", e)

@app.post("/upload")
async def upload_image(request: Request, seq: int = Query(...)):
    # 1) Read body
    data = await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="No data received")

    # 2) Load into PIL and compute crop box
    try:
        img = Image.open(io.BytesIO(data))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image data: {e}")

    w, h = img.size
    side = int(min(w, h) * CROP_RATIO)
    left = (w - side) // 2
    top  = (h - side) // 2
    right = left + side
    bottom = top + side

    cropped = img.crop((left, top, right, bottom))

    # 3) Save cropped JPEG
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    filename = UPLOAD_DIR / f"{ts}_seq{seq}_{side}x{side}.jpg"
    try:
        cropped.save(filename, format="JPEG")
    except Exception as e:
        print(f"❌ Failed to save {filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save cropped image")

    print(f"← Saved cropped seq={seq} → {filename}  ({side}×{side})")
    return {"status": "ok", "filename": str(filename)}

if __name__ == "__main__":
    uvicorn.run("WS_test:app", host="0.0.0.0", port=80)
