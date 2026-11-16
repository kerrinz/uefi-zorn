/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#include "ZornCheckpointDiscovery.h"
#include "ZornCheckpointStoragePins.h"
#include "ZornCheckpointUfsPathPins.h"
extern "C" {
#include <Library/BaseMemoryLib.h>
}
static EFI_GUID blockGuid=EFI_BLOCK_IO_PROTOCOL_GUID;
static EFI_GUID pathGuid=EFI_DEVICE_PATH_PROTOCOL_GUID;
static EFI_GUID partGuid=EFI_PARTITION_INFO_PROTOCOL_GUID;
static EFI_GUID diskGuid=EFI_DISK_IO_PROTOCOL_GUID;
static EFI_GUID*const protocols[]={&blockGuid,&pathGuid,&partGuid,&diskGuid};
bool ZornCheckpointDiscovery::external(const VOID*p,UINTN n)const
{const UINTN a=UINTN(p),b=UINTN(this);return p&&n&&a<=MAX_UINTN-(n-1)&&(a<=b?b-a>=n:a-b>=sizeof(*this));}
ZcdResult ZornCheckpointDiscovery::fail(ZcdResult r,UINT32 h,UINT32 p)
{if(!report_.FirstError){report_.FirstError=r;report_.FirstHandle=h;report_.FirstProtocol=p;}
 report_.State=3;report_.GptReadVerified=0;busy_=false;return r;}
ZcdReport ZornCheckpointDiscovery::report()const
{auto r=report_;r.ExpiredEvents=lifetime_.report().expired_events|reader_.lifetimeReport().expired_events;return r;}
bool ZornCheckpointDiscovery::lookupReport(UINT32 i,ZcdLookupReport*out)const
{if(!report_.State||i>=report_.HandleCount||!external(out,sizeof(*out)))return false;CopyMem(out,&rows_[i].Report,sizeof(*out));return true;}
ZcdResult ZornCheckpointDiscovery::lookup(EFI_BOOT_SERVICES*b,UINT32 h,UINT32 p,VOID**out)
{
 if(lifetime_.check(report_.Epoch)!=EFI_SUCCESS)return fail(ZCD_LIFETIME,h,p);
 auto&r=rows_[h].Report;*out=nullptr;r.Attempted|=1u<<p;
 const EFI_STATUS s=b->HandleProtocol(handles_[h],protocols[p],out);
 r.Status[p]=s;r.Returned|=1u<<p;if(*out)r.Available|=1u<<p;
 if(s!=EFI_SUCCESS)return fail(ZCD_LOOKUP,h,p);
 if(lifetime_.check(report_.Epoch)!=EFI_SUCCESS)return fail(ZCD_LIFETIME,h,p);
 if(!*out)return fail(ZCD_INTERFACE,h,p);
 return ZCD_OK;
}
bool ZornCheckpointDiscovery::copyPath(Row&r)
{
 UINTN at=0;
 for(unsigned nodes=0;nodes<32;++nodes){
  if(at>ZCP_PATH_MAX-4||UINTN(r.Path)>MAX_UINTN-at)return false;
  const auto*p=reinterpret_cast<const UINT8*>(r.Path)+at;
  if(!external(p,4))return false;
  const UINTN n=UINTN(p[2])|(UINTN(p[3])<<8);
  if(n<4||n>ZCP_PATH_MAX-at||!external(p,n))return false;
  CopyMem(r.PathCopy+at,p,n);at+=n;
  if(p[0]==END_DEVICE_PATH_TYPE){
   if(p[1]!=END_ENTIRE_DEVICE_PATH_SUBTYPE||n!=4)return false;
   r.Report.PathBytes=UINT32(at);return true;
  }
 }
 return false;
}
bool ZornCheckpointDiscovery::stable()const
{
 if(lifetime_.check(report_.Epoch)!=EFI_SUCCESS)return false;
 for(UINT32 i=0;i<report_.HandleCount;++i){const auto&r=rows_[i];
  if(CompareMem(r.Block,&r.BlockCopy,sizeof(r.BlockCopy))||
     CompareMem(r.BlockCopy.Media,&r.MediaCopy,sizeof(r.MediaCopy))||
     CompareMem(r.Path,r.PathCopy,r.Report.PathBytes))return false;
  if(r.Partition&&CompareMem(r.Partition,&r.PartitionCopy,sizeof(r.PartitionCopy)))return false;
  if(r.Disk&&CompareMem(r.Disk,&r.DiskCopy,sizeof(r.DiskCopy)))return false;
 }
 return true;
}
ZcdResult ZornCheckpointDiscovery::run(EFI_BOOT_SERVICES*b,UINT64 e,bool enabled)
{
 if(busy_||report_.State)return ZCD_USED;
 if(!enabled)return ZCD_DISABLED;
 if(!e||!external(b,sizeof(*b))||UINTN(b)%alignof(EFI_BOOT_SERVICES)||
    b->Hdr.Signature!=EFI_BOOT_SERVICES_SIGNATURE||b->Hdr.HeaderSize<sizeof(*b)||
    !b->LocateHandle||!b->HandleProtocol||!b->CreateEventEx||!b->CloseEvent||!b->CalculateCrc32)return ZCD_ARGUMENT;
 busy_=true;report_.State=1;report_.Epoch=e;
 report_.FirstHandle=report_.FirstProtocol=report_.ParentIndex=report_.ChildIndex=MAX_UINT32;
 if(lifetime_.prepare(b,e)!=ZCBL_OK)return fail(ZCD_LIFETIME);
 if(lifetime_.check(e)!=EFI_SUCCESS)return fail(ZCD_LIFETIME);
 UINTN bytes=sizeof(handles_);report_.LocateAttempted=1;
 const EFI_STATUS status=b->LocateHandle(ByProtocol,protocols[0],nullptr,&bytes,handles_);
 report_.LocateStatus=status;report_.LocateBytes=bytes;report_.LocateReturned=1;
 if(status!=EFI_SUCCESS)return fail(ZCD_LOCATE);
 if(lifetime_.check(e)!=EFI_SUCCESS)return fail(ZCD_LIFETIME);
 if(!bytes||bytes>sizeof(handles_)||bytes%sizeof(EFI_HANDLE))return fail(ZCD_CAPACITY);
 report_.HandleCount=UINT32(bytes/sizeof(EFI_HANDLE));
 for(UINT32 i=0;i<report_.HandleCount;++i){
  if(!handles_[i])return fail(ZCD_HANDLE,i);
  for(UINT32 j=0;j<i;++j)if(handles_[i]==handles_[j])return fail(ZCD_HANDLE,i);
 }
 UINT32 parents=0,children=0;
 for(UINT32 i=0;i<report_.HandleCount;++i){auto&r=rows_[i];VOID*p=nullptr;
  if(lookup(b,i,0,&p)!=ZCD_OK)return ZcdResult(report_.FirstError);
  r.Block=static_cast<EFI_BLOCK_IO_PROTOCOL*>(p);
  if(!external(p,sizeof(*r.Block))||UINTN(p)%alignof(EFI_BLOCK_IO_PROTOCOL))return fail(ZCD_INTERFACE,i,0);
  CopyMem(&r.BlockCopy,p,sizeof(r.BlockCopy));
  if(!external(r.BlockCopy.Media,sizeof(r.MediaCopy))||UINTN(r.BlockCopy.Media)%alignof(EFI_BLOCK_IO_MEDIA))return fail(ZCD_INTERFACE,i,0);
  CopyMem(&r.MediaCopy,r.BlockCopy.Media,sizeof(r.MediaCopy));
  for(UINT32 j=0;j<i;++j)if(r.Block==rows_[j].Block)return fail(ZCD_AMBIGUOUS,i,0);
  if(lookup(b,i,1,&p)!=ZCD_OK)return ZcdResult(report_.FirstError);
  r.Path=static_cast<EFI_DEVICE_PATH_PROTOCOL*>(p);
  if(!copyPath(r))return fail(ZCD_PATH,i,1);
  const auto*q=r.PathCopy;
  const bool lu0=r.Report.PathBytes>=24&&q[0]==HARDWARE_DEVICE_PATH&&q[1]==HW_VENDOR_DP&&q[2]==20&&!q[3]&&
   !CompareMem(q+4,&ZcpExpectedUfsLu0Guid,16);
  if(lu0&&r.Report.PathBytes==24){++parents;report_.ParentIndex=i;}
  if(lu0&&r.Report.PathBytes==66&&q[20]==MEDIA_DEVICE_PATH&&q[21]==MEDIA_HARDDRIVE_DP&&q[22]==42&&!q[23]&&
     q[60]==MBR_TYPE_EFI_PARTITION_TABLE_HEADER&&q[61]==SIGNATURE_TYPE_GUID&&
     !CompareMem(q+44,&ZcpExpectedPartitionGuid,16)){++children;report_.ChildIndex=i;}
 }
 if(parents>1||children>1)return fail(ZCD_AMBIGUOUS);
 if(parents!=1||children!=1)return fail(ZCD_MISSING);
 if(report_.ParentIndex==report_.ChildIndex)return fail(ZCD_AMBIGUOUS);
 auto&child=rows_[report_.ChildIndex];auto&parent=rows_[report_.ParentIndex];VOID*p=nullptr;
 if(CompareMem(child.PathCopy,parent.PathCopy,sizeof(VENDOR_DEVICE_PATH)))return fail(ZCD_PATH);
 if(lookup(b,report_.ChildIndex,2,&p)!=ZCD_OK)return ZcdResult(report_.FirstError);
 child.Partition=static_cast<EFI_PARTITION_INFO_PROTOCOL*>(p);
 if(!external(p,sizeof(child.PartitionCopy))||UINTN(p)%alignof(EFI_PARTITION_INFO_PROTOCOL))return fail(ZCD_INTERFACE,report_.ChildIndex,2);
 CopyMem(&child.PartitionCopy,p,sizeof(child.PartitionCopy));
 if(lookup(b,report_.ChildIndex,3,&p)!=ZCD_OK)return ZcdResult(report_.FirstError);
 child.Disk=static_cast<EFI_DISK_IO_PROTOCOL*>(p);
 if(!external(p,sizeof(child.DiskCopy))||UINTN(p)%alignof(EFI_DISK_IO_PROTOCOL))return fail(ZCD_INTERFACE,report_.ChildIndex,3);
 CopyMem(&child.DiskCopy,p,sizeof(child.DiskCopy));
 if(!stable())return fail(ZCD_CHANGED);
 // Every status below came from this run's actual firmware lookup, not a
 // zero-filled fixture, recovery result, caller assertion or Linux device.
 candidate_.Block=child.Block;candidate_.ParentBlock=parent.Block;
 candidate_.Disk=child.Disk;candidate_.Partition=child.Partition;
 candidate_.Path=child.Path;candidate_.ParentPath=parent.Path;
 candidate_.PathBytes=child.Report.PathBytes;candidate_.ParentPathBytes=parent.Report.PathBytes;
 const EFI_STATUS s[]={child.Report.Status[0],child.Report.Status[3],child.Report.Status[2],child.Report.Status[1],parent.Report.Status[0],parent.Report.Status[1]};
 for(unsigned i=0;i<6;++i)candidate_.Lookup[i]=s[i];
 if(child.Report.Available!=15||parent.Report.Available!=3)return fail(ZCD_INTERFACE);
 candidate_.NativeAvailable=63;report_.DiscoveryComplete=1;report_.VerifierAttempted=1;
 const ZcrmResult v=reader_.validate(b,&candidate_,1,e,&lifetime_);report_.VerifierResult=v;
 if(v!=ZCRM_OK)return fail(ZCD_VERIFY);
 if(!stable())return fail(ZCD_CHANGED);
 report_.GptReadVerified=reader_.report().GptReadVerified;
 report_.State=2;busy_=false;return ZCD_OK;
}
ZcblResult ZornCheckpointDiscovery::retire()
{
 if(busy_||!report_.State||report_.RetireAttempted)return ZCBL_USED;
 busy_=true;report_.RetireAttempted=1;
 ZcblResult a=ZCBL_OK,b=ZCBL_OK;
 if(report_.VerifierAttempted){a=reader_.retire();report_.ReaderRetire=a;}
 if(lifetime_.report().state){b=lifetime_.close();report_.LifetimeRetire=b;}
 report_.State=4;busy_=false;return a!=ZCBL_OK?a:b;
}
