# Selected ChipInfo registration and output boundary

The selected ChipInfoDxe publishes a direct EFI protocol under the package DEC
declaration `gEfiChipInfoProtocolGuid`,
`b0760469-970c-487a-a4b5-28db7b45cef1`. Its revision is `0x10005` and its
version, ID and family methods occupy offsets8/24/48. The header macro
`EFI_CHIPINFO_PROTOCOL_GUID` instead contains `61224fbe-...`. Both values are
retained; a future consumer must bind the selected declaration and provider,
without editing the SDK or silently substituting the stale macro.

This direct interface is separate from ClockDxe's private DAL handle. The
bootstrap GUID `ae37b942-...` leads to DALSys services; ordinary attach at
offset0xc8 and versioned attach at0xd0 are different entries. ChipInfo's module
registration has one driver and the device literal0x0200006f. Its attach path
constructs a handle whose second pointer reaches table RVA7f50. The exact
private DAL declarations remain unavailable in the searched selected headers
and pinned references. Binary call shapes do not supply those declarations.

The direct wrappers forward to private offsets0x48/0x58/0x70 and map any
nonzero private status to EFI_UNSUPPORTED. That mapping loses the private
error detail. The selected private implementations store32-bit cached values
and return zero. Initialization can receive no payload, still latch its
initialized flag, and return zero. Therefore even a successful direct getter
would not establish that its cached output came from valid hardware data.
The source, size and availability of the initialization payload remain a
separate contract to resolve. No nominal enum count becomes an eligibility
limit, and no frequency, variant, shared vote or voltage policy is selected.

The [offline checker](../scripts/check-zorn-dal-chipinfo.py) requires the
preserved selected blobs and firmware recipe:

```sh
python3 uefi-zorn/scripts/check-zorn-dal-chipinfo.py
```

It refuses an already completed result. Ten new registration/output semantic
corruptions are rejected after bypassing the outer SHA check. A new data-only
ARM64 annotation preserves both GUIDs and the direct prefix; independent LTO
objects have identical raw SHA. Its NOENTRY PE has zero code bytes and no
executable or writable sections. Three final-data corruptions are rejected.
No private typedef, request, native wrapper, FD, kernel or device candidate
is generated. The earlier public-versus-private ABI barrier is retained and
its suite is not repeated.

[Evidence](evidence/gpu-dal-chipinfo-2026-11-01.json) records the source hashes,
target annotation, registration edges and missing output contract. All prior
device claims remain consumed; native/provider/phone operations remain closed.
The query capture and existing log formats are unchanged.
