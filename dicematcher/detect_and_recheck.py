#!/usr/bin/env python3
"""
detect_and_recheck_flat.py
─────────────────────────
Predict the upward-facing side of cropped D6-numeral images
on a flat directory (no folders) and annotate each image
with the best predicted side and confidence. Outputs
annotated images in OUTPUT_DIR.
"""

import os, glob, cv2
import numpy as np
import tensorflow as tf
import itertools

# ──────────────────────────────────────────────── CONFIG ──
MODEL_PATH       = "dice_cnn_custom_978.h5"
TEST_DIR         = "fair_roller_tests/crop"   # flat directory of images
OUTPUT_DIR       = "output_cnn_recheck/"     # where to save annotated crops
IMG_SIZE         = (256, 256)                 # must match training
CONF_THRESH      = 0.88                       # retry trigger
MARGIN           = 0.06                       # margin guard
ROTATION_DEGREES = [15, 45, 90, 135, 180, 225, 270, 315]
BRIGHT_ALPHAS    = [0.40, 0.80, 1.00, 1.60, 1.80]
BRIGHT_BETAS     = [-20, 0, 10, 20, 50, 70]
SKEW_PIXELS      = [5, 10, 30, 50]

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ────────────────────────────────────── load model ──
model = tf.keras.models.load_model(MODEL_PATH)

# ────────────────────────── helper: single prediction ──
def _predict(img):
    r = cv2.resize(img, IMG_SIZE)
    x = r.astype("float32")[None, ...]  # 0-255 scale
    p = model.predict(x, verbose=0)[0]
    return int(p.argmax() + 1), float(p.max()), r

# ────────────────────────────── helper: robust predict ──
def best_prediction(rgb_img):
    best_cls, best_prob, best_img = _predict(rgb_img)
    if best_prob >= CONF_THRESH:
        return best_cls, best_prob, best_img

    h, w = rgb_img.shape[:2]
    center = (w//2, h//2)
    # ROTATIONS
    for deg in ROTATION_DEGREES:
        M = cv2.getRotationMatrix2D(center, deg, 1.0)
        rot = cv2.warpAffine(rgb_img, M, (w, h),
                              flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT,
                              borderValue=(255,255,255))
        cls, prob, img_r = _predict(rot)
        if prob > best_prob + MARGIN:
            best_cls, best_prob, best_img = cls, prob, img_r
            if best_prob >= CONF_THRESH:
                return best_cls, best_prob, best_img
    # BRIGHTNESS/CONTRAST
    for α, β in itertools.product(BRIGHT_ALPHAS, BRIGHT_BETAS):
        bc = cv2.convertScaleAbs(rgb_img, alpha=α, beta=β)
        cls, prob, img_r = _predict(bc)
        if prob > best_prob + MARGIN:
            best_cls, best_prob, best_img = cls, prob, img_r
            if best_prob >= CONF_THRESH:
                return best_cls, best_prob, best_img
    # PERSPECTIVE SKEWS
    for dx in SKEW_PIXELS:
        for corner in [(0,0),(w,0),(w,h),(0,h)]:
            pts1 = np.float32([[0,0],[w,0],[w,h],[0,h]])
            pts2 = pts1.copy()
            idx = {(0,0):0,(w,0):1,(w,h):2,(0,h):3}[corner]
            pts2[idx] += (-dx if idx in (0,3) else dx,
                          -dx if idx in (0,1) else dx)
            M = cv2.getPerspectiveTransform(pts1, pts2)
            skew = cv2.warpPerspective(rgb_img, M, (w,h),
                                       flags=cv2.INTER_LINEAR,
                                       borderMode=cv2.BORDER_CONSTANT,
                                       borderValue=(255,255,255))
            cls, prob, img_r = _predict(skew)
            if prob > best_prob + MARGIN:
                best_cls, best_prob, best_img = cls, prob, img_r
                if best_prob >= CONF_THRESH:
                    return best_cls, best_prob, best_img
    # NEGATIVE
    if rgb_img.mean() > 170:
        neg = 255 - rgb_img
        cls, prob, img_r = _predict(neg)
        if prob > best_prob + MARGIN:
            best_cls, best_prob, best_img = cls, prob, img_r
    return best_cls, best_prob, best_img

# ─────────────────────────────────────────── main loop ──
for path in sorted(glob.glob(os.path.join(TEST_DIR, "*.*"))):
    bgr = cv2.imread(path, cv2.IMREAD_COLOR)
    if bgr is None:
        print(f"⚠ Skipped unreadable {path}")
        continue
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    cls_num, prob, best_rgb = best_prediction(rgb)

    # annotate
    canvas = cv2.cvtColor(best_rgb, cv2.COLOR_RGB2BGR)
    txt = f"class_{cls_num:02d} ({prob:.2f})"
    cv2.putText(canvas, txt, (5,20), cv2.FONT_HERSHEY_SIMPLEX,
                0.5, (0,255,0), 1, cv2.LINE_AA)

    # save
    out_name = f"class_{cls_num:02d}_{prob:.2f}_{os.path.basename(path)}"
    cv2.imwrite(os.path.join(OUTPUT_DIR, out_name), canvas)
    print(f"Processed {os.path.basename(path)} → {out_name}")
