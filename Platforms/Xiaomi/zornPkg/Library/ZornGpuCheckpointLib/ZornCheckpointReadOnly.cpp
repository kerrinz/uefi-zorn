/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#include "ZornCheckpointReadOnly.h"
#include "ZornCheckpointStoragePins.h"
extern "C" {
#include <Library/BaseMemoryLib.h>
}
static bool span(const VOID*p,UINTN n){return p&&n&&UINTN(p)<=MAX_UINTN-(n-1);}
static bool apart(const VOID*a,UINTN an,const VOID*b,UINTN bn)
{return UINTN(a)<=UINTN(b)?UINTN(b)-UINTN(a)>=an:UINTN(a)-UINTN(b)>=bn;}
ZcrmResult ZornCheckpointReadOnly::fail(ZcrmResult r,UINT32 op)
{
 if(!report_.FirstError){report_.FirstError=r;report_.FirstOperation=op;}
 report_.State=3;report_.GptReadVerified=0;busy_=false;return r;
}
ZcrmReport ZornCheckpointReadOnly::report()const
{auto r=report_;r.ExpiredEvents=lifetime_.report().expired_events;return r;}
bool ZornCheckpointReadOnly::stable(const ZCP_CANDIDATE&c)const
{
 return discoveryLifetime_&&discoveryLifetime_->check(report_.Epoch)==EFI_SUCCESS&&
  lifetime_.check(report_.Epoch)==EFI_SUCCESS&&c.Block&&c.ParentBlock&&
  c.Block->Media==childMedia_&&c.ParentBlock->Media==parentMedia_&&
  !CompareMem(c.Block->Media,&child_,sizeof(child_))&&
  !CompareMem(c.ParentBlock->Media,&parent_,sizeof(parent_));
}
ZcrmResult ZornCheckpointReadOnly::read(const ZCP_CANDIDATE&c,UINT32 op,EFI_LBA lba,UINTN n,VOID*out)
{
 if(!stable(c))return fail(ZCRM_MEDIA,op);
 if(lba>parent_.LastBlock||!n||n%4096||n/4096>parent_.LastBlock-lba+1)return fail(ZCRM_HEADER,op);
 report_.Attempted|=1u<<op;
 const EFI_STATUS status=c.ParentBlock->ReadBlocks(c.ParentBlock,parent_.MediaId,lba,n,out);
 report_.NativeStatus[op]=status;report_.Returned|=1u<<op;
 // Keep actual native error/warning even if an EBS event also expired in-call.
 if(status!=EFI_SUCCESS)return fail(ZCRM_READ,op);
 if(!stable(c))return fail(ZCRM_MEDIA,op);
 return ZCRM_OK;
}
ZcrmResult ZornCheckpointReadOnly::crc(EFI_BOOT_SERVICES*bs,const ZCP_CANDIDATE&c,UINT32 i,VOID*p,UINTN n,UINT32 wanted)
{
 const UINT32 op=4+i;if(!stable(c))return fail(ZCRM_MEDIA,op);
 report_.Attempted|=1u<<op;UINT32 value=0;
 const EFI_STATUS status=bs->CalculateCrc32(p,n,&value);
 report_.NativeStatus[op]=status;report_.Returned|=1u<<op;
 if(status!=EFI_SUCCESS)return fail(ZCRM_CRC_NATIVE,op);
 report_.CrcValue[i]=value;report_.CrcAvailable|=1u<<i;
 if(!stable(c))return fail(ZCRM_MEDIA,op);
 if(value!=wanted)return fail(ZCRM_CRC,op);
 return ZCRM_OK;
}
ZcrmResult ZornCheckpointReadOnly::validate(EFI_BOOT_SERVICES*bs,const ZCP_CANDIDATE*c,UINTN n,UINT64 epoch,ZornCheckpointBootLifetime*discovery)
{
 if(busy_||report_.State)return ZCRM_USED;
 if(!span(bs,sizeof(*bs))||!apart(bs,sizeof(*bs),this,sizeof(*this))||
    !bs->CalculateCrc32||!epoch||!discovery||
    !span(discovery,sizeof(*discovery))||!apart(discovery,sizeof(*discovery),this,sizeof(*this))||
    UINTN(discovery)%alignof(ZornCheckpointBootLifetime)||!c||!n||n>ZCP_MAX_CANDIDATES||
    !span(c,n*sizeof(*c))||!apart(c,n*sizeof(*c),this,sizeof(*this))||
    UINTN(c)%alignof(ZCP_CANDIDATE))return ZCRM_ARGUMENT;
 // Prevent provider output buffers from aliasing any borrowed descriptor.
 for(UINTN i=0;i<n;++i){
  const VOID*p[]={c[i].Block,c[i].ParentBlock,c[i].Disk,c[i].Partition,c[i].Path,c[i].ParentPath};
  const UINTN sizes[]={sizeof(EFI_BLOCK_IO_PROTOCOL),sizeof(EFI_BLOCK_IO_PROTOCOL),sizeof(EFI_DISK_IO_PROTOCOL),sizeof(EFI_PARTITION_INFO_PROTOCOL),c[i].PathBytes,c[i].ParentPathBytes};
  for(unsigned j=0;j<6;++j)if(p[j]&&(!span(p[j],sizes[j])||!apart(p[j],sizes[j],this,sizeof(*this))))return ZCRM_ARGUMENT;
  const EFI_BLOCK_IO_MEDIA*media[]={c[i].Block?c[i].Block->Media:nullptr,c[i].ParentBlock?c[i].ParentBlock->Media:nullptr};
  for(unsigned j=0;j<2;++j)if(media[j]&&(!span(media[j],sizeof(*media[j]))||!apart(media[j],sizeof(*media[j]),this,sizeof(*this))))return ZCRM_ARGUMENT;
 }
 busy_=true;report_.State=1;report_.Epoch=epoch;report_.Selected=MAX_UINT32;report_.FirstOperation=MAX_UINT32;
 if(ZcpSelect(c,n,epoch,1,&selected_)!=0)return fail(ZCRM_DESCRIPTOR);
 report_.Selected=selected_.Selected;const auto&chosen=c[report_.Selected];
 parentMedia_=chosen.ParentBlock->Media;childMedia_=chosen.Block->Media;
 CopyMem(&parent_,chosen.ParentBlock->Media,sizeof(parent_));CopyMem(&child_,chosen.Block->Media,sizeof(child_));
 if(parent_.LastBlock!=ZcpExpectedDiskLastBlock||parent_.IoAlign>4096||
    (parent_.IoAlign>1&&(parent_.IoAlign&(parent_.IoAlign-1))))return fail(ZCRM_MEDIA);
 report_.ParentMediaId=parent_.MediaId;report_.ChildMediaId=child_.MediaId;
 discoveryLifetime_=discovery;
 if(discovery->check(epoch)!=EFI_SUCCESS)return fail(ZCRM_LIFETIME);
 if(lifetime_.prepare(bs,epoch,discovery)!=ZCBL_OK)return fail(ZCRM_LIFETIME);
 if(discovery->check(epoch)!=EFI_SUCCESS)return fail(ZCRM_LIFETIME);
 UINTN entryBytes=0,rounded=0;
 EFI_PARTITION_TABLE_HEADER h[2]{};
 for(UINT32 i=0;i<2;++i){
  const EFI_LBA here=i?parent_.LastBlock:1;
  if(read(chosen,i*2,here,4096,header_[i].bytes)!=ZCRM_OK)return ZcrmResult(report_.FirstError);
  CopyMem(&h[i],header_[i].bytes,sizeof(h[i]));auto&g=h[i];
  if(g.Header.Signature!=EFI_PTAB_HEADER_ID||g.Header.Revision!=0x10000||
     g.Header.HeaderSize!=sizeof(g)||g.Header.Reserved||g.MyLBA!=here||
     g.AlternateLBA!=(i?1:parent_.LastBlock)||g.SizeOfPartitionEntry!=sizeof(EFI_PARTITION_ENTRY)||
     !g.NumberOfPartitionEntries||g.NumberOfPartitionEntries>256||
     CompareMem(&g.DiskGUID,&ZcpExpectedDiskGuid,sizeof(EFI_GUID)))return fail(ZCRM_HEADER,i*2);
  const UINTN bytes=g.NumberOfPartitionEntries*sizeof(EFI_PARTITION_ENTRY),blocks=(bytes+4095)/4096;
  if(g.FirstUsableLBA<2+blocks||g.FirstUsableLBA>g.LastUsableLBA||
     g.LastUsableLBA>=parent_.LastBlock-blocks||g.FirstUsableLBA>ZCP_PARTITION_FIRST||
     g.LastUsableLBA<ZCP_PARTITION_LAST||
     (!i?g.PartitionEntryLBA!=2:(g.PartitionEntryLBA<=g.LastUsableLBA||g.PartitionEntryLBA>here-blocks)))return fail(ZCRM_HEADER,i*2);
  const UINT32 expected=g.Header.CRC32;auto crcHeader=g;crcHeader.Header.CRC32=0;
  if(crc(bs,chosen,i*2,&crcHeader,sizeof(crcHeader),expected)!=ZCRM_OK)return ZcrmResult(report_.FirstError);
  if(!i){entryBytes=bytes;rounded=blocks*4096;report_.EntryCount=g.NumberOfPartitionEntries;}
  else if(bytes!=entryBytes||g.FirstUsableLBA!=h[0].FirstUsableLBA||g.LastUsableLBA!=h[0].LastUsableLBA||
    g.PartitionEntryArrayCRC32!=h[0].PartitionEntryArrayCRC32)return fail(ZCRM_HEADER,i*2);
  if(read(chosen,i*2+1,g.PartitionEntryLBA,rounded,entries_[i].bytes)!=ZCRM_OK)return ZcrmResult(report_.FirstError);
  if(crc(bs,chosen,i*2+1,entries_[i].bytes,entryBytes,g.PartitionEntryArrayCRC32)!=ZCRM_OK)return ZcrmResult(report_.FirstError);
 }
 if(CompareMem(entries_[0].bytes,entries_[1].bytes,entryBytes))return fail(ZCRM_ENTRIES);
 UINT32 found=0;
 for(UINT32 i=0;i<h[0].NumberOfPartitionEntries;++i){
  const auto*e=reinterpret_cast<const EFI_PARTITION_ENTRY*>(entries_[0].bytes+i*sizeof(EFI_PARTITION_ENTRY));
  bool name=true;const char*text=ZCP_PARTITION_NAME;
  for(unsigned j=0;j<36;++j)if(e->PartitionName[j]!=(j<sizeof(ZCP_PARTITION_NAME)-1?UINT16(text[j]):0))name=false;
  if(!name)continue;++found;report_.PartitionOrdinal=i+1;
  if(i+1!=ZCP_PARTITION_ORDINAL||e->Attributes!=ZCP_PARTITION_ATTRIBUTES||e->StartingLBA!=ZCP_PARTITION_FIRST||e->EndingLBA!=ZCP_PARTITION_LAST||
     CompareMem(&e->UniquePartitionGUID,&ZcpExpectedPartitionGuid,sizeof(EFI_GUID))||
     CompareMem(&e->PartitionTypeGUID,&ZcpExpectedTypeGuid,sizeof(EFI_GUID))||
     CompareMem(e,&chosen.Partition->Info.Gpt,sizeof(*e)))return fail(ZCRM_PARTITION);
 }
 if(found!=1)return fail(ZCRM_PARTITION);
 ZCP_REPORT after{};
 if(!stable(chosen)||ZcpSelect(c,n,epoch,1,&after)!=0||after.Selected!=selected_.Selected||
    CompareMem(&after,&selected_,sizeof(after)))return fail(ZCRM_MEDIA);
 report_.GptReadVerified=1;report_.State=2;busy_=false;return ZCRM_OK;
}
ZcblResult ZornCheckpointReadOnly::retire()
{
 if(busy_||!report_.State||report_.RetireAttempted)return ZCBL_USED;
 busy_=true;report_.RetireAttempted=1;const auto r=lifetime_.close(discoveryLifetime_);
 report_.RetireResult=r;busy_=false;return r;
}
