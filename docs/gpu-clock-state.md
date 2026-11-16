# Inert clock-state preparation

The [source recipe](../scripts/stage-zorn-clock-state.py) creates a local source
capsule from exact preserved resolver/vote types. It refuses existing staged
files, checks their SHA256 and copies them to independent inodes. From the
common workspace parent:

```sh
python3 uefi-zorn/scripts/stage-zorn-clock-state.py
```

The preserved source capsules and actual SDK recipe are prerequisites. This
staging command does not build a clean firmware checkout, select a module/FD,
or execute a provider. The output is a256B non-callable request. Successful
preparation means only that its input shape and software scope are accepted.
It is not a native result, live owner, callable protocol or transport format.
Invocation, output/status availability, lifetime/running/ownership and runtime
flags remain zero. The already closed real capture is refused. Existing272B
capture and all log formats remain unchanged.

The two methods were bound against the exact archived provider and selected
header. `IsClockEnabled` is slot4/offset32 with a BOOLEAN output; its real path
can update backend bookkeeping and read MMIO. A missing callback can also yield
false. `GetClockFreqHz` is slot7/offset56 with a UINT32 output; it reads the
cached selected plan rather than measured or running frequency. Both have
mode paths returning SUCCESS without writing the output. Zero-initialized
storage and zero native status cannot establish that a result was produced.

The [evidence](evidence/gpu-clock-state-binding-2026-11-01.json) binds focused
data refusals, actual provider corruptions, target ABI and the SDK NOENTRY
link. Four LTO objects independently match raw SHA under the exact recipes.
The separate non-LTO inspection objects have explicit COFF timestamps and
hashes; their metadata is not normalized or declared equivalent. Native ABI
call wrappers are annotation objects only and are excluded from the link.

No getter or phone operation is authorized here. All prior trial claims remain
consumed; clock IDs/GCD metadata do not supply power/security/SMMU/DMA rights.
The remaining hardware-filter information inputs must be bound separately
before a rate/variant policy can be prepared. No rate is selected by this source.
