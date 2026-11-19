# uefi-zorn

[简体中文](README_CN.md)

Mu-Silicium board package for the Redmi K80 (`zorn`, SM8650-AB, 12 GB + 256 GB). **iOS 26.6.2 (23G90) is the active UniXNU port.** The iPadOS 17 GPU port is retired and recorded in the device repository. [Historical OS ports](https://github.com/kerrinz/UniXNU-zorn/blob/main/docs/archived-os.md)

This repository owns the firmware board package, BootShim, menu template and image packers. Use an existing Mu-Silicium checkout with its Common, Silicon, ACPI and EDK II inputs. [UniXNU-zorn](https://github.com/kerrinz/UniXNU-zorn) owns the kernel, device drivers, exact iOS 26 build evidence and [porting record](https://github.com/kerrinz/UniXNU-zorn/blob/main/porting.toml).

## Build and handoff

Use the staged Mu-Silicium build command and pinned inputs in the [firmware build and handoff guide](docs/build-and-handoff.md). The guide documents the BootShim mailbox and the read-only Block I/O published by `ZornBootMemoryDxe`. iOS 26 device trials bind the exact FD, loader, ADT, menu and root.

- `Platforms/Xiaomi/zornPkg/` contains the board DSC/FDF, memory map, boot-memory service and touch power handoff.
- `BootShim/` and `Resources/Configs/zorn.toml` contain the shim and board image parameters.
- `payload/` contains the menu template and storage descriptor. `scripts/` contains staging and packing tools.

The device runner operates on `92988a43` / `zorn` / slot A from verified Recovery, with an independent watchdog and explicit Android and Data protection. [Storage and Recovery boundaries](docs/storage-unixnu64.md)

New firmware code uses [BSD-2-Clause-Patent](LICENSE). Vendor binaries and generated images stay in the local workspace.
