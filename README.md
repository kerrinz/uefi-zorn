# uefi-zorn

[【简体中文】](README_CN.md)

Mu-Silicium board package for the Redmi K80 (`zorn`, SM8650-AB, 12 GB + 256 GB), used to temporarily boot UniXNU / DarwinBoot with iPad7,1 / j120ap, iPadOS 17.7.11 (21H461).

This repository owns the K80 firmware board package, BootShim, menu template and image packers. It is not a complete Mu-Silicium checkout. Common, Silicon, ACPI, EDK II and shared UniXNU components retain their upstream sources. [UniXNU-zorn](https://github.com/kerrinz/UniXNU-zorn) owns the kernel, board services and authoritative [porting record](https://github.com/kerrinz/UniXNU-zorn/blob/main/porting.toml).

Official format-2 device documentation is generated from that device repository's root `board.toml` and `porting.toml`; this firmware repository does not publish a duplicate whole-device record. See the [publication guide](https://unixnu.com/zh/porting/records#publishing-and-reuse).

## State

As of 2026-10-30, the combined port has owner-confirmed desktop and basic single-touch interaction, eight-core checks, retained 8 GiB Data, an 8 GiB XNU window and brightness 64. The CPU1 narrow root-publication fix has same-kernel controls and two-layout evidence. A later Apple-logo GUI failure remains unresolved; the final `c50ca7ea` observation showed a lock screen and all-core accounting progress, then recovered automatically. It does not qualify performance, system multi-touch or long-term stability.

The firmware handoff includes the UEFI menu, five-second countdown, DarwinBoot, GOP and the existing touch power handoff. The latest CPU / display observations reused the recorded FD; no new firmware or phone run is implied by this update. Non-GPU results and their limits are synchronized in the [progress snapshot](docs/progress-2026-10-30-non-gpu.md). GPU development progress is outside this update.

## Prerequisites

- Matching sibling `UniXNU/` and `UniXNU-zorn/` checkouts, with their recorded source / component pins.
- The existing Mu-Silicium source and its required submodules, matching Xcode / SDK / toolchain, and the recorded giulia SM8650 DXE inputs. Proprietary firmware is not redistributed.
- Matching donor IPSW, trust cache, prepared Data / owner inputs and ABI audit artifacts for full image assembly; see [UniXNU-zorn build instructions](https://github.com/kerrinz/UniXNU-zorn/blob/main/docs/build-and-debug.md).

Read the [UEFI integration guide](https://unixnu.com/zh/porting/uefi-firmware), [device repository guide](https://unixnu.com/zh/porting/device-repository), [AGENTS.md](AGENTS.md) and [firmware handoff instructions](docs/build-and-handoff.md).

## Build entry points

From the common parent, stage this board into an existing Mu-Silicium tree and use the firmware builder:

```sh
sh uefi-zorn/scripts/stage-into-mu.sh /path/to/Mu-Silicium
python3 uefi-zorn/scripts/build-zorn-firmware.py --help
```

The actual build requires the selected legacy diagnostic configuration; follow [build-and-handoff.md](docs/build-and-handoff.md) for its configuration step and complete command. The output is `Build/zornPkg/DEBUG_CLANGPDB/FV/SILICIUM_UEFI.fd` in Mu-Silicium and must be 3 MiB. These examples do not flash or boot a device.

UniXNU-zorn now has a format-2 root configuration and a fixed compatibility board for the existing diagnostic builder. Host configuration / DTS / tree checks are separate from full native-build or device equivalence. Do not use historical runs as verification of a newly migrated output path.

## Firmware and image inputs

- FD base: `0xA7100000`, size `0x300000`.
- BootShim decompression window: `0xA8000000`–`0xB8000000` (256 MiB); payload mailbox: `0xA7601000`, `ZORNPLD1`.
- Framebuffer: `0xFC400000`, 1440 × 3200, row bytes 5760, 32 bpp.
- Payload: 192 MiB FAT32 with 512-byte clusters; Android boot header v4 and gzip, without an Android ramdisk or appended DTB.

The BootShim window, FAT allocation and XNU-owned memory window are separate. Do not enlarge a payload based on nominal RAM capacity. The format-2 host DTS does not replace the currently installed firmware DTB.

## Layout

- `Platforms/Xiaomi/zornPkg/`: DSC / FDF, memory map, boot-memory service and touch power handoff.
- `BootShim/`, `Resources/Configs/zorn.toml`: board shim and firmware / image parameters.
- `payload/EFI/UniXNU/unixnu.toml`: menu template.
- `scripts/`: staging, firmware build, payload packing and boot-image packing.
- `docs/`: handoff instructions and synchronized device-result summaries.

## Temporary boot and recovery

Use UniXNU-zorn's fixed-target runner with a matching ready / input manifest and independent watchdog. The only target is `92988a43` / `zorn` / slot `b`; `f85d4270` is a CC9 and must not be operated on. No flash, erase, slot or GPT changes.

Do not boot Android or reinstall userdata. OS / SystemOS stay read-only. Data, the single log block and recovery BCB retain the exact bounds in the device record; firmware packaging does not expand those permissions. The default `42f3d518` and two desktop-confirmed `3a8ac966` baselines remain preserved. Automatic work is currently paused at the owner's request.

## License

New files use [BSD-2-Clause-Patent](LICENSE); upstream files retain their notices. Apple inputs, vendor binaries and generated firmware / boot images are not committed here.
