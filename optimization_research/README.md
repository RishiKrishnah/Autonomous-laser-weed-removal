# Optimization Research: FP32 vs INT8

This folder looks at whether the weed detector (YOLOv8n, 15 MH-Weed16 classes)
can run in INT8 to get more FPS on the targeting loop without losing detections.
The production pipeline (`src/weedlaser/`) is not touched by anything here.

## 1. How the model is stored and run today

| Stage | Precision |
|---|---|
| `models/hf/best.pt` on disk | **FP16** weights (Ultralytics halves checkpoints on save), 5.9 MB, 3.01 M params |
| After `YOLO(best.pt)` loads it | **FP32** (`.float()` on load) |
| `WeedDetector.predict()` at runtime | **FP32 on CPU**: no `device=` or `half=` is passed, and on a Mac Ultralytics defaults to CPU, not MPS |
| `scripts/export_model.py` | **FP32** ONNX / OpenVINO / TensorRT (no `half` / `int8` flags) |

So FP32 is the baseline.

## 2. Contents

| File | Purpose |
|---|---|
| `quantize_int8.py` | Exports `best.pt` to `models/best_fp32.onnx`, then builds `models/best_int8.onnx` using ONNX Runtime static post-training quantization (PTQ) |
| `compare_live.py` | Runs both models on the **same** live frame and shows them side by side, with latency, FPS, detections, model size, INT8 speed-up and detection agreement. Writes a per-frame CSV to `results/` |
| `models/` | Generated ONNX models |
| `results/` | Per-frame CSV logs, screenshots (`s` key) |

## 3. How to run

```bash
pip install onnx onnxruntime onnxslim

# build both models (calibrate on real field images if you have them)
python optimization_research/quantize_int8.py
python optimization_research/quantize_int8.py --calib data/yolo/images/val --num-calib 200

# live, webcam 0
python optimization_research/compare_live.py --int8-conf 0.45

# demo video on loop
python optimization_research/compare_live.py --source demo_inputs/test_video.mp4 --loop --int8-conf 0.45

# compare against the exact path production uses (PyTorch FP32)
python optimization_research/compare_live.py --fp32 models/hf/best.pt --int8-conf 0.45

# headless benchmark (prints a summary table)
python optimization_research/compare_live.py --source demo_inputs/test_video.mp4 --loop \
    --max-frames 300 --no-display --int8-conf 0.45
```

Keys: `q`/`Esc` quit, `p` pause, `s` screenshot.

**Agreement** is the share of detections that both models produce with the
same class and IoU ≥ 0.5 (greedy one-to-one matching). FP32 is the reference.

## 4. Quantization method

- ONNX Runtime `quantize_static`, QDQ format, MinMax calibration.
- Per-channel INT8 weights, symmetric INT8 activations.
- **Only `Conv` layers are quantized.** SiLU (`Sigmoid`·`Mul`), `Concat` and
  `Resize` stay FP32.
- **The Detect head post-processing stays FP32** (DFL softmax, box decode, and the
  final Concat). That Concat mixes box coordinates (0 to 640 px) with class scores
  (0 to 1) in one tensor, so a single INT8 scale cannot represent both.

## 5. Experiments (2026-11-02, Apple M1 CPU, ONNX Runtime 1.31.1 CPUExecutionProvider)

Metric: mean of the per-frame max class score over 30 frames, relative to FP32
(FP32 = 0.638, so every frame clears the 0.55 production threshold).

| Variant | Conf. kept vs FP32 | Frames ≥ 0.55 |
|---|---|---|
| All ops INT8, UINT8 activations, head post-proc FP32 | ~0.78 (single frame: 0.49 vs 0.63) | 0 detections live |
| Same, Percentile (99.99) calibration | 0.71 | 0/30 |
| + final head convs FP32 | 0.73 | 0/30 |
| Entire Detect head FP32 | 0.73 | 0/30 |
| Conv-only INT8, UINT8 activations | 0.78 | 0/30 |
| Conv-only, first conv also FP32 | 0.70 | 0/30 |
| **Conv-only, symmetric INT8 activations (chosen)** | **0.81** | **11/30** |

Takeaways:
- The confidence loss builds up in the backbone and neck, not the head. Keeping the
  whole head in FP32 does not recover it.
- Quantizing SiLU outputs hurts, so Conv-only quantization is better.
- Percentile calibration did not help here and is much slower to calibrate.

### Live comparison: ONNX FP32 vs INT8 (120 frames, demo video)

| | FP32 | INT8 @ conf 0.55 | INT8 @ conf 0.45 |
|---|---|---|---|
| Model size | 12.3 MB | 3.5 MB | 3.5 MB |
| Inference (mean) | ~42–48 ms | ~25–28 ms | ~25 ms |
| Speed-up | 1× | ~1.7× | **~1.7×** |
| Detections / frame | 1.00 | 0.37 | 1.00 |
| Agreement with FP32 | — | 37 % | **100 %** |

The production path (PyTorch FP32, `best.pt`) measured about 48 ms inference on
the same machine, so INT8 ONNX is roughly 2–2.7× faster than what runs today.
Timings vary ±10 ms between runs when other work is running on the machine.

## 6. Conclusions and caveats

1. **INT8 is about 1.7× faster than FP32 ONNX and 3.5× smaller**, but plain PTQ cuts
   class confidence by about 20 %. Running it at the production threshold (0.55)
   drops most detections. To reproduce FP32's detections, INT8 needs its own lower
   threshold (about 0.45).
2. **The model is the bottleneck, not the quantizer.** `best.pt` was trained for only
   **3 epochs**, so its top scores sit just above 0.55. A properly trained model
   has wider confidence margins and loses much less under PTQ.
3. **The calibration and test data are weak.** `demo_inputs/test_video.mp4` is
   30 frames (10 fps, 1280×1280) of a mosaic of training `val_batch` images, with
   ground-truth boxes burned into the pixels. The model makes about 1 real
   detection per frame on it. The same frames were used for calibration and
   evaluation, so the numbers above are optimistic. Re-run with real field footage
   and the MH-Weed16 validation images.
4. Changing the threshold is a safety-relevant change. `safety.minimum_confidence`
   in `configs/config.yaml` would need to change with it, so validate on real
   footage before you rely on INT8 detections for targeting.

## 7. Next steps

- Retrain for many more epochs, then re-run PTQ.
- Calibrate on 200–500 real validation images (`--calib`).
- Measure mAP on the validation split for FP32 and INT8 (`yolo val model=...onnx`).
  This is the proper accuracy metric, rather than score ratios.
- If PTQ is still too lossy: quantization-aware training (QAT).
- Deployment-target runtimes: TensorRT INT8 (Jetson) or OpenVINO INT8 (Intel),
  where INT8 speed-ups are usually larger than on ARM CPU. Also test FP16 on GPU
  as a middle option.
