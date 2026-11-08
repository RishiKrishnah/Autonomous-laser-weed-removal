"""Build the FP32 and INT8 ONNX models used by compare_live.py.

Steps:
1. Export models/hf/best.pt (stored FP16, loaded as FP32) to an FP32 ONNX graph.
2. Run ONNX Runtime static post-training quantization (QDQ, per-channel INT8
   weights, symmetric INT8 activations, Conv layers only) calibrated on real
   frames from a video or image folder.

The YOLOv8 detection-head post-processing (DFL softmax, box decode, the final
Concat that mixes 0-640 px box coords with 0-1 class scores) is kept in FP32,
because a single INT8 scale cannot represent both ranges.

Usage:
    python optimization_research/quantize_int8.py
    python optimization_research/quantize_int8.py --calib path/to/val/images --num-calib 200
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import cv2
import numpy as np
import onnx
from onnxruntime.quantization import (
    CalibrationDataReader,
    CalibrationMethod,
    QuantFormat,
    QuantType,
    quantize_static,
)
from onnxruntime.quantization.shape_inference import quant_pre_process
from ultralytics import YOLO
from ultralytics.data.augment import LetterBox

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}


def load_calibration_frames(source: Path, count: int) -> list[np.ndarray]:
    """Return up to `count` BGR frames, evenly sampled from a video or image folder."""
    if source.is_dir():
        paths = sorted(p for p in source.rglob("*") if p.suffix.lower() in IMAGE_EXTS)
        if not paths:
            raise SystemExit(f"No images found in {source}")
        step = max(1, len(paths) // count)
        return [cv2.imread(str(p)) for p in paths[::step][:count]]

    cap = cv2.VideoCapture(str(source))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total <= 0:
        raise SystemExit(f"Could not read video {source}")
    frames = []
    for idx in np.linspace(0, total - 1, num=min(count, total), dtype=int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, frame = cap.read()
        if ok:
            frames.append(frame)
    cap.release()
    return frames


class YoloCalibrationReader(CalibrationDataReader):
    """Feeds frames preprocessed exactly like Ultralytics predict (letterbox, RGB, /255)."""

    def __init__(self, frames: list[np.ndarray], input_name: str, imgsz: int):
        letterbox = LetterBox(new_shape=(imgsz, imgsz), auto=False)
        self.batches = []
        for frame in frames:
            img = letterbox(image=frame)[..., ::-1]  # BGR -> RGB
            img = np.ascontiguousarray(img.transpose(2, 0, 1), dtype=np.float32) / 255.0
            self.batches.append({input_name: img[None]})
        self.iterator = iter(self.batches)

    def get_next(self):
        return next(self.iterator, None)

    def rewind(self):
        self.iterator = iter(self.batches)


def head_postprocess_nodes(model: onnx.ModelProto) -> list[str]:
    """Nodes of the Detect head (model.22) that are not part of its conv branches."""
    return [
        n.name
        for n in model.graph.node
        if "/model.22/" in n.name and "/cv2." not in n.name and "/cv3." not in n.name
    ]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--weights", default=str(ROOT / "models/hf/best.pt"))
    p.add_argument("--calib", default=str(ROOT / "demo_inputs/test_video.mp4"),
                   help="Video file or folder of images used for INT8 calibration")
    p.add_argument("--num-calib", type=int, default=120)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--method", default="minmax", choices=["minmax", "percentile", "entropy"])
    p.add_argument("--out", default=str(HERE / "models"))
    args = p.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    fp32_path = out_dir / "best_fp32.onnx"
    prep_path = out_dir / "best_fp32_prep.onnx"
    int8_path = out_dir / "best_int8.onnx"

    # 1. FP32 ONNX export. Export into out_dir so models/hf stays untouched.
    work_pt = out_dir / "best.pt"
    shutil.copy2(args.weights, work_pt)
    exported = YOLO(str(work_pt)).export(format="onnx", imgsz=args.imgsz, simplify=True)
    Path(exported).replace(fp32_path)
    work_pt.unlink()
    print(f"FP32 ONNX: {fp32_path} ({fp32_path.stat().st_size / 1e6:.1f} MB)")

    # 2. INT8 static quantization.
    quant_pre_process(str(fp32_path), str(prep_path), skip_symbolic_shape=True)
    fp32_model = onnx.load(str(fp32_path))
    input_name = fp32_model.graph.input[0].name
    excluded = head_postprocess_nodes(fp32_model)

    frames = load_calibration_frames(Path(args.calib), args.num_calib)
    print(f"Calibrating on {len(frames)} frames from {args.calib} ({args.method})")
    reader = YoloCalibrationReader(frames, input_name, args.imgsz)

    method = {
        "minmax": CalibrationMethod.MinMax,
        "percentile": CalibrationMethod.Percentile,
        "entropy": CalibrationMethod.Entropy,
    }[args.method]
    quantize_static(
        str(prep_path),
        str(int8_path),
        reader,
        quant_format=QuantFormat.QDQ,
        per_channel=True,
        weight_type=QuantType.QInt8,
        activation_type=QuantType.QInt8,
        calibrate_method=method,
        nodes_to_exclude=excluded,
        # Only Conv runs in INT8; SiLU (Sigmoid*Mul), Concat, Resize stay FP32.
        # Quantizing SiLU outputs cost a further ~5-10% of class confidence.
        op_types_to_quantize=["Conv"],
        extra_options={"ActivationSymmetric": True},
    )
    prep_path.unlink()

    # Ultralytics reads class names / stride / imgsz from ONNX metadata; carry it over.
    int8_model = onnx.load(str(int8_path))
    del int8_model.metadata_props[:]
    int8_model.metadata_props.extend(fp32_model.metadata_props)
    onnx.save(int8_model, str(int8_path))
    print(f"INT8 ONNX: {int8_path} ({int8_path.stat().st_size / 1e6:.1f} MB), "
          f"{len(excluded)} head post-processing nodes kept in FP32")


if __name__ == "__main__":
    main()
