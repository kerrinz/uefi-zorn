#!/usr/bin/env python3
"""Pack gzip(BootShim + UEFI FD) into an Android boot header v4 image.

Xiaomi ABL on this generation keeps the DTB in the on-device vendor_boot
image and applies its own memory fixups. This container does not append a
device tree and does not include a ramdisk. It is for `fastboot boot` only.
Nothing here writes a partition.
"""
import argparse
import gzip
import hashlib
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = 4096
HEADER_SIZE = 1584
FD_SIZE = 0x300000
FD_BASE = 0xA7100000
# ABL decompresses the kernel at the start of the reserved Kernel window.
# The FAT appended after the FD has to stay inside that window.
KERNEL_LOAD = 0xA8000000
KERNEL_END = 0xB8000000


def llvm(name):
    found = shutil.which(name)
    if found:
        return found
    for prefix in ("/opt/homebrew/opt/llvm/bin", "/usr/local/opt/llvm/bin"):
        candidate = Path(prefix) / name
        if candidate.is_file():
            return str(candidate)
    sys.exit(f"{name} not found")


def os_version(major, minor, patch):
    return (major << 14) | (minor << 7) | patch


def os_patch(year, month):
    # AOSP: 7 bits of years since 2000, 4 bits of month.
    return ((year - 2000) << 4) | month


def compile_shim(scratch, payload_size):
    clang, objcopy, nm = llvm("clang"), llvm("llvm-objcopy"), llvm("llvm-nm")
    obj = scratch / "shim.o"
    subprocess.run(
        [clang, "--target=aarch64-none-elf", "-c",
         f"-DFD_BASE={FD_BASE}", f"-DFD_SIZE={FD_SIZE}",
         f"-DPAYLOAD_SIZE={payload_size}",
         "-DREQUIRES_KERNEL_HEADER=1",
         ROOT / "BootShim/BootShim.S", "-o", obj],
        check=True)
    subprocess.run([objcopy, "-O", "binary", obj, scratch / "shim.bin"], check=True)
    shim = (scratch / "shim.bin").read_bytes()
    symbols = subprocess.check_output([nm, "-n", obj], text=True)
    payload = next(int(line.split()[0], 16) for line in symbols.splitlines() if line.endswith(" _Payload"))
    if payload != len(shim):
        sys.exit("payload label is not at the end of the shim")
    image_size = len(shim) + FD_SIZE + payload_size
    if shim[56:60] != b"ARM\x64" or struct.unpack_from("<QQ", shim, 8) != (FD_BASE, image_size):
        sys.exit(f"ARM64 header does not describe shim + FD + payload ({image_size:#x})")
    return shim


def pack(kernel, ramdisk):
    header = bytearray(HEADER_SIZE)
    header[0:8] = b"ANDROID!"
    # signature size 0 matches the zorn TWRP v4 header. os version is Android 15,
    # patch 2024-09. A non-empty ramdisk is the UniXNU payload FAT volume.
    struct.pack_into("<4I", header, 8, len(kernel), len(ramdisk),
                     (os_version(15, 0, 0) << 11) | os_patch(2024, 9),
                     HEADER_SIZE)
    struct.pack_into("<I", header, 0x28, 4)
    struct.pack_into("<I", header, HEADER_SIZE - 4, 0)
    kernel_pad = (-len(kernel)) % PAGE
    ramdisk_pad = (-len(ramdisk)) % PAGE
    return (bytes(header) + b"\0" * (PAGE - HEADER_SIZE)
            + kernel + b"\0" * kernel_pad
            + ramdisk + b"\0" * ramdisk_pad)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fd", type=Path, required=True)
    parser.add_argument("--ramdisk", type=Path, help="FAT payload volume; omit for an empty ramdisk")
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()
    firmware = args.fd.read_bytes()
    if len(firmware) != FD_SIZE:
        sys.exit(f"FD is {len(firmware):#x} bytes, zorn.toml says {FD_SIZE:#x}")
    ramdisk = b""
    if args.ramdisk is not None:
        ramdisk = args.ramdisk.read_bytes()
        if len(ramdisk) == 0 or len(ramdisk) % 512:
            sys.exit("ramdisk must be a non-empty multiple of 512 bytes")
    scratch = args.output.parent / "shim-scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    # The FAT volume is appended to the FD inside the gzip. ABL decompresses
    # that as the kernel image. BootShim records its runtime address at
    # 0xA7601000. The Android ramdisk field stays empty: this ABL did not
    # leave an uncompressed v4 ramdisk in cacheable DRAM.
    shim = compile_shim(scratch, len(ramdisk))
    payload_end = KERNEL_LOAD + len(shim) + FD_SIZE + len(ramdisk)
    if payload_end > KERNEL_END:
        sys.exit(
            f"embedded FAT ends at {payload_end:#x}, past the reserved kernel window {KERNEL_END:#x}"
        )
    kernel = gzip.compress(shim + firmware + ramdisk, mtime=0)
    image = pack(kernel, b"")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(image)
    got = image[PAGE:PAGE + len(kernel)]
    if gzip.decompress(got) != shim + firmware + ramdisk:
        sys.exit("gzip payload did not round-trip")
    print(f"wrote {args.output} ({len(image)} bytes, sha256 {hashlib.sha256(image).hexdigest()})")
    print(f"embedded FAT {len(ramdisk)} bytes; no Android ramdisk; no appended DTB; fastboot boot only")


if __name__ == "__main__":
    main()
