/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#include "ZornCheckpointBootLifetime.h"
static EFI_GUID groups[]={EFI_EVENT_GROUP_BEFORE_EXIT_BOOT_SERVICES,EFI_EVENT_GROUP_EXIT_BOOT_SERVICES};
UINT32 ZornCheckpointBootLifetime::expired() const
{return __atomic_load_n(&expired_[0],__ATOMIC_ACQUIRE)|(__atomic_load_n(&expired_[1],__ATOMIC_ACQUIRE)<<1);}
VOID EFIAPI ZornCheckpointBootLifetime::notify(EFI_EVENT,VOID *p)
{
 auto *c=static_cast<Cookie*>(p);
 // The firmware borrows this exact persistent cookie supplied at registration.
 __atomic_store_n(&c->owner->expired_[c->kind],1u,__ATOMIC_RELEASE);
}
EFI_STATUS ZornCheckpointBootLifetime::check(UINT64 epoch) const
{return expired() || report_.state!=2 || busy_ || close_once_ || epoch!=report_.epoch?EFI_ABORTED:EFI_SUCCESS;}
ZcblReport ZornCheckpointBootLifetime::report() const
{auto r=report_;r.expired_events=expired();return r;}
ZcblResult ZornCheckpointBootLifetime::fail(ZcblResult r,bool native,EFI_STATUS status,UINT32 origin)
{
 if(!report_.first_error){report_.first_error=r;report_.native_available=native;report_.first_native=status;report_.native_origin=origin;}
 report_.state=3;return r;
}
ZcblResult ZornCheckpointBootLifetime::prepare(EFI_BOOT_SERVICES *bs,UINT64 epoch,const ZornCheckpointBootLifetime*guard)
{
 if(busy_ || report_.state)return ZCBL_USED;
 if(guard==this || !epoch || !bs || bs->Hdr.Signature!=EFI_BOOT_SERVICES_SIGNATURE ||
    bs->Hdr.HeaderSize<sizeof(*bs) || !bs->CreateEventEx || !bs->CloseEvent)return ZCBL_ARGUMENT;
 busy_=true;report_.state=1;report_.epoch=epoch;bs_=bs;
 for(unsigned i=0;i<2;++i){
  if(expired() || (guard&&guard->check(epoch)!=EFI_SUCCESS)){busy_=false;return fail(ZCBL_EXPIRED);}
  cookies_[i]={this,i};EFI_EVENT event=nullptr;report_.create_attempted|=1u<<i;
  EFI_STATUS status=bs_->CreateEventEx(EVT_NOTIFY_SIGNAL,TPL_NOTIFY,notify,&cookies_[i],&groups[i],&event);
  events_[i]=event;if(event)report_.returned_events|=1u<<i;
  report_.create_status[i]=status;
  // Error/warning can return uncertain partial handle: retain, never auto-close.
  if(status!=EFI_SUCCESS){busy_=false;return fail(ZCBL_CREATE,true,status,1);}
  if(!event){busy_=false;return fail(ZCBL_NULL_EVENT);}
  if(i && event==events_[0]){duplicate_event_=true;busy_=false;return fail(ZCBL_UNCERTAIN);}
  report_.created_events|=1u<<i;
 }
 if(expired() || (guard&&guard->check(epoch)!=EFI_SUCCESS)){busy_=false;return fail(ZCBL_EXPIRED);}
 busy_=false;
 if(expired() || (guard&&guard->check(epoch)!=EFI_SUCCESS))return fail(ZCBL_EXPIRED);
 report_.state=2;return ZCBL_OK;
}
ZcblResult ZornCheckpointBootLifetime::close(const ZornCheckpointBootLifetime*guard)
{
 if(busy_ || close_once_)return ZCBL_USED;
 if(!report_.state)return ZCBL_ARGUMENT;
 close_once_=true;busy_=true;
 
 if(duplicate_event_){bs_=nullptr;busy_=false;return fail(ZCBL_UNCERTAIN);}
 if(expired() || (guard&&guard->check(report_.epoch)!=EFI_SUCCESS)){bs_=nullptr;busy_=false;return fail(ZCBL_EXPIRED);}
 for(unsigned i=0;i<2;++i)if(report_.created_events&(1u<<i)){
  if(expired() || (guard&&guard->check(report_.epoch)!=EFI_SUCCESS)){bs_=nullptr;busy_=false;return fail(ZCBL_EXPIRED);}
  report_.close_attempted|=1u<<i;
  const EFI_STATUS status=bs_->CloseEvent(events_[i]);report_.close_status[i]=status;
  if(status!=EFI_SUCCESS){busy_=false;return fail(ZCBL_CLOSE,true,status,2);}
  report_.closed_events|=1u<<i;events_[i]=nullptr;
 }
 busy_=false;bs_=nullptr;
 if(expired() || (guard&&guard->check(report_.epoch)!=EFI_SUCCESS))return fail(ZCBL_EXPIRED);
 if(report_.returned_events!=report_.closed_events || report_.create_attempted!=report_.created_events)return fail(ZCBL_UNCERTAIN);
 report_.state=4;return ZCBL_OK;
}
