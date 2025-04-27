import tensorflow as tf
import numpy as np
import cv2, glob, os

# 1) Config
MODEL_PATH  = "dice_cnn.h5"
TEST_DIR    = "tests/"
OUTPUT_DIR  = "output_cnn/"
IMG_SIZE    = (256, 256)
CLASS_NAMES = ["side_01","side_02","side_03","side_04","side_05","side_06"]

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 2) Load model
model = tf.keras.models.load_model(MODEL_PATH)

# 3) Process test images
for path in sorted(glob.glob(os.path.join(TEST_DIR, "*.*"))):
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        continue

    # preprocess
    img_resized = cv2.resize(img, IMG_SIZE)
    x = img_resized.astype("float32") / 255.0
    x = np.expand_dims(x, axis=(0,-1))  # shape (1,256,256,1)

    # predict
    preds = model.predict(x)[0]              # shape (6,)
    for cls, p in zip(CLASS_NAMES, preds):
        print(f"{cls}: {p:.3f}")
    picked = np.argmax(preds)
    print("→ picked", CLASS_NAMES[picked])

    idx  = picked
    prob = preds[idx]

    label = CLASS_NAMES[idx] if prob > 0.5 else "unrecognized"

    # annotate (draw small text)
    out = cv2.cvtColor(img_resized, cv2.COLOR_GRAY2BGR)
    text = f"{label} ({prob:.2f})"
    cv2.putText(out, text, (5,20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)

    # save and report
    cv2.imwrite(os.path.join(OUTPUT_DIR, os.path.basename(path)), out)
    print(f"[{text}] {path}")
