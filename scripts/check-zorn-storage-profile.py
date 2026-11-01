#!/usr/bin/env python3
"""Self-contained offline descriptor/proof refusal tests; no device calls.

The synthetic kernel/proof below exercise file-consistency parsing only. They
are not a compiled kernel, a hardware owner, or a runnable candidate.
"""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
from zorn_storage_profile import validate

profile_path = Path(__file__).resolve().parents[1]/'payload/storage/unixnu64.json'
profile = json.loads(profile_path.read_text())
refused = 0
with tempfile.TemporaryDirectory(prefix='zorn-storage-profile-') as folder:
    root = Path(folder)
    kernel = root/'synthetic-kernel.macho'
    kernel.write_bytes(b'host format-consistency fixture, never boot')
    descriptor, proof_path = root/'profile.json', root/'proof.json'
    proof = dict(storage_profile='unixnu64',source_compiled=True,
                 native_selection='ZORN_UNIXNU64=1',
                 kernel_sha256=hashlib.sha256(kernel.read_bytes()).hexdigest())

    def check(desc, changes=None, data_profile='8g', store_mode=2, rejected=True):
        global refused
        descriptor.write_text(json.dumps(desc))
        receipt = dict(proof,profile_sha256=hashlib.sha256(descriptor.read_bytes()).hexdigest())
        receipt.update(changes or {})
        proof_path.write_text(json.dumps(receipt))
        try:
            validate(descriptor,proof_path,kernel,data_profile,store_mode)
        except ValueError:
            assert rejected
            refused += 1
        else:
            assert not rejected

    check(profile,rejected=False)
    for section,key,bad in [('root','slot','b'),('partition','name','userdata'),
        ('partition','unique_guid','cc6ddf0b-0ed0-d42e-76e4-cd44c1a849f4'),
        ('partition','bytes',128*1024**3),('Data','relative_first_lba',50331648),
        ('log','blocks',2),('Data','volume_uuid','00000000-0000-0000-0000-000000000000'),
        ('Data','seed_sha256','0'*64)]:
        candidate = copy.deepcopy(profile)
        (candidate if section=='root' else candidate[section])[key] = bad
        check(candidate)
    for key,bad in [('kernel_sha256','0'*64),('profile_sha256','1'*64),
                    ('source_compiled',False),('native_selection','legacy-userdata')]:
        check(profile,{key:bad})
    check(profile,data_profile='512m')
    check(profile,store_mode=0)
    check([])
    check(dict(profile,Data=[]))

print(json.dumps(dict(valid=1,refusals=refused,device_calls=0,
                     scope='offline consistency only; no hardware or boot qualification')))
