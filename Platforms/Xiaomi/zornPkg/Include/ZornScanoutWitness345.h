/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#ifndef ZORN_SCANOUT_WITNESS_345_H
#define ZORN_SCANOUT_WITNESS_345_H

#include <PiDxe.h>
#include <Library/DxeServicesTableLib.h>
#include "ZornScanoutHandoff345.h"

STATIC enum ZornScanoutFirmwareStatus
ZornVerifyScanoutMap (
  CONST EFI_MEMORY_DESCRIPTOR *Map,
  UINTN Size,
  UINTN Stride,
  UINT32 Version
  )
{
  BOOLEAN Covered = FALSE;
  UINT64 BackEnd = ZORN_SCANOUT_BACK + ZORN_SCANOUT_BYTES;
  if (Map == NULL || Stride < sizeof (*Map) || (Stride & 7) != 0 ||
      Size == 0 || Size % Stride != 0 || Version != EFI_MEMORY_DESCRIPTOR_VERSION) {
    return ZornScanoutEfiMapInvalid;
  }
  for (UINTN At = 0; At < Size; At += Stride) {
    EFI_MEMORY_DESCRIPTOR Entry;
    CopyMem (&Entry, (CONST UINT8 *)Map + At, sizeof (Entry));
    UINT64 Start = Entry.PhysicalStart;
    if ((Start & (EFI_PAGE_SIZE - 1)) != 0 || Entry.NumberOfPages == 0 ||
        Entry.NumberOfPages > (MAX_UINT64 - Start) / EFI_PAGE_SIZE) {
      return ZornScanoutEfiMapInvalid;
    }
    UINT64 End = Start + EFI_PAGES_TO_SIZE (Entry.NumberOfPages);
    if (Start >= BackEnd || End <= ZORN_SCANOUT_BACK) {
      continue;
    }
    // DXE merges GCD capabilities into reserved EFI descriptors. Actual
    // access protection is checked against the underlying GCD attributes.
    if (Covered || Entry.Type != EfiReservedMemoryType ||
        (Entry.Attribute & EFI_MEMORY_RUNTIME) != 0) {
      return ZornScanoutEfiMapConflict;
    }
    if (Start > ZORN_SCANOUT_BACK || End < BackEnd) {
      return ZornScanoutEfiMapUncovered;
    }
    Covered = TRUE;
  }
  return Covered ? ZornScanoutReserved : ZornScanoutEfiMapUncovered;
}

STATIC enum ZornScanoutFirmwareStatus
ZornVerifyScanoutReservation (
  CONST UINT64 Video[6],
  UINT64 XnuBase,
  UINT64 XnuSize
  )
{
  if (Video[0] != ZORN_SCANOUT_FRONT || Video[2] != ZORN_SCANOUT_STRIDE ||
      Video[3] != ZORN_SCANOUT_WIDTH || Video[4] != ZORN_SCANOUT_HEIGHT || Video[5] != 32) {
    return ZornScanoutWrongGop;
  }
  if (!zorn_scanout_matches_window (XnuBase, XnuSize)) {
    return ZornScanoutXnuOverlap;
  }
  EFI_GCD_MEMORY_SPACE_DESCRIPTOR Gcd;
  if (gDS == NULL || gDS->GetMemorySpaceDescriptor == NULL ||
      EFI_ERROR (gDS->GetMemorySpaceDescriptor (ZORN_SCANOUT_BACK, &Gcd))) {
    return ZornScanoutGcdUnavailable;
  }
  if (Gcd.BaseAddress != ZORN_SCANOUT_FRONT || Gcd.Length != ZORN_SCANOUT_END - ZORN_SCANOUT_FRONT ||
      Gcd.GcdMemoryType != EfiGcdMemoryTypeReserved || Gcd.ImageHandle || Gcd.DeviceHandle ||
      (Gcd.Attributes & (EFI_MEMORY_RUNTIME | EFI_MEMORY_RP | EFI_MEMORY_RO)) != 0) {
    return ZornScanoutGcdConflict;
  }
  return ZornScanoutReserved;
}

#endif
