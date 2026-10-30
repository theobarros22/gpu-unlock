#!/usr/bin/env python3
"""Compare workload runs offline (State A = original, C = tuned, B = unlocked).

Refuse comparison if environments diverge, complete markers are missing,
or quality checks failed.
"""

import argparse
import json
import math
from pathlib import Path
import sys


def time_reduction_pct(a: float, b: float) -> float:
    """Calculate percentage reduction in execution time: 100 * (1 - b / a)."""
    if not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
        raise TypeError("Inputs must be numbers")
    if not (math.isfinite(a) and math.isfinite(b)):
        raise ValueError("Inputs must be finite numbers")
    if a <= 0 or b <= 0:
        raise ValueError("Execution times must be strictly positive")
    return 100.0 * (1.0 - float(b) / float(a))


def throughput_gain_pct(a: float, b: float) -> float:
    """Calculate percentage increase in throughput: 100 * (b / a - 1)."""
    if not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
        raise TypeError("Inputs must be numbers")
    if not (math.isfinite(a) and math.isfinite(b)):
        raise ValueError("Inputs must be finite numbers")
    if a <= 0 or b <= 0:
        raise ValueError("Throughput values must be strictly positive")
    return 100.0 * (float(b) / float(a) - 1.0)


def completed(run_data: dict) -> bool:
    """Check if a run dictionary is verified as completed and quality-approved."""
    if not isinstance(run_data, dict):
        return False
    if run_data.get("exit_code") != 0:
        return False
    if run_data.get("quality_pass") is not True:
        return False
    if not run_data.get("metric_value") or not math.isfinite(run_data["metric_value"]):
        return False
    if run_data["metric_value"] <= 0:
        return False
    return True


def comparable(ctx1: dict, ctx2: dict) -> bool:
    """Ensure two run contexts are strictly comparable."""
    if not (isinstance(ctx1, dict) and isinstance(ctx2, dict)):
        return False
    # Check protocol version
    if ctx1.get("protocol_version") != ctx2.get("protocol_version"):
        return False
    # Check workload identity
    if ctx1.get("workload_name") != ctx2.get("workload_name"):
        return False
    # Check executable hash if provided
    if ctx1.get("executable_sha256") and ctx2.get("executable_sha256"):
        if ctx1["executable_sha256"].lower() != ctx2["executable_sha256"].lower():
            return False
    return True


def load_run_dir(path: Path) -> dict:
    marker = path / "complete.json"
    if not marker.exists():
        raise FileNotFoundError(f"Missing complete.json in {path}")
    data = json.loads(marker.read_text(encoding="utf-8-sig"))
    if not completed(data):
        raise ValueError(f"Run in {path} is not valid/completed/quality-approved")
    return data


def compare_runs(baseline_dir: Path, candidate_dir: Path, restored_dir: Path = None) -> dict:
    base = load_run_dir(baseline_dir)
    cand = load_run_dir(candidate_dir)

    if not comparable(base.get("context", {}), cand.get("context", {})):
        raise ValueError("Baseline and Candidate contexts are not comparable")

    metric_name = base.get("metric_name", "duration_seconds")
    base_val = float(base["metric_value"])
    cand_val = float(cand["metric_value"])

    time_red = time_reduction_pct(base_val, cand_val)
    if any(k in metric_name.lower() for k in ("second", "time", "duration", "ms")):
        tput_gain = throughput_gain_pct(1.0 / base_val, 1.0 / cand_val)
    else:
        tput_gain = throughput_gain_pct(base_val, cand_val)

    report = {
        "workload": base.get("context", {}).get("workload_name"),
        "metric_name": metric_name,
        "baseline_value": base_val,
        "candidate_value": cand_val,
        "time_reduction_pct": round(time_red, 4),
        "throughput_gain_pct": round(tput_gain, 4),
        "quality_pass": cand.get("quality_pass", False),
        "restored": None
    }

    if restored_dir and restored_dir.exists():
        restored = load_run_dir(restored_dir)
        if not comparable(base.get("context", {}), restored.get("context", {})):
            raise ValueError("Baseline and Restored contexts are not comparable")
        rest_val = float(restored["metric_value"])
        drift_pct = 100.0 * (rest_val - base_val) / base_val
        report["restored"] = {
            "restored_value": rest_val,
            "drift_vs_baseline_pct": round(drift_pct, 4),
            "restored_within_5pct": abs(drift_pct) <= 5.0
        }

    return report


def main():
    parser = argparse.ArgumentParser(description="Compare workload runs offline")
    parser.add_argument("--baseline", required=True, type=Path, help="Directory of baseline run (A or C)")
    parser.add_argument("--candidate", required=True, type=Path, help="Directory of candidate run (B)")
    parser.add_argument("--restored", required=False, type=Path, default=None, help="Directory of restored run (A2 or C2)")
    parser.add_argument("--output", required=True, type=Path, help="Output JSON path")
    args = parser.parse_args()

    report = compare_runs(args.baseline, args.candidate, args.restored)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Comparison report saved to {args.output}")
    print(f"Time reduction: {report['time_reduction_pct']}% | Quality pass: {report['quality_pass']}")
    if report.get("restored"):
        print(f"Restoration check: drift {report['restored']['drift_vs_baseline_pct']}% (within 5%: {report['restored']['restored_within_5pct']})")


if __name__ == "__main__":
    main()
