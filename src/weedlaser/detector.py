from __future__ import annotations

from pathlib import Path

from ultralytics import YOLO

from .localization import Detection


class WeedDetector:
    def __init__(self, weights: str | Path, confidence: float = 0.55, iou: float = 0.45, imgsz: int = 640):
        self.model = YOLO(str(weights))
        self.confidence = confidence
        self.iou = iou
        self.imgsz = imgsz

    def predict(self, frame):
        results = self.model.predict(
            source=frame,
            conf=self.confidence,
            iou=self.iou,
            imgsz=self.imgsz,
            verbose=False,
        )
        result = results[0]
        names = result.names
        detections = []

        if result.boxes is None:
            return detections

        for box in result.boxes:
            xyxy = box.xyxy[0].tolist()
            x1, y1, x2, y2 = map(int, xyxy)
            cls = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            detections.append(
                Detection(
                    class_id=cls,
                    class_name=str(names.get(cls, cls)),
                    confidence=conf,
                    bbox=(x1, y1, x2, y2),
                )
            )
        return detections
