# Windows Port Upstream Reference

## Upstream Repository
- **URL**: https://github.com/impacifist/Windows-GPU-UNLOCK
- **Pinned Commit**: `263741419ece69bcce73162ad5e98a742db8c6b5`
- **Commit Date**: 2026-10-29 22:52:26 +0900
- **Commit Message**: `Preserve captured PCI state and selected PROM pins in host fixtures`
- **Location in repo**: `windows/port/`

## Licensing and Notices
- The upstream project is licensed under the MIT License (`windows/port/LICENSE`).
- Third-party notices and licenses are preserved in `windows/port/THIRD_PARTY_NOTICES.md` and `windows/port/LICENSES/`:
  - EDK2 MdePkg headers (`EDK2-BSD-2-Clause-Patent.txt`)
  - NVIDIA MIT component licenses (`NVIDIA-MIT.txt`)
  - CMP40HX components (`CMP40HX-MIT.txt`)
  - NVIDIA Driver terms (`NVIDIA-Driver.txt`)

## Local Modifications and Extensions
All upstream source paths inside `windows/port/` are preserved as-is to ensure build and test script compatibility.
Dell G15 5530 (RTX 3050 Laptop GA107) extensions, diagnostics, benchmarks, and research runners reside in:
- `windows/Collect-Diagnostics.ps1`
- `windows/Run-Workload.ps1`
- `windows/Compare-Runs.py`
- `windows/tests/`
- `windows/workloads/`
- `windows/local/` (private local runs/fixtures, ignored by git)
