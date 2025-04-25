import requests
from io import BytesIO
from PIL import Image
import pytesseract

IMAGE_URL = "http://image-host/image.jpg"   # resolves via Docker DNS

def main():
    resp = requests.get(IMAGE_URL, timeout=10)
    resp.raise_for_status()
    img = Image.open(BytesIO(resp.content))

    text = pytesseract.image_to_string(img).strip()
    print(f"[OCR] extracted → {text!r}")

    # Example: forward result somewhere
    # requests.post("http://image-host/result", json={"text": text})

if __name__ == "__main__":
    main()
