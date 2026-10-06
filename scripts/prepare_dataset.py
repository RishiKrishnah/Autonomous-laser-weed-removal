from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path


CLASS_NAMES = [
    "Kena",
    "Lavhala",
    "Lambs Quarter Plant",
    "Little Mallow",
    "Moti dudhi",
    "Obscure morning glory",
    "Asian pigeonwings",
    "Bilayat",
    "Choti dudhi",
    "Digitaria SP",
    "Gajar gavat",
    "Graceful sandmat",
    "Sicklepod",
    "Harali",
    "Dwarf cassia",
]


def validate_yolo_label(
    label_path: Path,
) -> None:

    for line_number, line in enumerate(
        label_path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = line.strip()

        if not line:
            continue

        parts = line.split()

        if len(parts) != 5:
            raise ValueError(f"Invalid annotation in {label_path} line {line_number}: {line}")

        try:
            class_id = int(parts[0])
        except ValueError as exc:
            raise ValueError(f"Invalid class ID in {label_path} line {line_number}") from exc

        if not (0 <= class_id < len(CLASS_NAMES)):
            raise ValueError(f"Invalid class ID {class_id} in {label_path}")

        values = [float(value) for value in parts[1:]]

        if not all(0.0 <= value <= 1.0 for value in values):
            raise ValueError(f"Coordinates outside [0,1] in {label_path}")


def main():

    parser = argparse.ArgumentParser(
        description=("Prepare the 15-class MH-Weed16 subset for YOLO training.")
    )

    parser.add_argument(
        "--dataset-root",
        required=True,
    )

    parser.add_argument(
        "--output",
        default="data/yolo",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )

    args = parser.parse_args()

    root = Path(args.dataset_root).resolve()

    output = Path(args.output).resolve()

    image_dir = (
        root / "Crop with Weeds" / "intel Real Sense Depth_Clicks" / "intel Real Sense Depth_Clicks"
    )

    label_dir = (
        root
        / "Crop with Weeds"
        / "intel Real Sense Depth_Annotations"
        / "intel Real Sense Depth_Annotations"
        / "YOLO_darknet"
    )

    if not image_dir.exists():
        raise FileNotFoundError(f"Image directory not found: {image_dir}")

    if not label_dir.exists():
        raise FileNotFoundError(f"Label directory not found: {label_dir}")

    labels = sorted(label_dir.glob("*.txt"))

    if not labels:
        raise RuntimeError("No YOLO annotation files found.")

    pairs = []

    for label in labels:
        image = image_dir / f"{label.stem}.jpeg"

        if not image.exists():
            raise RuntimeError(f"Missing image for label: {label.name}")

        validate_yolo_label(label)

        pairs.append((image, label))

    print(f"Found {len(pairs)} image/label pairs.")

    random.seed(args.seed)

    random.shuffle(pairs)

    total = len(pairs)

    train_end = int(total * 0.70)

    val_end = train_end + int(total * 0.15)

    splits = {
        "train": pairs[:train_end],
        "val": pairs[train_end:val_end],
        "test": pairs[val_end:],
    }

    if output.exists():
        print(f"Removing existing dataset: {output}")

        shutil.rmtree(output)

    for split in splits:
        (output / "images" / split).mkdir(
            parents=True,
            exist_ok=True,
        )

        (output / "labels" / split).mkdir(
            parents=True,
            exist_ok=True,
        )

    for split, split_pairs in splits.items():
        for image, label in split_pairs:
            shutil.copy2(
                image,
                output / "images" / split / image.name,
            )

            shutil.copy2(
                label,
                output / "labels" / split / label.name,
            )

    yaml_lines = [
        f"path: {output}",
        "train: images/train",
        "val: images/val",
        "test: images/test",
        "",
        f"nc: {len(CLASS_NAMES)}",
        "names:",
    ]

    for index, name in enumerate(CLASS_NAMES):
        yaml_lines.append(f"  {index}: '{name}'")

    (output / "dataset.yaml").write_text(
        "\n".join(yaml_lines) + "\n",
        encoding="utf-8",
    )

    print()
    print("Dataset prepared successfully.")

    print(f"Train: {len(splits['train'])}")

    print(f"Val:   {len(splits['val'])}")

    print(f"Test:  {len(splits['test'])}")

    print(f"Total: {total}")

    print(f"Output: {output}")

    print(f"Classes: {len(CLASS_NAMES)}")


if __name__ == "__main__":
    main()
