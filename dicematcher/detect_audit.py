#!/usr/bin/env python3
"""
detect_audit_sorted.py
──────────────────────
Scan a dataset with a trained dice-face CNN and save ONLY:
  • wrong predictions   →  OUTPUT_DIR/incorrect/
  • low-confidence hits →  OUTPUT_DIR/lowconf/

Each saved image has an overlay (top-left) showing:
  • predicted class + prob
  • true class (and "LOW CONF" tag if applicable)

Perfect/certain hits are skipped to avoid clutter.
"""

import os, glob, cv2
import numpy as np
import tensorflow as tf

# ───────── config ──────────────────────────────────────────────────
MODEL_PATH  = "dice_cnn_custom_978.h5"
TEST_DIR    = "new_dataset/valid"
OUTPUT_DIR  = "output_cnn"
IMG_SIZE    = (150, 150)
CONF_THRESH = 0.85

INC_DIR     = os.path.join(OUTPUT_DIR, "incorrect")
LOW_DIR     = os.path.join(OUTPUT_DIR, "lowconf")
os.makedirs(INC_DIR, exist_ok=True)
os.makedirs(LOW_DIR, exist_ok=True)

# ───────── network ─────────────────────────────────────────────────
model = tf.keras.models.load_model(MODEL_PATH)

# ───────── helpers ────────────────────────────────────────────────
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.45
THICK      = 1
LINE_GAP   = 4          # px between overlay text lines

def put_multiline(img_bgr, lines, color):
    """Draw each string in *lines* below the previous one."""
    y = 5
    for text in lines:
        (w, h), _ = cv2.getTextSize(text, FONT, FONT_SCALE, THICK)
        cv2.putText(img_bgr, text, (5, y + h), FONT, FONT_SCALE, color, THICK, cv2.LINE_AA)
        y += h + LINE_GAP

# ───────── main loop ──────────────────────────────────────────────
total = wrong = low = 0

for path in sorted(glob.glob(os.path.join(TEST_DIR, "*", "*.*"))):
    total += 1
    true_num = int(os.path.basename(os.path.dirname(path)).split("_")[1])

    bgr = cv2.imread(path, cv2.IMREAD_COLOR)
    if bgr is None:
        print(f"⚠︎ unreadable {path}")
        continue
    rgb  = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    crop = cv2.resize(rgb, IMG_SIZE)

    preds   = model.predict(crop.astype("float32")[None, ...], verbose=0)[0]
    prob    = float(preds.max())
    pred_num= int(preds.argmax() + 1)
    correct = (pred_num == true_num)
    lowconf = (prob < CONF_THRESH)

    if correct and not lowconf:
        # confident & correct → skip saving
        continue

    # decide folder & overlay
    if correct:                    # low-confidence but right
        dest_dir = LOW_DIR;  low += 1
        color    = (0,255,255)    # yellow
        text = [f"pred {pred_num} ({prob:.2f})",
                "LOW CONF"]
    else:                         # wrong
        dest_dir = INC_DIR;  wrong += 1
        color    = (0,0,255)      # red
        tag      = "LOW CONF" if lowconf else ""
        text = [f"pred {pred_num} ({prob:.2f})",
                f"true {true_num} {tag}"]

    # draw overlay (BGR)
    canvas = cv2.cvtColor(crop, cv2.COLOR_RGB2BGR)
    put_multiline(canvas, text, color)

    # save with original filename
    out_path = os.path.join(dest_dir, os.path.basename(path))
    cv2.imwrite(out_path, canvas)
    print(f"[saved] {path}  →  {out_path}")

# ───────── summary ────────────────────────────────────────────────
print("\n=== Audit summary ===")
print(f"Total images    : {total}")
print(f"Incorrect       : {wrong}")
print(f"Low confidence  : {low}")
print(f"Skipped (clean) : {total - wrong - low}")
