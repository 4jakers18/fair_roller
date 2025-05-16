#!/usr/bin/env python3
import tensorflow as tf
import numpy as np
import cv2, glob, os

# ─── CONFIG ─────────────────────────────────────────────────────────────────────
MODEL_PATH     = "dice_cnn.h5"
TEST_DIR       = "tests"        # your test set organized as tests/side_XX/*.jpg
OUTPUT_DIR     = "output_cnn/"  # where to save annotated + renamed crops
IMG_SIZE       = (256, 256)
MIN_AREA_RATIO = 0.01           # ignore tiny contours (<1% of image area)
# ────────────────────────────────────────────────────────────────────────────────

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1) Load model
model = tf.keras.models.load_model(MODEL_PATH)

# 2) Helper: find the die bounding box in a grayscale image
def detect_die_bbox(gray):
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    v = np.median(blur)
    lo = int(max(0, 0.66 * v))
    hi = int(min(255, 1.33 * v))
    edges = cv2.Canny(blur, lo, hi)
    cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    H, W = gray.shape
    min_area = MIN_AREA_RATIO * W * H
    best_box = None
    best_area = 0
    for c in cnts:
        x,y,w,h = cv2.boundingRect(c)
        area = w*h
        if area >= min_area and area > best_area:
            best_area = area
            best_box = (x,y,w,h)
    # fallback to center crop if nothing found
    if best_box is None:
        margin = 0.1
        best_box = (
            int(W*margin), int(H*margin),
            int(W*(1-2*margin)), int(H*(1-2*margin))
        )
    return best_box

# 3) Process each test image, collect correctness
results = []  # list of booleans: True if correct, False if incorrect

for path in sorted(glob.glob(os.path.join(TEST_DIR, "*", "*.*"))):
    # derive true label from folder name, e.g. "side_02" → 2
    true_folder = os.path.basename(os.path.dirname(path))
    true_num    = int(true_folder.split("_")[1])

    # a) load as grayscale
    img_gray = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img_gray is None:
        continue

    # b) detect & crop
    x,y,w,h = detect_die_bbox(img_gray)
    crop = img_gray[y:y+h, x:x+w]

    # c) resize & normalize for model
    img_resized = cv2.resize(crop, IMG_SIZE, interpolation=cv2.INTER_AREA)
    x_input = img_resized.astype("float32") / 255.0
    x_input = np.expand_dims(x_input, axis=(0, -1))  # (1,256,256,1)

    # d) predict
    preds    = model.predict(x_input, verbose=0)[0]
    picked   = int(np.argmax(preds))
    prob     = preds[picked]
    cls_num  = picked + 1
    score_str = f"{prob:.2f}".replace('.', '_')
    is_correct = (cls_num == true_num)
    results.append(is_correct)

    # e) annotate overlay
    out = cv2.cvtColor(img_resized, cv2.COLOR_GRAY2BGR)
    label_text = f"class_{cls_num:02d} ({prob:.2f})"
    if not is_correct:
        label_text += " incorrect"
    color = (0,255,0) if is_correct else (0,0,255)
    cv2.putText(
        out, label_text, (5,20),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA
    )

    # f) save with new filename
    orig_name = os.path.basename(path)
    prefix = "class" if is_correct else "incorrect"
    new_name = f"{prefix}_{cls_num:02d}_{score_str}_{orig_name}"
    out_path = os.path.join(OUTPUT_DIR, new_name)
    cv2.imwrite(out_path, out)

    print(f"[{prefix} {cls_num:02d} ({prob:.2f})] {path} → {new_name}")

# 4) Compute & print accuracy stats
total = len(results)
correct = sum(results)
incorrect = total - correct
accuracy = correct / total if total else 0
std_dev = float(np.std(results))  # boolean array → 0/1 → std dev = sqrt(p*(1-p))

print("\n=== Summary ===")
print(f"Total images:    {total}")
print(f"Correct:         {correct}")
print(f"Incorrect:       {incorrect}")
print(f"Accuracy:        {accuracy:.3f}")
print(f"Std. deviation:  {std_dev:.3f}")
