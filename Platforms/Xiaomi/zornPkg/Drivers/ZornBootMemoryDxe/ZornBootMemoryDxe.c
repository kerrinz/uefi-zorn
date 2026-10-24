/** @file
  Memory and RAM disk from the device tree the previous stage handed over.

  The previous stage (a Linux-style boot loader) passes the physical address
  of a flattened device tree in x0, which SEC keeps in a HOB. Its /memory
  nodes list the real DRAM and its /reserved-memory nodes list what the
  secure side owns. Without the vendor memory manager the firmware only knows
  the few regions of its own memory map, so:

  * DRAM that no firmware region claims and no reserved-memory node covers is
    added to the GCD as system memory, up to a fixed amount;
  * the initrd the loader placed in memory (/chosen linux,initrd-start/-end)
    is published as a read-only block device, so a FAT image in the boot
    image's ramdisk shows up as a normal volume.

  Nothing here depends on a hardware address; every range comes from the DT.
**/

#include <Uefi.h>
#include <Library/BaseLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/DebugLib.h>
#include <Library/DxeServicesTableLib.h>
#include <Library/FdtLib.h>
#include <Library/HobLib.h>
#include <Library/MemoryAllocationLib.h>
#include <Library/UefiBootServicesTableLib.h>
#include <Protocol/BlockIo.h>
#include <Protocol/DevicePath.h>
#include <Protocol/SimpleFileSystem.h>

#define MAX_RANGES        64
#define MIN_PIECE_SIZE    SIZE_16MB
#define ADD_LIMIT         SIZE_1GB
#define ADD_BELOW         SIZE_4GB     // stay inside what the MMU setup maps

typedef struct {
  UINT64  Base;
  UINT64  End;       // exclusive
} RANGE;

STATIC
UINT64
ReadCells (
  IN CONST VOID  *Data,
  IN UINT32      Cells
  )
{
  if (Cells == 2) {
    return Fdt64ToCpu (ReadUnaligned64 (Data));
  }

  return Fdt32ToCpu (ReadUnaligned32 (Data));
}

STATIC
UINT32
GetCells (
  IN CONST VOID  *Fdt,
  IN INT32       Node,
  IN CONST CHAR8 *Name,
  IN UINT32      Default
  )
{
  CONST VOID  *Prop;
  INT32       Length;

  Prop = FdtGetProp (Fdt, Node, Name, &Length);
  if ((Prop == NULL) || (Length != sizeof (UINT32))) {
    return Default;
  }

  return Fdt32ToCpu (ReadUnaligned32 (Prop));
}

STATIC
UINTN
CollectReg (
  IN     CONST VOID  *Fdt,
  IN     INT32       Node,
  IN     UINT32      AddressCells,
  IN     UINT32      SizeCells,
  IN OUT RANGE       *Ranges,
  IN     UINTN       Count
  )
{
  CONST UINT8  *Reg;
  INT32        Length;
  UINT32       Entry;
  INT32        Offset;
  UINT64       Base;
  UINT64       Size;

  Reg = FdtGetProp (Fdt, Node, "reg", &Length);
  if (Reg == NULL) {
    return Count;
  }

  Entry = (AddressCells + SizeCells) * sizeof (UINT32);
  for (Offset = 0; (Offset + (INT32)Entry <= Length) && (Count < MAX_RANGES); Offset += Entry) {
    Base = ReadCells (Reg + Offset, AddressCells);
    Size = ReadCells (Reg + Offset + AddressCells * sizeof (UINT32), SizeCells);
    if ((Size != 0) && (Base + Size > Base)) {
      Ranges[Count].Base = Base;
      Ranges[Count].End  = Base + Size;
      Count++;
    }
  }

  return Count;
}

/**
  Remove every part of Pieces[] that lies inside Cut.
**/
STATIC
UINTN
Subtract (
  IN OUT RANGE  *Pieces,
  IN     UINTN  Count,
  IN     RANGE  Cut
  )
{
  UINTN  Index;
  UINTN  Result;
  RANGE  Out[MAX_RANGES];

  Result = 0;
  for (Index = 0; Index < Count; Index++) {
    if ((Cut.End <= Pieces[Index].Base) || (Cut.Base >= Pieces[Index].End)) {
      if (Result < MAX_RANGES) {
        Out[Result++] = Pieces[Index];
      }

      continue;
    }

    if ((Cut.Base > Pieces[Index].Base) && (Result < MAX_RANGES)) {
      Out[Result].Base  = Pieces[Index].Base;
      Out[Result].End   = Cut.Base;
      Result++;
    }

    if ((Cut.End < Pieces[Index].End) && (Result < MAX_RANGES)) {
      Out[Result].Base  = Cut.End;
      Out[Result].End   = Pieces[Index].End;
      Result++;
    }
  }

  CopyMem (Pieces, Out, Result * sizeof (RANGE));
  return Result;
}

STATIC
VOID
AddMemory (
  IN CONST VOID  *Fdt
  )
{
  EFI_STATUS                       Status;
  EFI_GCD_MEMORY_SPACE_DESCRIPTOR  *Map;
  UINTN                            MapCount;
  INT32                            Root;
  INT32                            Node;
  INT32                            Reserved;
  INT32                            Length;
  CONST CHAR8                      *Type;
  UINT32                           AddressCells;
  UINT32                           SizeCells;
  RANGE                            Banks[MAX_RANGES];
  RANGE                            Holes[MAX_RANGES];
  RANGE                            Pieces[MAX_RANGES];
  UINTN                            BankCount;
  UINTN                            HoleCount;
  UINTN                            PieceCount;
  UINTN                            ReservedCount;
  RANGE                            ReservedRanges[MAX_RANGES];
  UINTN                            Index;
  UINTN                            Other;
  UINT64                           Added;
  UINT64                           Base;
  UINT64                           End;

  Root         = FdtPathOffset (Fdt, "/");
  AddressCells = GetCells (Fdt, Root, "#address-cells", 2);
  SizeCells    = GetCells (Fdt, Root, "#size-cells", 2);

  BankCount = 0;
  for (Node = FdtFirstSubnode (Fdt, Root); Node >= 0; Node = FdtNextSubnode (Fdt, Node)) {
    Type = FdtGetProp (Fdt, Node, "device_type", &Length);
    if ((Type != NULL) && (AsciiStrCmp (Type, "memory") == 0)) {
      BankCount = CollectReg (Fdt, Node, AddressCells, SizeCells, Banks, BankCount);
    }
  }

  ReservedCount = 0;
  Reserved      = FdtPathOffset (Fdt, "/reserved-memory");
  if (Reserved >= 0) {
    UINT32  ResAddress = GetCells (Fdt, Reserved, "#address-cells", AddressCells);
    UINT32  ResSize    = GetCells (Fdt, Reserved, "#size-cells", SizeCells);

    for (Node = FdtFirstSubnode (Fdt, Reserved); Node >= 0; Node = FdtNextSubnode (Fdt, Node)) {
      ReservedCount = CollectReg (Fdt, Node, ResAddress, ResSize, ReservedRanges, ReservedCount);
    }
  }

  DEBUG ((DEBUG_ERROR, "ZORNMEM: DT has %u memory ranges and %u reserved ranges\n", (UINT32)BankCount, (UINT32)ReservedCount));
  if (BankCount == 0) {
    return;
  }

  Status = gDS->GetMemorySpaceMap (&MapCount, &Map);
  if (EFI_ERROR (Status)) {
    return;
  }

  //
  // Holes: DRAM the GCD does not know yet.
  //
  HoleCount = 0;
  for (Index = 0; Index < BankCount; Index++) {
    for (Other = 0; Other < MapCount; Other++) {
      if (Map[Other].GcdMemoryType != EfiGcdMemoryTypeNonExistent) {
        continue;
      }

      Base = MAX (Banks[Index].Base, Map[Other].BaseAddress);
      End  = MIN (Banks[Index].End, Map[Other].BaseAddress + Map[Other].Length);
      if ((Base < End) && (HoleCount < MAX_RANGES)) {
        Holes[HoleCount].Base = Base;
        Holes[HoleCount].End  = End;
        HoleCount++;
      }
    }
  }

  FreePool (Map);

  //
  // Minus everything the DT reserves; what is left is added right away.
  //
  Added = 0;
  for (Index = 0; (Index < HoleCount) && (Added < ADD_LIMIT); Index++) {
    Pieces[0]  = Holes[Index];
    PieceCount = 1;
    for (Other = 0; Other < ReservedCount; Other++) {
      PieceCount = Subtract (Pieces, PieceCount, ReservedRanges[Other]);
    }

    for (Other = 0; (Other < PieceCount) && (Added < ADD_LIMIT); Other++) {
      Base = ALIGN_VALUE (Pieces[Other].Base, SIZE_2MB);
      End  = Pieces[Other].End & ~((UINT64)SIZE_2MB - 1);
      if ((End <= Base) || (End - Base < MIN_PIECE_SIZE) || (End > ADD_BELOW)) {
        continue;
      }

      End = MIN (End, Base + (ADD_LIMIT - Added));

      //
      // Add and map before anything can allocate from it.
      //
      Status = gDS->AddMemorySpace (
                      EfiGcdMemoryTypeSystemMemory,
                      Base,
                      End - Base,
                      EFI_MEMORY_UC | EFI_MEMORY_WC | EFI_MEMORY_WT | EFI_MEMORY_WB
                      );
      if (!EFI_ERROR (Status)) {
        Status = gDS->SetMemorySpaceAttributes (Base, End - Base, EFI_MEMORY_WB);
        if (EFI_ERROR (Status)) {
          gDS->RemoveMemorySpace (Base, End - Base);
        } else {
          Added += End - Base;
        }
      }

      DEBUG ((DEBUG_ERROR, "ZORNMEM: system memory 0x%lx-0x%lx %r\n", Base, End - 1, Status));
    }
  }

  DEBUG ((DEBUG_ERROR, "ZORNMEM: added 0x%lx bytes of system memory\n", Added));
}

#define RAM_BLOCK_SIZE  512

#pragma pack(1)
typedef struct {
  VENDOR_DEVICE_PATH          Vendor;
  EFI_DEVICE_PATH_PROTOCOL    End;
} RAM_BLOCK_DEVICE_PATH;
#pragma pack()

STATIC RAM_BLOCK_DEVICE_PATH  mDevicePath = {
  {
    { HARDWARE_DEVICE_PATH, HW_VENDOR_DP, { (UINT8)sizeof (VENDOR_DEVICE_PATH), (UINT8)(sizeof (VENDOR_DEVICE_PATH) >> 8) } },
    { 0x7C4E91A2, 0x6B10, 0x4D33, { 0x88, 0x5A, 0xC4, 0x65, 0x00, 0xF7, 0xD8, 0x36 } }
  },
  { END_DEVICE_PATH_TYPE, END_ENTIRE_DEVICE_PATH_SUBTYPE, { sizeof (EFI_DEVICE_PATH_PROTOCOL), 0 } }
};

STATIC UINT8                    *mRamBase;
STATIC EFI_BLOCK_IO_MEDIA       mMedia;

STATIC
EFI_STATUS
EFIAPI
RamBlockReset (
  IN EFI_BLOCK_IO_PROTOCOL  *This,
  IN BOOLEAN                ExtendedVerification
  )
{
  return EFI_SUCCESS;
}

STATIC
EFI_STATUS
EFIAPI
RamBlockRead (
  IN  EFI_BLOCK_IO_PROTOCOL  *This,
  IN  UINT32                 MediaId,
  IN  EFI_LBA                Lba,
  IN  UINTN                  BufferSize,
  OUT VOID                   *Buffer
  )
{
  if (Buffer == NULL) {
    return EFI_INVALID_PARAMETER;
  }

  if (MediaId != mMedia.MediaId) {
    return EFI_MEDIA_CHANGED;
  }

  if ((BufferSize % RAM_BLOCK_SIZE) != 0) {
    return EFI_BAD_BUFFER_SIZE;
  }

  if ((Lba > mMedia.LastBlock) || ((BufferSize / RAM_BLOCK_SIZE) > (mMedia.LastBlock + 1 - Lba))) {
    return EFI_INVALID_PARAMETER;
  }

  CopyMem (Buffer, mRamBase + Lba * RAM_BLOCK_SIZE, BufferSize);
  return EFI_SUCCESS;
}

STATIC
EFI_STATUS
EFIAPI
RamBlockWrite (
  IN EFI_BLOCK_IO_PROTOCOL  *This,
  IN UINT32                 MediaId,
  IN EFI_LBA                Lba,
  IN UINTN                  BufferSize,
  IN VOID                   *Buffer
  )
{
  return EFI_WRITE_PROTECTED;
}

STATIC
EFI_STATUS
EFIAPI
RamBlockFlush (
  IN EFI_BLOCK_IO_PROTOCOL  *This
  )
{
  return EFI_SUCCESS;
}

STATIC EFI_BLOCK_IO_PROTOCOL  mBlockIo = {
  EFI_BLOCK_IO_PROTOCOL_REVISION,
  &mMedia,
  RamBlockReset,
  RamBlockRead,
  RamBlockWrite,
  RamBlockFlush
};

//
// DiskIo, Partition and Fat are already loaded. Bind them now and say whether
// \EFI\UniXNU\unixnu.toml is visible, before later DXE dispatch moves on.
//
STATIC
VOID
ProbeConfig (
  IN EFI_HANDLE  Handle
  )
{
  EFI_STATUS                       Status;
  EFI_HANDLE                       *Handles;
  UINTN                            Count;
  UINTN                            Index;
  UINTN                            Found;
  EFI_SIMPLE_FILE_SYSTEM_PROTOCOL  *Fs;
  EFI_FILE_PROTOCOL                *Root;
  EFI_FILE_PROTOCOL                *File;

  Status = gBS->ConnectController (Handle, NULL, NULL, TRUE);
  DEBUG ((DEBUG_ERROR, "ZORNMEM: connect %r\n", Status));

  Found  = 0;
  Status = gBS->LocateHandleBuffer (ByProtocol, &gEfiSimpleFileSystemProtocolGuid, NULL, &Count, &Handles);
  if (EFI_ERROR (Status)) {
    DEBUG ((DEBUG_ERROR, "ZORNMEM: no filesystem protocol\n"));
    return;
  }

  for (Index = 0; Index < Count; Index++) {
    if (EFI_ERROR (gBS->HandleProtocol (Handles[Index], &gEfiSimpleFileSystemProtocolGuid, (VOID **)&Fs))) {
      continue;
    }

    if (EFI_ERROR (Fs->OpenVolume (Fs, &Root))) {
      continue;
    }

    Status = Root->Open (Root, &File, L"\\EFI\\UniXNU\\unixnu.toml", EFI_FILE_MODE_READ, 0);
    Root->Close (Root);
    if (!EFI_ERROR (Status)) {
      File->Close (File);
      Found++;
    }
  }

  DEBUG ((DEBUG_ERROR, "ZORNMEM: unixnu.toml on %u of %u filesystems\n", (UINT32)Found, (UINT32)Count));
  FreePool (Handles);
}

STATIC
BOOLEAN
IsZornEsp (
  IN CONST UINT8  *Sector
  )
{
  // FAT32 stores the label at +0x47. FAT12/FAT16 store it at +0x2B.
  return (CompareMem (Sector + 0x47, "ZORNESP    ", 11) == 0) ||
         (CompareMem (Sector + 0x2B, "ZORNESP    ", 11) == 0);
}

STATIC
EFI_STATUS
PublishRange (
  IN UINT64  Start,
  IN UINT64  End
  )
{
  EFI_STATUS            Status;
  EFI_HANDLE            Handle;
  UINT64                Bytes;
  UINTN                 Pages;
  EFI_PHYSICAL_ADDRESS  Copy;

  if ((End <= Start) || (((End - Start) % RAM_BLOCK_SIZE) != 0)) {
    return EFI_INVALID_PARAMETER;
  }

  //
  // ABL leaves this image in the kernel load window. Later DXE allocations
  // reuse that window. Copy it into pages this driver owns before publishing.
  //
  Bytes = End - Start;
  Pages = EFI_SIZE_TO_PAGES (Bytes);
  Status = gBS->AllocatePages (AllocateAnyPages, EfiBootServicesData, Pages, &Copy);
  if (!EFI_ERROR (Status)) {
    CopyMem ((VOID *)(UINTN)Copy, (VOID *)(UINTN)Start, Bytes);
    DEBUG ((DEBUG_ERROR, "ZORNMEM: copied payload to 0x%lx\n", Copy));
    Start = Copy;
    End   = Copy + Bytes;
  } else {
    DEBUG ((DEBUG_ERROR, "ZORNMEM: copy failed %r, publishing the original\n", Status));
  }

  mRamBase                = (UINT8 *)(UINTN)Start;
  mMedia.MediaId          = 1;
  mMedia.RemovableMedia   = FALSE;
  mMedia.MediaPresent     = TRUE;
  mMedia.LogicalPartition = FALSE;
  mMedia.ReadOnly         = TRUE;
  mMedia.WriteCaching     = FALSE;
  mMedia.BlockSize        = RAM_BLOCK_SIZE;
  mMedia.IoAlign          = 1;
  mMedia.LastBlock        = (End - Start) / RAM_BLOCK_SIZE - 1;

  Handle = NULL;
  Status = gBS->InstallMultipleProtocolInterfaces (
                  &Handle,
                  &gEfiDevicePathProtocolGuid,
                  &mDevicePath,
                  &gEfiBlockIoProtocolGuid,
                  &mBlockIo,
                  NULL
                  );
  if (EFI_ERROR (Status)) {
    mRamBase = NULL;
  } else {
    ProbeConfig (Handle);
  }

  DEBUG ((DEBUG_ERROR, "ZORNMEM: ramdisk 0x%lx size 0x%lx %r\n", Start, End - Start, Status));
  return Status;
}

STATIC
EFI_STATUS
PublishInitrd (
  IN CONST VOID  *Fdt
  )
{
  INT32       Chosen;
  CONST VOID  *StartProp;
  CONST VOID  *EndProp;
  INT32       StartLength;
  INT32       EndLength;
  UINT64      Start;
  UINT64      End;

  Chosen = FdtPathOffset (Fdt, "/chosen");
  if (Chosen < 0) {
    DEBUG ((DEBUG_ERROR, "ZORNMEM: no /chosen\n"));
    return EFI_NOT_FOUND;
  }

  StartProp = FdtGetProp (Fdt, Chosen, "linux,initrd-start", &StartLength);
  EndProp   = FdtGetProp (Fdt, Chosen, "linux,initrd-end", &EndLength);
  if ((StartProp == NULL) || (EndProp == NULL) ||
      ((StartLength != 4) && (StartLength != 8)) || ((EndLength != 4) && (EndLength != 8)))
  {
    DEBUG ((DEBUG_ERROR, "ZORNMEM: no initrd in /chosen\n"));
    return EFI_NOT_FOUND;
  }

  Start = ReadCells (StartProp, StartLength / 4);
  End   = ReadCells (EndProp, EndLength / 4);
  return PublishRange (Start, End);
}

STATIC
EFI_STATUS
TrySector (
  IN UINT64  Address
  )
{
  UINT8   *Sector;
  UINT16  BytesPerSector;
  UINT32  TotalSectors;
  UINT64  Bytes;

  Sector = (UINT8 *)(UINTN)Address;
  if ((Sector[0] != 0xEB) || !IsZornEsp (Sector)) {
    return EFI_NOT_FOUND;
  }

  BytesPerSector = ReadUnaligned16 ((UINT16 *)(Sector + 0x0B));
  TotalSectors   = ReadUnaligned16 ((UINT16 *)(Sector + 0x13));
  if (TotalSectors == 0) {
    TotalSectors = ReadUnaligned32 ((UINT32 *)(Sector + 0x20));
  }

  // 0x80000 sectors is 256 MiB. The kernel window ends at 0xB8000000.
  if ((BytesPerSector != RAM_BLOCK_SIZE) || (TotalSectors == 0) || (TotalSectors > 0x80000)) {
    return EFI_NOT_FOUND;
  }

  Bytes = (UINT64)TotalSectors * BytesPerSector;
  DEBUG ((DEBUG_ERROR, "ZORNMEM: found ZORNESP at 0x%lx\n", Address));
  return PublishRange (Address, Address + Bytes);
}

/**
  ABL on this phone loads the boot-image ramdisk, but the DTB pointer saved
  from x0 is not always still a device tree by the time DXE runs. The payload
  FAT volume is labeled ZORNESP. Walk the firmware memory map for that label.
**/
STATIC
EFI_STATUS
ScanPayload (
  VOID
  )
{
  EFI_STATUS             Status;
  UINTN                  Size;
  UINTN                  MapKey;
  UINTN                  DescSize;
  UINT32                 DescVersion;
  EFI_MEMORY_DESCRIPTOR  *Map;
  EFI_MEMORY_DESCRIPTOR  *End;
  EFI_MEMORY_DESCRIPTOR  *Desc;
  UINT64                 Address;
  UINT64                 Limit;

  Size   = 0;
  Status = gBS->GetMemoryMap (&Size, NULL, &MapKey, &DescSize, &DescVersion);
  if (Status != EFI_BUFFER_TOO_SMALL) {
    return Status;
  }

  Size += SIZE_1KB;
  Map   = AllocatePool (Size);
  if (Map == NULL) {
    return EFI_OUT_OF_RESOURCES;
  }

  Status = gBS->GetMemoryMap (&Size, Map, &MapKey, &DescSize, &DescVersion);
  if (EFI_ERROR (Status)) {
    FreePool (Map);
    return Status;
  }

  End = (EFI_MEMORY_DESCRIPTOR *)((UINT8 *)Map + Size);
  for (Desc = Map; Desc < End; Desc = (EFI_MEMORY_DESCRIPTOR *)((UINT8 *)Desc + DescSize)) {
    // Reserved ranges include TZ and device windows. Reading those raises a
    // synchronous abort and ArmCpuDxe asserts in CpuExceptionHandlerLib.c.
    // Only cacheable DRAM is probed. The boot ramdisk sits in that DRAM.
    if ((Desc->Attribute & EFI_MEMORY_WB) == 0) {
      continue;
    }

    if ((Desc->PhysicalStart < 0x80000000) || (Desc->PhysicalStart >= 0x100000000ULL)) {
      continue;
    }

    Address = Desc->PhysicalStart;
    Limit   = Desc->PhysicalStart + Desc->NumberOfPages * EFI_PAGE_SIZE;
    if (Limit > 0x100000000ULL) {
      Limit = 0x100000000ULL;
    }

    // The kernel window is where ABL decompresses this image. Step 512 bytes
    // there: the FAT boot sector is only 16-byte aligned after BootShim.
    // Everywhere else stay on 4 KiB so device-sized ranges are not walked.
    if ((Address < 0xB8000000ULL) && (Limit > 0xA8000000ULL)) {
      UINT64  WindowBase;
      UINT64  WindowLimit;

      WindowBase  = MAX (Address, 0xA8000000ULL);
      WindowLimit = MIN (Limit, 0xB8000000ULL);
      WindowBase  = ALIGN_VALUE (WindowBase, RAM_BLOCK_SIZE);
      for ( ; WindowBase + RAM_BLOCK_SIZE <= WindowLimit; WindowBase += RAM_BLOCK_SIZE) {
        if (!EFI_ERROR (TrySector (WindowBase))) {
          FreePool (Map);
          return EFI_SUCCESS;
        }
      }
    }

    Address = ALIGN_VALUE (Address, SIZE_4KB);
    for ( ; Address + SIZE_4KB <= Limit; Address += SIZE_4KB) {
      if (!EFI_ERROR (TrySector (Address))) {
        FreePool (Map);
        return EFI_SUCCESS;
      }
    }
  }

  FreePool (Map);
  DEBUG ((DEBUG_ERROR, "ZORNMEM: ZORNESP not in the memory map\n"));
  return EFI_NOT_FOUND;
}

#define ZORN_PAYLOAD_MAILBOX  0xA7601000ULL
#define ZORN_PAYLOAD_MAGIC    0x31444C504E524F5AULL

STATIC
EFI_STATUS
PublishMailbox (
  VOID
  )
{
  UINT64  Magic;
  UINT64  Address;
  UINT64  Size;

  Magic   = ReadUnaligned64 ((UINT64 *)(UINTN)ZORN_PAYLOAD_MAILBOX);
  Address = ReadUnaligned64 ((UINT64 *)(UINTN)(ZORN_PAYLOAD_MAILBOX + 8));
  Size    = ReadUnaligned64 ((UINT64 *)(UINTN)(ZORN_PAYLOAD_MAILBOX + 16));
  if (Magic != ZORN_PAYLOAD_MAGIC) {
    DEBUG ((DEBUG_ERROR, "ZORNMEM: no payload mailbox magic 0x%lx\n", Magic));
    return EFI_NOT_FOUND;
  }

  if ((Size == 0) || (Size > SIZE_64MB) || ((Size % RAM_BLOCK_SIZE) != 0) || (Address < 0x80000000ULL)) {
    DEBUG ((DEBUG_ERROR, "ZORNMEM: mailbox address 0x%lx size 0x%lx rejected\n", Address, Size));
    return EFI_NOT_FOUND;
  }

  if (!IsZornEsp ((UINT8 *)(UINTN)Address)) {
    DEBUG ((DEBUG_ERROR, "ZORNMEM: mailbox 0x%lx is not ZORNESP\n", Address));
    return EFI_NOT_FOUND;
  }

  DEBUG ((DEBUG_ERROR, "ZORNMEM: mailbox payload at 0x%lx\n", Address));
  return PublishRange (Address, Address + Size);
}

EFI_STATUS
EFIAPI
ZornBootMemoryDxeEntry (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  )
{
  EFI_HOB_GUID_TYPE  *Hob;
  UINT64             Dtb;

  if (!EFI_ERROR (PublishMailbox ())) {
    return EFI_SUCCESS;
  }

  Hob = GetFirstGuidHob (&gZornEntryArgHobGuid);
  if (Hob == NULL) {
    DEBUG ((DEBUG_ERROR, "ZORNMEM: no entry argument HOB\n"));
  } else {
    Dtb = *(UINT64 *)GET_GUID_HOB_DATA (Hob);
    if ((Dtb == 0) || ((Dtb & 3) != 0) || (FdtCheckHeader ((VOID *)(UINTN)Dtb) != 0)) {
      DEBUG ((DEBUG_ERROR, "ZORNMEM: x0 0x%lx is not a device tree\n", Dtb));
    } else {
      DEBUG ((DEBUG_ERROR, "ZORNMEM: device tree at 0x%lx, %u bytes\n", Dtb, (UINT32)FdtTotalSize ((VOID *)(UINTN)Dtb)));
      AddMemory ((VOID *)(UINTN)Dtb);
      PublishInitrd ((VOID *)(UINTN)Dtb);
    }
  }

  if (mRamBase == NULL) {
    DEBUG ((DEBUG_ERROR, "ZORNMEM: scanning cacheable DRAM for ZORNESP\n"));
    ScanPayload ();
  }

  return EFI_SUCCESS;
}
