/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#pragma once
#include <Uefi.h>
#include <Protocol/BlockIo.h>
#include <Protocol/DiskIo.h>
#include <Protocol/PartitionInfo.h>
#include <Protocol/DevicePath.h>
/* Pure descriptor eligibility, NOT live discovery, GPT/CRC verification,
 * permission to issue I/O or post-EBS borrowed interface ownership. Normal
 * pre-EBS serialized caller owns all pointers/spans stable through return.
 * Caller must supply actual native lookup statuses, available bits separate;
 * selector never invents missing status or calls any protocol method. */
#define ZCP_MAX_CANDIDATES 32
#define ZCP_PATH_MAX 512
#include "ZornCheckpointStoragePins.h"
typedef struct {
 EFI_BLOCK_IO_PROTOCOL *Block,*ParentBlock;
 EFI_DISK_IO_PROTOCOL *Disk;
 EFI_PARTITION_INFO_PROTOCOL *Partition;
 CONST EFI_DEVICE_PATH_PROTOCOL *Path,*ParentPath;
 UINTN PathBytes,ParentPathBytes;
 EFI_STATUS Lookup[6]; /* Block/Disk/Partition/Path/ParentBlock/ParentPath */
 UINT32 NativeAvailable;
} ZCP_CANDIDATE;
typedef struct {
 UINT64 Epoch;
 UINT64 Lookup[ZCP_MAX_CANDIDATES][6];
 UINT64 RelativeLba,AbsoluteLba,PartitionFirst,PartitionLast;
 UINT32 State,Result,Count,Selected,Matches;
 UINT32 NativeAvailable[ZCP_MAX_CANDIDATES],Reason[ZCP_MAX_CANDIDATES];
 UINT32 MediaId,ParentMediaId,BlockSize,ReadOnly,LogicalPartition;
 UINT32 DescriptorEligible,LiveDiscoveryVerified,GptReadVerified,WriteAuthorized;
} ZCP_REPORT;
/* Output/report persistent caller-zeroed exclusive storage, single-use. No allocation, native
 * query, I/O, release, handles/pointers output, retry or destructor behavior. */
UINT32 ZcpSelect(CONST ZCP_CANDIDATE *,UINTN,UINT64,UINT32,ZCP_REPORT *);
