/* SPDX-License-Identifier: BSD-2-Clause-Patent */
/* HOST ONLY. Actual archived GPT bytes with synthetic UEFI interfaces/events.
 * No hardware, firmware service, media write or ownership evidence. */
#include "ZornCheckpointDiscovery.h"
#include "ZornCheckpointUfsPathPins.h"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iterator>
#include <memory>
#include <vector>
#include <zlib.h>
extern "C" INTN EFIAPI CompareMem(CONST VOID*a,CONST VOID*b,UINTN n){return memcmp(a,b,n);}
extern "C" VOID* EFIAPI CopyMem(VOID*d,CONST VOID*s,UINTN n){return memcpy(d,s,n);}
static std::vector<UINT8> primary,backup,p0,b0;
static EFI_BLOCK_IO_MEDIA media,whole;
static EFI_BLOCK_IO_PROTOCOL child,parent;
static EFI_DISK_IO_PROTOCOL disk;
static EFI_PARTITION_INFO_PROTOCOL part;
static UINT8 path[66],parentPath[24];
static EFI_BOOT_SERVICES bs;
static EFI_EVENT_NOTIFY notify[4];static VOID* cookies[4];
static unsigned calls,creates,closes,reads,crcs,writes;
static int failRead=-1,expireRead=-1;static EFI_STATUS failStatus;
static EFI_GUID blockGuid=EFI_BLOCK_IO_PROTOCOL_GUID,pathGuid=EFI_DEVICE_PATH_PROTOCOL_GUID;
static EFI_GUID partGuid=EFI_PARTITION_INFO_PROTOCOL_GUID;
static EFI_GUID diskGuid=EFI_DISK_IO_PROTOCOL_GUID;
static EFI_STATUS EFIAPI deniedBlock(EFI_BLOCK_IO_PROTOCOL*,UINT32,EFI_LBA,UINTN,VOID*){++writes;assert(false);return EFI_DEVICE_ERROR;}
static EFI_STATUS EFIAPI deniedDisk(EFI_DISK_IO_PROTOCOL*,UINT32,UINT64,UINTN,VOID*){++writes;assert(false);return EFI_DEVICE_ERROR;}
static EFI_STATUS EFIAPI readBlock(EFI_BLOCK_IO_PROTOCOL*b,UINT32 mid,EFI_LBA lba,UINTN n,VOID*out){
 ++calls;unsigned i=reads++;assert(b==&parent&&mid==whole.MediaId&&n&&n%4096==0&&UINTN(out)%4096==0);
 const UINT8*data=nullptr;
 if(lba==1){assert(n==4096);data=primary.data()+4096;}
 if(lba==2){assert(n==8192);data=primary.data()+8192;}
 if(lba==ZcpExpectedDiskLastBlock){assert(n==4096);data=backup.data()+16384;}
 if(lba==ZcpExpectedDiskLastBlock-4){assert(n==8192);data=backup.data();}
 assert(data);memcpy(out,data,n);
 if(int(i)==expireRead)notify[0]((EFI_EVENT)UINTN(0x1000),cookies[0]);
 return int(i)==failRead?failStatus:EFI_SUCCESS;
}
static EFI_STATUS EFIAPI crc(VOID*p,UINTN n,UINT32*out){++calls;++crcs;*out=UINT32(crc32(0,(const Bytef*)p,uInt(n)));return EFI_SUCCESS;}
static EFI_STATUS EFIAPI create(UINT32 t,EFI_TPL tpl,EFI_EVENT_NOTIFY f,CONST VOID*c,CONST EFI_GUID*g,EFI_EVENT*out){
 ++calls;assert(creates<4&&t==EVT_NOTIFY_SIGNAL&&tpl==TPL_NOTIFY&&f&&c&&g);
 notify[creates]=f;cookies[creates]=const_cast<VOID*>(c);*out=(EFI_EVENT)UINTN(0x1000+creates++);return EFI_SUCCESS;
}
static EFI_STATUS EFIAPI closeEvent(EFI_EVENT e){++calls;++closes;assert(UINTN(e)>=0x1000&&UINTN(e)<0x1000+creates);return EFI_SUCCESS;}
static EFI_STATUS EFIAPI locate(EFI_LOCATE_SEARCH_TYPE t,EFI_GUID*g,VOID*k,UINTN*n,EFI_HANDLE*out){
 ++calls;assert(t==ByProtocol&&!k&&!memcmp(g,&blockGuid,16)&&*n==4096);
 out[0]=(EFI_HANDLE)UINTN(1);out[1]=(EFI_HANDLE)UINTN(2);*n=2*sizeof(EFI_HANDLE);return EFI_SUCCESS;
}
static EFI_STATUS EFIAPI handle(EFI_HANDLE h,EFI_GUID*g,VOID**out){
 ++calls;assert(!*out);
 if(h==(EFI_HANDLE)UINTN(1)){
  if(!memcmp(g,&blockGuid,16))*out=&parent;
  if(!memcmp(g,&pathGuid,16))*out=parentPath;
 }else if(h==(EFI_HANDLE)UINTN(2)){
  if(!memcmp(g,&blockGuid,16))*out=&child;
  if(!memcmp(g,&pathGuid,16))*out=path;
  if(!memcmp(g,&partGuid,16))*out=&part;
  if(!memcmp(g,&diskGuid,16))*out=&disk;
 }
 assert(*out);return EFI_SUCCESS;
}
static void put32(UINT8*p,UINT32 v){memcpy(p,&v,4);}
static void put64(UINT8*p,UINT64 v){memcpy(p,&v,8);}
static ZCP_CANDIDATE setup(){
 primary=p0;backup=b0;calls=creates=closes=reads=crcs=writes=0;failRead=expireRead=-1;failStatus=0;
 memset(&media,0,sizeof(media));memset(&whole,0,sizeof(whole));memset(&child,0,sizeof(child));memset(&parent,0,sizeof(parent));memset(&disk,0,sizeof(disk));memset(&part,0,sizeof(part));memset(path,0,sizeof(path));memset(parentPath,0,sizeof(parentPath));memset(&bs,0,sizeof(bs));
 media.MediaId=0x12345678;whole.MediaId=0xfedcba98;media.MediaPresent=whole.MediaPresent=TRUE;
 media.LogicalPartition=TRUE;media.BlockSize=whole.BlockSize=4096;
 media.LastBlock=ZCP_PARTITION_LAST-ZCP_PARTITION_FIRST;whole.LastBlock=ZcpExpectedDiskLastBlock;whole.IoAlign=4096;
 child.Revision=parent.Revision=EFI_BLOCK_IO_PROTOCOL_REVISION;child.Media=&media;parent.Media=&whole;
 child.ReadBlocks=child.WriteBlocks=deniedBlock;parent.ReadBlocks=readBlock;parent.WriteBlocks=deniedBlock;
 disk.Revision=EFI_DISK_IO_PROTOCOL_REVISION;disk.ReadDisk=disk.WriteDisk=deniedDisk;
 part.Revision=EFI_PARTITION_INFO_PROTOCOL_REVISION;part.Type=PARTITION_TYPE_GPT;
 memcpy(&part.Info.Gpt,primary.data()+8192+34*128,128);
 path[0]=HARDWARE_DEVICE_PATH;path[1]=HW_VENDOR_DP;path[2]=20;memcpy(path+4,&ZcpExpectedUfsLu0Guid,16);
 path[20]=MEDIA_DEVICE_PATH;path[21]=MEDIA_HARDDRIVE_DP;path[22]=42;
 put32(path+24,35);put64(path+28,part.Info.Gpt.StartingLBA);put64(path+36,part.Info.Gpt.EndingLBA-part.Info.Gpt.StartingLBA+1);
 memcpy(path+44,&part.Info.Gpt.UniquePartitionGUID,16);path[60]=2;path[61]=2;path[62]=0x7f;path[63]=0xff;path[64]=4;
 memcpy(parentPath,path,20);parentPath[20]=0x7f;parentPath[21]=0xff;parentPath[22]=4;
 bs.Hdr.Signature=EFI_BOOT_SERVICES_SIGNATURE;bs.Hdr.HeaderSize=sizeof(bs);
 bs.CreateEventEx=create;bs.CloseEvent=closeEvent;bs.CalculateCrc32=crc;bs.LocateHandle=locate;bs.HandleProtocol=handle;
 ZCP_CANDIDATE c{};c.Block=&child;c.ParentBlock=&parent;c.Disk=&disk;c.Partition=&part;c.Path=(EFI_DEVICE_PATH_PROTOCOL*)path;c.ParentPath=(EFI_DEVICE_PATH_PROTOCOL*)parentPath;c.PathBytes=66;c.ParentPathBytes=24;c.NativeAvailable=63;return c;
}
static void descriptorReject(const ZCP_CANDIDATE&c){ZCP_REPORT r{};assert(ZcpSelect(&c,1,99,1,&r)!=0&&!r.WriteAuthorized&&!calls);}
static std::vector<UINT8> load(const char*p){std::ifstream f(p,std::ios::binary);assert(f);return std::vector<UINT8>((std::istreambuf_iterator<char>(f)),{});}
static void repairGpt(){
 memcpy(backup.data(),primary.data()+8192,16384);
 for(auto pair:{std::make_pair(primary.data()+4096,primary.data()+8192),std::make_pair(backup.data()+16384,backup.data())}){
  auto*h=(EFI_PARTITION_TABLE_HEADER*)pair.first;assert(h->NumberOfPartitionEntries==64&&h->SizeOfPartitionEntry==128);h->PartitionEntryArrayCRC32=UINT32(crc32(0,pair.second,8192));h->Header.CRC32=0;h->Header.CRC32=UINT32(crc32(0,pair.first,92));
 }
}
int main(int argc,char**argv){
 assert(argc==3);p0=load(argv[1]);b0=load(argv[2]);assert(p0.size()==24576&&b0.size()==20480);
 unsigned refusals=0;
 auto c=setup();ZCP_REPORT r{};assert(!ZcpSelect(&c,1,99,1,&r)&&r.DescriptorEligible&&!r.WriteAuthorized&&!r.LiveDiscoveryVerified&&!r.GptReadVerified&&!calls);
 assert(r.RelativeLba==2291712&&r.AbsoluteLba==49563392&&r.PartitionFirst==47271680&&r.PartitionLast==64048895&&r.MediaId!=r.ParentMediaId);
 for(unsigned byte=0;byte<16;++byte){c=setup();((UINT8*)&part.Info.Gpt.UniquePartitionGUID)[byte]^=1;descriptorReject(c);++refusals;c=setup();((UINT8*)&part.Info.Gpt.PartitionTypeGUID)[byte]^=1;descriptorReject(c);++refusals;}
 for(unsigned which=0;which<11;++which){c=setup();switch(which){
  case 0:put32(path+24,34);break;case 1:put32(path+24,36);break;
  case 2:part.Info.Gpt.Attributes=1;break;case 3:++part.Info.Gpt.StartingLBA;break;
  case 4:--part.Info.Gpt.EndingLBA;break;case 5:++whole.LastBlock;break;
  case 6:part.Info.Gpt.PartitionName[6]='x';break;case 7:part.Info.Gpt.PartitionName[0]='U';break;
  case 8:memcpy(&part.Info.Gpt,primary.data()+8192+33*128,128);put32(path+24,34);break;
  case 9:path[44]^=1;break;case 10:media.BlockSize=512;break;
 }descriptorReject(c);++refusals;}
 c=setup();auto owner=std::make_unique<ZornCheckpointDiscovery>();assert(owner->run(&bs,99)==ZCD_DISABLED&&!calls&&!owner->report().State);
 assert(owner->run(&bs,99,true)==ZCD_OK);auto q=owner->report();auto rr=owner->readerReport();
 assert(q.DiscoveryComplete&&q.GptReadVerified&&!q.WriteAuthorized&&!q.RuntimeComplete&&!q.LiveDiscoveryVerified&&rr.PartitionOrdinal==35&&rr.Attempted==255&&rr.Returned==255&&reads==4&&crcs==4&&!writes);
 assert(owner->retire()==ZCBL_OK&&closes==4);assert(owner->run(&bs,99,true)==ZCD_USED);
 for(int which=0;which<6;++which){c=setup();auto*e=(EFI_PARTITION_ENTRY*)(primary.data()+8192+34*128);
  if(which==0){memcpy(primary.data()+8192+35*128,e,128);memset(e,0,128);}
  if(which==1)memcpy(primary.data()+8192+35*128,e,128);
  if(which==2)e->Attributes=1;
  if(which==3)e->UniquePartitionGUID.Data4[7]^=1;
  if(which==4)e->PartitionTypeGUID.Data4[7]^=1;
  if(which==5)e->PartitionName[6]='x';
  repairGpt();owner=std::make_unique<ZornCheckpointDiscovery>();assert(owner->run(&bs,99,true)!=ZCD_OK&&!owner->report().GptReadVerified&&!owner->report().WriteAuthorized&&!writes);++refusals;
 }
 for(int i=0;i<4;++i)for(EFI_STATUS s:{EFI_STATUS(7),EFI_STATUS(0x8000fedcba987654ULL)}){
  c=setup();failRead=i;failStatus=s;owner=std::make_unique<ZornCheckpointDiscovery>();assert(owner->run(&bs,99,true)==ZCD_VERIFY);
  rr=owner->readerReport();assert(rr.FirstOperation==unsigned(i)&&rr.NativeStatus[i]==s&&!rr.GptReadVerified&&!rr.WriteAuthorized&&reads==unsigned(i+1));++refusals;
 }
 c=setup();expireRead=0;owner=std::make_unique<ZornCheckpointDiscovery>();assert(owner->run(&bs,99,true)==ZCD_VERIFY&&!owner->report().GptReadVerified&&reads==1);++refusals;
 printf("{\"new_profile_refusals\":%u,\"default_off_native_calls\":0,\"host_GPT_reads\":4,\"host_CRCs\":4,\"media_writes\":0,\"native_device_calls\":0}\n",refusals);
}
