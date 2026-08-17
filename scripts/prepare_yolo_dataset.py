"""Convert the raw Airbus Aircraft Detection annotations.csv (polygon per
aircraft, in pixel coordinates) into a YOLO-format dataset: one .txt label
file per image with `class_id cx cy w h` (all normalized 0-1), split into
train/val/test image folders, plus a data.yaml Ultralytics can train on.

Usage:
    uv run python scripts/prepare_yolo_dataset.py
"""

from __future__ import annotations

import ast
import csv
import random
import shutil
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw"
IMAGES_DIR = RAW_DIR / "images"
ANNOTATIONS_CSV = RAW_DIR / "annotations.csv"
OUTPUT_DIR = REPO_ROOT / "data" / "yolo"

CLASSES = ["Airplane"]
# Truncated_airplane is the same physical object as Airplane, just cropped by
# the satellite tile boundary - not a distinct detection target for our use
# case (positioning/collision), and too rare (9 test instances) to train as
# its own class. Both source labels collapse onto the single "Airplane" class.
CLASS_TO_ID = {"Airplane": 0, "Truncated_airplane": 0}

TRAIN_FRAC = 0.7
VAL_FRAC = 0.15
# remaining ~0.15 goes to test
SEED = 42


def load_annotations() -> dict[str, list[tuple[int, tuple[float, float, float, float]]]]:
    """Returns {image_id: [(class_id, (cx, cy, w, h) in pixels), ...]}."""
    per_image: dict[str, list[tuple[int, tuple[float, float, float, float]]]] = {}

    with ANNOTATIONS_CSV.open() as f:
        for row in csv.DictReader(f):
            image_id = row["image_id"]
            class_name = row["class"]
            if class_name not in CLASS_TO_ID:
                continue

            points = ast.literal_eval(row["geometry"])
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            x_min, x_max = min(xs), max(xs)
            y_min, y_max = min(ys), max(ys)

            cx = (x_min + x_max) / 2
            cy = (y_min + y_max) / 2
            w = x_max - x_min
            h = y_max - y_min

            per_image.setdefault(image_id, []).append((CLASS_TO_ID[class_name], (cx, cy, w, h)))

    return per_image


def split_image_ids(image_ids: list[str]) -> dict[str, list[str]]:
    rng = random.Random(SEED)
    shuffled = list(image_ids)
    rng.shuffle(shuffled)

    n = len(shuffled)
    n_train = int(n * TRAIN_FRAC)
    n_val = int(n * VAL_FRAC)

    return {
        "train": shuffled[:n_train],
        "val": shuffled[n_train : n_train + n_val],
        "test": shuffled[n_train + n_val :],
    }


def write_split(split_name: str, image_ids: list[str], annotations: dict) -> None:
    images_out = OUTPUT_DIR / "images" / split_name
    labels_out = OUTPUT_DIR / "labels" / split_name
    images_out.mkdir(parents=True, exist_ok=True)
    labels_out.mkdir(parents=True, exist_ok=True)

    for image_id in image_ids:
        src_image = IMAGES_DIR / image_id
        if not src_image.exists():
            print(f"WARNING: missing image {image_id}, skipping")
            continue

        shutil.copy2(src_image, images_out / image_id)

        with Image.open(src_image) as im:
            img_w, img_h = im.size

        label_lines = []
        for class_id, (cx, cy, w, h) in annotations.get(image_id, []):
            label_lines.append(
                f"{class_id} {cx / img_w:.6f} {cy / img_h:.6f} {w / img_w:.6f} {h / img_h:.6f}"
            )

        label_path = labels_out / (Path(image_id).stem + ".txt")
        label_path.write_text("\n".join(label_lines) + ("\n" if label_lines else ""))


def write_data_yaml() -> None:
    content = (
        f"path: {OUTPUT_DIR}\n"
        "train: images/train\n"
        "val: images/val\n"
        "test: images/test\n"
        f"nc: {len(CLASSES)}\n"
        f"names: {CLASSES}\n"
    )
    (OUTPUT_DIR / "data.yaml").write_text(content)


def main() -> None:
    annotations = load_annotations()
    image_ids = sorted(annotations.keys())
    print(f"Found {len(image_ids)} annotated images, {sum(len(v) for v in annotations.values())} instances")

    splits = split_image_ids(image_ids)
    for split_name, ids in splits.items():
        print(f"  {split_name}: {len(ids)} images")
        write_split(split_name, ids, annotations)

    write_data_yaml()
    print(f"Dataset written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
