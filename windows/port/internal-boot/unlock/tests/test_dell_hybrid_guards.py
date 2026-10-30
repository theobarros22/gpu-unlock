"""GPL-2.0-only. Host regressions for the Dell G15 hybrid (unattached dGPU) route.

The Dell branches relax three guards that hold for every reviewed board:
bus master already enabled at cold boot, no NVIDIA console GOP, and no GOP
release stages. These tests prove the relaxations compile only for the Dell
research profile and that reviewed boards keep the original guards.
No GPU, EFI or firmware execution.
"""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT.parent / 'boot'
FIXTURE = Path(__file__).resolve().parent / 'fixtures' / 'dell-g15'
EDK2 = ROOT.parents[1] / 'deps' / 'edk2' / 'MdePkg' / 'Include'
CLANG = shutil.which('clang') or 'clang'
REVIEWED = ['B650M_3090FE', 'B660M_3070TI', 'B660M_3090TI', 'X870_3090TI', 'B660PLUS_3060', 'H610M_3060']
DELL = '-DGU_PROFILE_DELL_G15_RESEARCH'
INCLUDES = ['-I', str(ROOT), '-I', str(ROOT / 'compat'), '-I', str(FIXTURE), '-I', str(EDK2), '-I', str(EDK2 / 'X64')]

# Command register exactly as both Dell captures report it: memory decode + bus master.
DELL_COLD_COMMAND = 0x00100006
REVIEWED_COLD_COMMAND = 0x00100002


def compile_source(source, defines=()):
    return subprocess.run([CLANG, '-std=c11', '-Wall', '-Wextra', '-Werror', '-fsyntax-only',
                           '-x', 'c', '-', *INCLUDES, *defines],
                          input=source, capture_output=True, text=True)


CHECK_CONFIG = r'''
#include "checks.h"
#include <stdio.h>
#include <string.h>
int main(int argc, char **argv) {
  UINT32 C[64]; GU_CAPS Caps;
  unsigned long command = strtoul(argv[1], NULL, 16);
  memset(C, 0, sizeof(C));
  C[0] = GU_BOARD_ID; C[1] = (UINT32)command; C[2] = 0x030000a1; C[3] = 0x00800000;
  C[0x2c / 4] = GU_BOARD_SUBSYSTEM; C[0x34 / 4] = 0x40;
  C[0x40 / 4] = 0x00034801; C[0x48 / 4] = 0x00020010; C[0x4c / 4] = 0x10000000;
  (void)argc;
  return GuCheckConfig(C, GU_TARGET_SEGMENT, GU_TARGET_BUS, 0, 0, &Caps) ? 0 : 3;
}
'''


class HybridSwitchTests(unittest.TestCase):
    def test_reviewed_boards_never_select_the_hybrid_route(self):
        source = ('#include "machine-profile.h"\n'
                  '#ifdef GU_HYBRID_DGPU_NO_CONSOLE\n#error hybrid route selected\n#endif\n')
        for profile in REVIEWED:
            with self.subTest(profile=profile):
                done = compile_source(source, ['-DGU_PROFILE_' + profile])
                self.assertEqual(done.returncode, 0, done.stderr)

    def test_dell_profile_selects_the_hybrid_route(self):
        source = ('#include "machine-profile.h"\n'
                  '#ifndef GU_HYBRID_DGPU_NO_CONSOLE\n#error hybrid route missing\n#endif\n'
                  '_Static_assert(GU_BOARD_ID == 0x25ec10deU, "Dell dGPU");\n')
        done = compile_source(source, [DELL])
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_forcing_the_hybrid_route_on_a_reviewed_board_fails(self):
        for profile in REVIEWED:
            with self.subTest(profile=profile):
                done = compile_source('#include "machine-profile.h"\n',
                                      ['-DGU_PROFILE_' + profile, '-DGU_HYBRID_DGPU_NO_CONSOLE=1'])
                self.assertNotEqual(done.returncode, 0)
                self.assertIn('reviewed only for the Dell', done.stderr)

    def test_dell_profile_with_console_children_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = (FIXTURE / 'profile-dell-research.h').read_text()
            bad = text.replace('#define GU_CONSOLE_CHILD_COUNT 0', '#define GU_CONSOLE_CHILD_COUNT 1')
            self.assertNotEqual(bad, text)
            Path(tmp, 'profile-dell-research.h').write_text(bad)
            done = subprocess.run([CLANG, '-std=c11', '-fsyntax-only', '-x', 'c', '-',
                                   '-I', str(ROOT), '-I', tmp, DELL],
                                  input='#include "machine-profile.h"\n', capture_output=True, text=True)
            if (ROOT / 'profile-dell-research.h').exists():
                self.skipTest('private profile beside machine-profile.h shadows the fixture')
            self.assertNotEqual(done.returncode, 0)
            self.assertIn('unattached dGPU', done.stderr)

    def test_headless_console_check_keeps_the_strict_rule_on_reviewed_boards(self):
        # headless-policy.h is reached from app.c without prepare-console.c's
        # default child count, which is where 486ffc4 leaked the Dell rule.
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'build', 'headless').mkdir(parents=True)
            Path(tmp, 'platform-config.h').write_text(
                '#define GU_INTERNAL_PARTITION_INITIALIZER {0,0,0,{0,0,0,0,0,0,0,0}}\n'
                '#define GU_WINDOWS_PARTITION_INITIALIZER {0,0,0,{0,0,0,0,0,0,0,0}}\n')
            flags = ['-target', 'x86_64-pc-windows-msvc', '-std=c11', '-ffreestanding', '-fshort-wchar', '-E', '-P',
                     '-D__KERNEL__', '-DGU_UEFI_PORT', '-DGU_HEADLESS_RESEARCH', '-DGU_SINGLE_RTX_CONSOLE',
                     '-DGU_FULL_UNLOCK', '-DGU_AUTOMATIC_BOOT', '-DGU_USB_MEDIA', '-DGU_INTERNAL_BOOT',
                     '-DGU_EXPERIMENTAL_3090', '-DGU_ENTRY_LATCHED_SS1_FULL', '-I', tmp, *INCLUDES]
            for profile, expect_dell in [(p, False) for p in ('B650M_3090FE', 'X870_3090TI', 'H610M_3060')] + [('DELL_G15_RESEARCH', True)]:
                with self.subTest(profile=profile):
                    done = subprocess.run([CLANG, *flags, '-DGU_PROFILE_' + profile, str(ROOT / 'app.c')],
                                          capture_output=True, text=True)
                    self.assertEqual(done.returncode, 0, done.stderr[-400:])
                    self.assertEqual('LocateDevicePath(&pci' in done.stdout, expect_dell)

    def test_sources_never_key_on_an_implicit_zero_child_count(self):
        # A comparison is safe only when the same line first requires the macro to be defined.
        pattern = re.compile(r'^\s*#\s*(if|elif)\b(?!.*defined\s*\(\s*GU_CONSOLE_CHILD_COUNT)'
                             r'.*GU_CONSOLE_CHILD_COUNT\s*(==\s*0|>\s*0|!=\s*0)', re.M)
        for path in sorted(list(BOOT.glob('*.[ch]')) + list(ROOT.glob('*.[ch]'))):
            with self.subTest(path=path.name):
                self.assertIsNone(pattern.search(path.read_text(errors='replace')))


class BusMasterAdmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.exes = {}
        for name, define in [('dell', DELL), ('b650m', '-DGU_PROFILE_B650M_3090FE')]:
            src = Path(cls.tmp.name, 'check_config.c')
            src.write_text(CHECK_CONFIG.replace('#include <string.h>', '#include <string.h>\n#include <stdlib.h>'))
            exe = Path(cls.tmp.name, f'{name}.exe')
            done = subprocess.run([CLANG, '-std=c11', '-O1', '-D_CRT_SECURE_NO_WARNINGS', *INCLUDES, define,
                                   str(src), str(ROOT / 'checks.c'), '-o', str(exe)],
                                  capture_output=True, text=True)
            if done.returncode:
                raise unittest.SkipTest('host compile unavailable: ' + done.stderr[-400:])
            cls.exes[name] = exe

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_check(self, name, command):
        return subprocess.run([str(self.exes[name]), f'{command:08x}']).returncode

    def test_dell_accepts_its_captured_cold_command(self):
        self.assertEqual(self.run_check('dell', DELL_COLD_COMMAND), 0)

    def test_reviewed_board_refuses_bus_master_at_cold_boot(self):
        self.assertEqual(self.run_check('b650m', REVIEWED_COLD_COMMAND), 0)
        self.assertNotEqual(self.run_check('b650m', DELL_COLD_COMMAND), 0)

    def test_dell_still_requires_memory_decode(self):
        self.assertNotEqual(self.run_check('dell', 0x00100004), 0)


if __name__ == '__main__':
    unittest.main()
