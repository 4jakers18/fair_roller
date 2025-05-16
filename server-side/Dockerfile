FROM python:3.12-slim

# --- install system deps --------------------------------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# --- install python deps --------------------------------------------------
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- copy code & launch ---------------------------------------------------
COPY ocr_script.py .
CMD ["python", "ocr_script.py"]
