# Default-OFF resource-query checkpoint join

The one authorized `762a1234` media trial has finished and its claim is consumed.
The new source capsule joins the existing query capture to that typed media
path. It introduces no new wire fields or GPU/power operation. Native execution
is disabled in the complete firmware built in this stage.

The source delta is maintained in
[stage-zorn-resource-query.py](../scripts/stage-zorn-resource-query.py).
From the common workspace parent, the fixed offline recipe is:

```sh
python3 uefi-zorn/scripts/stage-zorn-resource-query.py
python3 uefi-zorn/scripts/build-zorn-firmware.py --gpu-resource-query-checkpoint
```

The staging recipe requires the preserved closed `unixnu64` parent capsule and
existing SDK. It refuses an existing output and never overwrites a completed
stage. This is not a clean bootstrap or a device-execution entry.

The new `ZMQ_RESOURCE_QUERY` flag defaults to0. Its selected inspection body
calls the real media adapter first. Only media success reaches the original
query function, which retains its own real EBS owner and original272B capture.
After the query returns, a48B collector report distinguishes an armed report
(`Attempted=0`) from a terminal attempt (`Attempted=1`). An existing attempt,
including a failed encoding, is retained without a second collection. An early
adapter error with no terminal attempt is retained at full64-bit width. Only an
available existing record can reach preparation; failed preparation cannot
reach commit. The dedicated diagnostic stop always precedes payload execution.

The current backend deliberately reports policy unavailable: clock IDs and a
GCD descriptor do not supply vote/rate/variant authority. Its selected LTO body
therefore has no successful policy branch. This result must not be changed to
success for progress. Raw lookup statuses remain in the existing query capture.

Local validation links the real collector/codec with explicit orchestration
peers that never construct a hardware owner; media preparation always refuses.
The separate real SDK inspection links all20 newly selected module objects
directly, excludes the old closed module archive, and has entry RVA0. It is not
inserted into the full FD. The normal full FD keeps all five native selectors0.
The [evidence summary](evidence/gpu-resource-query-checkpoint-2026-11-01.json)
records the host controls, independent objects and final-link mutations.

The previous media trial establishes a historical checkpoint observation only.
It gives no authorization for another native query or boot. A future selected
observation candidate needs its own exact image, immutable inputs, admission,
fresh BCB/watchdog/recovery checks and explicit execution decision.

The subsequent [resource-observation candidate](gpu-resource-observation.md)
now supplies that complete offline image and distinct admission. Its execution
decision is still pending; the closed FD and this stage's NOENTRY annotation
remain separate preserved artifacts.
