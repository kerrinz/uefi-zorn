/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#pragma once
#include "ZornCheckpointReadOnly.h"
enum ZcdResult:UINT32 {ZCD_OK,ZCD_ARGUMENT,ZCD_USED,ZCD_LIFETIME,ZCD_LOCATE,
 ZCD_CAPACITY,ZCD_HANDLE,ZCD_LOOKUP,ZCD_INTERFACE,ZCD_PATH,ZCD_AMBIGUOUS,
 ZCD_MISSING,ZCD_CHANGED,ZCD_VERIFY,ZCD_DISABLED};
enum {ZCD_MAX_HANDLES=512};
struct ZcdLookupReport {EFI_STATUS Status[4];UINT32 Attempted,Returned,Available,PathBytes;};
struct ZcdReport {
 UINT64 Epoch,LocateBytes;EFI_STATUS LocateStatus;
 UINT32 State,FirstError,FirstHandle,FirstProtocol,LocateAttempted,LocateReturned;
 UINT32 HandleCount,ParentIndex,ChildIndex,DiscoveryComplete,VerifierAttempted,VerifierResult;
 UINT32 GptReadVerified,LiveDiscoveryVerified,WriteAuthorized,RuntimeComplete;
 UINT32 RetireAttempted,ReaderRetire,LifetimeRetire,ExpiredEvents;
};
/* Default-off explicit caller, never installed/entered by this isolated stage.
 * One fixed-capacity LocateHandle(ByProtocol,BlockIO); no allocation, rescan,
 * ConnectController, write/reset/flush, query carrier, GPU or SCM calls.
 * Firmware supplies valid stable typed interfaces/device paths; bounded path
 * walking and range checks do not authenticate arbitrary pointers. Normal
 * serialized pre-EBS thread only. Context must persist for all possible event
 * callbacks, including unknown partial registration/close. No dtor cleanup.
 * Real Before-EBS/EBS owner gates every lookup; composed reader owns its own
 * real events around reads/CRC. Parent is the unique actual LU0 parent path
 * in the same returned handle inventory. Reports describe an epoch-bound
 * observation, never a current lease/write/GPU ownership or readback proof.
 * Selected SDK HandleProtocol delegates to CoreOpenProtocol with the DXE core
 * agent and can allocate/increment protocol bookkeeping; its internal loops
 * and native service latency are not bounded by this caller's capacity. No
 * CloseProtocol is invented for an agent/context this code does not own.
 */
class alignas(4096) ZornCheckpointDiscovery final {
public:
 constexpr ZornCheckpointDiscovery()=default;
 ~ZornCheckpointDiscovery()=default;
 ZornCheckpointDiscovery(const ZornCheckpointDiscovery&)=delete;
 ZornCheckpointDiscovery&operator=(const ZornCheckpointDiscovery&)=delete;
 ZcdResult run(EFI_BOOT_SERVICES*,UINT64,bool enabled=false);
 ZcblResult retire();
 ZcdReport report()const;
 bool lookupReport(UINT32,ZcdLookupReport*)const;
 ZcrmReport readerReport()const{return reader_.report();}
 ZcblReport lifetimeReport()const{return lifetime_.report();}
 ZcblReport readerLifetimeReport()const{return reader_.lifetimeReport();}
private:
 friend class ZornEarlyFailureSink;
 struct Row {
  ZcdLookupReport Report{};
  EFI_BLOCK_IO_PROTOCOL*Block{};EFI_DEVICE_PATH_PROTOCOL*Path{};
  EFI_DISK_IO_PROTOCOL*Disk{};EFI_PARTITION_INFO_PROTOCOL*Partition{};
  EFI_BLOCK_IO_PROTOCOL BlockCopy{};EFI_BLOCK_IO_MEDIA MediaCopy{};
  EFI_DISK_IO_PROTOCOL DiskCopy{};EFI_PARTITION_INFO_PROTOCOL PartitionCopy{};
  UINT8 PathCopy[ZCP_PATH_MAX]{};
 };
 ZornCheckpointBootLifetime lifetime_{};ZcdReport report_{};
 EFI_HANDLE handles_[ZCD_MAX_HANDLES]{};Row rows_[ZCD_MAX_HANDLES]{};
 ZCP_CANDIDATE candidate_{};
 bool busy_{};ZornCheckpointReadOnly reader_{};
 ZcdResult fail(ZcdResult,UINT32=MAX_UINT32,UINT32=MAX_UINT32);
 bool external(const VOID*,UINTN)const;
 bool stable()const;
 ZcdResult lookup(EFI_BOOT_SERVICES*,UINT32,UINT32,VOID**);
 bool copyPath(Row&);
};
