"""Decode the source-defined v191 first-failure preparation observation."""
STAGES = {1:'open-entry',2:'begin-operation-return',3:'scope-match',4:'empty-process-list',
          5:'prepare-return',6:'select-return',7:'attach-vm-return',8:'open-client-return',9:'finish-return',
          16:'operation-authority-return',17:'operation-postcheck',24:'transition-connection',
          25:'transition-quiesce-return',26:'domain-transition-return',32:'quiesce-health',
          33:'foreign-process-idle',34:'selected-process-wait',35:'runtime-wait',
          36:'ring-guard',37:'ring-idle',38:'no-outstanding-jobs'}
STAGES.update({40:'domain-entry-permission',41:'domain-caller-gate',42:'domain-window-prerequisites',43:'domain-begin-window-return',44:'domain-runtime-state',45:'domain-global-fault-return',46:'domain-bank-owner',47:'domain-bank-fault-return',48:'domain-stream-conflict-return',49:'domain-bank-postcheck',50:'domain-consumer-claim',51:'host-tables-prepare-return',52:'domain-final-postcheck'})
STAGES[61]='native-window-result'
WINDOW_PREDICATES={53:'held-gate',54:'native-runtime-ready',55:'native-controller-claim',56:'domain-health',57:'window-not-open',58:'context-thread-empty',59:'blocked-thread-empty'}
REQUIRED = {61} | set(range(40,53)) | set(range(1,10)) | {16,24,25,26,32,33,35,36,37,38}

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
    if at==61 and ((raw==0 and detail!=0) or (raw!=0 and (raw!=0xe00002d8 or detail not in WINDOW_PREDICATES))):raise ValueError('window predicate/raw mismatch')
    return dict(observed=True,complete=at==9 and not failed and all(mask&(1<<n) for n in REQUIRED),
                stage=at,name=STAGES[at],window_predicate=WINDOW_PREDICATES.get(detail) if at==61 else None,raw=raw,detail=detail,events=events,failed=bool(failed),mask=mask,
                raw_kind='native-ring-result' if at in (36,37) else 'IOReturn')
