/* SPDX-License-Identifier: BSD-2-Clause-Patent
 * Native RPMh/Clock interface pattern from UniXNU-houji TouchHandoff.h.
 * K80 live DT: ldob14 = 3.2 V, ldob12 = 1.8 V. No direct PMIC writes.
 * The exact giulia provider binaries and method ABI are checked by the host.
 */
#include <Protocol/EFIClock.h>
typedef struct { UINT64 Version; VOID *Methods[24]; } ZT_RPMH;
typedef struct { UINT64 Version; VOID *Methods[8]; } ZT_CMDDB;
typedef EFI_STATUS (EFIAPI *ZT_QUERY)(ZT_CMDDB *, CONST CHAR8 *, UINT32 *);
typedef EFI_STATUS (EFIAPI *ZT_VALID)(UINT32, BOOLEAN *);
typedef EFI_STATUS (EFIAPI *ZT_CREATE)(UINT32, CONST CHAR8 *, VOID **);
typedef EFI_STATUS (EFIAPI *ZT_ISSUE)(VOID *, UINT32, BOOLEAN, UINT32, UINT32, UINT32 *);
typedef EFI_STATUS (EFIAPI *ZT_WAIT)(VOID *, UINT32);
STATIC EFI_GUID mZtRpmh = {0xe1d0b573,0xf29f,0x495d,{0x93,0x52,0xca,0x0d,0xd4,0x2a,0x0a,0x74}};
STATIC EFI_GUID mZtDb = {0x1c34f691,0xd33d,0x4e14,{0xb8,0xf8,0x32,0xc6,0xc0,0x29,0xe9,0x5b}};
STATIC VOID *mZtClient;
STATIC BOOLEAN mZtReady;

STATIC EFI_STATUS PrepareZornTouchPower (IN CONST UINT8 *Sector) {
  EFI_CLOCK_PROTOCOL *Clock = NULL;
  ZT_RPMH *Rpmh = NULL;
  ZT_CMDDB *Db = NULL;
  CONST CHAR8 *Names[3] = {"gcc_qupv3_wrap_1_m_ahb_clk", "gcc_qupv3_wrap_1_s_ahb_clk", "gcc_qupv3_wrap1_s4_clk"};
  CONST CHAR8 *Resources[2] = {"ldob14", "ldob12"};
  CONST UINT32 Millivolts[2] = {3200,1800};
  UINTN Ids[3] = {0};
  UINT32 Address[2] = {0}, Slave[2] = {0}, Hz = 0;
  BOOLEAN Valid = FALSE;
  EFI_STATUS Status;
  if (CompareMem (Sector + 0x190, "ZORNTPWR", 8) != 0) { return EFI_SUCCESS; }
  if (ReadUnaligned32 ((CONST UINT32 *)(Sector + 0x198)) != 1 ||
      ReadUnaligned32 ((CONST UINT32 *)(Sector + 0x19c)) != 0xfffffffe ||
      CompareMem (Sector + 0x180, "ZORNGHWD", 8) != 0 ||
      ReadUnaligned32 ((CONST UINT32 *)(Sector + 0x188)) != 1) { return EFI_COMPROMISED_DATA; }
  if (mZtReady) { return EFI_SUCCESS; }
  Status = gBS->LocateProtocol (&gEfiClockProtocolGuid,NULL,(VOID **)&Clock);
  if (EFI_ERROR(Status)) { return Status; }
  Status = gBS->LocateProtocol (&mZtRpmh,NULL,(VOID **)&Rpmh);
  if (EFI_ERROR(Status)) { return Status; }
  Status = gBS->LocateProtocol (&mZtDb,NULL,(VOID **)&Db);
  if (EFI_ERROR(Status)) { return Status; }
  if (!Clock || !Clock->GetClockID || !Clock->SetClockFreqHz || !Clock->EnableClock ||
      !Clock->IsClockOn || !Rpmh || !Db || Rpmh->Version != 0x10001 || Db->Version != 0x10000 ||
      !Rpmh->Methods[1] || !Rpmh->Methods[5] || !Rpmh->Methods[18] || !Rpmh->Methods[11] ||
      !Db->Methods[1] || !Db->Methods[7]) { return EFI_UNSUPPORTED; }
  // Resolve every resource before the first vote. Only these two live-DT rails.
  for (UINTN I=0; I<3; I++) {
    Status = Clock->GetClockID (Clock,Names[I],&Ids[I]);
    DEBUG ((DEBUG_ERROR,"ZORNTOUCH: clock %a lookup %r\n",Names[I],Status));
    if (EFI_ERROR(Status)) { return Status; }
  }
  for (UINTN I=0; I<2; I++) {
    Status = ((ZT_QUERY)Db->Methods[1])(Db,Resources[I],&Address[I]);
    if (!EFI_ERROR(Status)) { Status = ((ZT_QUERY)Db->Methods[7])(Db,Resources[I],&Slave[I]); }
    DEBUG ((DEBUG_ERROR,"ZORNTOUCH: %a address %x slave %u status %r\n",Resources[I],Address[I],Slave[I],Status));
    if (EFI_ERROR(Status) || Slave[I]!=4 || (Address[I]>>16)!=4 || (Address[I]&15) ||
        (I && Address[0]==Address[1])) { return EFI_UNSUPPORTED; }
  }
  Status = ((ZT_VALID)Rpmh->Methods[1])(2,&Valid);
  if (EFI_ERROR(Status) || !Valid) { return EFI_UNSUPPORTED; }
  Status = ((ZT_CREATE)Rpmh->Methods[5])(2,"zorn-touch-vdd",&mZtClient);
  if (EFI_ERROR(Status) || !mZtClient) { return EFI_NOT_READY; }
  for (UINTN I=0; I<2; I++) {
    CONST UINT32 Offsets[3] = {0,8,4};
    CONST UINT32 Values[3] = {Millivolts[I],7,1}; // pmic5-ldo HPM; voltage, mode, enable.
    for (UINTN J=0; J<3; J++) {
      UINT32 Request = 0;
      Status = ((ZT_ISSUE)Rpmh->Methods[18])(mZtClient,0,TRUE,Address[I]+Offsets[J],Values[J],&Request);
      if (!EFI_ERROR(Status) && Request) { Status = ((ZT_WAIT)Rpmh->Methods[11])(mZtClient,Request); }
      DEBUG ((DEBUG_ERROR,"ZORNTOUCH: %a+%u=%u result %r\n",Resources[I],Offsets[J],Values[J],Status));
      if (EFI_ERROR(Status)) { return Status; }
    }
  }
  Status = Clock->SetClockFreqHz (Clock,Ids[2],19200000,EFI_CLOCK_FREQUENCY_HZ_EXACT,&Hz);
  if (EFI_ERROR(Status) || Hz!=19200000) { return EFI_UNSUPPORTED; }
  for (UINTN I=0; I<3; I++) {
    BOOLEAN On = FALSE;
    Status = Clock->EnableClock (Clock,Ids[I]);
    if (!EFI_ERROR(Status)) { Status = Clock->IsClockOn (Clock,Ids[I],&On); }
    if (EFI_ERROR(Status) || !On) { return EFI_NOT_READY; }
  }
  mZtReady = TRUE;
  DEBUG ((DEBUG_ERROR,"ZORNTOUCH: L14=3200 L12=1800 clocks-on; native votes retained\n"));
  return EFI_SUCCESS;
}
