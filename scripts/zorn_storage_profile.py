"""Offline consistency checks for the dedicated unixnu storage payload.

This metadata selects an already compiled kernel. It does not relocate an old
kernel, operate a device, or establish runtime storage ownership.
"""
import hashlib
import json
from pathlib import Path


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validate(profile_path, proof_path, kernel, data_profile, store_mode):
    profile_path, proof_path = Path(profile_path), Path(proof_path)
    profile = json.loads(profile_path.read_text())
    proof = json.loads(proof_path.read_text())
    if not isinstance(profile, dict) or not isinstance(proof, dict):
        raise ValueError('storage descriptor/proof must be objects')
    partition, data, log = profile['partition'], profile['Data'], profile['log']
    if not all(isinstance(value, dict) for value in (partition, data, log, profile['system'], profile['native_selection'])):
        raise ValueError('storage descriptor sections must be objects')
    if (profile['schema_version'] != 1 or profile['name'] != 'unixnu64' or
        profile['serial'] != '92988a43' or profile['product'] != 'zorn' or profile['slot'] != 'a' or
        partition['name'] != 'unixnu' or partition['lba_bytes'] != 4096 or
        partition['first_lba'] != 47271680 or partition['last_lba'] != 64048895 or
        partition['bytes'] != 64*1024**3 or
        partition['type_guid'] != '0fc63daf-8483-4772-8e79-3d69d8477de4' or
        partition['unique_guid'] != 'b279731f-ccad-4ef5-a8b7-e7440cd08de3'):
        raise ValueError('dedicated unixnu64 partition identity differs')
    if (data_profile != '8g' or store_mode not in (1, 2) or
        data['profile'] != '8g' or data['relative_first_lba'] != 4194304 or
        data['pages'] != 2097152 or data['bitmap_blocks'] != 64 or
        data['volume_uuid'] != 'C7D77FF3-6437-4C4A-8E05-E8E239AC1641' or
        data['seed_sha256'] != 'f05d5604237ef74da29181b5c1de5524b7ad0af9e18bad9c439df318dd5d2703' or
        data['window_blocks'] != 2097217 or log != dict(relative_lba=2291712,blocks=1) or
        (data['relative_first_lba']+data['window_blocks'])*4096 > partition['bytes'] or
        profile['system']['image_bytes'] != 9382658048 or
        profile['system']['runtime_readonly'] is not True or
        profile['native_selection']['Android_userdata_fallback'] is not False):
        raise ValueError('unixnu64 Data/system/log geometry differs')
    if (proof['storage_profile'] != profile['name'] or
        proof['profile_sha256'] != sha(profile_path) or
        proof['kernel_sha256'] != sha(kernel) or
        proof['source_compiled'] is not True or proof['native_selection'] != 'ZORN_UNIXNU64=1'):
        raise ValueError('kernel was not bound to this dedicated storage profile')
    return dict(storage_profile='unixnu64',partition='unixnu',slot='a',
        kernel_sha256=sha(kernel),profile_sha256=sha(profile_path),
        build_proof_sha256=sha(proof_path),partition_bytes=partition['bytes'],
        logical_Data_bytes=data['pages']*4096,device_operations=False,allow_boot=False)
