/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#pragma once
#include <Uefi.h>
#include <Guid/EventGroup.h>
enum ZcblResult : UINT32 {ZCBL_OK,ZCBL_ARGUMENT,ZCBL_USED,ZCBL_EXPIRED,ZCBL_CREATE,ZCBL_NULL_EVENT,ZCBL_RESOLVER_UNUSED,ZCBL_CLOSE,ZCBL_UNCERTAIN};
struct ZcblReport {
 UINT64 epoch;EFI_STATUS create_status[2],close_status[2];
 UINT32 state,first_error,native_available,native_origin;EFI_STATUS first_native;
 UINT32 create_attempted,returned_events,created_events,close_attempted,closed_events,expired_events;
};
/* Event registration/callback/partial-handle/close core derived from exact
 * prior real lifecycle owner. No Clock/RPMh/CommandDB resolver or fake gate.
 * Normal serialized pre-EBS thread, persistent noncopy owner until every
 * possible callback ends; no destructor cleanup or retry. Before-EBS latches
 * even on a later failed EBS attempt. Cannot cancel an in-flight provider.
 * This lifetime protects firmware calls only, not GPU/power/SMMU/DMA rights. */
class ZornCheckpointBootLifetime final {
public:
 constexpr ZornCheckpointBootLifetime()=default;
 ~ZornCheckpointBootLifetime()=default;
 ZornCheckpointBootLifetime(const ZornCheckpointBootLifetime&)=delete;
 ZornCheckpointBootLifetime&operator=(const ZornCheckpointBootLifetime&)=delete;
 ZcblResult prepare(EFI_BOOT_SERVICES*,UINT64,const ZornCheckpointBootLifetime* guard=nullptr);
 ZcblResult close(const ZornCheckpointBootLifetime* guard=nullptr);
 EFI_STATUS check(UINT64)const;
 ZcblReport report()const;
private:
 struct Cookie {ZornCheckpointBootLifetime*owner;UINT32 kind;};
 Cookie cookies_[2]{};EFI_EVENT events_[2]{};EFI_BOOT_SERVICES*bs_{};
 UINT32 expired_[2]{};bool busy_{},close_once_{},duplicate_event_{};ZcblReport report_{};
 static VOID EFIAPI notify(EFI_EVENT,VOID*);
 UINT32 expired()const;
 ZcblResult fail(ZcblResult,bool=false,EFI_STATUS=0,UINT32=0);
};
