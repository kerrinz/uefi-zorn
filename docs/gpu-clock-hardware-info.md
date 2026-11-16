# Clock hardware-information boundary

The exact selected ClockDxe filter uses a bootstrap protocol, services table
and double-indirect handle calls. It does not call the selected SDK's direct
`EFI_CHIPINFO_PROTOCOL` layout. Matching familiar method names is insufficient
to substitute one interface for the other.

The [offline check](../scripts/check-zorn-clock-hardware-info.py) requires the
preserved firmware recipe and creates a data-only target annotation:

```sh
python3 uefi-zorn/scripts/check-zorn-clock-hardware-info.py
```

It refuses a completed result. The annotation checks the actual public EFI
header types, offsets and GUID. Its numerical inequalities reject a possible
wrong mapping; they do not identify the functions at the private indirect
offsets. No proprietary DAL handle, vtable, callable typedef or request is
invented. The linked PE has no code or entry, uses no SDK library/old module
archive, and is never selected into a module, FD or device candidate.

The selected ClockDxe obtains the bootstrap GUID
`ae37b942-457f-4c91-a196-d9669fd347a3`, initializes a services table, attaches
device literal `0x0200006f` at interface version `0x10000`, and uses handle+8
before indirect calls at offsets `0x70` and `0x58`. Those calls' return status
is ignored before loading32-bit output slots. The exact native declarations
and their output guarantees are still unavailable in the selected SDK.

The filter's cached version word is written by initialization and can receive
zero after attach failure. An initial FILE zero, the nominal public enum counts
or a successful clock-resource lookup is not valid hardware information. No
eligibility model, variant/rate selection or voltage/vote ownership follows.

Existing selected generated section files were compared in place with their
independent archived bytes and source blobs; no new module extraction occurred.
The [evidence](evidence/gpu-clock-hardware-info-2026-11-01.json) binds these
consumer facts, the target ABI barrier and precise missing native contract.
The next source work must resolve that contract and provider registration with
traceable inputs. Provider/phone/GPU invocation and all prior consumed scopes
remain closed; existing capture and log formats remain unchanged.
