from __future__ import annotations

import argparse

from ultralytics import YOLO


def main():

    parser = argparse.ArgumentParser(description="Evaluate trained weed detector")

    parser.add_argument(
        "--weights",
        required=True,
    )

    parser.add_argument(
        "--data",
        required=True,
    )

    parser.add_argument(
        "--device",
        default="0",
    )

    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
    )

    args = parser.parse_args()

    model = YOLO(args.weights)

    metrics = model.val(
        data=args.data,
        split="test",
        imgsz=args.imgsz,
        device=args.device,
        plots=True,
        verbose=True,
    )

    print()
    print("========== FINAL TEST RESULTS ==========")

    print(f"mAP@0.50: {metrics.box.map50:.4f}")

    print(f"mAP@0.50:0.95: {metrics.box.map:.4f}")

    print(f"Precision: {metrics.box.mp:.4f}")

    print(f"Recall: {metrics.box.mr:.4f}")


if __name__ == "__main__":
    main()
