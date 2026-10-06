from __future__ import annotations

import argparse

from ultralytics import YOLO


def main():

    parser = argparse.ArgumentParser(description="Train YOLO weed detector")

    parser.add_argument(
        "--data",
        required=True,
    )

    parser.add_argument(
        "--model",
        default="yolov8n.pt",
    )

    parser.add_argument(
        "--epochs",
        type=int,
        default=100,
    )

    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
    )

    parser.add_argument(
        "--batch",
        type=int,
        default=16,
    )

    parser.add_argument(
        "--device",
        default="0",
    )

    parser.add_argument(
        "--project",
        default="runs",
    )

    parser.add_argument(
        "--name",
        default="weed_detector_final",
    )

    args = parser.parse_args()

    model = YOLO(args.model)

    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=args.project,
        name=args.name,
        pretrained=True,
        patience=20,
        workers=4,
        cos_lr=True,
        plots=True,
        verbose=True,
    )


if __name__ == "__main__":
    main()
