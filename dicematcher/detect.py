#!/usr/bin/env python3
# detect_dice_coarse_fine_resized.py
# —————————————————————————————————————————
# Two-stage matcher with incoming test images resized to 256×256.

import cv2, glob, os, pickle

# CONFIG
TEMPLATE_DIR = "template_data"    # side_XX.pkl files, each template at 256×256
TEST_DIR     = "tests/"           # your query images
OUTPUT_DIR   = "output_cf_resized/"
THRESHOLD    = 0.7
COARSE_STEP  = 5                 # coarse angular step
FINE_RANGE   = 0.1               # ± range for fine pass
ANGLE_STEP   = 10                 # your template increment
TARGET_SIZE  = (256, 256)         # match the size of your precomputed templates

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1) Load per-side templates
template_data = {}
angles       = list(range(0, 360, ANGLE_STEP))
for pkl_path in sorted(glob.glob(os.path.join(TEMPLATE_DIR, "side_*.pkl"))):
    side = os.path.splitext(os.path.basename(pkl_path))[0]  # e.g. "side_02"
    with open(pkl_path, "rb") as f:
        template_data[side] = pickle.load(f)
    print(f"[+] {side}: {len(template_data[side])} templates loaded")

# Precompute which indices correspond to the coarse angles
coarse_idxs = [i for i, a in enumerate(angles) if a % COARSE_STEP == 0]

# 2) Process each test image
for img_path in sorted(glob.glob(os.path.join(TEST_DIR, "*.*"))):
    img = cv2.imread(img_path)
    if img is None:
        print(f"[!] Skipping unreadable: {img_path}")
        continue

    # → Resize to 256×256 for matching
    img_resized = cv2.resize(img, TARGET_SIZE, interpolation=cv2.INTER_AREA)
    img_gray    = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)

    # ——— COARSE PASS ———
    best_side  = None
    best_ang   = None
    best_score = -1.0

    for side, tmpls in template_data.items():
        for idx in coarse_idxs:
            res = cv2.matchTemplate(img_gray, tmpls[idx], cv2.TM_CCOEFF_NORMED)
            _, score, _, _ = cv2.minMaxLoc(res)
            if score > best_score:
                best_score = score
                best_side  = side
                best_ang   = angles[idx]

    # ——— EARLY EXIT ———
    if best_score >= 0.95:
        final_score = best_score
        final_side  = best_side
        final_ang   = best_ang
        # get location for annotation
        _, _, _, loc = cv2.minMaxLoc(
            cv2.matchTemplate(
                img_gray, 
                template_data[best_side][angles.index(best_ang)], 
                cv2.TM_CCOEFF_NORMED
            )
        )
        final_loc = loc
    else:
        # ——— FINE PASS ———
        final_score = -1.0
        final_side  = best_side
        final_ang   = None
        final_loc   = (0, 0)

        def within(a, center, rng):
            d = abs((a - center + 180) % 360 - 180)
            return d <= rng

        for idx, ang in enumerate(angles):
            if not within(ang, best_ang, FINE_RANGE):
                continue
            res = cv2.matchTemplate(img_gray, template_data[best_side][idx], 
                                    cv2.TM_CCOEFF_NORMED)
            _, score, _, loc = cv2.minMaxLoc(res)
            if score > final_score:
                final_score = score
                final_ang   = ang
                final_loc   = loc

    # ——— ANNOTATION ———
    x, y = final_loc
    h, w = TARGET_SIZE  # templates are 256×256
    color = (0,255,0) if final_score >= THRESHOLD else (0,0,255)
    cv2.rectangle(img_resized, (x, y), (x + w, y + h), color, 2)

    if final_score >= THRESHOLD:
        label = f"{final_side}@{final_ang}° ({final_score:.2f})"
    else:
        label = f"unrecognized ({final_score:.2f})"

    cv2.putText(img_resized, label, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)

    # 3) Save and report
    out_path = os.path.join(OUTPUT_DIR, os.path.basename(img_path))
    cv2.imwrite(out_path, img_resized)
    print(f"[{label}] {img_path} → saved to {out_path}")
