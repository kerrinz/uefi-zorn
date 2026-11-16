#!/usr/bin/env python3
"""Stage an isolated resource observation candidate offline; no device access."""
import hashlib
import json
from pathlib import Path
import secrets
import shutil

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'out/zorn/gpu-resource-observation-candidate'
PARENT=ROOT/'out/zorn/gpu-resource-query-checkpoint-20261101'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    cp=ROOT/'out/zorn/unattended-active/current.json'
    current=json.loads(cp.read_text())
    if any(current.get(k) for k in ('active_run','active_build','runner_session')):
        raise ValueError('Another build/run is active')
    if (OUT/'Packages').exists():
        raise ValueError('Do not overwrite an existing candidate')
    parent=json.loads((PARENT/'source-provenance.json').read_text())
    for path,value in parent['staged_sources'].items():
        if sha(path)!=value:raise ValueError('Parent source changed: '+path)
    shutil.copytree(PARENT/'Packages',OUT/'Packages',copy_function=shutil.copy2)
    module=OUT/'Packages/zornPkg/Drivers/ZornBootMemoryDxe'
    inf=module/'ZornBootMemoryDxe.inf';text=inf.read_text()
    for name in ('ZEF_MEDIA_QUALIFICATION_COMMIT','ZMQ_QUALIFICATION_CALLER',
                 'ZMQ_QUALIFICATION_DRIVER','ZMQ_RESOURCE_QUERY'):
        old='-D'+name+'=0'
        if text.count(old)!=1:raise ValueError('Exact default-OFF parent required')
        text=text.replace(old,'-D'+name+'=1')
    assert text.count('-DZEF_NATIVE_COMMIT_INSPECTION=0')==1
    inf.write_text(text)
    dsc=OUT/'Packages/zornPkg/zorn.dsc';text=dsc.read_text()
    assert text.count(str(PARENT/'Build/zornGpuPrepare'))==1
    dsc.write_text(text.replace(str(PARENT/'Build/zornGpuPrepare'),str(OUT/'Build/zornGpuPrepare')))
    prior=ROOT/'out/zorn/gpu-media-qualification-candidate/owner-approval.json'
    policy=dict(scope='offline candidate production only; no new device permission',
        storage_profile='unixnu64',resource_observation_only=True,terminal_before_payload=True,
        lookup_bookkeeping_may_allocate_or_block=True,no_clock_vote_rate_reset=True,
        no_SCM_PAS_MMIO_GPU=True,native_activation_approved=False,prior_policy=str(prior),
        prior_policy_sha256=sha(prior),allow_boot=False,WriteAuthorized=0)
    (OUT/'offline-policy.json').write_text(json.dumps(policy,indent=2)+'\n')
    kernel=ROOT/'out/zorn/dual-system-reinstall-20261101/native-build/kernel.prelinked.macho'
    files={str(p):sha(p) for p in (OUT/'Packages').rglob('*') if p.is_file() and p.name not in ('.DS_Store','ZefBuildIdentity.h')}
    for p in [kernel,OUT/'offline-policy.json',ROOT/'uefi-zorn/payload/storage/unixnu64.json',
              ROOT/'UniXNU-zorn/scripts/zorn_gpu_resource_trial.py',Path(__file__).resolve()]:
        files[str(p)]=sha(p)
    (OUT/'pre-injection-inputs.json').write_text(json.dumps(dict(scope='acyclic source/kernel identity; no boot or write lease',inputs=files),sort_keys=True,indent=2)+'\n')
    nonce=secrets.token_bytes(16);identity=nonce+bytes.fromhex(sha(kernel))+bytes.fromhex(sha(OUT/'pre-injection-inputs.json'))
    (module/'ZefBuildIdentity.h').write_text('/* New resource diagnostic identity; no execution permission. */\n#pragma once\nextern "C" const UINT8 ZefBuildIdentity[80]={'+','.join('0x%02x'%x for x in identity)+'};\n')
    (OUT/'expected-identity.json').write_text(json.dumps(dict(nonce=nonce.hex(),kernel_sha256=sha(kernel),input_sha256=sha(OUT/'pre-injection-inputs.json')),indent=2)+'\n')
    receipt=dict(original_platform_sources=parent['original_platform_sources'],
        reused_audited_inputs=parent['staged_sources'],
        staged_sources={str(p):sha(p) for p in (OUT/'Packages').rglob('*') if p.is_file() and p.name!='.DS_Store'},
        resource_query_compiled=True,offline_policy_sha256=sha(OUT/'offline-policy.json'),
        storage_invocation_allowed=False,native_gpu_queries_allowed=False,
        native_gpu_operations_allowed=False,WriteAuthorized=0,allow_boot=False,readback_qualified=False)
    (OUT/'source-provenance.json').write_text(json.dumps(receipt,indent=2)+'\n')
    current.update(active_build='offline-selected-resource-observation-candidate-FD',
                   active_phase='GPU-selected-resource-observation-candidate-building-offline')
    cp.write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n')
    print('Dedicated resource candidate staged; ordinary firmware unchanged; no device execution')

if __name__=='__main__':main()
