/* SPDX-License-Identifier: BSD-2-Clause-Patent */
#pragma once
#include "ZornApplicationJournal248.h"
// The existing producer calls this synchronously, once per frame. Cursor is
// advanced only once the whole formatted fragment fits; transport loss remains
// the existing CDC receiver's responsibility and cannot be declared complete.
template<class Sample,class Encode>
static unsigned zorn_journal_append248(char *line,unsigned cap,unsigned size,
 uint32_t &cursor,Sample sample,Encode encode){
 constexpr unsigned overhead=5+2*17+11*9+4+2; // ,jl=1 + fields + ,jb= + CRLF
 if(!line || size<2 || size>=cap || cap-(size-2)<=overhead)return 0;
 unsigned room=cap-(size-2)-overhead-1;
 unsigned raw=(room/4)*3;if(raw>ZornJournalChunk248)raw=ZornJournalChunk248;
 uint8_t bytes[ZornJournalChunk248]{};ZornJournalSnapshot248 s{};
 const unsigned have=raw && sample(cursor,bytes,raw,&s)?1u:0u;
 char header[overhead+1];
 const int n=snprintf(header,sizeof(header),
  ",jl=%u/%016llx/%016llx/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x/%08x,jb=",
  have,(unsigned long long)s.unique,(unsigned long long)s.seen_bytes,s.pid,s.reserved,
  s.published,s.records,s.pending,s.gaps,s.exited,s.exit_status,s.crc32,s.offset,s.bytes);
 if(n<0 || unsigned(n)>=sizeof(header) || s.bytes>raw || (!have && s.bytes))return 0;
 const unsigned encoded=4*((s.bytes+2)/3),start=size-2;
 if(unsigned(n)+encoded+2>=cap-start)return 0;
 memcpy(line+start,header,unsigned(n));encode(line+start+n,bytes,s.bytes);
 line[start+n+encoded]='\r';line[start+n+encoded+1]='\n';line[start+n+encoded+2]=0;
 if(have)cursor+=s.bytes;
 return start+unsigned(n)+encoded+2;
}
