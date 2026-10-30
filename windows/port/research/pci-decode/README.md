# PCI decode-cache synchronization research

This is a host-testable research core, **not an executable fix**. No production
build, probe, LOCAL profile gate, USB staging script or EFI entry point uses it.
Current captures with inconsistent PCI attributes remain refused.

Reports [#102](https://github.com/impacifist/Windows-GPU-UNLOCK/issues/102),
[#121](https://github.com/impacifist/Windows-GPU-UNLOCK/issues/121) and
[#129](https://github.com/impacifist/Windows-GPU-UNLOCK/issues/129) describe a
GPU command register of `0x0002` but PciIo attributes of `0x300` (IO + memory).
Contributors report that disabling the IO attribute reconciled these values
before running their separate unlock workflow. Their results concern specific
firmware/builds; they do not establish a generic firmware correction.

The independent implementation here offers exactly one write capability:
`DisableIo`. It does not adopt the contributor pre-step's initial IO-enable attempt.
Its callback must eventually be bound to the reviewed GPU's
`PciIo->Attributes(Disable, IO)`. The research library adapter described below is
implemented and tested only against RAM-backed EFIAPI mocks; it is not connected
to any boot image and has not been authorized or tested on physical hardware.

`GuDecodeSync` requires an exact baseline GPU and 1–16 caller-verified immediate
parent bridges, including location, handle/interface tokens, all 64 config
dwords and full attribute/support values. It rejects aliasing, invalid BDF ranges,
inconsistent parent buses and unreviewed target identities. GPU command must be
exactly `2`; the only admitted discrepancy is raw attributes `0x300` instead of
`0x200`. An already consistent baseline is observed without a write.

Before the single Disable call, the core freezes its input/callback table, flushes
the intent log and checks a fresh complete snapshot. It compares the complete GPU
and every parent after the call and at four bounded logical follow-ups. Only the
GPU's IO attribute may clear; raw PCI config, memory/BME state, other attributes,
locations, interfaces and parents must remain identical. Only `EFI_SUCCESS` and
canonical boolean log success are accepted. A failed write still receives one
bounded observation because an error does not prove that state was unchanged.
There is no retry, rollback, IO/BME enable, config/MMIO write or chainload capability.

The caller must retain one zero-initialized transaction object and never reset
it to retry. Reentry using the same object refuses before a callback. The caller
must also serialize operations and prevent reuse through another object. The
snapshot callback's honesty, ownership and freshness are separate obligations;
tokens and a `Complete` flag are not authenticated evidence. Parent topology must
be verified from actual device paths by the future adapter, not inferred only
from matching bus numbers. Immediate host samples do not prove timed stability
or detect every change between observations. Hidden firmware state and real GPU
behavior are outside this mock model.

Run only the host model from an MSVC/Windows SDK developer environment:

```powershell
python -I research/pci-decode/test-decode-sync.py --mutations --clang C:\TOOLS\LLVM20\bin\clang.exe --output research/pci-decode/build/your-new-run
```

Use a new output directory. Tests exercise failures/warnings/partial output,
callback reentry and input mutation, log failure/drift, changes in every config
dword of the GPU and all 16 parents, full attribute/token/location drift, and
attempts to reuse a transaction. All protocol effects are RAM callbacks; no GPU,
firmware, boot setting or physical media is accessed. Passing this model grants
no hardware support, LOCAL write evidence or permission to run a correction.
The optional mutation checks compile ten deliberately broken copies in the ignored
output directory and require the host tests to reject them. A compile failure does
not count as detecting a broken guard. Original source files remain unchanged.

## Research UEFI adapter

`efi-adapter.c` binds an exact caller-supplied baseline and PCI controller paths.
Initialization validates/copies inputs without firmware calls and cannot reset a
used context. Run freezes a private copy and spends the context before its first
callback, including against reentry through a fresh core transaction object.
Caller-owned policy changes cannot alter the active copy. Contexts must remain
private, zero-initialized and serialized; callers must not reset/recreate them to retry.

The GPU controller route uses the existing bounded PNP0A03/PNP0A08 parser. Two to
sixteen PCI nodes correspond to one to fifteen immediate parent bridges. Each
parent's path must be the exact corresponding prefix plus an End node; its PCI
device/function must match the last node. This adapter's parent limit is smaller
than the standalone core's sixteen-parent bound.

Each snapshot uses `HandleProtocol`, `LocateDevicePath`, `GetLocation`, a full
64-dword PCI read, and Attributes Get/Supported. It requires the pinned interface,
exact path bytes and exact Locate consumption at the End node. Two full chain
scans use different config initialization patterns, so successful partial reads
cannot pass merely by leaving the same sentinel twice. Method pointers and both
BootServices methods are pinned and rechecked, including all devices after the
last callback. Before the sole Disable(IO), the adapter performs another full
scan and callback-free whole-chain capability check. It does not expose generic
Attributes, config-write, MMIO, install/uninstall, disk or boot capabilities.

The mock adapter suite injects warning/error with valid output, absent output,
partial config, path/Locate-consumption errors, changed interfaces/methods,
early and late parent drift, Init/Run reentry, caller input changes and a failing
write that nevertheless changes state. Mutation checks also break Locate bounds,
the differing sentinels, whole-chain method checks and one-shot initialization.

This is not ownership acquisition, GPU qualification, a snapshot of all firmware
state, atomic observation across devices or proof of real-time stability. A future
experiment must independently establish authorized ownership, lifetime/freshness,
boot/display consequences, logging durability and physical validation. Existing
read-only probes, LOCAL admission and build-evidence rules remain unchanged.
