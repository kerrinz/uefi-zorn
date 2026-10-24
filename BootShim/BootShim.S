// BootShim from UniXNU/uefi-sheng (branch sheng).
// The image-size field covers this shim plus the firmware volume. The
// Mu-Silicium BootShim only stores FD_SIZE, which the unixnu check rejects.
// The copy loop still moves FD_SIZE bytes. Cache maintenance runs before the
// branch into the relocated volume.

_Head:
  adr   x1, _Payload    /* Set _Entry address */
  b     _Start          /* Jump to the real code */

#if REQUIRES_KERNEL_HEADER == 1
_StackBase:
  .quad FD_BASE         /* Text Offset */

_StackSize:
  .quad FD_SIZE + PAYLOAD_SIZE + (_Payload - _Head) /* shim, FD, and embedded FAT */
  .quad 0               /* Flags */
  .quad 0               /* Reserved */
  .quad 0               /* Reserved */
  .quad 0               /* Reserved */
  .ascii "ARM\x64"      /* ARM64 Magic */
  .long 0               /* Reserved */
#endif

_Start:
  mov   x4, x1
  ldr   x5, =FD_BASE
  cmp   x4, x5
  beq   _Entry
  ldr   x6,  =FD_SIZE

_CopyLoop:
  ldp   x2, x3, [x4], #16
  stp   x2, x3, [x5], #16
  subs  x6, x6, #16
  b.ne  _CopyLoop
#if PAYLOAD_SIZE
  /* x4 now points at the FAT image appended after the FD. Record it for
     ZornBootMemoryDxe. 0xA7601000 is the Info_Blk, writable DRAM. */
  ldr   x5, =0xA7601000
  movz  x6, #0x4F5A
  movk  x6, #0x4E52, lsl #16
  movk  x6, #0x4C50, lsl #32
  movk  x6, #0x3144, lsl #48
  str   x6, [x5]
  str   x4, [x5, #8]
  ldr   x6, =PAYLOAD_SIZE
  str   x6, [x5, #16]
  dsb   sy
#endif
  ldr   x5, =FD_BASE

_Entry:
  /* Publish the copied instructions before executing them. */
  dsb   sy
  mrs   x9, ctr_el0
  ubfx  x9, x9, #16, #4
  mov   x10, #4
  lsl   x9, x10, x9
  sub   x10, x9, #1
  bic   x8, x5, x10
  ldr   x7, =FD_SIZE
  add   x7, x5, x7

_CleanLoop:
  dc    cvac, x8
  add   x8, x8, x9
  cmp   x8, x7
  b.lo  _CleanLoop
  dsb   sy
  ic    iallu
  dsb   sy
  isb
  br    x5

_Dead:
  b     _Dead

.text
.ltorg
/* 4 KiB so the FAT after this shim and the 3 MiB FD stays page-aligned.
   The DRAM scan steps 4 KiB and misses a boot sector at +0xF0. */
.align 12

_Payload:
