#!/usr/bin/env python3
"""Bind selected DAL registration and the distinct outer EFI ChipInfo prefix.

Offline FILE inspection only. Requires preserved selected blobs, the prior
bounded PE reader and firmware recipe. Never declares a private DAL ABI,
calls firmware, or constructs a hardware-info request/device candidate.
"""
from pathlib import Path
import ast
import hashlib
import json
import re
import shlex
import struct
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'out/zorn/gpu-dal-chipinfo-contract'
PARENT = ROOT/'out/zorn/gpu-resource-observation-candidate'
MU = ROOT.parent/'Mu-Silicium'
PKG = MU/'Silicon/Qualcomm/QcomPkg'
READER = ROOT/'out/zorn/gpu-real-caller/audit-module.py'
BLOBS = MU/'Binaries/giulia/QcomPkg/Drivers'
HASHES = {
    'DALSYSDxe': '295f1465f9f9679fdb4e6188e6d71db1486ea3bc4003447af40b72d088ecb96d',
    'ChipInfoDxe': '38c7c0d036ff9e9fc0700983874bca910d87b2d853e22dd6c1d542a8757a5185',
}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reader_class():
    node = next(n for n in ast.parse(READER.read_text()).body
                if isinstance(n, ast.ClassDef) and n.name == 'PE')
    ns = dict(Path=Path, struct=struct)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(READER), 'exec'), ns)
    return ns['PE']


def dec_guid():
    # Only this named declaration; not a general DEC parser or a guessed GUID.
    text = (PKG/'QcomPkg.dec').read_text()
    rows = re.findall(r'^\s*gEfiChipInfoProtocolGuid\s*=\s*(\{[^\n]+\})', text, re.M)
    require(len(rows) == 1, 'ambiguous selected package GUID')
    values = [int(x, 16) for x in re.findall(r'0x[0-9a-fA-F]+', rows[0])]
    require(len(values) == 11, 'selected GUID initializer shape')
    return struct.pack('<IHH8B', *values), rows[0]


def inspect(dal, chip, guid):
    def u64(pe, at):
        return struct.unpack('<Q', pe.read(at, 8))[0]

    def words(pe, at, expected):
        require(pe.read(at, len(expected)*4) == struct.pack('<'+'I'*len(expected), *expected),
                'instruction contract at '+hex(at))

    bootstrap = uuid.UUID('ae37b942-457f-4c91-a196-d9669fd347a3').bytes_le
    require(dal.read(0x29068, 16) == bootstrap, 'DAL bootstrap registration GUID')
    require(u64(dal, 0x290b8) == 0x10002 and u64(dal, 0x290c0) == 0x14a0,
            'bootstrap revision/init table')
    words(dal, 0x1558, [0x90000141, 0x90000142, 0x9101a021, 0x9102e042])
    words(dal, 0x1578, [0xf940a508, 0xd63f0100])
    # Init publishes services290d0 through output x2 before initialization calls.
    words(dal, 0x14b4, [0x90000149, 0xaa0103f3, 0xaa0003f4, 0x91034129,
                       0x394162a8, 0xf9000049])
    require(u64(dal, 0x290d0+0xc8) == 0x2e64, 'ordinary attach service')
    require(u64(dal, 0x290d0+0xd0) == 0x2fcc, 'versioned attach service')
    # Registry slot search then attach callback with x0=0, w1=device, x2=out.
    words(dal, 0x2dfc, [0xf8296940])
    words(dal, 0x2ef8, [0xf94001a8, 0xaa1f03e0, 0x2a0203e1, 0xaa1303e2, 0xd63f0100])
    words(dal, 0x2fe4, [0x2a0103f3, 0x2a0103e0, 0xaa0303e1,
                       0xaa0303f5, 0x2a0203f4])
    words(dal, 0x3000, [0x97ffff99])
    # Module registration -> one driver -> literal device array -> attach3884.
    require(u64(chip, 0xa0c8) == 1 and u64(chip, 0xa0d0) == 0xa0d8
            and u64(chip, 0xa0d8) == 0x7f38, 'module registration list')
    require([u64(chip, a) for a in [0x7f38, 0x7f40, 0x7f48]] == [0x3884, 1, 0xa1d0],
            'registered attach/count/device-array')
    require(struct.unpack('<I', chip.read(0xa1d0, 4))[0] == 0x0200006f, 'registered device literal')
    words(chip, 0x38c0, [0x529b43e8, 0xaa1403f6, 0x72bb43e8,
                        0x90000029, 0x913d4129, 0xaa1403e0,
                        0xb8018ec8, 0x52800308, 0xa9025289, 0xb9003288])
    words(chip, 0x38ec, [0xf9000276])
    # Direct EFI interface is installed separately, after native attach/init.
    require(chip.read(0xa068, 16) == guid, 'DEC/installed direct GUID mismatch')
    require(u64(chip, 0xa0e0) == 0x10005, 'direct EFI revision')
    words(chip, 0x1b28, [0xb0000041, 0xb0000042, 0x9101a021, 0x91038042])
    words(chip, 0x1b4c, [0xf940a508, 0xd63f0100])
    methods = []
    for name, outer, wrapper, private, impl, getter, cache, store in [
        ('version', 8, 0x14e4, 0x48, 0x3990, 0x3618, 0xa424, 0x39ac),
        ('id', 24, 0x1564, 0x58, 0x39e8, 0x3630, 0xa420, 0x3a04),
        ('family', 48, 0x1624, 0x70, 0x3a60, 0x3674, 0xa42c, 0x3a7c),
    ]:
        require(u64(chip, 0xa0e0+outer) == wrapper, 'direct '+name+' slot')
        require(u64(chip, 0x7f50+private) == impl, 'private '+name+' target')
        words(chip, wrapper+16, [0xb2410bf3, 0xf9416d00, 0xb40000c0,
                                0xf9400408, 0xf9400108 | ((private//8) << 10),
                                0xd63f0100, 0x7100001f, 0x9a9303f3])
        # x1 is preserved to the 32-bit output store; private result is zero.
        words(chip, impl+12, [0xaa0103f3])
        branch = struct.unpack('<I', chip.read(impl+16, 4))[0]
        delta = (branch & 0x3ffffff)
        if delta & 0x2000000:
            delta -= 0x4000000
        require(branch >> 26 == 0x25 and impl+16+delta*4 == getter, 'cached getter edge')
        words(chip, store-8, [0x2a0003e8, 0x2a1f03e0, 0xb9000268])
        words(chip, getter, [0xf0000028, 0xb9400100 | (((cache-0xa000)//4) << 10), 0xd65f03c0])
        methods.append(dict(name=name, direct_offset=outer, wrapper_RVA=wrapper,
                            private_offset=private, private_RVA=impl, cache_RVA=cache,
                            output_bytes=4, private_error_detail_lost_in_outer_status=True))
    # Absent init payload can still latch initialized and return zero. This
    # blocks promotion of a successful outer getter into valid hardware data.
    words(chip, 0x5b8c, [0x9400005c, 0xb40009a0])
    words(chip, 0x5cdc, [0x52800028, 0x391062a8, 0xa9434ff4, 0x2a1f03e0])
    words(chip, 0x5d08, [0x52801120, 0xd10013a1, 0x940000c8])
    return methods


def main():
    require(not (OUT/'registration-result.json').exists(), 'completed result; do not repeat')
    OUT.mkdir(parents=True, exist_ok=True)
    PE = reader_class()
    paths = {n: BLOBS/n/(n+'.efi') for n in HASHES}
    for n, p in paths.items():
        require(sha(p) == HASHES[n], 'selected source blob changed: '+n)
    guid, initializer = dec_guid()
    require(str(uuid.UUID(bytes_le=guid)) == 'b0760469-970c-487a-a4b5-28db7b45cef1',
            'selected package declaration changed')
    dal, chip = [PE(paths[n]) for n in ['DALSYSDxe', 'ChipInfoDxe']]
    methods = inspect(dal, chip, guid)
    negatives = []
    # All mutations bypass the outer source SHA guard: semantic inspection,
    # rather than a digest mismatch, must reject each independent FILE copy.
    cases = [
        ('bootstrap-services-output', 'DALSYSDxe', 0x14c8, struct.pack('<I', 0xd503201f)),
        ('versioned-attach-slot', 'DALSYSDxe', 0x291a0, struct.pack('<Q', 0x2e64)),
        ('registration-device', 'ChipInfoDxe', 0xa1d0, struct.pack('<I', 0x02000070)),
        ('registration-attach', 'ChipInfoDxe', 0x7f38, struct.pack('<Q', 0x3990)),
        ('handle-vtable', 'ChipInfoDxe', 0x38d0, struct.pack('<I', 0xd503201f)),
        ('stale-header-GUID', 'ChipInfoDxe', 0xa068,
         uuid.UUID('61224fbe-b240-4d53-b661-a9a1f343b05c').bytes_le),
        ('outer-family-target', 'ChipInfoDxe', 0xa110, struct.pack('<Q', 0x1564)),
        ('outer-private-error-mapping', 'ChipInfoDxe', 0x1650, struct.pack('<I', 0xd503201f)),
        ('version-output-store', 'ChipInfoDxe', 0x39ac, struct.pack('<I', 0xd503201f)),
        ('init-fallback-latch', 'ChipInfoDxe', 0x5ce0, struct.pack('<I', 0xd503201f)),
    ]
    for name, selected, rva, replacement in cases:
        p = PE(paths[selected])
        section = p.section(rva, len(replacement))
        at = section['off']+rva-section['va']
        bad = OUT/(name+'.efi')
        data = bytearray(paths[selected].read_bytes())
        data[at:at+len(replacement)] = replacement
        bad.write_bytes(data)
        pair = dict(DALSYSDxe=dal, ChipInfoDxe=chip)
        pair[selected] = PE(bad)
        try:
            inspect(pair['DALSYSDxe'], pair['ChipInfoDxe'], guid)
        except ValueError as error:
            negatives.append(dict(name=name, refused=str(error), sha256=sha(bad)))
        else:
            raise ValueError('semantic mutation survived: '+name)
    result = dict(selected_blobs={str(paths[n]): HASHES[n] for n in paths},
        selected_DEC=str(PKG/'QcomPkg.dec'), selected_DEC_sha256=sha(PKG/'QcomPkg.dec'),
        direct_registered_GUID=str(uuid.UUID(bytes_le=guid)), direct_initializer=initializer,
        header_macro_GUID='61224fbe-b240-4d53-b661-a9a1f343b05c',
        private_bootstrap_GUID='ae37b942-457f-4c91-a196-d9669fd347a3',
        bootstrap_revision=0x10002, bootstrap_init_RVA=0x14a0,
        services_RVA=0x290d0, attach_RVA=0x2e64, versioned_attach_RVA=0x2fcc,
        registration_path_RVAs=[0xa0b8, 0xa0d8, 0x7f38, 0xa1d0, 0x3884],
        literal_device=0x0200006f, private_vtable_RVA=0x7f50,
        methods=methods, semantic_mutations_refused=negatives,
        direct_prefix_typed_via_real_SDK_but_not_a_private_DAL_typedef=True,
        original_private_native_declarations_still_unavailable=True,
        cached_output_init_can_latch_without_payload=True,
        no_native_query_request_or_runtime_eligibility_constructed=True,
        native_status_available=False, native_output_available=False,
        native_or_phone_invocation=False, allow_boot=False, readback_qualified=False,
        WriteAuthorized=0)
    (OUT/'registration-result.json').write_text(json.dumps(result, indent=2)+'\n')
    target(guid, initializer)
    print('Selected registration and distinct DEC-bound EFI prefix verified;10 semantic corruptions refused; no calls/request')


def target(guid, initializer):
    meta = json.loads((PARENT/'module-inputs.json').read_text())
    old = str(PARENT/'Packages/zornPkg/Drivers/ZornBootMemoryDxe/ZornGpuPowerResolver.cpp')
    recipe = next(c for c in meta['commands'] if old in c['arguments'])
    commands = []

    def run(args, name):
        args = list(map(str, args))
        p = subprocess.run(args, cwd=recipe['cwd'], capture_output=True, text=True, timeout=55)
        commands.append(dict(arguments=args, cwd=recipe['cwd'], returncode=p.returncode))
        (OUT/(name+'.log')).write_text(p.stdout+p.stderr)
        p.check_returncode()

    source = OUT/'selected-direct-registration.cpp'
    source.write_text('''#include <Uefi.h>
#include <Protocol/EFIChipInfo.h>
#include <stddef.h>
// Local data annotation of the selected DEC declaration, not an SDK edit,
// AutoGen replacement, private DAL table, native callback or hardware request.
extern "C" const EFI_GUID zdc_selected_guid = '''+initializer+''';
extern "C" const EFI_GUID zdc_header_macro = EFI_CHIPINFO_PROTOCOL_GUID;
extern "C" const UINT64 zdc_direct_prefix[] = {
 EFI_CHIPINFO_PROTOCOL_REVISION,
 offsetof(EFI_CHIPINFO_PROTOCOL,GetChipVersion),
 offsetof(EFI_CHIPINFO_PROTOCOL,GetChipId),
 offsetof(EFI_CHIPINFO_PROTOCOL,GetChipFamily)};
''')
    obj = OUT/'selected-direct-registration.obj'
    args = list(recipe['arguments'])
    args[args.index(old)] = str(source)
    args[args.index('-o')+1] = str(obj)
    args[args.index('-MF')+1] = str(obj)+'.deps'
    run(args, 'target-first')
    first = OUT/'selected-direct-registration-first.obj'
    first.write_bytes(obj.read_bytes())
    run(args, 'target-independent')
    require(sha(first) == sha(obj) and first.stat().st_ino != obj.stat().st_ino,
            'independent raw target object mismatch')
    dep = OUT/'target.d'
    pp = []
    i = 0
    while i < len(args):
        if args[i] in ['-o', '-MF', '-MT']:
            i += 2
        elif args[i] in ['-c', '-MMD']:
            i += 1
        else:
            pp.append(args[i])
            i += 1
    run(pp+['-M', '-MF', str(dep), '-MT', 'input'], 'target-dependencies')
    inputs = {str(PKG/'QcomPkg.dec'): sha(PKG/'QcomPkg.dec')}
    for n in shlex.split(dep.read_text().replace('\\\n', ' ').split(':', 1)[1]):
        p = Path(n)
        if not p.is_absolute():
            p = Path(recipe['cwd'])/p
        inputs[str(p)] = sha(p)
    image = OUT/'selected-direct-registration.efi'
    run([ROOT/'UniXNU/out/zorn/toolchain/lld-link', '/NOLOGO', '/NODEFAULTLIB', '/WX',
         '/DLL', '/NOENTRY', '/MACHINE:ARM64', '/SUBSYSTEM:EFI_BOOT_SERVICE_DRIVER',
         '/include:zdc_selected_guid', '/include:zdc_header_macro', '/include:zdc_direct_prefix',
         '/out:'+str(image), obj], 'target-data-link')
    data = image.read_bytes()
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    require(struct.unpack_from('<I', data, pe+24+16)[0] == 0, 'entry must be zero')
    require(struct.unpack_from('<I', data, pe+24+4)[0] == 0, 'code bytes must be zero')
    require(data.count(guid) == 1, 'selected DEC GUID in linked image')
    require(data.count(uuid.UUID('61224fbe-b240-4d53-b661-a9a1f343b05c').bytes_le) == 1,
            'header GUID discrepancy retained')
    require(data.count(struct.pack('<4Q', 0x10005, 8, 24, 48)) == 1, 'direct prefix linked data')
    count, opt = struct.unpack_from('<H', data, pe+6)[0], struct.unpack_from('<H', data, pe+20)[0]
    for i in range(count):
        flags = struct.unpack_from('<I', data, pe+24+opt+40*i+36)[0]
        require(flags & (0x20000000 | 0x80000000) == 0, 'no executable/writable section')
    (OUT/'target-result.json').write_text(json.dumps(dict(inputs=inputs, commands=commands,
        raw_SHA_independent_equal=True, object_sha256=sha(obj), image_sha256=sha(image),
        data_only_entry0_code0=True, direct_DEC_GUID_and_stale_macro_both_preserved=True,
        no_SDK_or_old_module_libraries_required=True, no_invocation_or_new_request=True,
        allow_boot=False, readback_qualified=False, WriteAuthorized=0), indent=2)+'\n')


if __name__ == '__main__':
    main()
