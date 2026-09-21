from __future__ import annotations

import argparse

from ultralytics import YOLO


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--weights", required=True)
    p.add_argument("--data", required=True)
    p.add_argument("--device", default="0")
    p.add_argument("--imgsz", type=int, default=640)
    args = p.parse_args()

    model = YOLO(args.weights)
    metrics = model.val(
        data=args.data,
        imgsz=args.imgsz,
        device=args.device,
        plots=True,
        verbose=True,
    )

    print("\n=== Detection metrics ===")
    print(f"mAP50:       {metrics.box.map50:.4f}")
    print(f"mAP50-95:    {metrics.box.map:.4f}")
    print(f"Precision:   {metrics.box.mp:.4f}")
    print(f"Recall:      {metrics.box.mr:.4f}")


if __name__ == "__main__":
    main()
