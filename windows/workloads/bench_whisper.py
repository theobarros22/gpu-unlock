#!/usr/bin/env python3
"""Standardized Faster-Whisper benchmark for State A (CPU int8) vs State C (CUDA fp16).
Conforms to PLAN-DELL-G15-RTX3050 section 5 / W2 requirements.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

# Fallback if external HF_HOME drive is disconnected
hf_home = os.environ.get("HF_HOME")
if hf_home and not os.path.exists(Path(hf_home).anchor):
    os.environ["HF_HOME"] = str(Path.home() / ".cache" / "huggingface")

try:
    from faster_whisper import WhisperModel
except ImportError:
    print("ERROR: faster_whisper not installed", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True, type=Path)
    parser.add_argument("--model-size", default="small")
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    parser.add_argument("--compute-type", choices=["int8", "float16", "float32"], default="float16")
    parser.add_argument("--warmup-runs", type=int, default=1)
    parser.add_argument("--measured-runs", type=int, default=3)
    args = parser.parse_args()

    if not args.audio.exists():
        print(f"ERROR: Audio file not found: {args.audio}", file=sys.stderr)
        sys.exit(1)

    # Compute audio file hash for provenance
    audio_bytes = args.audio.read_bytes()
    audio_sha256 = hashlib.sha256(audio_bytes).hexdigest()

    t_load = time.perf_counter()
    model = WhisperModel(args.model_size, device=args.device, compute_type=args.compute_type)
    load_time = time.perf_counter() - t_load

    # Warmup
    for _ in range(args.warmup_runs):
        list(model.transcribe(str(args.audio), language="pt", word_timestamps=True)[0])

    durations = []
    transcription_text = ""
    audio_duration = 0.0

    for _ in range(args.measured_runs):
        t0 = time.perf_counter()
        segments, info = model.transcribe(str(args.audio), language="pt", word_timestamps=True)
        seg_list = list(segments)
        dt = time.perf_counter() - t0
        durations.append(dt)
        audio_duration = info.duration
        transcription_text = " ".join(s.text.strip() for s in seg_list)

    durations.sort()
    median_duration = durations[len(durations) // 2]
    rtf = median_duration / max(audio_duration, 0.001)
    text_sha256 = hashlib.sha256(transcription_text.encode("utf-8")).hexdigest()

    result = {
        "benchmark_protocol": 2,
        "workload": "faster_whisper_vollare",
        "device": args.device,
        "compute_type": args.compute_type,
        "model_size": args.model_size,
        "audio_sha256": audio_sha256,
        "audio_duration_seconds": round(audio_duration, 3),
        "model_load_seconds": round(load_time, 3),
        "samples": len(durations),
        "median_seconds": round(median_duration, 4),
        "min_seconds": round(durations[0], 4),
        "max_seconds": round(durations[-1], 4),
        "rtf": round(rtf, 4),
        "text_sha256": text_sha256,
        "quality_pass": len(transcription_text) > 50
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
