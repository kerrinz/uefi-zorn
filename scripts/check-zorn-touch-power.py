#!/usr/bin/env python3
"""Pin native provider ABI and exercise the real handoff header with mocks."""
import hashlib,json,struct,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HEADER=ROOT/'uefi-zorn/Platforms/Xiaomi/zornPkg/Drivers/ZornBootMemoryDxe/ZornTouchPower.h'
BLOBS=ROOT.parent/'Mu-Silicium/Binaries/giulia/QcomPkg/Drivers'
PINS={'RpmhDxe':'cdebce5c9f96d16e71a0db8f9c4dbf591ed314dd94a6543b08c238902df65267',
      'CmdDbDxe':'5c58d445f356af9f8497ea6f449ba534fd7920b045067cd3b02ad997863077bf',
      'ClockDxe':'b1608ab9a4759dbbc50e5e5836ee402ff832d8076011e5145460e4af97ba7686'}
inputs={}
for name,sha in PINS.items():
    path=(BLOBS/name/(name+'.efi')).resolve(); data=path.read_bytes()
    assert hashlib.sha256(data).hexdigest()==sha,'native provider changed: '+name
    inputs[str(path)]=sha
    if name=='RpmhDxe':
        assert struct.unpack_from('<25Q',data,0xe108)==(0x10001,0x16e8,0x1700,0x173c,0x1778,0x17bc,0x1800,0x1844,0x185c,0x1874,0x188c,0x18c8,0x18e0,0x18f8,0x1910,0x1928,0x196c,0x1984,0x199c,0x19a4,0x19e0,0x19f8,0x14dc,0x1a10,0x1a18)
    if name=='CmdDbDxe':
        assert struct.unpack_from('<9Q',data,0x6098)==(0x10000,0x1438,0x148c,0x14d4,0x151c,0x1568,0x15b0,0x15f8,0x1650)
stub=r'''
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <assert.h>
#define STATIC static
#define IN
#define CONST const
#define EFIAPI
#define VOID void
#define TRUE true
#define FALSE false
#define DEBUG(x) do {} while(0)
#define EFI_SUCCESS 0
#define EFI_UNSUPPORTED 3
#define EFI_NOT_READY 6
#define EFI_COMPROMISED_DATA 33
#define EFI_ERROR(x) ((x)!=0)
#define EFI_CLOCK_FREQUENCY_HZ_EXACT 3
typedef uint64_t UINT64;typedef uint32_t UINT32;typedef uint8_t UINT8;typedef size_t UINTN;
typedef char CHAR8;typedef bool BOOLEAN;typedef uint64_t EFI_STATUS;
typedef struct {uint32_t a;uint16_t b,c;uint8_t d[8];} EFI_GUID;
typedef struct EFI_CLOCK_PROTOCOL EFI_CLOCK_PROTOCOL;
struct EFI_CLOCK_PROTOCOL {UINT64 Version;
EFI_STATUS (*GetClockID)(EFI_CLOCK_PROTOCOL*,const char*,UINTN*);
EFI_STATUS (*SetClockFreqHz)(EFI_CLOCK_PROTOCOL*,UINTN,UINT32,unsigned,UINT32*);
EFI_STATUS (*EnableClock)(EFI_CLOCK_PROTOCOL*,UINTN);
EFI_STATUS (*IsClockOn)(EFI_CLOCK_PROTOCOL*,UINTN,bool*);};
static EFI_GUID gEfiClockProtocolGuid={1,0,0,{0}};
struct BootServices {EFI_STATUS(*LocateProtocol)(EFI_GUID*,void*,void**);};
static BootServices *gBS;
static int CompareMem(const void*a,const void*b,size_t n){return memcmp(a,b,n);}
static uint32_t ReadUnaligned32(const uint32_t*p){uint32_t x;memcpy(&x,p,4);return x;}
'''
tests=r'''
static int calls,failAt,votes,lookups;static bool badRail;
static int step(){return ++calls==failAt?7:0;}
static EFI_CLOCK_PROTOCOL clk;
static ZT_RPMH rpm;static ZT_CMDDB db;
static EFI_STATUS locate(EFI_GUID*g,void*,void**p){int e=step();if(e)return e;*p=g==&mZtRpmh?(void*)&rpm:g==&mZtDb?(void*)&db:(void*)&clk;return 0;}
static EFI_STATUS id(EFI_CLOCK_PROTOCOL*,const char*n,UINTN*p){assert(strstr(n,"gcc_qupv3_wrap"));*p=++lookups;return step();}
static EFI_STATUS freq(EFI_CLOCK_PROTOCOL*,UINTN id,UINT32 hz,unsigned mode,UINT32*out){assert(id==3&&hz==19200000&&mode==3);*out=hz;return step();}
static EFI_STATUS enable(EFI_CLOCK_PROTOCOL*,UINTN id){assert(id>=1&&id<=3);return step();}
static EFI_STATUS on(EFI_CLOCK_PROTOCOL*,UINTN id,bool*p){assert(id>=1&&id<=3);*p=true;return step();}
static EFI_STATUS addr(ZT_CMDDB*,const char*n,UINT32*p){assert(!strcmp(n,"ldob14")||!strcmp(n,"ldob12"));*p=!strcmp(n,"ldob14")?0x400d0:0x400b0;return step();}
static EFI_STATUS slave(ZT_CMDDB*,const char*,UINT32*p){*p=badRail?3:4;return step();}
static EFI_STATUS valid(UINT32 id,bool*p){assert(id==2);*p=true;return step();}
static EFI_STATUS create(UINT32 id,const char*n,void**p){assert(id==2&&!strcmp(n,"zorn-touch-vdd"));*p=&rpm;return step();}
static EFI_STATUS issue(void*p,UINT32 set,bool completion,UINT32 a,UINT32 v,UINT32*r){
static const UINT32 aa[]={0x400d0,0x400d8,0x400d4,0x400b0,0x400b8,0x400b4};
static const UINT32 vv[]={3200,7,1,1800,7,1};
assert(p==&rpm&&set==0&&completion&&votes<6&&a==aa[votes]&&v==vv[votes]);++votes;*r=votes;return step();}
static EFI_STATUS wait(void*p,UINT32 req){assert(p==&rpm&&req>=1&&req<=6);return step();}
static void reset(){calls=votes=lookups=failAt=0;badRail=false;mZtReady=false;mZtClient=nullptr;
rpm={};rpm.Version=0x10001;rpm.Methods[1]=(void*)valid;rpm.Methods[5]=(void*)create;rpm.Methods[18]=(void*)issue;rpm.Methods[11]=(void*)wait;
db={};db.Version=0x10000;db.Methods[1]=(void*)addr;db.Methods[7]=(void*)slave;
clk={0,id,freq,enable,on};static BootServices bs={locate};gBS=&bs;}
int main(){UINT8 b[512]={};reset();assert(PrepareZornTouchPower(b)==0&&calls==0);
memcpy(b+0x190,"ZORNTPWR",8);assert(PrepareZornTouchPower(b)!=0&&calls==0);
UINT32 v=1,inv=~v;memcpy(b+0x198,&v,4);memcpy(b+0x19c,&inv,4);memcpy(b+0x180,"ZORNGHWD",8);memcpy(b+0x188,&v,4);
reset();assert(PrepareZornTouchPower(b)==0&&votes==6&&mZtReady);int total=calls;assert(PrepareZornTouchPower(b)==0&&calls==total);
for(int i=1;i<=total;i++){reset();failAt=i;assert(PrepareZornTouchPower(b)!=0&&calls==i&&!mZtReady);}
reset();badRail=true;assert(PrepareZornTouchPower(b)!=0&&votes==0);
reset();rpm.Version++;assert(PrepareZornTouchPower(b)!=0&&votes==0);
reset();db.Methods[7]=nullptr;assert(PrepareZornTouchPower(b)!=0&&votes==0);
}
'''
with tempfile.TemporaryDirectory(prefix='zorn-touch-power-') as td:
    p=Path(td);(p/'Protocol').mkdir();(p/'Protocol/EFIClock.h').write_text('// host mock uses just the called members\n')
    (p/'test.cpp').write_text(stub+'\n#include "'+str(HEADER)+'"\n'+tests)
    subprocess.run(['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I',str(p),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
report={'provider_sha256':inputs,'header_sha256':hashlib.sha256(HEADER.read_bytes()).hexdigest(),
 'rpmh_method_indices':[1,5,11,18],'cmddb_method_indices':[1,7],'rails':{'ldob14':3200,'ldob12':1800},
 'host_tests':'real header; no marker, bad marker, exact votes, idempotence, every call failure, invalid rail/version/method',
 'hardware_qualified':False}
out=ROOT/'out/zorn/touch/power-host-check.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
