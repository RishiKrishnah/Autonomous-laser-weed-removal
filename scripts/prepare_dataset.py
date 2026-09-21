from __future__ import annotations

import argparse
import json
import random
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def normalize_name(value: str) -> str:
    value = value.strip().lower()
    value = value.replace("_", " ").replace("-", " ")
    return " ".join(value.split())


def read_classes(path: Path) -> list[str]:
    return [x.strip() for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def find_image(source: Path, stem: str) -> Path | None:
    for p in source.rglob("*"):
        if p.suffix.lower() in IMAGE_EXTS and p.stem == stem:
            return p
    return None


def voc_to_yolo(xml_path: Path, class_map: dict[str, int]):
    root = ET.parse(xml_path).getroot()
    size = root.find("size")
    if size is None:
        return None
    w = float(size.findtext("width", "0"))
    h = float(size.findtext("height", "0"))
    if w <= 0 or h <= 0:
        return None

    rows = []
    for obj in root.findall("object"):
        name = obj.findtext("name", "").strip()
        normalized = normalize_name(name)
        if normalized not in class_map:
            continue
        class_id = class_map[normalized]
        box = obj.find("bndbox")
        if box is None:
            continue
        x1 = float(box.findtext("xmin", "0"))
        y1 = float(box.findtext("ymin", "0"))
        x2 = float(box.findtext("xmax", "0"))
        y2 = float(box.findtext("ymax", "0"))
        xc = ((x1 + x2) / 2) / w
        yc = ((y1 + y2) / 2) / h
        bw = (x2 - x1) / w
        bh = (y2 - y1) / h
        rows.append(f"{class_id} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")
    return rows


def convert_coco(json_path: Path, class_map: dict[str, int]):
    data = json.loads(json_path.read_text(encoding="utf-8"))
    images = {x["id"]: x for x in data.get("images", [])}
    cats = {x["id"]: x["name"] for x in data.get("categories", [])}
    anns = {}
    for ann in data.get("annotations", []):
        anns.setdefault(ann["image_id"], []).append(ann)

    output = []
    for image_id, image in images.items():
        rows = []
        w = float(image["width"])
        h = float(image["height"])
        for ann in anns.get(image_id, []):
            name = cats.get(ann["category_id"])
            normalized = normalize_name(name or "")
            if normalized not in class_map:
                continue
            class_id = class_map[normalized]
            x, y, bw, bh = ann["bbox"]
            xc = (x + bw / 2) / w
            yc = (y + bh / 2) / h
            rows.append(f"{class_id} {xc:.6f} {yc:.6f} {bw/w:.6f} {bh/h:.6f}")
        output.append((image["file_name"], rows))
    return output


def is_yolo_file(path: Path) -> bool:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return False
    if not lines:
        return False
    for line in lines[:10]:
        parts = line.split()
        if len(parts) != 5:
            return False
        try:
            int(parts[0])
            for x in parts[1:]:
                float(x)
        except ValueError:
            return False
    return True


def main():
    p = argparse.ArgumentParser(description="Prepare MH-Weed16/common annotation formats for YOLO.")
    p.add_argument("--source", required=True)
    p.add_argument("--output", default="data/yolo")
    p.add_argument("--classes", default="configs/classes.txt")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--val", type=float, default=0.15)
    p.add_argument("--test", type=float, default=0.15)
    args = p.parse_args()

    source = Path(args.source).resolve()
    output = Path(args.output)
    classes = read_classes(Path(args.classes))
    class_map = {normalize_name(name): i for i, name in enumerate(classes)}

    for split in ["train", "val", "test"]:
        (output / "images" / split).mkdir(parents=True, exist_ok=True)
        (output / "labels" / split).mkdir(parents=True, exist_ok=True)

    pairs = []

    # Prefer explicit Pascal VOC XML files.
    for xml in source.rglob("*.xml"):
        rows = voc_to_yolo(xml, class_map)
        if rows is None:
            continue
        image = find_image(source, xml.stem)
        if image:
            pairs.append((image, rows))

    # Then JSON files containing COCO annotations.
    if not pairs:
        for js in source.rglob("*.json"):
            try:
                converted = convert_coco(js, class_map)
            except Exception:
                continue
            base = js.parent
            for name, rows in converted:
                image = base / name
                if not image.exists():
                    image = find_image(source, Path(name).stem)
                if image and rows:
                    pairs.append((image, rows))

    # Finally, accept YOLO txt/image pairs.
    if not pairs:
        for txt in source.rglob("*.txt"):
            if txt.name == Path(args.classes).name:
                continue
            if not is_yolo_file(txt):
                continue
            image = find_image(source, txt.stem)
            if image:
                rows = txt.read_text(encoding="utf-8").splitlines()
                pairs.append((image, rows))

    # Deduplicate by image path.
    unique = {}
    for image, rows in pairs:
        unique[str(image.resolve())] = (image, rows)
    pairs = list(unique.values())

    if not pairs:
        raise SystemExit(
            "No compatible annotated image pairs found. Inspect the source release and "
            "use its annotation export, or adapt this script to the exact directory layout."
        )

    random.Random(args.seed).shuffle(pairs)
    n = len(pairs)
    n_test = int(n * args.test)
    n_val = int(n * args.val)
    test_pairs = pairs[:n_test]
    val_pairs = pairs[n_test:n_test+n_val]
    train_pairs = pairs[n_test+n_val:]

    for split, items in [("train", train_pairs), ("val", val_pairs), ("test", test_pairs)]:
        for image, rows in items:
            dst_image = output / "images" / split / image.name
            dst_label = output / "labels" / split / f"{image.stem}.txt"
            shutil.copy2(image, dst_image)
            dst_label.write_text("\n".join(rows) + "\n", encoding="utf-8")

    yaml_lines = [
        f"path: {output.resolve().as_posix()}",
        "train: images/train",
        "val: images/val",
        "test: images/test",
        f"nc: {len(classes)}",
        "names:",
    ]
    yaml_lines.extend([f"  {i}: {name}" for i, name in enumerate(classes)])
    (output / "dataset.yaml").write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")

    print(f"Prepared {len(pairs)} annotated images.")
    print(f"train={len(train_pairs)}, val={len(val_pairs)}, test={len(test_pairs)}")
    print(f"Dataset YAML: {output / 'dataset.yaml'}")


if __name__ == "__main__":
    main()
