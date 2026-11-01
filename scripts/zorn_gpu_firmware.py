"""Host-only build of the isolated zorn GPU preparation firmware sources.

No phone operations, SDK patching/submodule updates or baseline publication.
The source receipt selects the reviewed overlay. The approved media diagnostic
stage compiles a terminal single-log-block path without invoking it. Building
never grants device I/O, GPU operations or boot permission.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tomllib


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(root, uefi, stage='gpu-canonical-firmware'):
    if stage not in ('gpu-canonical-firmware', 'gpu-canonical-checkpoint', 'gpu-terminal-collector', 'gpu-terminal-commit-integration', 'gpu-media-qualification-candidate'):
        raise SystemExit('Unknown isolated firmware stage')
    out = root / 'out/zorn' / stage
    receipt = json.loads((out / 'source-provenance.json').read_text())
    assert receipt['native_gpu_queries_allowed'] is False
    assert receipt['native_gpu_operations_allowed'] is False
    assert receipt['WriteAuthorized'] == 0 and not receipt['allow_boot']
    for group in ('original_platform_sources', 'reused_audited_inputs', 'staged_sources'):
        for path, expected in receipt[group].items():
            if sha(path) != expected:
                raise SystemExit('Firmware source changed: ' + path)
    if stage == 'gpu-media-qualification-candidate':
        approval_path = out / 'owner-approval.json'
        if sha(approval_path) != receipt['owner_approval_sha256']:
            raise SystemExit('Media candidate approval differs')
        approval = json.loads(approval_path.read_text())
        if (approval.get('answer') != '批准该策略，继续制作完整候选' or
                approval.get('approved_diagnostic_policy') is not True or
                approval.get('native_activation_approved') is not False or
                sha(approval['proposal']) != approval['proposal_sha256']):
            raise SystemExit('Exact diagnostic policy approval required; no activation permission')
        if receipt.get('media_qualification_body_compiled') is not True:
            raise SystemExit('Missing selected diagnostic source receipt')
    current = json.loads((root / 'out/zorn/unattended-active/current.json').read_text())
    if current.get('active_run') or current.get('runner_session'):
        raise SystemExit('A device run is active')
    if stage == 'gpu-media-qualification-candidate' and current.get('active_build') != 'offline-approved-media-qualification-candidate-FD':
        raise SystemExit('Media candidate requires its exclusive recorded build phase')
    edk2 = root / 'UniXNU/out/feeds/mu_basecore-89034cbb'
    tools = edk2 / 'BaseTools'
    if not (tools / 'Source/C/bin/GenFw').is_file():
        raise SystemExit('Existing BaseTools required; no shared SDK mutation')
    conf = out / 'conf'
    conf.mkdir(exist_ok=True)
    for name in ('target', 'tools_def', 'build_rule'):
        dst = conf / (name + '.txt')
        if not dst.exists():
            shutil.copy2(tools / 'Conf' / (name + '.template'), dst)
    board = tomllib.loads((root / 'UniXNU-zorn/compat/legacy/board.toml').read_text())
    config = tomllib.loads((uefi / 'Resources/Configs/zorn.toml').read_text())
    fw = board['firmware']
    # The completed Darwin23 kernel uses this explicit canonical source view.
    # board {tree} refers to the core tree, not the device metadata repository.
    fields = dict(uefi=uefi, edk2=edk2,
                  tree=root / 'out/zorn/gen7-canonical-workspace/UniXNU')
    packages = [str(out / 'Packages')] + [p.format(**fields) for p in fw['packages']]
    defines = dict(FD_BASE=hex(config['uefi_fd']['base']),
                   FD_SIZE=hex(config['uefi_fd']['size']),
                   FD_BLOCKS=str(config['uefi_fd']['size'] // 4096))
    defines.update({k: str(v) for k, v in fw.get('defines', {}).items()})
    epoch = subprocess.check_output(['git', '-C', str(uefi), 'log', '-1', '--format=%ct'], text=True).strip()
    env = dict(os.environ, WORKSPACE=str(uefi), EDK_TOOLS_PATH=str(tools),
               CONF_PATH=str(conf), PACKAGES_PATH=':'.join(packages),
               PYTHON_COMMAND='python3', PYTHONDONTWRITEBYTECODE='1',
               CLANG_BIN=str(root / 'UniXNU/out/zorn/toolchain') + '/',
               SOURCE_DATE_EPOCH=epoch,
               PATH=os.pathsep.join([str(tools / 'BinWrappers/PosixLike'),
                                     str(tools / 'Source/C/bin'), os.environ['PATH']]))
    command = ['build', '-p', str(out / 'Packages/zornPkg/zorn.dsc'),
               '-a', 'AARCH64', '-b', 'DEBUG', '-t', 'CLANGPDB', '-n', '4']
    for key, value in defines.items():
        command.extend(['-D', key + '=' + value])
    baseline_paths = [root / 'out/zorn/boot.img', root / 'out/zorn/firmware.inputs.json',
                      root / 'out/zorn/SILICIUM_UEFI-05b8b30b.fd',
                      uefi / 'Build/zornPkg/DEBUG_CLANGPDB/FV/SILICIUM_UEFI.fd']
    baselines = {str(p): sha(p) for p in baseline_paths}
    attempt = 1
    while (out / ('build-%02d.log' % attempt)).exists():
        attempt += 1
    log = out / ('build-%02d.log' % attempt)
    info = dict(command=command, cwd=str(uefi),
                environment={k: env[k] for k in ('WORKSPACE', 'EDK_TOOLS_PATH', 'CONF_PATH',
                    'PACKAGES_PATH', 'CLANG_BIN', 'SOURCE_DATE_EPOCH')},
                baseline_SHA=baselines, source_receipt_sha256=sha(out / 'source-provenance.json'),
                allow_boot=False, native_GPU_invoked=False, WriteAuthorized=0)
    with log.open('w') as stream:
        result = subprocess.run(command, cwd=uefi, env=env, stdout=stream, stderr=subprocess.STDOUT)
    info['returncode'] = result.returncode
    info['baselines_unchanged'] = all(sha(p) == expected for p, expected in baselines.items())
    (out / ('build-%02d.json' % attempt)).write_text(json.dumps(info, indent=2) + '\n')
    if not info['baselines_unchanged']:
        raise SystemExit('Firmware build changed a baseline')
    if result.returncode:
        raise SystemExit('Firmware build failed; see ' + str(log))
    built = out / 'Build/zornGpuPrepare/DEBUG_CLANGPDB'
    fd = built / 'FV/SILICIUM_UEFI.fd'
    modules = [p for p in built.rglob('ZornBootMemoryDxe.efi') if p.parent.name == 'OUTPUT']
    if len(modules) != 1 or fd.stat().st_size != config['uefi_fd']['size']:
        raise SystemExit('Expected the actual module and complete 3 MiB FD')
    info.update(fd=str(fd), fd_sha256=sha(fd), module=str(modules[0]), module_sha256=sha(modules[0]))
    (out / 'build-result.json').write_text(json.dumps(info, indent=2) + '\n')
    print('Actual isolated FD:', info['fd_sha256'], 'module:', info['module_sha256'])
