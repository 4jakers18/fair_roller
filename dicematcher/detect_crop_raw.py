#!/usr/bin/env python3
import tensorflow as tf
import numpy as np
import cv2
import glob
import os

# ─── CONFIG ─────────────────────────────────────────────────────────────────────
MODEL_PATH       = "dice_cnn_custom.h5"
TEST_DIR         = "fair_roller_tests"   # flat directory of images
MIN_AREA_RATIO   = 0.01                   # ignore tiny contours (<1% of image area)
CONF_THRESHOLD   = 0.50                   # only count predictions above this confidence
CROPS_DIR        = "fair_roller_tests/crops"  # where to save cropped images
BACKGROUND_PATH  = "background.jpg"     # where to save the averaged background
MIN_CROP_RATIO   = 60 / 360.0            # minimum crop size ratio (60px @ 360px)
MAX_CROP_RATIO   = 80 / 360.0            # maximum crop size ratio (80px @ 360px)
# ────────────────────────────────────────────────────────────────────────────────

# 1) Prepare output directory for crops
os.makedirs(CROPS_DIR, exist_ok=True)

# 2) Load model and infer its expected input size & channels
model = tf.keras.models.load_model(MODEL_PATH)
_, H, W, C = model.input_shape     # e.g. (None, 128, 128, 3)
IMG_SIZE = (W, H)                  # cv2.resize expects (width, height)
num_sides = model.output_shape[-1]

# 3) Compute background by averaging all color images
bg_sum = None
count = 0
for path in sorted(glob.glob(os.path.join(TEST_DIR, "*.*"))):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        continue
    img_f = img.astype('float32')
    bg_sum = img_f if bg_sum is None else bg_sum + img_f
    count += 1
if count > 0:
    background = (bg_sum / count).astype('uint8')
    cv2.imwrite(BACKGROUND_PATH, background)
    print(f"Saved averaged background to {BACKGROUND_PATH}")
else:
    background = None
    print("No images found; background not computed.")

# 4) Improved die detection using threshold + morphology

def detect_die_bbox(diff_gray):
    # 4.1) Blur to reduce noise
    blur = cv2.GaussianBlur(diff_gray, (5,5), 0)
    # 4.2) Binary threshold via Otsu
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # 4.3) Morphological operations to close gaps and remove noise
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
    opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel, iterations=1)

    # 4.4) Find contours on cleaned mask
    cnts, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    H0, W0 = diff_gray.shape
    min_area = MIN_AREA_RATIO * W0 * H0
    best_box, best_area = None, 0
    for c in cnts:
        x,y,w,h = cv2.boundingRect(c)
        area = w * h
        if area >= min_area and area > best_area:
            best_box, best_area = (x, y, w, h), area

    # 4.5) Fallback if nothing found
    if best_box is None:
        margin = 0.1
        x = int(W0 * margin)
        y = int(H0 * margin)
        w = int(W0 * (1 - 2 * margin))
        h = int(H0 * (1 - 2 * margin))
    else:
        x, y, w, h = best_box

    # 4.6) Enforce square crop size
    min_side = int(MIN_CROP_RATIO * W0)
    max_side = int(MAX_CROP_RATIO * W0)
    side = max(w, h)
    side = np.clip(side, min_side, max_side)

    # Center square around detected region
    cx, cy = x + w//2, y + h//2
    x0 = max(0, min(cx - side//2, W0 - side))
    y0 = max(0, min(cy - side//2, H0 - side))
    return x0, y0, side, side

# 5) Initialize tally
counts = {i+1: 0 for i in range(num_sides)}

# 6) Process each image with improved detection
for path in sorted(glob.glob(os.path.join(TEST_DIR, "*.*"))):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None or background is None:
        continue

    # Compute color diff and collapse to gray by max channel
    diff_color = cv2.absdiff(img, background)
    diff_gray = np.max(diff_color, axis=2).astype('uint8')

    # Detect and crop
    x, y, w, h = detect_die_bbox(diff_gray)
    crop = img[y:y+h, x:x+w]

    # Save crop and perform prediction
    base = os.path.splitext(os.path.basename(path))[0]
    cv2.imwrite(os.path.join(CROPS_DIR, f"{base}_crop.jpg"), crop)
    resized = cv2.resize(crop, IMG_SIZE, interpolation=cv2.INTER_AREA)
    x_input = np.expand_dims(resized.astype("float32")/255.0, axis=0)
    preds = model.predict(x_input, verbose=0)[0]
    choice, prob = int(np.argmax(preds)), np.max(preds)
    side = choice + 1
    if prob > CONF_THRESHOLD:
        counts[side] += 1

# 7) Print final tally
print(f"\n=== Detection Tally (confidence > {CONF_THRESHOLD:.0%}) ===")
for side, cnt in counts.items():
    print(f"Side {side}: {cnt} detections")
