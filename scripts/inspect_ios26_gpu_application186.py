"""Decode source-defined v186 application observation; no device operations."""
import base64,re

def inspect_application(stage,publication,native,encoded,tag,known_image):
    if stage not in (87,88):
        if any(x is not None for x in (publication,native,encoded)):raise ValueError('unexpected application fields')
        return dict(published=False,complete=False,native=None,report=None,reasons=['not-reached'])
    if publication is None:raise ValueError('missing application publication')
    pub=int(publication,16)
    if pub>>32!=1 or (stage==88)!=(pub&0xffffffff==0):raise ValueError('publication stage/raw mismatch')
    if stage==87:
        if native is not None or encoded is not None:raise ValueError('application fields before publication')
        return dict(published=False,complete=False,publication_raw=pub&0xffffffff,native=None,report=None,reasons=['publication-failed'])
    if native is None or encoded is None:raise ValueError('missing application capture')
    fields=native.split(b'/');bases=[16,10,16,10,10,16,10,16,10,10,10,10,10]
    if len(fields)!=13:raise ValueError('native field count')
    v=[int(x,base) for x,base in zip(fields,bases)]
    keys=['unique','pid','flags','calls','method','raw','close_returned','close_raw','attempts','copy_errors','lines','bytes','dropped'];n=dict(zip(keys,v))
    if v[2]&~255 or v[3]>256 or v[6]>1 or v[8]>32 or v[9]>v[8] or v[10]>v[8] or v[11]>=384:raise ValueError('native bounds')
    raw=base64.b64decode(encoded,validate=True)
    if len(raw)!=v[11] or base64.b64encode(raw)!=encoded:raise ValueError('output size/base64 differs')
    report=None;reasons=[]
    if raw:
        pattern=(r'ZORN186APP run='+re.escape(tag)+r' pid=(\d+) phase=(\d+) method=(\d+) raw=([0-9a-f]+) flags=([0-9a-f]+) iova=([0-9a-f]+) fence=(\d+) crc=([0-9a-f]{8}) firstBad=([0-9a-f]+) ticks=(\d+) closed=([01])\n').encode()
        m=re.fullmatch(pattern,raw)
        if not m:raise ValueError('application report syntax/run differs')
        values=[int(x,base) for x,base in zip(m.groups(),[10,10,10,16,16,16,10,16,16,10,10])]
        report=dict(zip(['pid','phase','method','raw','flags','iova','fence','crc','first_bad','ticks','closed'],values))
        if report['pid']!=n['pid'] or not n['unique'] or not n['lines']:raise ValueError('application/native identity differs')
    if not n['unique'] or not n['pid']:reasons.append('client-not-admitted')
    if n['flags']!=255 or not n['calls'] or not n['close_returned'] or n['close_raw'] or n['raw']:reasons.append('native-session-incomplete')
    if n['copy_errors'] or n['dropped']:reasons.append('diagnostic-loss')
    if report is None:reasons.append('no-complete-user-report')
    elif (report['phase']!=11 or report['method']!=4 or report['raw'] or report['flags']!=1023 or
          report['crc']!=0xe843b26a or report['first_bad']!=0xffffffff or not report['ticks'] or report['closed']!=1 or
          report['iova']&4095 or report['iova']>0xffff8000 or not report['iova'] or not known_image or report['fence']<=known_image[7]):
        reasons.append('user-image-or-close-incomplete')
    return dict(published=True,complete=not reasons,publication_raw=0,native=n,report=report,reasons=reasons)
