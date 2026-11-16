/* SPDX-License-Identifier: MIT */
#include "ZornCommandDbFile.h"
static unsigned u16(const uint8_t *p){return p[0]|(unsigned)p[1]<<8;}
static int extent(size_t at,size_t n,size_t bytes){return at<=bytes&&n<=bytes-at;}
static int span(const void *p,size_t n,size_t alignment){
    return p&&n&&!((uintptr_t)p%alignment)&&n-1<=UINTPTR_MAX-(uintptr_t)p;
}
static int overlap(const void *p,size_t n,const void *q,size_t m){
    uintptr_t a=(uintptr_t)p,b=(uintptr_t)q;
    return n&&m&&(a<=b?b-a<n:a-b<m);
}
static void copy(uint8_t *to,const uint8_t *from,size_t n){for(size_t i=0;i<n;++i)to[i]=from[i];}
ZornCommandDbFileStatus ZornCommandDbDecodeFile(const uint8_t *data,size_t bytes,
    ZornCommandDbFileEntry *entries,size_t capacity,ZornCommandDbFileSummary *summary){
    if(bytes<ZCDF_HEADER_BYTES||bytes>ZCDF_MAX_FILE_BYTES||capacity>ZCDF_MAX_ENTRIES||
       !span(data,bytes,1)||!span(summary,sizeof(*summary),_Alignof(ZornCommandDbFileSummary))||
       (capacity&&!span(entries,capacity*sizeof(*entries),_Alignof(ZornCommandDbFileEntry))))return ZCDF_ARGUMENT;
    size_t output_bytes=capacity*sizeof(*entries);
    if(overlap(data,bytes,summary,sizeof(*summary))||
       (capacity&&(overlap(data,bytes,entries,output_bytes)||overlap(summary,sizeof(*summary),entries,output_bytes))))return ZCDF_ALIAS;
    if((data[0]==0x7f&&data[1]=='E'&&data[2]=='L'&&data[3]=='F')||
       (data[0]==0xd0&&data[1]==0x0d&&data[2]==0xfe&&data[3]==0xed)||
       data[4]!=0xdb||data[5]!=0x30||data[6]!=0x03||data[7]!=0x0c)return ZCDF_FORMAT;
    size_t heads[8]={0},sizes[8]={0},aux[8]={0},total=0;unsigned rows=0;
    for(unsigned i=0;i<8;++i){
        const uint8_t *r=data+8+16*i;unsigned count=u16(r+6);
        if(!u16(r))break;
        if(count>ZCDF_MAX_ENTRIES-total)return ZCDF_BUDGET;
        total+=count;heads[i]=ZCDF_HEADER_BYTES+u16(r+2);sizes[i]=(size_t)count*24;
        aux[i]=ZCDF_HEADER_BYTES+u16(r+4);
        if(!extent(heads[i],sizes[i],bytes)||!extent(aux[i],0,bytes))return ZCDF_RANGE;
        ++rows;
    }
    if(total>capacity)return ZCDF_CAPACITY;
    /* Validation pass:do not expose a partial result for a late bad AUX. */
    for(unsigned i=0;i<rows;++i)for(size_t at=heads[i];at<heads[i]+sizes[i];at+=24){
        const uint8_t *e=data+at;size_t offset=aux[i]+u16(e+22),length=u16(e+20);
        if(!extent(offset,length,bytes))return ZCDF_RANGE;
    }
    size_t out=0;
    for(unsigned i=0;i<rows;++i)for(size_t at=heads[i];at<heads[i]+sizes[i];at+=24){
        const uint8_t *e=data+at;ZornCommandDbFileEntry built={0};copy(built.raw,e,24);
        built.row_index=i;built.entry_index=(uint32_t)((at-heads[i])/24);
        built.record_file_offset=at;built.aux_file_offset=aux[i]+u16(e+22);built.aux_bytes=u16(e+20);
        if(built.aux_bytes)for(unsigned j=0;j<rows;++j)
            if(sizes[j]&&built.aux_file_offset<heads[j]+sizes[j]&&heads[j]<built.aux_file_offset+built.aux_bytes)
                built.aux_overlaps_record_table=1;
        entries[out++]=built;
    }
    ZornCommandDbFileSummary built={0};copy(built.header_raw,data,ZCDF_HEADER_BYTES);
    built.source_bytes=bytes;built.entry_count=total;built.searched_rows=rows;
    *summary=built;return ZCDF_OK;
}
