/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#include "ZornCheckpointIdentity.h"
#include <Library/BaseMemoryLib.h>
#include "ZornCheckpointStoragePins.h"
#include "ZornCheckpointUfsPathPins.h"
enum {ZCP_OK,ZCP_ARGUMENT,ZCP_USED,ZCP_SCOPE,ZCP_NATIVE,ZCP_INTERFACE,ZCP_MEDIA,ZCP_PARTITION,ZCP_PATH,ZCP_GEOMETRY,ZCP_AMBIGUOUS,ZCP_NONE};
static BOOLEAN span(CONST VOID*p,UINTN n){return p&&n&&(UINTN)p<=MAX_UINTN-(n-1);}
static BOOLEAN apart(CONST VOID*a,UINTN an,CONST VOID*b,UINTN bn){UINTN x=(UINTN)a,y=(UINTN)b;return x<=y?y-x>=an:x-y>=bn;}
static UINT16 u16(CONST UINT8*p){return (UINT16)(p[0]|((UINT16)p[1]<<8));}
static UINT32 u32(CONST UINT8*p){return (UINT32)p[0]|((UINT32)p[1]<<8)|((UINT32)p[2]<<16)|((UINT32)p[3]<<24);}
static UINT64 u64(CONST UINT8*p){UINT64 v=0;for(unsigned i=0;i<8;++i)v|=(UINT64)p[i]<<(8*i);return v;}
static BOOLEAN guid_nonzero(CONST VOID*p){CONST UINT8*q=p;UINT8 any=0;for(unsigned i=0;i<16;++i)any|=q[i];return any!=0;}
/* The selected archived UFSDxe constructs exactly a20B hardware vendor
 * LU GUID followed by EndEntire. Only its LU0 GUID is eligible here. The
 * Partition provider appends the GPT HD node; no guessed standard UFS node,
 * optional prefix, sibling LUN, controller/RPMB path or Linux handle mapping.
 * This is descriptor identity only, not live protocol/ownership/GPT evidence. */
static UINT32 path(CONST ZCP_CANDIDATE*c){
 CONST UINT8*p=(CONST UINT8*)c->Path,*parent=(CONST UINT8*)c->ParentPath;
 const UINTN hd=sizeof(VENDOR_DEVICE_PATH);
 if(!span(p,c->PathBytes)||!span(parent,c->ParentPathBytes)||
    c->PathBytes!=hd+sizeof(HARDDRIVE_DEVICE_PATH)+4||c->ParentPathBytes!=hd+4)return ZCP_PATH;
 if(p[0]!=HARDWARE_DEVICE_PATH||p[1]!=HW_VENDOR_DP||u16(p+2)!=sizeof(VENDOR_DEVICE_PATH)||
    CompareMem(p+4,&ZcpExpectedUfsLu0Guid,sizeof(EFI_GUID)))return ZCP_PATH;
 if(CompareMem(parent,p,hd)||parent[hd]!=END_DEVICE_PATH_TYPE||
    parent[hd+1]!=END_ENTIRE_DEVICE_PATH_SUBTYPE||u16(parent+hd+2)!=4)return ZCP_PATH;
 if(p[hd]!=MEDIA_DEVICE_PATH||p[hd+1]!=MEDIA_HARDDRIVE_DP||u16(p+hd+2)!=sizeof(HARDDRIVE_DEVICE_PATH))return ZCP_PATH;
 if(u32(p+hd+4)!=ZCP_PARTITION_ORDINAL||u64(p+hd+8)!=ZCP_PARTITION_FIRST||u64(p+hd+16)!=ZCP_PARTITION_LAST-ZCP_PARTITION_FIRST+1||
    p[hd+40]!=MBR_TYPE_EFI_PARTITION_TABLE_HEADER||p[hd+41]!=SIGNATURE_TYPE_GUID||
    CompareMem(p+hd+24,&c->Partition->Info.Gpt.UniquePartitionGUID,16))return ZCP_GEOMETRY;
 const UINTN end=hd+sizeof(HARDDRIVE_DEVICE_PATH);
 if(p[end]!=END_DEVICE_PATH_TYPE||p[end+1]!=END_ENTIRE_DEVICE_PATH_SUBTYPE||u16(p+end+2)!=4)return ZCP_PATH;
 return ZCP_OK;
}
static UINT32 candidate(CONST ZCP_CANDIDATE*c){
 if(c->NativeAvailable!=63)return ZCP_NATIVE;
 for(unsigned j=0;j<6;++j)if(c->Lookup[j]!=EFI_SUCCESS)return ZCP_NATIVE;
 if(!c->Block||!c->ParentBlock||!c->Disk||!c->Partition||c->Block==c->ParentBlock||
    c->Block->Revision<EFI_BLOCK_IO_PROTOCOL_REVISION||c->ParentBlock->Revision<EFI_BLOCK_IO_PROTOCOL_REVISION||
    c->Disk->Revision!=EFI_DISK_IO_PROTOCOL_REVISION||!c->Block->Media||!c->ParentBlock->Media||
    !c->Block->ReadBlocks||!c->Block->WriteBlocks||!c->Disk->ReadDisk||!c->Disk->WriteDisk)return ZCP_INTERFACE;
 CONST EFI_BLOCK_IO_MEDIA*m=c->Block->Media,*pm=c->ParentBlock->Media;
 if(!m->MediaPresent||!pm->MediaPresent||m->RemovableMedia||pm->RemovableMedia||!m->LogicalPartition||pm->LogicalPartition||m->ReadOnly||pm->ReadOnly||m->BlockSize!=4096||pm->BlockSize!=4096)return ZCP_MEDIA;
 CONST EFI_PARTITION_INFO_PROTOCOL*part=c->Partition;
 if(part->Revision!=EFI_PARTITION_INFO_PROTOCOL_REVISION||part->Type!=PARTITION_TYPE_GPT||part->System||part->Info.Gpt.Attributes!=ZCP_PARTITION_ATTRIBUTES||
    !guid_nonzero(&part->Info.Gpt.UniquePartitionGUID)||!guid_nonzero(&part->Info.Gpt.PartitionTypeGUID)||
    CompareMem(&part->Info.Gpt.UniquePartitionGUID,&ZcpExpectedPartitionGuid,sizeof(EFI_GUID))||
    CompareMem(&part->Info.Gpt.PartitionTypeGUID,&ZcpExpectedTypeGuid,sizeof(EFI_GUID)))return ZCP_PARTITION;
 for(unsigned i=0;i<36;++i){CONST char *name=ZCP_PARTITION_NAME;UINT16 wanted=i<sizeof(ZCP_PARTITION_NAME)-1?(UINT16)name[i]:0;if(part->Info.Gpt.PartitionName[i]!=wanted)return ZCP_PARTITION;}
 if(part->Info.Gpt.StartingLBA!=ZCP_PARTITION_FIRST||part->Info.Gpt.EndingLBA!=ZCP_PARTITION_LAST||m->LastBlock!=ZCP_PARTITION_LAST-ZCP_PARTITION_FIRST||pm->LastBlock!=ZcpExpectedDiskLastBlock||
    ZCP_LOG_RELATIVE>m->LastBlock||ZCP_PARTITION_FIRST>MAX_UINT64-ZCP_LOG_RELATIVE||ZCP_LOG_ABSOLUTE>pm->LastBlock)return ZCP_GEOMETRY;
 return path(c);
}
UINT32 ZcpSelect(CONST ZCP_CANDIDATE*c,UINTN n,UINT64 epoch,UINT32 scope,ZCP_REPORT*out){
 if(!out||!c||!n||n>ZCP_MAX_CANDIDATES||!span(c,n*sizeof(*c))||!span(out,sizeof(*out))||!apart(c,n*sizeof(*c),out,sizeof(*out)))return ZCP_ARGUMENT;
 if((UINTN)c%__alignof__(ZCP_CANDIDATE)||(UINTN)out%__alignof__(ZCP_REPORT))return ZCP_ARGUMENT;
 if(out->State)return ZCP_USED;
 for(UINTN k=0;k<sizeof(*out);++k)if(((CONST UINT8*)out)[k])return ZCP_ARGUMENT;
 for(UINTN i=0;i<n;++i){
  CONST VOID*ptrs[]={c[i].Block,c[i].ParentBlock,c[i].Disk,c[i].Partition,c[i].Path,c[i].ParentPath};
  UINTN sizes[]={sizeof(EFI_BLOCK_IO_PROTOCOL),sizeof(EFI_BLOCK_IO_PROTOCOL),sizeof(EFI_DISK_IO_PROTOCOL),sizeof(EFI_PARTITION_INFO_PROTOCOL),c[i].PathBytes,c[i].ParentPathBytes};
  for(unsigned j=0;j<6;++j)if(ptrs[j]&&(!span(ptrs[j],sizes[j])||!apart(ptrs[j],sizes[j],out,sizeof(*out))))return ZCP_ARGUMENT;
  CONST EFI_BLOCK_IO_MEDIA*media[]={c[i].Block?c[i].Block->Media:NULL,c[i].ParentBlock?c[i].ParentBlock->Media:NULL};
  for(unsigned j=0;j<2;++j)if(media[j]&&(!span(media[j],sizeof(*media[j]))||!apart(media[j],sizeof(*media[j]),out,sizeof(*out))))return ZCP_ARGUMENT;
 }
 /* Pure output owner only: this is scope assertion, not EBS event/hardware
  * lease. This function stores no borrowed interface for later reuse. */
 out->State=1;out->Selected=MAX_UINT32;out->Count=(UINT32)n;out->Epoch=epoch;
 if(!epoch||scope!=1){out->Result=ZCP_SCOPE;out->State=3;return out->Result;}
 BOOLEAN incomplete=FALSE;
 for(UINTN i=0;i<n;++i){
  out->NativeAvailable[i]=c[i].NativeAvailable;
  for(unsigned j=0;j<6;++j)out->Lookup[i][j]=c[i].Lookup[j];
  UINT32 r=candidate(c+i);out->Reason[i]=r;
  if(r==ZCP_NATIVE)incomplete=TRUE;
  if(!r){++out->Matches;out->Selected=(UINT32)i;}
 }
 if(incomplete||out->Matches!=1){out->Result=incomplete?ZCP_NATIVE:out->Matches?ZCP_AMBIGUOUS:ZCP_NONE;out->Selected=MAX_UINT32;out->State=3;return out->Result;}
 CONST ZCP_CANDIDATE*chosen=c+out->Selected;
 out->MediaId=chosen->Block->Media->MediaId;out->ParentMediaId=chosen->ParentBlock->Media->MediaId;
 out->BlockSize=chosen->Block->Media->BlockSize;out->ReadOnly=chosen->Block->Media->ReadOnly;out->LogicalPartition=chosen->Block->Media->LogicalPartition;
 out->RelativeLba=ZCP_LOG_RELATIVE;out->AbsoluteLba=ZCP_LOG_ABSOLUTE;out->PartitionFirst=ZCP_PARTITION_FIRST;out->PartitionLast=ZCP_PARTITION_LAST;
 out->DescriptorEligible=1;out->LiveDiscoveryVerified=out->GptReadVerified=out->WriteAuthorized=0;out->State=2;out->Result=ZCP_OK;return ZCP_OK;
}
