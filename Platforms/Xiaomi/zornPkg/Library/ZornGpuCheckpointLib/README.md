# unixnu64 GPU checkpoint preparation

This library binds the existing typed UEFI checkpoint selector, read-only GPT
verifier, handle discovery and Before/ExitBootServices lifetime to the installed
K80 `unixnu64` profile. It is deliberately absent from the board DSC/FDF. The
isolated firmware entry remains disabled; adding an INF does not authorize I/O.

The child must be GPT entry35, named `unixnu`, with the exact type/unique GUID,
4096-byte geometry and zero attributes in
[the storage descriptor](../../../../../payload/storage/unixnu64.json).
The HD device-path ordinal must agree. Both GPT copies and CRCs must agree with
the selected `PartitionInfo` entry. Android `userdata` is never a fallback.
The only prospective log block remains relative2291712 (absolute49563392).
An archived GPT is a test input, never a live UEFI handle or permission.

The code preserves the prior report layouts, raw64 statuses, separate child and
parent MediaId, persistent noncopy owners, single-use failure retention and real
EBS-event gates. Native services may block; the library cannot cancel an
in-flight service. WriteAuthorized, LiveDiscoveryVerified and RuntimeComplete
remain zero even when a host double successfully verifies archived GPT bytes.
No writer, SCM, MMIO or GPU operation is introduced here.

Run the focused host oracle with an existing Mu BaseCore SDK and the archived
GPT from this installation (not device paths):

```sh
python3 scripts/check-zorn-gpu-checkpoint.py \
  --sdk /path/to/mu_basecore \
  --primary /path/to/gpt-primary.after \
  --backup /path/to/gpt-backup.after \
  --out /path/to/new-empty-output
```

The host fixture uses synthetic interfaces/events and actual archived GPT bytes.
It checks the new identity, CRC-valid moved/duplicate entries, attributes,
warnings/raw errors, expiry, default OFF and four compiled guard mutations.
It never writes media. Firmware target and final-FD results are described in
[the evidence summary](../../../../../docs/evidence/gpu-unixnu64-checkpoint-2026-11-01.json).
The prior local capsule and all old claims remain historical and unchanged.
