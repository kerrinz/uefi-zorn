/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#pragma once
#include <Uefi.h>
/* Installed unixnu64 profile, checked against storage/unixnu64.json and the
 * archived primary/backup GPT. These bytes never grant native I/O or a lease.
 * Do not substitute Android userdata, an APFS UUID, or a Linux device handle.
 */
#define ZCP_PARTITION_NAME "unixnu"
#define ZCP_PARTITION_ORDINAL 35u
#define ZCP_PARTITION_ATTRIBUTES 0ULL
#define ZCP_PARTITION_FIRST 47271680ULL
#define ZCP_PARTITION_LAST 64048895ULL
#define ZCP_LOG_RELATIVE 2291712ULL
#define ZCP_LOG_ABSOLUTE (ZCP_PARTITION_FIRST+ZCP_LOG_RELATIVE)
static CONST EFI_GUID ZcpExpectedPartitionGuid={0xb279731f,0xccad,0x4ef5,{0xa8,0xb7,0xe7,0x44,0x0c,0xd0,0x8d,0xe3}};
static CONST EFI_GUID ZcpExpectedTypeGuid={0x0fc63daf,0x8483,0x4772,{0x8e,0x79,0x3d,0x69,0xd8,0x47,0x7d,0xe4}};
static CONST EFI_GUID ZcpExpectedDiskGuid={0xdc8e1b86,0x0f82,0x0eeb,{0x83,0xb3,0x03,0x52,0x7a,0xc7,0x74,0xa2}};
static CONST UINT64 ZcpExpectedDiskLastBlock=64049151ULL;
