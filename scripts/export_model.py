from __future__ import annotations

import argparse
from ultralytics import YOLO


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--weights", required=True)
    p.add_argument("--format", default="onnx", choices=["onnx", "openvino", "engine"])
    p.add_argument("--imgsz", type=int, default=640)
    args = p.parse_args()

    model = YOLO(args.weights)
    path = model.export(format=args.format, imgsz=args.imgsz)
    print(f"Exported model: {path}")


if __name__ == "__main__":
    main()
