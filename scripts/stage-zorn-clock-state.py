#!/usr/bin/env python3
"""Stage an inert clock-state request against exact preserved firmware types.

This local source capsule is not selected into a module/FD and cannot query a
provider. The preserved source inputs and actual SDK recipe are prerequisites.
"""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'out/zorn/gpu-clock-state-observation-binding'
INPUTS = {
    'out/zorn/gpu-power-resolver/ZornGpuPowerResolver.h':
        'fb8b2813044348a2a5e08d4d57a2a1a6d3259caa5644fa6e8210ef8644d1a4fc',
    'out/zorn/gpu-power-transition-binding/ZornGpuPowerVoteRequest.h':
        '342586e8ed4ab75acb6c18d1288465488e5dab25c5490fc508159d2d187d427f',
    'out/zorn/gpu-power-transition-binding/ZornGpuPowerVoteRequest.cpp':
        '9c078036d42a3d37d199474b4f6e55d158cdc53ca0667e9e4589bb1cb715b5bf',
}

HEADER = r'''/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#pragma once
#include "ZornGpuPowerVoteRequest.h"
enum ZcsResult:UINT32 {ZCS_OK,ZCS_ARGUMENT,ZCS_SCOPE,ZCS_SOURCE};
enum:UINT32 {ZCS_IS_ENABLED=1,ZCS_CACHED_HZ=2};
enum:UINT32 {ZCS_SUCCESS_CAN_LEAVE_UNWRITTEN=1,ZCS_MAY_READ_MMIO=2,
 ZCS_MAY_UPDATE_BACKEND=4,ZCS_CACHED_SELECTED_FREQUENCY=8};
struct ZcsRequest {
 ZprReport Source;
 UINTN ResourceId,MethodOffset;EFI_STATUS NativeStatus;UINT64 RawOutput;
 UINT32 Operation,Resource,Scope,NativeOutputBytes;
 UINT32 InvokeAllowed,NativeAttempted,NativeStatusAvailable,OutputAvailable;
 UINT32 OutputWrittenVerified,LifetimeVerified,RuntimeComplete,MissingProviders;
 UINT32 Semantics,SourceIsLiveOwner,ClockRunningVerified,OwnershipVerified;
};
/* Pure non-callable data, not a provider/caller or wire format. Shape-valid
 * input is not an authenticated live report or a hardware/EBS lease. No
 * protocol pointer/output address is exported. All invocation/result/owner
 * availability remains0, even on ZCS_OK. Raw64 source status/IDs are retained.
 * A closed historical source refuses. Stable typed caller storage is required;
 * range checks do not authenticate arbitrary addresses. Failure keeps output.
 * Real IsClockEnabled may enter locks, backend bookkeeping and MMIO. GetFreq
 * reads the cached selected plan, not measured/running frequency. Both have
 * provider mode paths returning SUCCESS without writing output. A future
 * separately qualified caller must not infer a value from zero status/storage.
 */
ZcsResult ZornGpuPrepareClockState(const ZprReport*,UINT32 scope,UINT32 resource,
 UINT32 operation,ZcsRequest*);
'''

SOURCE = r'''/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#include "ZornGpuClockState.h"
#include <string.h>
static bool valid(const void*p,size_t n,size_t a)
{return p&&n&&!(UINTN(p)%a)&&UINTN(p)<=MAX_UINTN-(n-1);}
static bool overlap(const void*a,size_t an,const void*b,size_t bn)
{return UINTN(a)<=UINTN(b)?UINTN(b)-UINTN(a)<an:UINTN(a)-UINTN(b)<bn;}
ZcsResult ZornGpuPrepareClockState(const ZprReport*s,UINT32 scope,UINT32 resource,
 UINT32 operation,ZcsRequest*out)
{
 if(!valid(s,sizeof(*s),alignof(ZprReport))||!valid(out,sizeof(*out),alignof(ZcsRequest))||
    overlap(s,sizeof(*s),out,sizeof(*out))||(resource!=ZPR_GMU&&resource!=ZPR_HUB)||
    (operation!=ZCS_IS_ENABLED&&operation!=ZCS_CACHED_HZ))return ZCS_ARGUMENT;
 if(scope!=ZPR_BOOT_SERVICES)return ZCS_SCOPE;
 ZptRequest checked{};
 // Reuse only the existing pure shape validator, never issue a vote.
 if(ZornGpuPreparePowerVote(s,scope,ZPT_ENABLE,resource,&checked)!=ZPT_OK)return ZCS_SOURCE;
 ZcsRequest built{};memcpy(&built.Source,&checked.source,sizeof(built.Source));
 built.ResourceId=checked.resource_id;built.Operation=operation;
 built.Resource=resource;built.Scope=scope;
 built.MethodOffset=operation==ZCS_IS_ENABLED?offsetof(EFI_CLOCK_PROTOCOL,IsClockEnabled):offsetof(EFI_CLOCK_PROTOCOL,GetClockFreqHz);
 built.NativeOutputBytes=operation==ZCS_IS_ENABLED?sizeof(BOOLEAN):sizeof(UINT32);
 built.Semantics=ZCS_SUCCESS_CAN_LEAVE_UNWRITTEN|
    (operation==ZCS_IS_ENABLED?(ZCS_MAY_READ_MMIO|ZCS_MAY_UPDATE_BACKEND):ZCS_CACHED_SELECTED_FREQUENCY);
 built.InvokeAllowed=0;built.MissingProviders=0xff;
 memcpy(out,&built,sizeof(built));return ZCS_OK;
}
'''


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(exist_ok=True)
    destinations = [OUT/Path(p).name for p in INPUTS]
    destinations += [OUT/'ZornGpuClockState.h', OUT/'ZornGpuClockState.cpp', OUT/'source-provenance.json']
    if any(p.exists() for p in destinations):
        raise SystemExit('Refuse to overwrite a staged source capsule')
    for name, expected in INPUTS.items():
        source = ROOT/name
        if digest(source) != expected:
            raise SystemExit('Pinned preserved input changed: '+name)
    for name in INPUTS:
        source = ROOT/name
        destination = OUT/source.name
        shutil.copyfile(source, destination)
        assert source.stat().st_ino != destination.stat().st_ino
    (OUT/'ZornGpuClockState.h').write_text(HEADER)
    (OUT/'ZornGpuClockState.cpp').write_text(SOURCE)
    receipt = dict(inputs={str(ROOT/p): h for p, h in INPUTS.items()},
                   outputs={str(p): digest(p) for p in destinations[:-1]},
                   recipe=str(Path(__file__).resolve()), recipe_sha256=digest(Path(__file__)),
                   phone_operations=False, provider_invocation=False, no_FD_selection=True,
                   allow_boot=False, readback_qualified=False, WriteAuthorized=0)
    destinations[-1].write_text(json.dumps(receipt, indent=2)+'\n')
    print('Staged non-callable clock-state request; no provider/phone/FD operation')


if __name__ == '__main__':
    main()
