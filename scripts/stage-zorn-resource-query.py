#!/usr/bin/env python3
"""Stage a default-OFF query/checkpoint join. No phone, boot or SDK writes."""
import hashlib
import json
from pathlib import Path
import secrets
import shutil

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'out/zorn/gpu-resource-query-checkpoint-20261101'
PARENT = ROOT/'out/zorn/gpu-unixnu64-closed-firmware'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Reviewed source preimage differs')
    return text.replace(old, new)


def main():
    current_path = ROOT/'out/zorn/unattended-active/current.json'
    current = json.loads(current_path.read_text())
    if any(current.get(k) for k in ('active_run', 'active_build', 'runner_session')):
        raise ValueError('Another build/run is active')
    if (OUT/'Packages').exists():
        raise ValueError('Never overwrite an existing source capsule')
    receipt = json.loads((PARENT/'source-provenance.json').read_text())
    for path, expected in receipt['staged_sources'].items():
        if sha(path) != expected:
            raise ValueError('Parent staged source changed: '+path)
    shutil.copytree(PARENT/'Packages', OUT/'Packages', copy_function=shutil.copy2)
    module = OUT/'Packages/zornPkg/Drivers/ZornBootMemoryDxe'
    header = module/'ZornMediaQualification.h'
    text = header.read_text()
    text = replace_once(text, '#ifndef ZMQ_QUALIFICATION_DRIVER', '''#ifndef ZMQ_RESOURCE_QUERY
#define ZMQ_RESOURCE_QUERY 0
#endif
#if ZMQ_RESOURCE_QUERY != 0 && ZMQ_RESOURCE_QUERY != 1
#error "Resource query selection must be exactly 0 or 1"
#endif
#if ZMQ_RESOURCE_QUERY && !ZMQ_QUALIFICATION_CALLER
#error "A resource query requires the explicit terminal media caller"
#endif
#ifndef ZMQ_QUALIFICATION_DRIVER''')
    text = replace_once(text, 'ZMQ_POLICY_STOP=5', 'ZMQ_POLICY_STOP=5,ZMQ_QUERY_STOP=6')
    header.write_text(text)
    source = module/'ZornMediaQualification.cpp'
    text = replace_once(source.read_text(), '#include "ZornTerminalCollector.h"', '''#include "ZornTerminalCollector.h"
#if ZMQ_RESOURCE_QUERY
#include "ZornGpuQuery.h"
#endif''')
    old = '''  // Proposed deliberate DIAGNOSTIC stop, not a native hardware failure and
  // never a normal successful boot. This policy needs a new owner decision.
  primary=ZMQ_POLICY_STOP;r.DiagnosticPolicyStop=1;
  ZefCollectTerminal(8,ZEF_ORIGIN_ADAPTER,EFI_ABORTED,1);'''
    new = '''#if ZMQ_RESOURCE_QUERY
  // Actual media discovery succeeded before any query. The native query
  // uses its own real EBS owner and release-publishes its original272B
  // capture before collecting its first failure. It supplies no GPU lease.
  const EFI_STATUS queried=ZornGpuQueryRun(bs,sector,bytes,wdt);
  ZefCollectorReport first{};
  const bool retained=ZefCollectorCopyReport(&first)&&
   first.Bytes==sizeof(first)&&first.Version==1&&first.Attempted==1;
  if(retained){
   // Keep even an unsuccessful first encoding. No second collect/record,
   // status replacement or retry after the backend has attempted capture.
   primary=ZMQ_QUERY_STOP;
  }else if(queried!=EFI_SUCCESS){
   // A returned early adapter status without a terminal attempt is retained
   // at full64-bit width. It is never relabelled a native provider cause.
   primary=ZMQ_QUERY_STOP;
   ZefCollectTerminal(3,ZEF_ORIGIN_ADAPTER,queried,1);
  }else{
   primary=ZMQ_POLICY_STOP;r.DiagnosticPolicyStop=1;
   ZefCollectTerminal(8,ZEF_ORIGIN_ADAPTER,EFI_ABORTED,1);
  }
#else
  // Original media-only diagnostic policy, unchanged when the new flag is0.
  primary=ZMQ_POLICY_STOP;r.DiagnosticPolicyStop=1;
  ZefCollectTerminal(8,ZEF_ORIGIN_ADAPTER,EFI_ABORTED,1);
#endif'''
    source.write_text(replace_once(text, old, new))
    inf = module/'ZornBootMemoryDxe.inf'
    inf.write_text(replace_once(inf.read_text(), '-DZMQ_QUALIFICATION_DRIVER=0',
                               '-DZMQ_QUALIFICATION_DRIVER=0 -DZMQ_RESOURCE_QUERY=0'))
    dsc = OUT/'Packages/zornPkg/zorn.dsc'
    dsc.write_text(replace_once(dsc.read_text(), str(PARENT/'Build/zornGpuPrepare'),
                               str(OUT/'Build/zornGpuPrepare')))
    files = {str(p):sha(p) for p in (OUT/'Packages').rglob('*') if p.is_file() and p.name not in ('.DS_Store','ZefBuildIdentity.h')}
    files[str(Path(__file__).resolve())] = sha(Path(__file__).resolve())
    (OUT/'pre-injection-inputs.json').write_text(json.dumps(dict(scope='closed source identity; no activation',inputs=files),sort_keys=True,indent=2)+'\n')
    kernel = ROOT/'out/zorn/dual-system-reinstall-20261101/native-build/kernel.prelinked.macho'
    nonce = secrets.token_bytes(16)
    identity = nonce+bytes.fromhex(sha(kernel))+bytes.fromhex(sha(OUT/'pre-injection-inputs.json'))
    (module/'ZefBuildIdentity.h').write_text('/* Closed source identity; no execution authorization. */\n#pragma once\nextern "C" const UINT8 ZefBuildIdentity[80]={'+','.join('0x%02x'%x for x in identity)+'};\n')
    (OUT/'expected-identity.json').write_text(json.dumps(dict(nonce=nonce.hex(),kernel_sha256=sha(kernel),input_sha256=sha(OUT/'pre-injection-inputs.json')),indent=2)+'\n')
    new_receipt = dict(original_platform_sources=receipt['original_platform_sources'],
        reused_audited_inputs=receipt['staged_sources'],
        staged_sources={str(p):sha(p) for p in (OUT/'Packages').rglob('*') if p.is_file() and p.name!='.DS_Store'},
        delta_sources={str(source):sha(source),str(header):sha(header),str(inf):sha(inf)},
        resource_query_flag=0,storage_invocation_allowed=False,native_gpu_queries_allowed=False,
        native_gpu_operations_allowed=False,WriteAuthorized=0,allow_boot=False,readback_qualified=False)
    (OUT/'source-provenance.json').write_text(json.dumps(new_receipt,indent=2)+'\n')
    current['active_build']='offline-resource-query-checkpoint-closed-FD'
    current['active_phase']='GPU-resource-query-checkpoint-offline-source-build'
    current_path.write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n')
    print('New source staged; all native selectors0; no phone operation')


if __name__ == '__main__':
    main()
