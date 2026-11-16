#!/usr/bin/env python3
"""Offline selected ChipInfo payload call/length barrier; no native calls."""
from pathlib import Path
import ast
import hashlib
import json
import struct
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'out/zorn/gpu-chipinfo-payload-contract'
BLOB = ROOT.parent/'Mu-Silicium/Binaries/giulia/QcomPkg/Drivers/ChipInfoDxe/ChipInfoDxe.efi'
SHA = '38c7c0d036ff9e9fc0700983874bca910d87b2d853e22dd6c1d542a8757a5185'
# Exact new used paths only. No register-based native typedef is inferred.
WORDS = {
 0x5d08: [0x52801120,0xd10013a1,0x940000c8,0xb85fc3a8],
 0x5d1c: [0x7100011f,0xfa401804,0x9a8003e0],
 0x6074: [0xf9428108,0xb4000228,0xf9400508,0xb40001e8],
 0x6094: [0x2a1303e0,0xaa1403e1,0xd63f0100],
 0x5f4c: [0x90000028,0x91066108,0xf800c268],
 0x5fc0: [0x90000029,0x52a00188,0x910b4129,0xb9000268,0xf800c269],
 0x6388: [0xb9400968,0xb9000268],
 0x63b8: [0x9000002a,0xb944f14a,0x6b0a017f,0x540000a2],
 0x63c8: [0x8b0a0129,0x8b080288,0xeb09011f,0x54000063],
 0x63d8: [0xaa1f03f4,0xb900027f],
 0x5bf4: [0xb9407809,0xb940ac0a],
}
def inspect(pe):
 for at,words in WORDS.items():
  if pe.read(at,4*len(words)) != struct.pack('<'+'I'*len(words),*words):
   raise ValueError('payload contract at '+hex(at))
 if struct.unpack('<4Q',pe.read(0x9198,32)) != (0x61e4,0x62e8,0x6400,0x6484):
  raise ValueError('internal function table; not EFI SMEM')
def main():
 if (OUT/'combined-result.json').exists():raise SystemExit('Completed result; do not repeat')
 if hashlib.sha256(BLOB.read_bytes()).hexdigest()!=SHA:raise ValueError('selected blob changed')
 reader=ROOT/'out/zorn/gpu-real-caller/audit-module.py'
 node=next(n for n in ast.parse(reader.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='PE')
 ns=dict(Path=Path,struct=struct);exec(compile(ast.Module(body=[node],type_ignores=[]),str(reader),'exec'),ns)
 PE=ns['PE'];pe=PE(BLOB);inspect(pe);negative=[]
 for name,rva in [('item-number',0x5d08),('nonzero-size-check',0x5d1c),('internal-get-slot',0x607c),('payload-size-output',0x638c),('region-boundary',0x63d4)]:
  data=bytearray(BLOB.read_bytes());s=pe.section(rva,4);at=s['off']+rva-s['va'];data[at:at+4]=struct.pack('<I',0xd503201f)
  bad=OUT/(name+'.efi');bad.write_bytes(data)
  try:inspect(PE(bad))
  except ValueError as error:negative.append(dict(name=name,refused=str(error)))
  else:raise ValueError('surviving mutation '+name)
 result=dict(state='selected-internal-shared-memory-path-bound-payload-validity-unavailable',source_blob=str(BLOB),source_sha256=SHA,
  item_literal=137,internal_tables_RVA=[0x9198,0x92d0],selected_internal_get_RVA=0x62e8,
  no_public_EFI_SMEM_call_on_this_path=True,public_EFI_SMEM_not_substituted=True,
  get_return_shape='x0 pointer, x1 points to UINT32 size; observed shape only, not a fabricated callable typedef',
  consumer_nonzero_pointer_and_size_only=True,consumer_minimum_length_not_checked=True,
  unconditional_read_end_exclusive=0xb0,unconditional_string_copy=[0x7c,32],
  version_gated_read_end_exclusive={14:0xac,16:0xb8,19:0xd8},
  internal_region_check_does_not_prove_payload_schema=True,
  native_payload_size_version_namespace_or_provenance_available=False,
  private_native_types_and_payload_primary_definition_unbound=True,
  new_semantic_mutations_refused=negative,words={hex(k):[hex(v) for v in vals] for k,vals in WORDS.items()},
  supplemental_primary_fetches='Linux v6.1 raw GitHub returned429; kernel.org inaccessible. No remote source incorporated or claimed exact selected source.',
  no_new_native_component_so_no_target_compile_required=True,
  provider_or_phone_calls=0,new_request_or_candidate=False,allow_boot=False,readback_qualified=False,WriteAuthorized=0)
 (OUT/'combined-result.json').write_text(json.dumps(result,indent=2)+'\n')
 print('Internal payload path and length barrier bound;5 new semantic mutations refused; no native interface invented')
if __name__=='__main__':main()
