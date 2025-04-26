#!/usr/bin/env python3
# precompute_templates.py
# —————————————————————————————————————————
# Reads all template images under templates/side_XX/,
# generates 10°-increment rotations, and pickles each side
# into its own file: side_01.pkl, side_02.pkl, … side_06.pkl

import cv2
import glob
import os
import pickle

# CONFIG
TEMPLATE_ROOT = "templates"     # contains side_01, side_02, … side_06
ANGLE_STEP    = 10              # degrees between rotations
OUTPUT_DIR    = "template_data" # where to write individual .pkl files

# ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

print(f"🔄 Precompute templates: will rotate every {ANGLE_STEP}° and save per-side .pkl files\n")

# for each side folder, e.g. templates/side_01
for side_dir in sorted(glob.glob(os.path.join(TEMPLATE_ROOT, "side_*"))):
    label = os.path.basename(side_dir)   # "side_01", …
    base_paths = sorted(glob.glob(os.path.join(side_dir, "*.*")))

    # confirm with user
    resp = input(f"Process templates for '{label}'? [Y/n]: ").strip().lower()
    if resp in ("n", "no"):
        print(f"⏭ Skipping {label}\n")
        continue

    print(f"\n✅ Processing '{label}': found {len(base_paths)} base image(s):")
    for p in base_paths:
        print(f"   • {p}")

    rotations = []
    angles = list(range(0, 360, ANGLE_STEP))
    print(f"\n➡ Generating {len(angles)} rotations per template:")

    for img_path in base_paths:
        base = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if base is None:
            print(f"   [!] Could not read '{img_path}', skipping")
            continue

        h, w = base.shape
        cx, cy = w // 2, h // 2
        print(f"   – Rotating '{os.path.basename(img_path)}':")

        for angle in angles:
            M = cv2.getRotationMatrix2D((cx, cy), angle, 1.0)
            rot = cv2.warpAffine(base, M, (w, h))
            rotations.append(rot)
        print(f"       generated {len(angles)} rotations")

    print(f"\n🔢 Total rotations for {label}: {len(rotations)}")

    # write out this side's rotations
    out_path = os.path.join(OUTPUT_DIR, f"{label}.pkl")
    with open(out_path, "wb") as f:
        pickle.dump(rotations, f, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"💾 Saved {len(rotations)} templates to '{out_path}'\n")

print("🎉 Precomputation complete!")  
