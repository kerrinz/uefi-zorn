# K80 iOS26 and retained firmware — 2026-11-17

The companion UniXNU-zorn v261 candidate reached the iOS lockscreen/desktop. The owner confirms swipe,tap,long-press and unlock responses,then a freeze after long-pressing Settings. Both GPU and pure CPU paths have low frame rate;no ranking or measured FPS is claimed. GPU-path stability remains unresolved. This is partial functionality,not full GPU/Metal/display/touch acceptance.

One protected boot returned automatically to verifiedTWRP in333.628seconds with zero retries.39CDC frames/67975bytes and240seconds of silent USB-camera video were saved. Seven protected sample pairs matched and the BCB full-page/tail checks passed. The second native client had3325sampled calls without a sampled Close or process exit;first recorded backend error is method3 BoMap NoResources. The inner resource branch and the later Settings freeze are not yet causally linked. Existing120s CDC polling misses late UI behavior;next driver work is bounded late-window and real mapping diagnostics.

Exact inputs:

- Kernel: `fd74f710a949b40d1f7076e534d2836106aa140bf45e7365fecf718a9c4de90f`.
- Boot image: `0e2b7278b8d5cd54121f11add6a71cf02628d1411620f9e404d2a32b950b7596`.
- Reused FD: `1bf94507996700b508474956f5d7f96fa7df764201951b0ce8e5ce8b592a11ab`.
- ADT: `98f04ff54b9573ddaa2c4716da0e954fae8192d15b1f105426eba7f216805936`.
- Retained installed252 root: `859c7ebae6355ef7e089896680b0b8ffd9a03af8a1f078918feec740b7a06b02`.

The independent candidate changed the kernel payload only. Firmware,launcher,root,Android,Recovery,iPadOS17,Data,GPT and boot partitions retain their recorded scope;this is not a new firmware build or firmware installation. The default format2 iPadOS17 profile and historical inputs remain preserved. [Firmware reuse evidence](evidence/k80-ios26-v261-reused-firmware-2026-11-17.json) records the companion exact result;large raw logs and video remain in the local trial archive.

The authoritative device record belongs to [UniXNU-zorn](https://github.com/kerrinz/UniXNU-zorn). Its catalog fix moves the complete historical ledger out of the oversized root entry,keeps a concise root record below48KiB and adds a completeness guard. The complete published record parses;the official Blob.text ingestion path does not check truncation. Actual official-scanner controls accept complete data and reproduce the EOF error from deliberately truncated historical text. The authenticated API cutoff was not directly captured. This firmware repository does not create a duplicate whole-device porting.toml. See the companion catalog-ingestion note after publication and the [official record guide](https://unixnu.com/zh/porting/records).

Current companion source and results are included in the owner-requested local repository update. Publication of the corrected device revision and a subsequent official catalog scan/deployment are still required for the online page to change. Local commits are created at the owner’s explicit request. This synchronization makes no new phone operation,remote push or official-workflow request.
