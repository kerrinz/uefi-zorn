#!/usr/bin/env python3
"""Build the ZORNESP FAT volume embedded in the zorn boot image.

The prelinked kernel is about 49 MiB and the packed restore ramdisk is
about 131 MiB, so the volume is 192 MiB FAT32 with 512-byte clusters.
The decompressed image stays well inside the 256 MiB kernel window.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
SECTORS = 192 * 2048  # 192 MiB; sparse ramdisk plus kernel, with room in the 256 MiB window
LABEL = b"ZORNESP    "


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
    parser.add_argument("-o", "--output", type=Path, default=REPO / "out/zorn/payload.img")
    args = parser.parse_args()
    toml, kernel, adt, root_img, out = args.toml, args.kernel, args.adt, args.root, args.output
    for path in (toml, kernel, adt, root_img):
        if not path.is_file():
            sys.exit(f"missing {path}")
    out.parent.mkdir(parents=True, exist_ok=True)
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
    run(["mcopy", "-i", str(out), "-Q", str(root_img), "::/EFI/UniXNU/Payloads/root.img"])
    data = bytearray(out.read_bytes())
    if len(data) != SECTORS * 512:
        sys.exit(f"image is {len(data)} bytes, expected {SECTORS * 512}")
    data[0x1BE:0x1FE] = b"\x00" * 64
    out.write_bytes(data)
    edk2_fat32(bytes(data))
    listing = subprocess.check_output(
        ["mdir", "-i", str(out), "-/", "::/EFI/UniXNU/Payloads"],
        env=dict(os.environ, MTOOLS_SKIP_CHECK="1", TZ="UTC"),
        text=True,
    )
    if "kernel.macho" not in listing or "root" not in listing.lower() or "unixnu" not in listing.lower():
        sys.exit(f"payload listing is missing the kernel:\n{listing}")
    print(listing)
    print(f"wrote {out} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
