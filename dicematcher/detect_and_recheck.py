#!/usr/bin/env python3
"""
detect_and_recheck.py
─────────────────────────
Predict the upward-facing side of cropped D6-numeral images.
If the first prediction’s confidence is below CONF_THRESH, the script
tries a bank of rotated variants (and can be extended with flips, etc.)
and keeps the most confident result.

Outputs:
  • annotated PNGs/JPEGs in OUTPUT_DIR
  • overall accuracy summary on stdout
"""

import os, glob, cv2
import numpy as np
import tensorflow as tf

# ────────────────────────────────────────────────────────── CONFIG ──
MODEL_PATH        = "dice_cnn_custom_978.h5"
TEST_DIR          = "new_dataset/train"          # folders side_01 … side_06
OUTPUT_DIR        = "output_cnn_recheck/"
IMG_SIZE          = (150, 150)                  # must match training
CONF_THRESH       = 0.88                     # retry trigger
MARGIN          = 0.06                        # margin guard
ROTATION_DEGREES  = [ 15, 45, 90, 135, 180, 225, 270, 315 ]  # fallback angles

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ───────────────────────────────────────────────────── load model ──
model = tf.keras.models.load_model(MODEL_PATH)

# ─────────────────────────────────────── helper: test many views ──
import itertools, random
# …

# Controlled sweep values ───────────────────────────────────────────
BRIGHT_ALPHAS   = [0.40, 0.80, 1.00, 1.60, 1.8]       # contrast
BRIGHT_BETAS    = [-20, 0, 10, 20, 50, 70]             # brightness shift
SKEW_PIXELS     = [  5, 10, 30, 50 ]               # how much to drag one corner
# ────────────────────────────────────────────────────────────────────

def _predict(img):
    """Resize, predict, return (cls, prob)."""
    r = cv2.resize(img, IMG_SIZE)
    x = r.astype("float32")[None, ...]            # 0-255 scale
    p = model.predict(x, verbose=0)[0]
    return int(p.argmax() + 1), float(p.max()), r

def best_prediction(rgb_img, conf_thresh=CONF_THRESH, margin=MARGIN):
    """
    Original → (rotations if needed) → (brightness/contrast) →
    (perspective skews) → optional negative.
    Stops as soon as we cross `conf_thresh + margin`.
    """
    best_cls, best_prob, best_img = _predict(rgb_img)

    if best_prob >= conf_thresh:
        return best_cls, best_prob, best_img          # early win

    # # ── ROTATIONS (as before) ─────────────────────────────────────
    h, w = rgb_img.shape[:2]
    center = (w//2, h//2)
    # for deg in ROTATION_DEGREES:
    #     M   = cv2.getRotationMatrix2D(center, deg, 1.0)
    #     rot = cv2.warpAffine(rgb_img, M, (w, h),
    #                          flags=cv2.INTER_LINEAR,
    #                          borderMode=cv2.BORDER_CONSTANT,
    #                          borderValue=(255, 255, 255))
    #     cls, prob, rimg = _predict(rot)
    #     if prob > best_prob + margin:
    #         best_cls, best_prob, best_img = cls, prob, rimg
    #         if best_prob >= conf_thresh:      # stop if confident
    #             return best_cls, best_prob, best_img

    # ── BRIGHTNESS / CONTRAST grid search ─────────────────────────
    for α, β in itertools.product(BRIGHT_ALPHAS, BRIGHT_BETAS):
        bc = cv2.convertScaleAbs(rgb_img, alpha=α, beta=β)
        cls, prob, rimg = _predict(bc)
        if prob > best_prob + margin:
            best_cls, best_prob, best_img = cls, prob, rimg
            if best_prob >= conf_thresh:
                return best_cls, best_prob, best_img

    # ── PERSPECTIVE SKEWS (pull one corner) ───────────────────────
    for dx in SKEW_PIXELS:
        for corner in ["tl", "tr", "bl", "br"]:
            pts1 = np.float32([[0,0],[w,0],[w,h],[0,h]])
            pts2 = pts1.copy()
            if corner == "tl": pts2[0] += (-dx, -dx)
            if corner == "tr": pts2[1] += ( dx, -dx)
            if corner == "br": pts2[2] += ( dx,  dx)
            if corner == "bl": pts2[3] += (-dx,  dx)
            M   = cv2.getPerspectiveTransform(pts1, pts2)
            skew = cv2.warpPerspective(rgb_img, M, (w,h),
                                        flags=cv2.INTER_LINEAR,
                                        borderMode=cv2.BORDER_CONSTANT,
                                        borderValue=(255, 255, 255))
            cls, prob, rimg = _predict(skew)
            if prob > best_prob + margin:
                best_cls, best_prob, best_img = cls, prob, rimg
                if best_prob >= conf_thresh:
                    return best_cls, best_prob, best_img

    # ── NEGATIVE (only if bg is bright) ───────────────────────────
    mean_lum = rgb_img[..., :3].mean()
    if mean_lum > 170:                 # arbitrary “bright bg” cut
        neg = 255 - rgb_img
        cls, prob, rimg = _predict(neg)
        if prob > best_prob + margin:
            best_cls, best_prob, best_img = cls, prob, rimg

    return best_cls, best_prob, best_img

# ───────────────────────────────────────────── main loop ──
results = []

for path in sorted(glob.glob(os.path.join(TEST_DIR, "*", "*.*"))):
    # ground-truth from folder name e.g. side_04
    true_num = int(os.path.basename(os.path.dirname(path)).split("_")[1])

    # load image (RGB)
    bgr = cv2.imread(path, cv2.IMREAD_COLOR)
    if bgr is None:
        print(f"⚠︎ Skipped unreadable file {path}")
        continue
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    # robust prediction
    cls_num, prob, best_rgb = best_prediction(rgb)

    # stats
    is_correct = (cls_num == true_num)
    results.append(is_correct)

    # annotate + save
    canvas = cv2.cvtColor(best_rgb, cv2.COLOR_RGB2BGR)
    text   = f"class_{cls_num:02d} ({prob:.2f})"
    if not is_correct:
        text += " incorrect"
    color = (0,255,0) if is_correct else (0,0,255)
    cv2.putText(canvas, text, (5,20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

    outfile = os.path.join(
        OUTPUT_DIR,
        f"{'class' if is_correct else 'incorrect'}_{cls_num:02d}_{prob:.2f}_{os.path.basename(path)}"
    )
    cv2.imwrite(outfile, canvas)
    print(f"[{'✓' if is_correct else '✗'} {cls_num} | {prob:.2f}]  {path} → {os.path.basename(outfile)}")

# ───────────────────────────────────────────── summary ──
total     = len(results)
correct   = sum(results)
accuracy  = correct / total if total else 0.0
print("\n=== Summary ===")
print(f"Total images : {total}")
print(f"Correct      : {correct}")
print(f"Incorrect    : {total - correct}")
print(f"Accuracy     : {accuracy:.3%}")
