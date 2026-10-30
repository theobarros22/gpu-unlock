"""GPL-2.0-only. GA107 Dell G15 research profile and family admission tests.
Validates exact admission for 10DE:25EC (RTX 3050 6GB Laptop) on GA107.
"""
import copy
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = Path(__file__).resolve().parents[3] / 'research' / 'profile'
CLANG = shutil.which('clang') or 'clang'

# Load make-profile and test_local_topology modules
spec_mp = importlib.util.spec_from_file_location('make_profile', RESEARCH / 'make-profile.py')
mp = importlib.util.module_from_spec(spec_mp)
spec_mp.loader.exec_module(mp)

spec_topo = importlib.util.spec_from_file_location('local_topology', RESEARCH / 'test_local_topology.py')
topo = importlib.util.module_from_spec(spec_topo)
spec_topo.loader.exec_module(topo)


def compile_source(source, defines=(), extra=()):
    return subprocess.run([CLANG, '-std=c11', '-Wall', '-Wextra', '-Werror', '-fsyntax-only',
                           '-x', 'c', '-', '-I', str(ROOT), *defines, *extra],
                          input=source, capture_output=True, text=True)


class GA107AdmissionTests(unittest.TestCase):
    def setUp(self):
        # Research envelope containing GA107 candidate definition
        self.research_envelope = {
            'probe_device_ids': ['25ec10de', '220410de', '248710de', '250410de'],
            'class_revision': '030000a1',
            'chips': [
                {
                    'chip': 'b77000a1',
                    'family': 'GA107',
                    'memory': ['1800'],
                    'pci_memory': {'25ec10de': ['1800']},
                    'nvgop': [{'version': '60010', 'text_sha256': '615b37a708b1894e18d7fa60cfcdacaa4d8b598863a10b8103d231a595847b2b'}],
                    'evidence': ['evidence/dell-g15-5530-research']
                }
            ],
            'min_captures': 2
        }

    def test_ga107_c_header_admits_exact_rtx3050_hardware(self):
        source = (
            '#include "gpu-family.h"\n'
            '_Static_assert(GU_GPU_FAMILY == 107, "GA107 family constant");\n'
            '_Static_assert(GU_CHIP_ID == 0xb77000a1U, "GA107 chip revision A1");\n'
            '_Static_assert(GU_DEVICE_MEMORY_SIZE == 0x1800U, "6144 MiB VRAM");\n'
            '_Static_assert(GU_BOARD_ID == 0x25ec10deU, "PCI VEN 10DE DEV 25EC");\n'
        )
        done = compile_source(
            source,
            ['-DGU_PROFILE_LOCAL', '-DGU_BOARD_ID=0x25ec10deU',
             '-DGU_DEVICE_MEMORY_SIZE=0x1800U', '-DGU_CHIP_ID=0xb77000a1U']
        )
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_ga107_c_header_rejects_divergent_tuples(self):
        cases = [
            (107, 0x25ec10de, 0x2000, 0xb77000a1),  # Wrong memory (8GB instead of 6GB)
            (107, 0x25ec10de, 0x1000, 0xb77000a1),  # Wrong memory (4GB instead of 6GB)
            (107, 0x25ec10de, 0x1800, 0xb77000a2),  # Wrong revision (A2)
            (107, 0x250410de, 0x1800, 0xb77000a1),  # Wrong board (GA106 board on GA107)
            (106, 0x25ec10de, 0x1800, 0xb76000a1),  # Family mismatch (GA106 with 25EC)
            (104, 0x25ec10de, 0x1800, 0xb74000a1),  # Family mismatch (GA104 with 25EC)
            (107, 0x25ec10de, 0x1800, 0xb76000a1),  # GA106 chip on GA107 family
        ]
        for family, board, memory, chip in cases:
            with self.subTest(family=family, board=board, memory=memory, chip=chip):
                done = compile_source(
                    '#include "gpu-family.h"\n',
                    [f'-DGU_GPU_FAMILY={family}', f'-DGU_BOARD_ID={board}U',
                     f'-DGU_DEVICE_MEMORY_SIZE={memory}U', f'-DGU_CHIP_ID={chip}U']
                )
                self.assertNotEqual(done.returncode, 0, f"Expected rejection for {(family, board, memory, chip)}")

    def test_ga107_research_envelope_topology_admission(self):
        # Synthetic capture for Dell G15 5530: Bus 1, Intel iGPU present, 2 children, 6GB VRAM
        text = topo.synthetic_capture(
            board=0x25ec10de,
            chip=0xb77000a1,
            memory=0x1800,
            bus=1,
            igpu=True,
            no_edid=True,
            children=2
        )
        result = topo.analyze(text, self.research_envelope)
        defines = dict(result['defines'])
        self.assertEqual(defines['GU_CHIP_ID'], '0xb77000a1U')
        self.assertEqual(defines['GU_BOARD_ID'], '0x25ec10deU')
        self.assertEqual(defines['GU_DEVICE_MEMORY_SIZE'], '0x1800U')

    def test_ga107_research_envelope_rejects_divergent_memory_or_board(self):
        for board, chip, memory in [
            (0x25ec10de, 0xb77000a1, 0x2000),  # 8GB not allowed for 25EC
            (0x25ec10de, 0xb77000a1, 0x3000),  # 12GB not allowed for 25EC
            (0x25ec10de, 0xb76000a1, 0x1800),  # Wrong chip
            (0x999910de, 0xb77000a1, 0x1800),  # Unknown board
        ]:
            with self.subTest(board=board, chip=chip, memory=memory):
                text = topo.synthetic_capture(
                    board=board,
                    chip=chip,
                    memory=memory,
                    bus=1
                )
                with self.assertRaises(topo.mp.Refused):
                    topo.analyze(text, self.research_envelope)


if __name__ == '__main__':
    unittest.main()
