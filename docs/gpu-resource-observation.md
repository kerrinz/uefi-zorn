# Resource-observation diagnostic candidate

This offline candidate builds on the
[default-off query/checkpoint join](gpu-resource-query-checkpoint.md). The
normal firmware keeps native selection off. Only the dedicated staging recipe
selects the existing typed media path and resource observation, with an actual
module entry in a complete FD. No new GPU activation path is introduced.

From the common workspace parent, the fixed offline entries are:

```sh
python3 uefi-zorn/scripts/build-zorn-firmware.py --gpu-resource-observation-candidate
python3 UniXNU-zorn/scripts/build-zorn-debug.py --gpu-resource-observation-image --os 17
```

The [source recipe](../scripts/stage-zorn-resource-observation.py) requires the
preserved source capsule and SDK. It refuses an existing output and keeps all
completed images and manifests. This is a local staged build, with the exact
tested Darwin23 kernel and retained FAT/menu/ADT reused. It is not a fresh
kernel bootstrap or an execution entry. The diagnostic stops before payload.

Media identity and ownership must succeed before the query runs. The query uses
the original Clock/RPMh/CommandDB types, EBS owner, GCD observer and272B capture.
At most3 protocol locates,3 clock-resource ID lookups and16 GCD descriptor calls
are possible. Lookup can allocate bookkeeping or block inside the provider;
call counts are not a time bound. GCD reports describe the existing declared
range without physical dereference. The real backend still reports unavailable
vote/rate/variant policy. These results cannot supply power, stop, SMMU or DMA
ownership. Clock enable/rate/vote, SCM/PAS, MMIO and GPU execution remain absent.

The existing ZORNGQF1 first terminal attempt is retained, including failed
encoding. No second collection/retry or new wire fields are added. A valid
typed owner permits at most one original4KiB log write and a success-only
readback. Failure before that owner, or a nonreturning provider/I/O, can leave no
new record. A fresh record is not proof of both private native commit statuses.

The dedicated fixed runner accepts a distinct exact-image admission. It claims
once before any USB query, requires OrangeFox/92988a43/zorn/slotA and the exact
unixnu64 GPT/root/Data identity, preserves and reads back the full recovery BCB,
and uses the original independent watchdog1 plus600-second Recovery limit.
It has no bootstrap, retry, flash or restore fallback. The consumed762a media
authorization cannot authorize this resource observation.

At offline completion the pending admission remained disabled. No active
owner, ready or claim was created by the offline build. Actual-file preflight uses temporary
hypothetical host approval files and removes them; it never invokes USB or
creates a claim. A new explicit execution decision was required for the
subsequent trial described below. The [source evidence](evidence/gpu-resource-observation-candidate-2026-11-01.json)
binds candidate a315c9bb/FD73567093, its object/link/image checks, exact input
archives and concrete activation proposal. GPU rendering and Metal are still
unqualified.

## Authorized one-shot observation completed

The subsequent explicit owner decision was used once. The candidate recovered
to verified OrangeFox in40.660s with a fresh matching terminal record. All3
protocol locates,3 resource-ID lookups and1 GCD descriptor call returned raw0.
The two query events closed and local protocol borrows retired. Stage8/raw5
is the existing unavailable-policy adapter result, not a native lookup failure.
The full policy report and private native commit statuses are not on this wire.

The operational per-trial ready is historical and its claim is consumed. No
new execution permission remains. Resource IDs/GCD reservation do not grant
power/security/SMMU/DMA or GPU ownership. See the
[actual trial evidence](evidence/gpu-resource-observation-trial-2026-11-01.json).
