"""Live side-by-side comparison of the FP32 and INT8 weed detectors.

Each frame from the camera (or a video) goes through both models one after the
other, so both panels see the identical image. Each panel shows that model's
detections, latency breakdown, FPS, detection count and file size; the bar at
the bottom shows the INT8 speed-up and how often INT8 agrees with FP32.

Keys: q / Esc quit, p pause, s save a screenshot to optimization_research/results/.

Usage:
    python optimization_research/compare_live.py                       # webcam 0
    python optimization_research/compare_live.py --source demo_inputs/test_video.mp4 --loop
    python optimization_research/compare_live.py --fp32 models/hf/best.pt   # vs the PyTorch path
    python optimization_research/compare_live.py --source demo_inputs/test_video.mp4 \
        --no-display --max-frames 300                                  # headless benchmark
"""

from __future__ import annotations

import argparse
import csv
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"


@dataclass
class Runner:
    label: str
    path: Path
    model: YOLO = field(init=False)
    totals_ms: deque = field(default_factory=lambda: deque(maxlen=30))
    all_infer_ms: list = field(default_factory=list)
    all_total_ms: list = field(default_factory=list)
    all_dets: list = field(default_factory=list)

    def __post_init__(self):
        self.model = YOLO(str(self.path), task="detect")
        self.size_mb = self.path.stat().st_size / 1e6

    def __call__(self, frame, conf, iou, imgsz):
        t0 = time.perf_counter()
        result = self.model.predict(frame, conf=conf, iou=iou, imgsz=imgsz, verbose=False)[0]
        total_ms = (time.perf_counter() - t0) * 1000
        self.totals_ms.append(total_ms)
        self.all_total_ms.append(total_ms)
        self.all_infer_ms.append(result.speed["inference"])
        self.all_dets.append(len(result.boxes))
        return result, total_ms

    @property
    def fps(self):
        return 1000 / np.mean(self.totals_ms) if self.totals_ms else 0.0


def box_iou(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Pairwise IoU between xyxy boxes a (N,4) and b (M,4)."""
    tl = np.maximum(a[:, None, :2], b[None, :, :2])
    br = np.minimum(a[:, None, 2:], b[None, :, 2:])
    inter = np.prod(np.clip(br - tl, 0, None), axis=2)
    area_a = np.prod(a[:, 2:] - a[:, :2], axis=1)
    area_b = np.prod(b[:, 2:] - b[:, :2], axis=1)
    return inter / (area_a[:, None] + area_b[None, :] - inter + 1e-9)


def agreement(ref, other, iou_thr=0.5) -> float:
    """Share of detections that match (same class, IoU >= iou_thr) between the two models."""
    n_ref, n_other = len(ref.boxes), len(other.boxes)
    if n_ref == 0 and n_other == 0:
        return 1.0
    if n_ref == 0 or n_other == 0:
        return 0.0
    ious = box_iou(ref.boxes.xyxy.cpu().numpy(), other.boxes.xyxy.cpu().numpy())
    same_cls = ref.boxes.cls.cpu().numpy()[:, None] == other.boxes.cls.cpu().numpy()[None, :]
    ious = np.where(same_cls, ious, 0)
    matched = 0
    while ious.size and ious.max() >= iou_thr:  # greedy one-to-one matching
        i, j = np.unravel_index(ious.argmax(), ious.shape)
        matched += 1
        ious[i, :] = 0
        ious[:, j] = 0
    return matched / max(n_ref, n_other)


def draw_panel(runner: Runner, result, total_ms: float, width: int) -> np.ndarray:
    panel = result.plot(line_width=2)
    scale = width / panel.shape[1]
    panel = cv2.resize(panel, (width, int(panel.shape[0] * scale)))
    sp = result.speed
    lines = [
        runner.label,
        f"infer {sp['inference']:.1f} ms | total {total_ms:.1f} ms",
        f"pre {sp['preprocess']:.1f} / post {sp['postprocess']:.1f} ms",
        f"FPS {runner.fps:.1f} | dets {len(result.boxes)} | {runner.size_mb:.1f} MB",
    ]
    cv2.rectangle(panel, (0, 0), (width, 22 + 24 * len(lines)), (0, 0, 0), -1)
    for k, text in enumerate(lines):
        color = (0, 255, 255) if k == 0 else (255, 255, 255)
        cv2.putText(panel, text, (10, 26 + 24 * k), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return panel


def draw_footer(width: int, speedup: float, agree: float, frame_idx: int) -> np.ndarray:
    bar = np.zeros((40, width, 3), dtype=np.uint8)
    text = (f"INT8 speed-up (inference, last 30): {speedup:.2f}x   |   "
            f"FP32/INT8 detection agreement: {agree * 100:.0f}%   |   frame {frame_idx}")
    cv2.putText(bar, text, (10, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    return bar


def open_source(source: str):
    cap = cv2.VideoCapture(int(source) if source.isdigit() else source)
    if source.isdigit():
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    if not cap.isOpened():
        raise SystemExit(f"Could not open source {source}")
    return cap


def summarize(fp32: Runner, int8: Runner, agreements: list[float]):
    def stats(values):
        v = np.asarray(values[5:] or values)  # drop warm-up frames
        return f"mean {v.mean():6.1f}  p50 {np.percentile(v, 50):6.1f}  p95 {np.percentile(v, 95):6.1f}"

    print(f"\nFrames compared: {len(agreements)}")
    for r in (fp32, int8):
        print(f"{r.label:<28} size {r.size_mb:5.1f} MB")
        print(f"  inference ms  {stats(r.all_infer_ms)}")
        print(f"  end-to-end ms {stats(r.all_total_ms)}")
        print(f"  mean detections/frame {np.mean(r.all_dets):.2f}")
    speedup = np.mean(fp32.all_infer_ms[5:]) / np.mean(int8.all_infer_ms[5:])
    print(f"INT8 inference speed-up: {speedup:.2f}x")
    print(f"Mean FP32/INT8 detection agreement: {np.mean(agreements) * 100:.1f}%")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", default="0", help="Camera index or video path")
    p.add_argument("--fp32", default=str(HERE / "models/best_fp32.onnx"))
    p.add_argument("--int8", default=str(HERE / "models/best_int8.onnx"))
    p.add_argument("--conf", type=float, default=0.55)
    p.add_argument("--int8-conf", type=float, default=None,
                   help="Separate confidence threshold for INT8 (defaults to --conf)")
    p.add_argument("--iou", type=float, default=0.45)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--panel-width", type=int, default=640)
    p.add_argument("--loop", action="store_true", help="Restart the video when it ends")
    p.add_argument("--max-frames", type=int, default=0, help="Stop after N frames (0 = no limit)")
    p.add_argument("--no-display", action="store_true", help="Headless benchmark, no window")
    args = p.parse_args()

    for path in (args.fp32, args.int8):
        if not Path(path).exists():
            raise SystemExit(f"{path} not found. Run optimization_research/quantize_int8.py first.")

    fp32_label = "FP32 (PyTorch)" if args.fp32.endswith(".pt") else "FP32 (ONNX Runtime)"
    fp32 = Runner(fp32_label, Path(args.fp32))
    int8_conf = args.conf if args.int8_conf is None else args.int8_conf
    int8 = Runner(f"INT8 (ONNX Runtime) conf {int8_conf:.2f}", Path(args.int8))

    RESULTS.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    log_file = open(RESULTS / f"compare_{stamp}.csv", "w", newline="")
    log = csv.writer(log_file)
    log.writerow(["frame", "fp32_infer_ms", "fp32_total_ms", "fp32_dets",
                  "int8_infer_ms", "int8_total_ms", "int8_dets", "agreement"])

    cap = open_source(args.source)
    agreements: list[float] = []
    recent_agree = deque(maxlen=30)
    frame_idx, paused, view = 0, False, None
    try:
        while True:
            if not paused:
                ok, frame = cap.read()
                if not ok:
                    if args.loop and not args.source.isdigit():
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    break
                frame_idx += 1

                r32, t32 = fp32(frame, args.conf, args.iou, args.imgsz)
                r8, t8 = int8(frame, int8_conf, args.iou, args.imgsz)
                agree = agreement(r32, r8)
                agreements.append(agree)
                recent_agree.append(agree)
                log.writerow([frame_idx, f"{r32.speed['inference']:.2f}", f"{t32:.2f}", len(r32.boxes),
                              f"{r8.speed['inference']:.2f}", f"{t8:.2f}", len(r8.boxes), f"{agree:.3f}"])

                if not args.no_display:
                    left = draw_panel(fp32, r32, t32, args.panel_width)
                    right = draw_panel(int8, r8, t8, args.panel_width)
                    speedup = np.mean(fp32.all_infer_ms[-30:]) / np.mean(int8.all_infer_ms[-30:])
                    footer = draw_footer(left.shape[1] * 2, speedup, np.mean(recent_agree), frame_idx)
                    view = np.vstack([np.hstack([left, right]), footer])

                if args.max_frames and frame_idx >= args.max_frames:
                    break

            if args.no_display:
                continue
            cv2.imshow("FP32 vs INT8 - weed detector", view)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("p"):
                paused = not paused
            if key == ord("s"):
                shot = RESULTS / f"screenshot_{time.strftime('%Y%m%d_%H%M%S')}.png"
                cv2.imwrite(str(shot), view)
                print(f"Saved {shot}")
    finally:
        cap.release()
        log_file.close()
        cv2.destroyAllWindows()

    if agreements:
        summarize(fp32, int8, agreements)
        print(f"Per-frame log: {RESULTS / f'compare_{stamp}.csv'}")


if __name__ == "__main__":
    main()
