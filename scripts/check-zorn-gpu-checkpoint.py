#!/usr/bin/env python3
"""Host-only unixnu64 checkpoint checks; never opens a device or enables I/O."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import struct
import subprocess
import uuid
import zlib


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', required=True, type=Path, help='existing Mu BaseCore root')
    parser.add_argument('--primary', required=True, type=Path, help='archived 6-sector GPT prefix')
    parser.add_argument('--backup', required=True, type=Path, help='archived 5-sector GPT suffix')
    parser.add_argument('--out', required=True, type=Path, help='new empty host output directory')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    src = root / 'Platforms/Xiaomi/zornPkg/Library/ZornGpuCheckpointLib'
    descriptor = root / 'payload/storage/unixnu64.json'
    d = json.loads(descriptor.read_text())
    pins = (src / 'ZornCheckpointStoragePins.h').read_text()
    for name, expected in [('PARTITION_FIRST', d['partition']['first_lba']),
                           ('PARTITION_LAST', d['partition']['last_lba']),
                           ('PARTITION_ORDINAL', 35), ('PARTITION_ATTRIBUTES', 0),
                           ('LOG_RELATIVE', d['log']['relative_lba'])]:
        match = re.search(r'#define ZCP_' + name + r' (\d+)', pins)
        assert match and int(match[1]) == expected, name
    assert '#define ZCP_PARTITION_NAME "' + d['partition']['name'] + '"' in pins
    for variable, expected in [('ZcpExpectedPartitionGuid', d['partition']['unique_guid']),
                               ('ZcpExpectedTypeGuid', d['partition']['type_guid'])]:
        match = re.search(variable + r'=\{(.*?)\};', pins)
        values = [int(x, 16) for x in re.findall(r'0x[0-9a-f]+', match[1])]
        assert struct.pack('<IHH8B', *values) == uuid.UUID(expected).bytes_le
    assert d['partition']['lba_bytes'] == 4096 and d['log']['blocks'] == 1
    assert d['partition']['bytes'] == (d['partition']['last_lba'] - d['partition']['first_lba'] + 1) * 4096
    assert d['log']['relative_lba'] == 2291712
    primary, backup = args.primary.read_bytes(), args.backup.read_bytes()
    assert len(primary) == 24576 and len(backup) == 20480
    for block, entries in [(primary[4096:8192], primary[8192:]),
                           (backup[16384:], backup[:16384])]:
        assert block[:8] == b'EFI PART' and struct.unpack_from('<I', block, 12)[0] == 92
        header = bytearray(block[:92])
        expected = struct.unpack_from('<I', header, 16)[0]
        struct.pack_into('<I', header, 16, 0)
        assert zlib.crc32(header) == expected
        count, size, crc = struct.unpack_from('<III', block, 80)
        assert (count, size) == (64, 128) and zlib.crc32(entries[:count*size]) == crc
        assert block[56:72] == uuid.UUID('dc8e1b86-0f82-0eeb-83b3-03527ac774a2').bytes_le
    assert primary[8192:] == backup[:16384]
    entry = primary[8192+34*128:8192+35*128]
    assert entry[:16] == uuid.UUID(d['partition']['type_guid']).bytes_le
    assert entry[16:32] == uuid.UUID(d['partition']['unique_guid']).bytes_le
    assert struct.unpack_from('<QQQ', entry, 32) == (d['partition']['first_lba'], d['partition']['last_lba'], 0)
    assert entry[56:].decode('utf-16le').rstrip('\0') == 'unixnu'
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise SystemExit('Use a new empty output directory; old evidence is never overwritten')
    includes = ['-I'+str(src), '-I'+str(args.sdk.resolve()/'MdePkg/Include'),
                '-I'+str(args.sdk.resolve()/'MdePkg/Include/AArch64')]
    flags = ['-fshort-wchar', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
             '-Wno-unused-parameter', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', *includes]
    commands = []

    def run(command, name, must_pass=True):
        command = list(map(str, command))
        result = subprocess.run(command, capture_output=True, text=True, timeout=55)
        commands.append(dict(arguments=command, returncode=result.returncode))
        (out / (name+'.log')).write_text(result.stdout+result.stderr)
        if must_pass:
            result.check_returncode()
        return result

    run(['clang', '-std=c11', *flags, '-c', src/'ZornCheckpointIdentity.c', '-o', out/'identity.o'], 'identity')
    sources = [src / ('ZornCheckpoint'+name+'.cpp') for name in ('ReadOnly', 'Discovery', 'BootLifetime')]
    run(['clang++', '-std=c++17', *flags, src/'test-unixnu64.cpp', *sources, out/'identity.o',
         '-lz', '-o', out/'host-check'], 'build')
    result = run([out/'host-check', args.primary.resolve(), args.backup.resolve()], 'run')
    checks = json.loads(result.stdout)
    # Actual guard mutations; each must compile, then fail the same host oracle.
    mutations = []
    for name, filename, old, new in [
        ('wrong-HD-ordinal', 'ZornCheckpointIdentity.c', 'u32(p+hd+4)!=ZCP_PARTITION_ORDINAL||', 'u32(p+hd+4)<ZCP_PARTITION_ORDINAL||'),
        ('attributes-accepted', 'ZornCheckpointIdentity.c', 'part->Info.Gpt.Attributes!=ZCP_PARTITION_ATTRIBUTES||', ''),
        ('moved-GPT-entry', 'ZornCheckpointReadOnly.cpp', 'i+1!=ZCP_PARTITION_ORDINAL||', ''),
        ('default-enabled', 'ZornCheckpointDiscovery.cpp', 'if(!enabled)return ZCD_DISABLED;', '(void)enabled;'),
    ]:
        original = (src/filename).read_text()
        assert original.count(old) == 1
        mutant = out/(name+Path(filename).suffix)
        mutant.write_text(original.replace(old, new))
        ident = out/'identity.o'
        changed = sources[:]
        if filename.endswith('.c'):
            ident = out/(name+'.o')
            run(['clang', '-std=c11', *flags, '-c', mutant, '-o', ident], name+'-identity')
        else:
            changed[changed.index(src/filename)] = mutant
        exe = out/name
        run(['clang++', '-std=c++17', *flags, src/'test-unixnu64.cpp', *changed, ident, '-lz', '-o', exe], name+'-build')
        refused = run([exe, args.primary.resolve(), args.backup.resolve()], name+'-run', must_pass=False)
        assert refused.returncode != 0, name
        mutations.append(dict(name=name, refused=True, returncode=refused.returncode))
    inputs = {str(p): sha(p) for p in [descriptor, args.primary, args.backup, Path(__file__), *src.glob('*')] if p.is_file()}
    # Capture actual recursively selected SDK headers, separate from host doubles.
    deps = run(['clang++', '-std=c++17', '-fshort-wchar', *includes, '-M', src/'test-unixnu64.cpp'], 'dependencies').stdout
    for item in shlex.split(deps.replace('\\\n', ' ').split(':', 1)[1]):
        p = Path(item)
        if p.is_file():
            inputs[str(p.resolve())] = sha(p)
    report = dict(checks=checks, mutations=mutations, commands=commands, inputs=inputs,
                  host_only=True, native_device_calls=0, WriteAuthorized=0,
                  allow_boot=False, readback_qualified=False)
    (out/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(checks=checks, mutations=len(mutations), result=str(out/'result.json'))))


if __name__ == '__main__':
    main()
