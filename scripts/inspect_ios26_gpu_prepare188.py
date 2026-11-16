"""Decode the source-defined v188 first-failure preparation observation."""
STAGES = {1:'open-entry',2:'begin-operation-return',3:'scope-match',4:'empty-process-list',
          5:'prepare-return',6:'select-return',7:'attach-vm-return',8:'open-client-return',9:'finish-return',
          16:'operation-authority-return',17:'operation-postcheck',24:'transition-connection',
          25:'transition-quiesce-return',26:'domain-transition-return',32:'quiesce-health',
          33:'foreign-process-idle',34:'selected-process-wait',35:'runtime-wait',
          36:'ring-guard',37:'ring-idle',38:'no-outstanding-jobs'}
REQUIRED = set(range(1,10)) | {16,24,25,26,32,33,35,36,37,38}

def inspect_prepare(stage, encoded):
    if stage != 88:
        if encoded is not None:raise ValueError('unexpected preparation observation')
        return dict(observed=False,complete=False)
    if encoded is None:raise ValueError('missing preparation observation')
    fields=encoded.split(b'/')
    if len(fields)!=6:raise ValueError('preparation field count')
    at,raw,detail,events,failed,mask=[int(x,b) for x,b in zip(fields,[10,16,16,10,10,16])]
    allowed=sum(1<<n for n in STAGES)
    if raw>0xffffffff or detail>0xffffffff or events>128 or failed not in (0,1) or mask&~allowed:
        raise ValueError('preparation bounds')
    if not events:
        if any((at,raw,detail,failed,mask)):raise ValueError('empty preparation differs')
        return dict(observed=False,complete=False,events=0)
    if at not in STAGES or not mask&(1<<at) or mask.bit_count()>events or bool(failed)!=bool(raw):
        raise ValueError('preparation stage/raw/mask differs')
    return dict(observed=True,complete=at==9 and not failed and all(mask&(1<<n) for n in REQUIRED),
                stage=at,name=STAGES[at],raw=raw,detail=detail,events=events,failed=bool(failed),mask=mask,
                raw_kind='native-ring-result' if at in (36,37) else 'IOReturn')
