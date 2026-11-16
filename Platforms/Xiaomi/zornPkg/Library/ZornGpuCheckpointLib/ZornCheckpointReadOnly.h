/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#pragma once
#include "ZornCheckpointBootLifetime.h"
extern "C" {
#include "ZornCheckpointIdentity.h"
}
#include <Uefi/UefiGpt.h>
enum ZcrmResult : UINT32 {ZCRM_OK,ZCRM_ARGUMENT,ZCRM_USED,ZCRM_LIFETIME,ZCRM_DESCRIPTOR,
 ZCRM_MEDIA,ZCRM_READ,ZCRM_HEADER,ZCRM_CRC_NATIVE,ZCRM_CRC,ZCRM_ENTRIES,ZCRM_PARTITION};
struct ZcrmReport {
 UINT64 Epoch;EFI_STATUS NativeStatus[8];UINT32 CrcValue[4];
 UINT32 State,FirstError,FirstOperation,Attempted,Returned,CrcAvailable;
 UINT32 Selected,ParentMediaId,ChildMediaId,EntryCount,PartitionOrdinal;
 UINT32 GptReadVerified,LiveDiscoveryVerified,WriteAuthorized,RuntimeComplete;
 UINT32 RetireAttempted,RetireResult,ExpiredEvents;
};
/* Fixed-target pre-EBS READ-ONLY native verifier, not a generic GPT decoder or
 * storage writer. Caller owns stable real typed descriptors/paths/interfaces
 * across the whole serialized normal-thread call. ZcpSelect is rerun before
 * I/O and after it, with actual media identity compared around each provider.
 * A typed real discovery event owner is required and checked alongside this
 * reader's own events before/after every ReadBlocks/CalculateCrc32.
 * This closes expiry during nested registration; no fabricated callback gate. No
 * caller-success lease, imported recovery success or protocol discovery claim.
 * Persistent noncopy context/buffers must survive every possible callback;
 * failure retains all bytes/statuses. No destructor cleanup, retry, reset,
 * flush, write, allocation, mount, SMC, GPU access or new wire/transport.
 * Explicit retire closes only known events while still pre-EBS. Expiry cannot
 * cancel an in-flight provider; calls are not wall-clock bounded. Native read
 * status has no returned byte count: errors/warnings never parse the buffer.
 * Even successful GPT verification is not write/GPU/runtime authorization.
 */
class alignas(4096) ZornCheckpointReadOnly final {
public:
 constexpr ZornCheckpointReadOnly()=default;
 ~ZornCheckpointReadOnly()=default;
 ZornCheckpointReadOnly(const ZornCheckpointReadOnly&)=delete;
 ZornCheckpointReadOnly&operator=(const ZornCheckpointReadOnly&)=delete;
 ZcrmResult validate(EFI_BOOT_SERVICES*,const ZCP_CANDIDATE*,UINTN,UINT64,ZornCheckpointBootLifetime*);
 ZcblResult retire();
 ZcrmReport report()const;
 ZcblReport lifetimeReport()const{return lifetime_.report();}
private:
 friend class ZornEarlyFailureSink;
 struct alignas(4096) HeaderBlock {UINT8 bytes[4096]{};};
 struct alignas(4096) EntryBlock {UINT8 bytes[32768]{};};
 ZornCheckpointBootLifetime lifetime_{};ZcrmReport report_{};
 ZCP_REPORT selected_{};EFI_BLOCK_IO_MEDIA parent_{},child_{};
 const EFI_BLOCK_IO_MEDIA*parentMedia_{},*childMedia_{};
 ZornCheckpointBootLifetime*discoveryLifetime_{};bool busy_{};
 HeaderBlock header_[2]{};EntryBlock entries_[2]{};
 ZcrmResult fail(ZcrmResult,UINT32=MAX_UINT32);
 bool stable(const ZCP_CANDIDATE&)const;
 ZcrmResult read(const ZCP_CANDIDATE&,UINT32,EFI_LBA,UINTN,VOID*);
 ZcrmResult crc(EFI_BOOT_SERVICES*,const ZCP_CANDIDATE&,UINT32,VOID*,UINTN,UINT32);
};
