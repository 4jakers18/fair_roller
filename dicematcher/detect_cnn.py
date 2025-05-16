#!/usr/bin/env python3
import tensorflow as tf
import numpy as np
import cv2, glob, os
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
# 1) Config
MODEL_PATH         = "dice_mobilenetv2.h5"
TEST_DIR           = "new_dataset/train"    # your cropped test set
OUTPUT_DIR         = "output_cnn/"
IMG_SIZE           = (256, 256)
SAVE_CORRECT_IMGS  = False  # ← set to True to write correct images as well

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 2) Load model
model = tf.keras.models.load_model(MODEL_PATH)

# 3) Process each test image, track correctness
results = []

for path in sorted(glob.glob(os.path.join(TEST_DIR, "*", "*.*"))):
    # True label from folder name e.g. "side_02" → 2
    true_folder = os.path.basename(os.path.dirname(path))
    true_num    = int(true_folder.split("_")[1])

    img = cv2.imread(path, cv2.IMREAD_COLOR)          # 3-channel BGR
    if img is None:
        continue
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)        # BGR ➜ RGB
    img_resized = cv2.resize(img, IMG_SIZE)

    # Prepare for prediction  (match training pipeline!)
    x = preprocess_input(img_resized.astype("float32"))  # 0-255 → [-1,1]
    x = np.expand_dims(x, axis=0)                        # (1,256,256,3)

    # Predict
    preds  = model.predict(x, verbose=0)[0]           # e.g. [0.1, 0.7, …]
    picked = int(np.argmax(preds))                    # index 0–5
    prob   = preds[picked]

    # Class number (1–6)
    cls_num   = picked + 1
    score_str = f"{prob:.2f}".replace('.', '_')       # e.g. "0_74"

    # Determine correctness
    is_correct = (cls_num == true_num)
    results.append(is_correct)

    # 4) Annotate overlay
    out = img_resized.copy()                          # already RGB
    label_text = f"class_{cls_num:02d} ({prob:.2f})"
    if not is_correct:
        label_text += " incorrect"
    color = (0, 255, 0) if is_correct else (0, 0, 255)
    cv2.putText(
        out,
        label_text,
        (5, 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        color,
        1,
        cv2.LINE_AA
    )

    # 5) Save with new filename (optionally skip correct ones)
    if (is_correct and SAVE_CORRECT_IMGS) or not is_correct:
        orig_name = os.path.basename(path)
        prefix = "class" if is_correct else "incorrect"
        new_name = f"{prefix}_{cls_num:02d}_{score_str}_{orig_name}"
        out_path = os.path.join(OUTPUT_DIR, new_name)
        cv2.imwrite(out_path, out)
        print(f"[{prefix} {cls_num:02d} ({prob:.2f})] {path} → {new_name}")
    # else:
        # still print something brief so you know it was processed
        # print(f"[skip   {cls_num:02d} ({prob:.2f})] {path}")

# 4) Compute & print accuracy stats
total     = len(results)
correct   = sum(results)
incorrect = total - correct
accuracy  = correct / total if total else 0.0
std_dev   = float(np.std(results))  # bool → 0/1 gives sqrt(p*(1-p))

print("\n=== Summary ===")
print(f"Total images:    {total}")
print(f"Correct:         {correct}")
print(f"Incorrect:       {incorrect}")
print(f"Accuracy:        {accuracy:.3f}")
print(f"Std. deviation:  {std_dev:.3f}")
