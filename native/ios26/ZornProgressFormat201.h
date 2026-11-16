// SPDX-License-Identifier: MIT
#pragma once
#include "ZornApplicationObservation26.h"
// Caller supplies the existing bounded base64 encoder and snprintf.
static unsigned zorn_progress_format201(char *line,unsigned cap,const char *tag,
 unsigned sequence,unsigned state,unsigned smr,unsigned spawn,unsigned snapshot,
 uint64_t publication,const ZornApplicationObservation26 &a){
 if(!line || !cap || !tag || a.bytes>=sizeof(a.text) || a.rawBytes>=sizeof(a.rawText) || a.sessions>4)return 0;
 char encoded[zorn26_base64_size(sizeof(a.text))+1]{};
 char raw[zorn26_base64_size(sizeof(a.rawText))+1]{};
 zorn26_base64_encode(encoded,reinterpret_cast<const uint8_t *>(a.text),a.bytes);
 zorn26_base64_encode(raw,reinterpret_cast<const uint8_t *>(a.rawText),a.rawBytes);
 int n=snprintf(line,cap,"K80 GPU PROGRESS %s seq=%u,state=%u,smr=%u,spawn=%u,snap=%u,ap=%016llx,au=%016llx/%u/%x/%u/%u/%x/%u/%x/%u/%u/%u/%u/%u,at=%s,ms=%u/%u/%u,mp=%016llx/%u/%u/%u,mt=%s",
 tag,sequence,state,smr,spawn,snapshot,static_cast<unsigned long long>(publication),
 static_cast<unsigned long long>(a.unique),a.pid,a.flags,a.calls,a.method,a.raw,a.closeReturned,a.closeRaw,a.attempts,a.copyErrors,a.lines,a.bytes,a.dropped,encoded,
 a.sessions,a.sessionRejected,a.reportTerminal,static_cast<unsigned long long>(a.reportUnique),a.reportPid,a.rawBytes,a.rawDropped,raw);
 if(n<0 || unsigned(n)>=cap)return 0;unsigned length=unsigned(n);
 for(unsigned i=0;i<a.sessions;++i){const auto &h=a.history[i];
  n=snprintf(line+length,cap-length,",mh%u=%x/%u/%u/%x/%u/%x/%u/%x/%x/%u/%u/%016llx",i,h.flags,h.calls,h.method,h.raw,h.closeReturned,h.closeRaw,h.prepareStage,h.prepareRaw,h.prepareDetail,h.prepareEvents,h.prepareFailed,static_cast<unsigned long long>(h.prepareMask));
  if(n<0 || unsigned(n)>=cap-length)return 0;length+=unsigned(n);
 }
 if(cap-length<3)return 0;line[length++]='\r';line[length++]='\n';line[length]=0;return length;
}
