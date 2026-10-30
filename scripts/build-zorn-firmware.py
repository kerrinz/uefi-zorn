#!/usr/bin/env python3
"""Build the zorn FD and record its compiled early-watchdog capability."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--uefi", type=Path, default=ROOT.parent / "Mu-Silicium")
parser.add_argument("--record-existing", action="store_true", help="record a just-completed build, after checking output timestamps")
args = parser.parse_args()
args.uefi = args.uefi.resolve()
subprocess.run(["python3", str(ROOT / "uefi-zorn/scripts/check-zorn-touch-power.py")], check=True)
if not args.record_existing:
    sys.path.insert(0, str(ROOT / 'UniXNU-zorn/scripts'))
    from zorn_legacy_device import prepare as prepare_legacy_device
    device = prepare_legacy_device(ROOT / 'UniXNU-zorn', ROOT / 'out/zorn/legacy-device')
    subprocess.run([ROOT / "UniXNU/unixnu", "build", "firmware", "-D", device,
                    "--uefi", args.uefi], cwd=ROOT / "UniXNU", check=True)
build = args.uefi / "Build/zornPkg/DEBUG_CLANGPDB"
fd = build / "FV/SILICIUM_UEFI.fd"
modules = [p for p in build.rglob("ZornBootMemoryDxe.efi") if p.parent.name == "OUTPUT"]
if len(modules) != 1 or fd.stat().st_size != 0x300000:
    raise SystemExit("Expected one compiled zorn module and a 3 MiB FD")
module = modules[0]
sources = [ROOT / "uefi-zorn/Platforms/Xiaomi/zornPkg" / p for p in
           ["Drivers/ZornBootMemoryDxe/ZornBootMemoryDxe.c", "Drivers/ZornBootMemoryDxe/ZornTouchPower.h", "Drivers/ZornBootMemoryDxe/ZornBootMemoryDxe.inf", "zorn.dsc", "zorn.fdf"]]
if module.stat().st_mtime < max(p.stat().st_mtime for p in sources) or fd.stat().st_mtime < module.stat().st_mtime:
    raise SystemExit("Firmware outputs predate sources; rebuild first")
pe = module.read_bytes()
peoff = int.from_bytes(pe[0x3c:0x40], "little")
if pe[:2] != b"MZ" or pe[peoff:peoff + 4] != b"PE\0\0" or int.from_bytes(pe[peoff + 4:peoff + 6], "little") != 0xaa64:
    raise SystemExit("Expected an actual AArch64 PE firmware module")
digest = hashlib.sha256(fd.read_bytes()).hexdigest()
out = ROOT / "out/zorn"
out.mkdir(parents=True, exist_ok=True)
archive = out / ("SILICIUM_UEFI-" + digest[:8] + ".fd")
shutil.copyfile(fd, archive)
record = {"fd": str(fd), "sha256": digest, "archive": str(archive),
          "touch_power_supported": True,
          "touch_power_audit": json.loads((out / "touch/power-host-check.json").read_text()),
          "module_sha256": hashlib.sha256(pe).hexdigest(), "early_watchdog_supported": True,
          "source_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
          "hardware_tested": False}
(out / "firmware.inputs.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2))
