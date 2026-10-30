#!/usr/bin/env python3
"""Unit tests for Compare-Runs.py conforming to PLAN-DELL-G15-RTX3050 specifications."""

import math
from pathlib import Path
import sys
import tempfile
import unittest

# Ensure parent directory is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from importlib import import_module
compare_mod = import_module("Compare-Runs")
time_reduction_pct = compare_mod.time_reduction_pct
throughput_gain_pct = compare_mod.throughput_gain_pct
comparable = compare_mod.comparable
completed = compare_mod.completed
compare_runs = compare_mod.compare_runs


class TestCompareRuns(unittest.TestCase):
    def test_plan_mandated_assertions(self):
        # Exactly required by section 5 W2 of the plan:
        self.assertEqual(round(time_reduction_pct(100.0, 80.0), 1), 20.0)
        self.assertEqual(round(throughput_gain_pct(100.0, 125.0), 1), 25.0)
        self.assertTrue(time_reduction_pct(100.0, 110.0) < 0)
        self.assertFalse(comparable({"protocol_version": 1}, {"protocol_version": 2}))
        self.assertFalse(completed({"exit_code": 1, "quality_pass": True}))

    def test_rejections(self):
        # Must reject zero, negative and infinite values
        for bad_val in (0.0, -10.0, float('nan'), float('inf'), -float('inf')):
            with self.assertRaises((ValueError, TypeError)):
                time_reduction_pct(bad_val, 50.0)
            with self.assertRaises((ValueError, TypeError)):
                time_reduction_pct(50.0, bad_val)
            with self.assertRaises((ValueError, TypeError)):
                throughput_gain_pct(bad_val, 50.0)
            with self.assertRaises((ValueError, TypeError)):
                throughput_gain_pct(50.0, bad_val)

    def test_completed_contract(self):
        self.assertTrue(completed({
            "exit_code": 0,
            "quality_pass": True,
            "metric_value": 45.2
        }))
        self.assertFalse(completed({
            "exit_code": 0,
            "quality_pass": False,
            "metric_value": 45.2
        }))
        self.assertFalse(completed({
            "exit_code": 0,
            "quality_pass": True,
            "metric_value": -1.0
        }))
        self.assertFalse(completed(None))

    def test_comparable_contract(self):
        ctx_a = {"protocol_version": 1, "workload_name": "whisper", "executable_sha256": "ABC"}
        ctx_b = {"protocol_version": 1, "workload_name": "whisper", "executable_sha256": "abc"}
        ctx_diff_hash = {"protocol_version": 1, "workload_name": "whisper", "executable_sha256": "XYZ"}
        ctx_diff_wl = {"protocol_version": 1, "workload_name": "comfy", "executable_sha256": "ABC"}

        self.assertTrue(comparable(ctx_a, ctx_b))
        self.assertFalse(comparable(ctx_a, ctx_diff_hash))
        self.assertFalse(comparable(ctx_a, ctx_diff_wl))

    def test_full_comparison_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base_dir = tmp_path / "baseline"
            cand_dir = tmp_path / "candidate"
            rest_dir = tmp_path / "restored"

            base_dir.mkdir()
            cand_dir.mkdir()
            rest_dir.mkdir()

            ctx = {"protocol_version": 1, "workload_name": "smoke", "executable_sha256": "HASH123"}

            import json
            (base_dir / "complete.json").write_text(json.dumps({
                "exit_code": 0, "quality_pass": True, "metric_value": 100.0, "context": ctx
            }), encoding="utf-8")

            (cand_dir / "complete.json").write_text(json.dumps({
                "exit_code": 0, "quality_pass": True, "metric_value": 85.0, "context": ctx
            }), encoding="utf-8")

            (rest_dir / "complete.json").write_text(json.dumps({
                "exit_code": 0, "quality_pass": True, "metric_value": 99.5, "context": ctx
            }), encoding="utf-8")

            report = compare_runs(base_dir, cand_dir, rest_dir)
            self.assertEqual(report["time_reduction_pct"], 15.0)
            self.assertTrue(report["quality_pass"])
            self.assertIsNotNone(report["restored"])
            self.assertTrue(report["restored"]["restored_within_5pct"])


if __name__ == "__main__":
    unittest.main()
