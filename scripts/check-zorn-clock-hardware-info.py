#!/usr/bin/env python3
"""Offline target ABI barrier: the selected EFI header is not a DAL table.

Requires the preserved exact firmware recipe. Produces data-only annotation,
not a callable hardware-info request, module, FD or device candidate.
"""
from pathlib import Path
import hashlib
import json
import shlex
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'out/zorn/gpu-clock-hardware-info-binding'
PARENT = ROOT/'out/zorn/gpu-resource-observation-candidate'
MODULE = PARENT/'Packages/zornPkg/Drivers/ZornBootMemoryDxe'

ANNOTATION = r'''#include <Uefi.h>
#include <Protocol/EFIChipInfo.h>
#include <stddef.h>
static_assert(sizeof(EFI_STATUS)==8&&sizeof(VOID*)==8,"native status/pointer width");
static_assert(sizeof(EFIChipInfoVersionType)==4&&sizeof(EFIChipInfoIdType)==4&&sizeof(EFIChipInfoFamilyType)==4,"selected public scalar widths");
static_assert(__is_same(EFI_DALCHIPINFO_GETCHIPVERSION,EFI_STATUS(EFIAPI*)(EFI_CHIPINFO_PROTOCOL*,EFIChipInfoVersionType*)),"public version prototype");
static_assert(__is_same(EFI_DALCHIPINFO_GETCHIPID,EFI_STATUS(EFIAPI*)(EFI_CHIPINFO_PROTOCOL*,EFIChipInfoIdType*)),"public ID prototype");
static_assert(__is_same(EFI_DALCHIPINFO_GETCHIPFAMILY,EFI_STATUS(EFIAPI*)(EFI_CHIPINFO_PROTOCOL*,EFIChipInfoFamilyType*)),"public family prototype");
static_assert(offsetof(EFI_CHIPINFO_PROTOCOL,GetChipVersion)==8,"public version slot");
static_assert(offsetof(EFI_CHIPINFO_PROTOCOL,GetChipId)==24,"public ID slot");
static_assert(offsetof(EFI_CHIPINFO_PROTOCOL,GetChipFamily)==48,"public family slot");
// Actual ClockDxe uses handle+8 -> another table and different slots. These
// inequalities are a barrier, not a declaration of the missing DAL ABI.
static_assert(offsetof(EFI_CHIPINFO_PROTOCOL,GetChipVersion)!=0x48,"do not cast a DAL version table");
static_assert(offsetof(EFI_CHIPINFO_PROTOCOL,GetChipId)!=0x58,"do not cast a DAL ID table");
static_assert(offsetof(EFI_CHIPINFO_PROTOCOL,GetChipFamily)!=0x70,"do not cast a DAL family table");
extern "C" const UINT64 zhi_public_layout[]={sizeof(EFI_STATUS),sizeof(VOID*),sizeof(EFIChipInfoVersionType),sizeof(EFIChipInfoIdType),sizeof(EFIChipInfoFamilyType),offsetof(EFI_CHIPINFO_PROTOCOL,GetChipVersion),offsetof(EFI_CHIPINFO_PROTOCOL,GetChipId),offsetof(EFI_CHIPINFO_PROTOCOL,GetChipFamily),EFI_CHIPINFO_PROTOCOL_REVISION,EFICHIPINFO_NUM_IDS,EFICHIPINFO_NUM_FAMILIES,sizeof(EFI_CHIPINFO_PROTOCOL)};
extern "C" const EFI_GUID zhi_public_GUID=EFI_CHIPINFO_PROTOCOL_GUID;
'''


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if (OUT/'target-result.json').exists():
        raise SystemExit('Completed target result exists; refuse to repeat')
    meta = json.loads((PARENT/'module-inputs.json').read_text())
    recipe = next(c for c in meta['commands']
                  if str(MODULE/'ZornGpuPowerResolver.cpp') in c['arguments'])
    commands = []

    def run(args, name):
        args = list(map(str, args))
        p = subprocess.run(args, cwd=recipe['cwd'], capture_output=True, text=True, timeout=55)
        commands.append(dict(arguments=args, cwd=recipe['cwd'], returncode=p.returncode))
        (OUT/(name+'.log')).write_text(p.stdout+p.stderr)
        return p

    def compile_source(source, target, extra=()):
        args = list(recipe['arguments'])
        args[args.index(str(MODULE/'ZornGpuPowerResolver.cpp'))] = str(source)
        args[args.index('-o')+1] = str(target)
        if '-MF' in args:
            args[args.index('-MF')+1] = str(target)+'.deps'
        args += list(extra)
        return args

    source = OUT/'public-EFI-not-DAL.cpp'
    source.write_text(ANNOTATION)
    obj = OUT/'public-EFI-not-DAL.obj'
    args = compile_source(source, obj)
    run(args, 'actual-recipe-first').check_returncode()
    first = OUT/'public-EFI-not-DAL-first.obj'
    first.write_bytes(obj.read_bytes())
    run(args, 'actual-recipe-independent').check_returncode()
    assert digest(first) == digest(obj) and first.stat().st_ino != obj.stat().st_ino
    annotation = OUT/'public-layout-inspection.obj'
    run(compile_source(source, annotation, ['-fno-lto', '-mgeneral-regs-only']),
        'public-layout-inspection').check_returncode()
    data = annotation.read_bytes()
    _, count, _, _, _, opt, _ = struct.unpack_from('<HHIIIHH', data)
    ro = []
    for i in range(count):
        at = 20+opt+40*i
        if data[at:at+8].rstrip(b'\0') == b'.rdata':
            size, raw = struct.unpack_from('<II', data, at+16)
            ro.append(data[raw:raw+size])
    assert sorted(map(len, ro)) == [16, 96]
    layout = list(struct.unpack('<12Q', next(x for x in ro if len(x) == 96)))
    assert layout == [8, 8, 4, 4, 4, 8, 24, 48, 0x10005, 401, 102, 184], layout
    negative = []
    for name, old, new in [
        ('wrong-DAL-family-slot', 'GetChipFamily)==48', 'GetChipFamily)==0x70'),
        ('wrong-DAL-ID-slot', 'GetChipId)==24', 'GetChipId)==0x58'),
    ]:
        assert ANNOTATION.count(old) == 1
        bad = OUT/(name+'.cpp')
        bad.write_text(ANNOTATION.replace(old, new))
        p = run(compile_source(bad, OUT/(name+'.obj')), name)
        assert p.returncode != 0 and 'static assertion failed' in p.stderr
        negative.append(dict(name=name, compiler_refused=True))
    dep = OUT/'public-EFI-not-DAL.d'
    preprocess = []
    i = 0
    while i < len(args):
        if args[i] in ['-o', '-MF', '-MT']:
            i += 2
            continue
        if args[i] in ['-c', '-MMD']:
            i += 1
            continue
        preprocess.append(args[i])
        i += 1
    run(preprocess+['-M', '-MF', str(dep), '-MT', 'input'], 'dependencies').check_returncode()
    inputs = {}
    for name in shlex.split(dep.read_text().replace('\\\n', ' ').split(':', 1)[1]):
        path = Path(name)
        if not path.is_absolute():
            path = Path(recipe['cwd'])/path
        inputs[str(path)] = digest(path)
    image = OUT/'public-interface-barrier.efi'
    link = [ROOT/'UniXNU/out/zorn/toolchain/lld-link', '/NOLOGO', '/NODEFAULTLIB', '/WX',
            '/DLL', '/NOENTRY', '/MACHINE:ARM64', '/SUBSYSTEM:EFI_BOOT_SERVICE_DRIVER',
            '/include:zhi_public_layout', '/include:zhi_public_GUID',
            '/lldmap:'+str(OUT/'public-interface.map'), '/out:'+str(image), obj]
    run(link, 'data-only-NOENTRY-link').check_returncode()
    result = dict(inputs=inputs, commands=commands, actual_public_layout=layout,
        actual_recipe_LTO_raw_SHA_independent_equal=True, object_sha256=digest(obj),
        inspection_object_sha256=digest(annotation), inspection_COFF_timestamp=struct.unpack_from('<I', data, 4)[0],
        inspection_timestamp_not_normalized=True, compile_refusals=negative,
        image_sha256=digest(image), no_SDK_library_or_old_module_archive_required=True,
        no_code_or_native_wrapper_in_annotation=True, no_DAL_prototypes_or_request_invented=True,
        native_hardware_info_or_phone_invoked=False, allow_boot=False,
        readback_qualified=False, WriteAuthorized=0)
    (OUT/'target-result.json').write_text(json.dumps(result, indent=2)+'\n')
    print('Actual public EFI ABI barrier built;2 wrong DAL slot substitutions refused;no callable request')


if __name__ == '__main__':
    main()
