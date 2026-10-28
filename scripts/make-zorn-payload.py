#!/usr/bin/env python3
"""Build the ZORNESP FAT volume embedded in the zorn boot image.

The verified prelinked kernel is about 120 MiB. The rootless payload uses
192 MiB FAT32 with 512-byte clusters; any optional RAM disk must fit too.
The decompressed image stays well inside the 256 MiB kernel window.
"""
import argparse
import hashlib
import os
import re
import struct
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
SECTORS = 192 * 2048  # 192 MiB; kernel and optional files, with room in the 256 MiB window
LABEL = b"ZORNESP    "
ORIGINAL_TRUST_SHA256 = "7416ca4f8377146626bb284e2133c76bee6cb4e3ee0af5d648b186235a7323a7"


def development_wifi_identity():
    """Stable locally administered address for this port, not a factory MAC."""
    address = bytearray(hashlib.sha256(b"UniXNU:zorn:development-wifi:v1\0" + b"92988a43").digest()[:6])
    address[0] = (address[0] & 0xfc) | 2
    return bytes(address)


def trustcache_adt(data, omit_ramdisk=False, with_trust_cache=True, packed_data=False,
                   owned_memory=None, cpu_fixups=None, wifi_identity=None):
    """Match loader placeholders to supplied files without changing the input."""
    def parse(at, depth=0):
        if depth > 32 or at + 8 > len(data):
            raise ValueError("invalid ADT node")
        np, nc = struct.unpack_from("<II", data, at)
        if np > 256 or nc > 256:
            raise ValueError("invalid ADT counts")
        at += 8
        properties = []
        for _ in range(np):
            start = at
            if at + 36 > len(data):
                raise ValueError("truncated ADT property")
            name = data[at:at + 32].split(b"\0", 1)[0]
            size = struct.unpack_from("<I", data, at + 32)[0] & 0x7fffffff
            at += 36
            value = data[at:at + size]
            at += (size + 3) & ~3
            if at > len(data):
                raise ValueError("ADT property exceeds input")
            properties.append((name, value, data[start:at]))
        children = []
        for _ in range(nc):
            child, at = parse(at, depth + 1)
            children.append(child)
        return [properties, children], at

    def emit(node):
        props, children = node
        return (struct.pack("<II", len(props), len(children)) +
                b"".join(p[2] for p in props) + b"".join(emit(c) for c in children))

    def child(node, name):
        matches = [c for c in node[1]
                   if any(p[0] == b"name" and p[1].rstrip(b"\0") == name for p in c[0])]
        if len(matches) != 1:
            raise ValueError(f"ADT requires exactly one {name!r} child")
        return matches[0]

    root, end = parse(0)
    if end != len(data) or emit(root) != data:
        raise ValueError("ADT did not round-trip exactly")
    chosen = child(root, b"chosen")
    memory = child(chosen, b"memory-map")
    def install(name, value, replace=False):
        matches = [p for p in chosen[0] if p[0] == name]
        if len(matches) > 1 or (matches and matches[0][1] != value and not replace):
            raise ValueError(f"conflicting ADT property {name!r}")
        chosen[0][:] = [p for p in chosen[0] if p[0] != name]
        raw = name.ljust(32, b"\0") + struct.pack("<I", len(value)) + value
        raw += bytes((-len(value)) & 3)
        chosen[0].append((name, value, raw))
    if owned_memory:
        previous = [p for p in chosen[0] if p[0] == b"darwinboot-memory-size"]
        if len(previous) != 1 or len(previous[0][1]) != 8:
            raise ValueError("memory experiment requires one explicit owned window")
        install(b"darwinboot-memory-size", struct.pack("<Q", owned_memory), replace=True)
    if cpu_fixups:
        install(b"display-scale", struct.pack("<I", 2))
        install(b"display-rotation", struct.pack("<I", 0))
        install(b"text-fixups", b"".join(s.encode("ascii") + b"\0" for s in cpu_fixups))
    if omit_ramdisk and packed_data:
        raise ValueError("Data seed and omitted initrd are mutually exclusive")
    if omit_ramdisk or packed_data:
        for prop in memory[0]:
            if prop[0] in (b"RAMDisk", b"PackedRAMDisk") and prop[1] != bytes(16):
                raise ValueError("cannot omit a ramdisk with a nonzero/invalid ADT allocation")
        memory[0][:] = [p for p in memory[0] if p[0] not in (b"RAMDisk", b"PackedRAMDisk")]
        # This flag describes volatile writable Data, not the authenticated
        # UFS OS/SystemOS volumes. Without their RAMDisk seed, keep no stale
        # declaration that can select ephemeral-storage startup behavior.
        chosen[0][:] = [p for p in chosen[0] if p[0] != b"ephemeral-storage"]
        if packed_data:
            raw = b"PackedRAMDisk".ljust(32, b"\0") + struct.pack("<I", 16) + bytes(16)
            memory[0].append((b"PackedRAMDisk", bytes(16), raw))
            value = struct.pack("<I", 1)
            raw = b"ephemeral-storage".ljust(32, b"\0") + struct.pack("<I", 4) + value
            chosen[0].append((b"ephemeral-storage", value, raw))
    if wifi_identity is not None:
        if len(wifi_identity) != 6 or wifi_identity[0] & 3 != 2:
            raise ValueError("development Wi-Fi identity must be six-byte locally administered unicast")
        install(b"mac-address-wifi0", wifi_identity)
    found = [p for p in memory[0] if p[0] == b"TrustCache"]
    if not with_trust_cache:
        if found:
            raise ValueError("ADT requests a trust cache but no sidecar was supplied")
        return emit(root)
    if found:
        if len(found) != 1 or found[0][1] != bytes(16):
            raise ValueError("TrustCache must be one zeroed 16-byte loader placeholder")
    else:
        raw = b"TrustCache".ljust(32, b"\0") + struct.pack("<I", 16) + bytes(16)
        memory[0].append((b"TrustCache", bytes(16), raw))
    return emit(root)


def run(cmd):
    subprocess.run(cmd, check=True, env=dict(os.environ, MTOOLS_SKIP_CHECK="1", TZ="UTC"))


def edk2_fat32(image: bytes):
    sec = image[:512]
    if sec[0] != 0xEB or sec[0x1FE:0x200] != b"\x55\xAA":
        raise SystemExit("boot sector signature is not a FAT boot sector")
    if sec[0x47:0x52] != LABEL:
        raise SystemExit(f"FAT32 label at +0x47 is {sec[0x47:0x52]!r}")
    if any(sec[0x1BE + i * 16 + 4] != 0 for i in range(4)):
        raise SystemExit("MBR partition type is still set")
    bps = int.from_bytes(sec[0x0B:0x0D], "little")
    spc = sec[0x0D]
    reserved = int.from_bytes(sec[0x0E:0x10], "little")
    fats = sec[0x10]
    tot16 = int.from_bytes(sec[0x13:0x15], "little")
    spf16 = int.from_bytes(sec[0x16:0x18], "little")
    tot32 = int.from_bytes(sec[0x20:0x24], "little")
    spf32 = int.from_bytes(sec[0x24:0x28], "little")
    flags = int.from_bytes(sec[0x28:0x2A], "little")
    version = int.from_bytes(sec[0x2A:0x2C], "little")
    sectors = tot32 if tot16 == 0 else tot16
    if spf16 != 0 or fats == 0 or reserved == 0 or sectors == 0 or spf32 == 0:
        raise SystemExit("BPB is not the FAT32 shape EDK2 expects")
    if version != 0 or (flags & 0x80):
        raise SystemExit("FAT32 header is not mountable")
    if bps != 512 or spc == 0 or (spc & (spc - 1)):
        raise SystemExit(f"sector {bps} cluster {spc} rejected")
    first = reserved + fats * spf32
    clusters = (sectors - first) // spc
    if clusters < 0xFFF5:
        raise SystemExit(f"only {clusters} clusters; EDK2 Fat wants at least 65525")
    print(f"FAT32 {sectors} sectors, {spc} sector/cluster, {clusters} clusters")


def main():
    parser = argparse.ArgumentParser(description="Pack the ZORNESP FAT volume. Does not flash.")
    parser.add_argument("--toml", type=Path, default=ROOT / "payload/EFI/UniXNU/unixnu.toml")
    parser.add_argument("--kernel", type=Path, default=REPO / "UniXNU/out/zorn/kernel/kernel.macho")
    parser.add_argument("--adt", type=Path, default=REPO / "out/zorn/kernel.macho.adt")
    parser.add_argument("--root", type=Path, default=REPO / "out/zorn/root.img")
    parser.add_argument("--no-initrd", action="store_true", help="readonly UFS root; omit the unused restore ramdisk")
    parser.add_argument("--data-seed", type=Path, help="DBRDISK1 volatile Data seed; root remains readonly UFS md0")
    parser.add_argument("--display-mode", type=int, choices=(1, 2, 3), help="display lifecycle (1), publication (2), or CPU presentation (3)")
    parser.add_argument("--memory-mib", type=int, help="derive an owned window of 256..8192 MiB, allocated by UEFI from actual free memory")
    parser.add_argument("--gui-watch", action="store_true", help="opt-in bounded passive GUI process/thread observations")
    parser.add_argument("--gui-user-stacks", action="store_true", help="opt-in bounded original-VM GUI frame reads with independent timeout recovery")
    parser.add_argument("--gui-kernel-stacks", action="store_true", help="bounded nofault capture of blocked GUI kernel stacks; single CPU only")
    parser.add_argument("--gui-runnable-kernel-stacks", action="store_true", help="also inspect referenced, non-current runnable kernel contexts; explicit CPU0 diagnostic")
    parser.add_argument("--gui-launchservices", action="store_true", help="sample lsd instead of launchd, with bounded user-stack reads")
    parser.add_argument("--gui-service-thread", type=int, default=0, help="sample an lsd thread window starting at ordinal 0..63")
    parser.add_argument("--gui-backboard-thread", type=int, default=0, help="sample a backboardd thread window starting at ordinal 0..63")
    parser.add_argument("--development-wifi-identity", action="store_true", help="add a local development MAC for MobileGestalt identity queries; no Wi-Fi transport")
    parser.add_argument("--data-permissions", action="store_true", help="numeric metadata repair on this boot's verified RAM Data only")
    parser.add_argument("--keystore-state", action="store_true", help="upstream AppleKeyStoreState for volatile unprotected RAM Data only")
    parser.add_argument("--shared-data-volume", action="store_true", help="use original APFS shared-Data mode for the single RAM Data volume")
    parser.add_argument("--data-store-mode", type=int, choices=(0, 1, 2), default=0,
                        help="optional exact reserved Data overlay; 1 readonly probe, 2 write-through")
    parser.add_argument("--retained-data", action="store_true", help="require existing Data marker; no first-boot template replay")
    parser.add_argument("--quiet-gui", action="store_true", help="keep GUI snapshots but omit verbose user-write/exec capture")
    parser.add_argument("--brightness-mode", type=int, choices=(0, 1, 2, 3, 4), default=0,
                        help="K80 brightness: registers (1), DCS read (2), low limit/readback (3), short dim test (4)")
    parser.add_argument("--touch-probe", action="store_true", help="read-only touch/display handoff; short recovery test")
    parser.add_argument("--touch-handoff", action="store_true", help="explicit K80 touch power and clock votes in UEFI")
    parser.add_argument("--touch-identify", action="store_true", help="bounded FT3683 GPIO SPI ID read after native handoff")
    parser.add_argument("--touch-frames", action="store_true", help="bounded 20-second raw FT3683 frame reads after ID; no HID")
    parser.add_argument("--hid-family", action="store_true", help="load original HID OS services without publishing a touch/input device")
    parser.add_argument("--minimal-services", action="store_true", help="apply an upstream-derived temporary service policy on RAM Data")
    parser.add_argument("--lite-services", action="store_true", help="use the upstream sheng-lite list instead of the four-job minimal list")
    parser.add_argument("--disable-jobs", default="", help="additional comma-separated launchd labels for the temporary RAM Data policy")
    parser.add_argument("--gui-hold-seconds", type=int, default=0, help="explicit bounded startup observer keepalive (30..1800 seconds)")
    parser.add_argument("--disable-dyld-compact-info", action="store_true", help="request Apple's dyld bit 19; this does not qualify Atlas as disabled on dyld-1165.3")
    parser.add_argument("--checkpoint", help="override the derived menu's bounded recovery checkpoint")
    parser.add_argument("--early-watchdog", type=int, choices=(0, 1, 2), default=0,
                        help="opt-in UEFI Gunyah watchdog; requires host-verified recovery BCB (2 deliberately stops UEFI)")
    parser.add_argument("--trust-cache", type=Path, help="unchanged original 21H461 static+System bundle")
    parser.add_argument("-o", "--output", type=Path, default=REPO / "out/zorn/payload.img")
    args = parser.parse_args()
    if args.touch_handoff and (not args.touch_probe or args.early_watchdog != 1):
        parser.error("touch handoff requires bounded touch probe and early watchdog")
    if args.touch_frames and not args.touch_identify:
        parser.error("--touch-frames requires --touch-identify")
    if args.touch_identify and not (args.touch_handoff and args.touch_probe):
        parser.error("touch ID requires probe and native handoff")
    if args.retained_data and (args.data_store_mode!=2 or not args.data_permissions):
        parser.error("--retained-data requires mode2 and guarded Data metadata policy")
    if args.touch_probe:
        if args.display_mode!=3 or args.early_watchdog!=1 or args.brightness_mode or (args.checkpoint and args.checkpoint!="TOUCHRO"):
            parser.error("touch probe requires CPU display/watchdog, no brightness transaction, TOUCHRO checkpoint")
        args.checkpoint="TOUCHRO"
    if args.brightness_mode:
        expected_checkpoint = "BLFAIL" if args.brightness_mode == 3 else "BLSNAP"
        if args.display_mode != 3 or args.early_watchdog != 1 or (args.checkpoint and args.checkpoint != expected_checkpoint):
            parser.error("brightness requires CPU display, watchdog and its recovery checkpoint")
        args.checkpoint = expected_checkpoint
    toml, kernel, adt, root_img, out = args.toml, args.kernel, args.adt, args.root, args.output
    if args.display_mode and not args.data_seed:
        parser.error("display experiment requires the independent RAM Data seed")
    if args.gui_watch and args.display_mode != 3:
        parser.error("--gui-watch requires --display-mode 3 and an independent RAM Data seed")
    if args.gui_user_stacks and (not args.gui_watch or args.early_watchdog != 1):
        parser.error("--gui-user-stacks requires --gui-watch and --early-watchdog 1")
    if args.gui_launchservices and not args.gui_user_stacks:
        parser.error("--gui-launchservices requires --gui-user-stacks")
    if args.gui_kernel_stacks and not args.gui_user_stacks:
        parser.error("--gui-kernel-stacks requires --gui-user-stacks")
    if args.gui_runnable_kernel_stacks and not args.gui_kernel_stacks:
        parser.error("--gui-runnable-kernel-stacks requires --gui-kernel-stacks")
    if not 0 <= args.gui_service_thread <= 63 or (args.gui_service_thread and not args.gui_launchservices):
        parser.error("--gui-service-thread requires --gui-launchservices and an ordinal 0..63")
    if not 0 <= args.gui_backboard_thread <= 63 or (args.gui_backboard_thread and not args.gui_user_stacks):
        parser.error("--gui-backboard-thread requires --gui-user-stacks and an ordinal 0..63")
    if args.development_wifi_identity and args.display_mode != 3:
        parser.error("--development-wifi-identity requires the CPU GUI profile")
    if args.data_permissions and (not args.minimal_services or not args.gui_launchservices):
        parser.error("--data-permissions requires --minimal-services and --gui-launchservices")
    if args.keystore_state and (args.display_mode != 3 or not args.data_seed):
        parser.error("--keystore-state requires --display-mode 3 and an independent RAM Data seed")
    if args.shared_data_volume and not args.data_seed:
        parser.error("--shared-data-volume requires an independent RAM Data seed")
    if args.data_store_mode and (not args.data_seed or not args.gui_watch or args.early_watchdog != 1):
        parser.error("--data-store-mode requires Data seed and GUI watchdog")
    if args.quiet_gui and not args.gui_watch:
        parser.error("--quiet-gui requires --gui-watch")
    if args.hid_family and args.display_mode != 3:
        parser.error("--hid-family requires --display-mode 3")
    if args.minimal_services and (not args.data_seed or not args.gui_watch or args.early_watchdog != 1):
        parser.error("--minimal-services requires RAM Data, --gui-watch and --early-watchdog 1")
    if args.lite_services and not args.minimal_services:
        parser.error("--lite-services requires --minimal-services")
    extra_jobs = args.disable_jobs.split(",") if args.disable_jobs else []
    if extra_jobs and (not args.minimal_services or len(args.disable_jobs) > 199 or len(extra_jobs) > 32 or
                       any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", name) for name in extra_jobs)):
        parser.error("--disable-jobs requires --minimal-services, at most 32 labels and 199 ASCII label characters")
    if args.gui_hold_seconds and (not args.gui_watch or args.early_watchdog != 1 or not 30 <= args.gui_hold_seconds <= 1800):
        parser.error("--gui-hold-seconds requires --gui-watch, --early-watchdog 1 and 30..1800 seconds")
    if args.disable_dyld_compact_info and args.display_mode != 3:
        parser.error("--disable-dyld-compact-info requires --display-mode 3")
    if args.memory_mib is not None and (not 256 <= args.memory_mib <= 8192 or args.memory_mib % 2):
        parser.error("owned memory must be 256..8192 MiB, aligned to 2 MiB")
    cpu_fixups = None
    if args.display_mode == 3:
        import json
        profile = REPO / "UniXNU/profiles/os/ipados-17.7.11-21H461/profile.toml"
        proof = json.loads((REPO / "out/zorn/cpu-profile/profile.json").read_text())
        cpu_fixups = tomllib.loads(profile.read_text())["payload"]["text_fixups"][:3]
        if proof["profile_sha256"] != hashlib.sha256(profile.read_bytes()).hexdigest() or \
                [c["entry"] for c in proof["checks"]] != cpu_fixups or \
                not all(c["original_bytes_match"] for c in proof["checks"]):
            parser.error("prepare and verify the exact CPU OS profile before packaging")
    if args.checkpoint and (not 1 <= len(args.checkpoint) <= 7 or
                            any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" for c in args.checkpoint)):
        parser.error("checkpoint must contain 1..7 uppercase letters/digits")
    if args.data_seed:
        if args.no_initrd:
            parser.error("--data-seed cannot be combined with --no-initrd")
        root_img = args.data_seed.resolve()
        sys.path.insert(0, str(REPO / "UniXNU/drivers/DarwinBoot/Test"))
        import packed_ramdisk
        seed, _ = packed_ramdisk.inspect(root_img)
        if not seed["packed"] or seed["bytes"] > 2 * 1024**3:
            parser.error("volatile Data requires a packed seed no larger than 2 GiB")
    for path in (toml, kernel, adt) + (() if args.no_initrd else (root_img,)):
        if not path.is_file():
            sys.exit(f"missing {path}")
    if args.no_initrd:
        entries = tomllib.loads(toml.read_text()).get("entry", [])
        xnu = [e for e in entries if e.get("type") == "xnu"]
        if len(xnu) != 1 or xnu[0].get("initrd") or "rd=md0" not in xnu[0].get("args", "").split():
            sys.exit("--no-initrd requires one XNU entry with rd=md0 and no initrd")
    if args.data_seed or args.display_mode or args.checkpoint:
        parts = toml.read_text().split("[[entry]]")
        count = 0
        for index in range(1, len(parts)):
            entry = tomllib.loads("[[entry]]" + parts[index])["entry"][0]
            if entry.get("type") != "xnu":
                continue
            if entry.get("initrd") or "rd=md0" not in entry.get("args", "").split():
                parser.error("Data seed requires a UFS md0 XNU entry without another initrd")
            if args.data_seed:
                parts[index] += '\ninitrd = "Payloads/data.dbr"\n'
            if args.display_mode or args.checkpoint or args.shared_data_volume:
                import json
                tokens = entry.get("args", "").split()
                tokens = [t for t in tokens if t != "-apfs_shared_datavolume"]
                if args.shared_data_volume:
                    tokens.append("-apfs_shared_datavolume")
                checkpoint = args.checkpoint
                if args.display_mode:
                    prefixes = ("offline-mobile-graphics-load=", "offline-legacy-register=", "offline-legacy-gop=",
                                "offline-legacy-phase=", "zorn_display=", "zorn_exec_budget=",
                                "offline-legacy-pm=", "offline-legacy-validate=", "offline-legacy-transfer=",
                                "offline-legacy-cpu-present=", "sheng-vsync=", "wfi=", "armcpu-diagnostics=", "zorn_gui_watch=", "zorn_gui_hold=",
                                "offline-key-events=", "sheng-aks=", "zorn_data_store=", "zorn_data_retained=", "zorn_brightness=", "zorn_touch=", "zorn_gui_quiet=", "zorn_hid_family=", "zorn_gui_stack=", "zorn_gui_kstack=", "zorn_gui_krun=", "zorn_gui_service=", "zorn_gui_service_thread=", "zorn_gui_backboard_thread=",
                                "sheng-disable-jobs=", "sheng-disable-watchdogd=", "sheng-lite=", "zorn_data_permissions=")
                    tokens = [t for t in tokens if not t.startswith(prefixes)]
                    tokens += ["offline-mobile-graphics-load=1", "offline-legacy-register=1",
                               "offline-legacy-gop=1", "offline-legacy-phase=4", f"zorn_display={min(args.display_mode, 2)}"]
                    if args.display_mode >= 2:
                        tokens.append("zorn_exec_budget=180")
                    if args.display_mode == 3:
                        if args.touch_probe:
                            tokens.append("zorn_touch=3" if args.touch_frames else "zorn_touch=2" if args.touch_identify else "zorn_touch=1")
                        if args.brightness_mode:
                            tokens.append("zorn_brightness=" + str(args.brightness_mode))
                        if args.retained_data:
                            tokens.append("zorn_data_retained=1")
                        tokens += ["offline-legacy-pm=1", "offline-legacy-validate=1", "offline-legacy-transfer=1",
                                   "offline-legacy-cpu-present=1", "sheng-vsync=60", "wfi=0", "armcpu-diagnostics=1"]
                        if args.keystore_state:
                            tokens += ["offline-key-events=1", "sheng-aks=1"]
                        if args.gui_watch:
                            tokens.append("zorn_gui_watch=1")
                        if args.gui_user_stacks:
                            tokens.append("zorn_gui_stack=1")
                        if args.gui_kernel_stacks:
                            tokens.append("zorn_gui_kstack=1")
                        if args.gui_runnable_kernel_stacks:
                            tokens.append("zorn_gui_krun=1")
                        if args.data_store_mode:
                            if any(t.startswith(("sheng-data-reset=", "sheng-data-persist=")) for t in tokens):
                                raise ValueError("Reserved Data overlay forbids implicit reset or another store provider")
                            tokens.append("zorn_data_store=" + str(args.data_store_mode))
                        if args.gui_launchservices:
                            tokens.append("zorn_gui_service=1")
                        if args.gui_service_thread:
                            tokens.append("zorn_gui_service_thread=" + str(args.gui_service_thread))
                        if args.gui_backboard_thread:
                            tokens.append("zorn_gui_backboard_thread=" + str(args.gui_backboard_thread))
                        if args.data_permissions:
                            tokens.append("zorn_data_permissions=1")
                        if args.quiet_gui:
                            tokens.append("zorn_gui_quiet=1")
                        if args.hid_family:
                            tokens.append("zorn_hid_family=1")
                        if args.minimal_services:
                            tokens.append("sheng-disable-watchdogd=1")
                            if args.lite_services:
                                tokens.append("sheng-lite=1")
                                jobs = list(extra_jobs)
                            else:
                                jobs = ["com.apple.identityservicesd", "com.apple.locationd", "com.apple.CommCenter", "com.apple.bluetoothd", *extra_jobs]
                            if jobs:
                                jobs_text = ",".join(jobs)
                                if len(jobs_text) > 199:
                                    parser.error("combined --disable-jobs labels exceed the native 199-byte input")
                                tokens.append("sheng-disable-jobs=" + jobs_text)
                        if args.gui_hold_seconds:
                            tokens.append("zorn_gui_hold=" + str(args.gui_hold_seconds))
                        if args.disable_dyld_compact_info:
                            flags = [t for t in tokens if t.startswith("dyld_flags=")]
                            if len(flags) > 1:
                                parser.error("multiple dyld_flags entries")
                            previous = int(flags[0].split("=", 1)[1], 0) if flags else 0
                            if not 0 <= previous < (1 << 64):
                                parser.error("dyld_flags exceeds its unsigned 64-bit ABI")
                            tokens = [t for t in tokens if not t.startswith("dyld_flags=")]
                            tokens.append("dyld_flags=" + hex((previous | 0x80000) & ~0x40000))
                    checkpoint = checkpoint or ("DSPINIT" if args.display_mode == 1 else "NOHIT")
                if checkpoint:
                    tokens = [t for t in tokens if not t.startswith("zorn_checkpoint=")]
                    tokens.append("zorn_checkpoint=" + checkpoint)
                parts[index], changed = re.subn(r'(?m)^args[ \t]*=[ \t]*"[^\n]*"[ \t]*$',
                                                 lambda _: "args = " + json.dumps(" ".join(tokens)), parts[index])
                if changed != 1:
                    parser.error("expected exactly one quoted XNU args line")
            count += 1
        if count != 1:
            parser.error("Data seed requires exactly one XNU entry")
        toml = out.parent / ("payload-ramdata.toml" if args.data_seed else "payload-debug.toml")
        toml.parent.mkdir(parents=True, exist_ok=True)
        toml.write_text("[[entry]]".join(parts))
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.trust_cache:
        trust = args.trust_cache.read_bytes()
        if hashlib.sha256(trust).hexdigest() != ORIGINAL_TRUST_SHA256:
            sys.exit("trust cache is not the pinned original 21H461 static+System bundle")
    if args.trust_cache or args.no_initrd or args.data_seed:
        handoff = trustcache_adt(adt.read_bytes(), omit_ramdisk=args.no_initrd,
                                with_trust_cache=bool(args.trust_cache), packed_data=bool(args.data_seed),
                                owned_memory=args.memory_mib * 1024**2 if args.memory_mib else None,
                                cpu_fixups=cpu_fixups,
                                wifi_identity=development_wifi_identity() if args.development_wifi_identity else None)
        adt = out.parent / "payload-with-trustcache.adt"
        adt.write_bytes(handoff)
        print(f"loader ADT {len(handoff)} bytes; initrd={'omitted' if args.no_initrd else 'present'}")
    if out.exists():
        out.unlink()
    run([
        "mformat", "-C", "-F", "-c", "1", "-T", str(SECTORS),
        "-v", "ZORNESP", "-N", "53484e47", "-i", str(out), "::",
    ])
    for directory in ("::/EFI", "::/EFI/UniXNU", "::/EFI/UniXNU/Payloads"):
        run(["mmd", "-i", str(out), directory])
    run(["mcopy", "-i", str(out), "-Q", str(toml), "::/EFI/UniXNU/unixnu.toml"])
    run(["mcopy", "-i", str(out), "-Q", str(kernel), "::/EFI/UniXNU/Payloads/kernel.macho"])
    run(["mcopy", "-i", str(out), "-Q", str(adt), "::/EFI/UniXNU/Payloads/kernel.macho.adt"])
    if not args.no_initrd:
        initrd_name = "data.dbr" if args.data_seed else "root.img"
        run(["mcopy", "-i", str(out), "-Q", str(root_img), "::/EFI/UniXNU/Payloads/" + initrd_name])
    if args.trust_cache:
        run(["mcopy", "-i", str(out), "-Q", str(args.trust_cache),
             "::/EFI/UniXNU/Payloads/kernel.macho.trustcache"])
    data = bytearray(out.read_bytes())
    if len(data) != SECTORS * 512:
        sys.exit(f"image is {len(data)} bytes, expected {SECTORS * 512}")
    data[0x1BE:0x1FE] = b"\x00" * 64
    if args.early_watchdog:
        marker = b"ZORNGHWD" + struct.pack("<II", args.early_watchdog, args.early_watchdog ^ 0xffffffff)
        data[0x180:0x190] = marker
        backup = int.from_bytes(data[0x32:0x34], "little")
        reserved = int.from_bytes(data[0x0e:0x10], "little")
        if not 0 < backup < reserved:
            sys.exit("invalid FAT backup boot sector for early-watchdog marker")
        data[backup * 512 + 0x180:backup * 512 + 0x190] = marker
    if args.touch_handoff:
        marker = b"ZORNTPWR" + struct.pack("<II", 1, 0xfffffffe)
        data[0x190:0x1a0] = marker
        data[backup * 512 + 0x190:backup * 512 + 0x1a0] = marker
    out.write_bytes(data)
    edk2_fat32(bytes(data))
    listing = subprocess.check_output(
        ["mdir", "-i", str(out), "-/", "::/EFI/UniXNU/Payloads"],
        env=dict(os.environ, MTOOLS_SKIP_CHECK="1", TZ="UTC"),
        text=True,
    )
    if "kernel.macho" not in listing or "unixnu" not in listing.lower():
        sys.exit(f"payload listing is missing the kernel:\n{listing}")
    if not args.no_initrd and ("data" if args.data_seed else "root") not in listing.lower():
        sys.exit("payload is missing the requested restore ramdisk")
    if args.no_initrd and "root" in listing.lower():
        sys.exit("unexpected restore ramdisk in the UFS-only payload")
    if args.trust_cache and "kernel.macho.trustcache" not in listing:
        sys.exit("payload is missing trust cache sidecar")
    print(listing)
    print(f"wrote {out} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
