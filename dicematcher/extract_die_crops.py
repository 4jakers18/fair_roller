#!/usr/bin/env python3
import os, json, cv2
from glob import glob

# ─── USER CONFIG ───────────────────────────────────────────────────────────────
DATA_ROOT      = "big_dataset"       # contains 'train', 'valid', 'test' subfolders
SPLITS         = ["train", "valid", "test"]
NEW_DATA_ROOT  = "big_dataset_cropped"   # where to write your cropped classification set
IMG_SIZE       = (256, 256)      # match your CNN input
# map COCO category_id → folder name
CLASS_MAP = {i: f"side_{i:02d}" for i in range(1, 7)}
# ────────────────────────────────────────────────────────────────────────────────

# make sure output dirs exist
for split in SPLITS:
    for cls in CLASS_MAP.values():
        os.makedirs(os.path.join(NEW_DATA_ROOT, split, cls), exist_ok=True)

for split in SPLITS:
    split_dir = os.path.join(DATA_ROOT, split)
    # find the one JSON file
    json_paths = glob(os.path.join(split_dir, "*.json"))
    if not json_paths:
        print(f"[!] No .json in {split_dir}, skipping")
        continue
    ann_path = json_paths[0]
    print(f"→ Processing {split}: reading {os.path.basename(ann_path)}")

    coco = json.load(open(ann_path, "r"))
    # images may live in split/images/ or directly in split/
    img_root = os.path.join(split_dir, "images")
    if not os.path.isdir(img_root):
        img_root = split_dir

    # build id → filename map
    id2file = {img["id"]: img["file_name"] for img in coco["images"]}

    for ann in coco["annotations"]:
        cid = ann["category_id"]
        # skip background or other categories
        if cid not in CLASS_MAP:
            continue

        cls_name = CLASS_MAP[cid]
        img_id   = ann["image_id"]
        fname    = id2file.get(img_id)
        if not fname:
            print(f"  [!] Missing file for image_id {img_id}")
            continue

        img_path = os.path.join(img_root, fname)
        img = cv2.imread(img_path)
        if img is None:
            print(f"  [!] Could not load {img_path}")
            continue

        x, y, w, h = map(int, ann["bbox"])
        crop = img[y:y+h, x:x+w]
        if crop.size == 0:
            print(f"  [!] Empty crop for ann {ann['id']}, skipping")
            continue

        # resize & save
        out = cv2.resize(crop, IMG_SIZE, interpolation=cv2.INTER_AREA)
        base = os.path.splitext(fname)[0]
        out_name = f"{base}_ann{ann['id']}.jpg"
        out_path = os.path.join(NEW_DATA_ROOT, split, cls_name, out_name)
        cv2.imwrite(out_path, out)

    print(f"  ✅ Saved crops for split '{split}' into '{NEW_DATA_ROOT}/{split}/'")

print("🎉 All done!")
