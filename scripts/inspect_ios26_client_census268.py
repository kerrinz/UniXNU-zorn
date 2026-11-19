"""Tighten267 bounded probe evidence with complete actual per-client census."""
from inspect_ios26_metal_probe267 import inspect_progress as inspect_probe,save_shot

def assess_census(result):
    rows=result.get('clients261',[]);app=result.get('last_application') or {};identity=app.get('program_identity') or {};ids={r['id'] for r in rows if r.get('available') and r.get('id')};total=max([r.get('records',0) for r in rows]+[0]);bound=bool(identity.get('unique') and rows and all((r['unique'],r['pid'])==(identity['unique'],identity['pid']) for r in rows));coverage=bool(0<total<=64 and len(ids)==len(rows)==total and all(r.get('available') for r in rows));closed=bool(rows and all(r['flags']&8 and not r['flags']&(2|16) and r['close_stage']==16 and not r['close_raw'] and r['calls'] for r in rows));no_failure=bool(rows and all(not r['failure']['sequence'] and not r['dropped'] and not r['recycled'] for r in rows) and not result.get('client_diagnostic_loss261'));complete=bool(result['Metal_probe267']['bounded_probe_and_required_lifecycle_complete'] and bound and coverage and closed and no_failure)
    return dict(reported_registered_records=total,observed_client_ids=sorted(ids),all_records_observed=coverage,all_task_bound=bound,all_actual_close_returned_success=closed,no_backend_failure_or_diagnostic_loss=no_failure,complete=complete,scope='Actual source-owned registered native clients of this one ordinary Metal probe,including both additional Query/Close members;not cross-task isolation or all future workloads')

def inspect_progress(data,tag,program_tag):
    result=inspect_probe(data,tag,program_tag);result['client_census268']=assess_census(result);result['complete_client_lifecycle268']=result['client_census268']['complete'];result['full_GPU_qualification']=False
    return result
