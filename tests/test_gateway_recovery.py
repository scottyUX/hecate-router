import json
import pytest
from hecate.execution.model_gateway import Gateway, ModelOutputError, ProtocolError


def body():
    return {'input':[{'role':'user','content':'Read source'}], 'tools':[
        {'type':'function','name':'exec_command','parameters':{'type':'object','properties':{'cmd':{'type':'string'}}}}]}


def response(message, finish='stop'):
    return {'model':'fixture','choices':[{'message':message,'finish_reason':finish}],
            'usage':{'prompt_tokens':5,'completion_tokens':2,'total_tokens':7}}


def unknown():
    return response({'content':None,'tool_calls':[{'id':'bad','type':'function','function':
        {'name':'read_file','arguments':'{"path":"source.py"}'}}]},'tool_calls')


def valid():
    return response({'content':None,'tool_calls':[{'id':'good','type':'function','function':
        {'name':'exec_command','arguments':'{"cmd":"cat source.py"}'}}]},'tool_calls')


def gateway(tmp_path, transport, **options):
    return Gateway(tmp_path/'s','http://127.0.0.1:8135/v1','fixture',tmp_path,
                   request_limit=options.pop('request_limit',10),sampling={},transport=transport,
                   recover_model_outputs=options.pop('recover_model_outputs',True),**options)


def test_unknown_and_reasoning_recover_before_exposing_only_valid_action(tmp_path):
    payloads=[]
    answers=iter([unknown(),response({'content':None,'reasoning':'I should inspect the file'}),valid()])
    def transport(payload):
        payloads.append(payload)
        return next(answers)
    g=gateway(tmp_path,transport)
    result=g.complete(body())
    assert g.requests==3 and len(g.metrics)==3
    assert [x['name'] for x in result['output']]==['exec_command']
    assert payloads[1]['messages'][-2]['tool_calls'][0]['function']['name']=='read_file'
    assert 'No action was executed' in payloads[1]['messages'][-1]['content']
    assert 'exec_command' in payloads[1]['messages'][-1]['content']
    assert 'reasoning but no tool action' in payloads[2]['messages'][-1]['content']
    assert all(x['usage']['total_tokens']==7 for x in g.metrics)
    events=[json.loads(x) for x in (tmp_path/'gateway.jsonl').read_text().splitlines()]
    assert [x['kind'] for x in events if x['event']=='model_output_recovery']==['unknown_tool','reasoning_only']
    assert len([x for x in events if x['event']=='upstream_response'])==3


@pytest.mark.parametrize('visible', [None, '\n\n'])
def test_repeated_reasoning_stops_at_recovery_limit(tmp_path,visible):
    g=gateway(tmp_path,lambda _:response({'reasoning_content':'thinking','content':visible}),max_response_recoveries=2)
    with pytest.raises(ModelOutputError,match='recovery limit'):
        g.complete(body())
    assert g.requests==3 and len(g.metrics)==3


def test_recoveries_consume_shared_request_budget(tmp_path):
    g=gateway(tmp_path,lambda _:unknown(),request_limit=2)
    with pytest.raises(ProtocolError,match='budget exhausted'):
        g.complete(body())
    assert g.cap_hit and g.requests==2 and len(g.metrics)==2


def test_legacy_behavior_and_real_final_answers(tmp_path):
    g=gateway(tmp_path,lambda _:unknown(),recover_model_outputs=False)
    with pytest.raises(ModelOutputError,match='unadvertised'):
        g.complete(body())
    assert g.requests==1


def test_invalid_batch_executes_nothing_and_removed_builtin_is_not_forwarded(tmp_path):
    raw=valid()
    raw['choices'][0]['message']['tool_calls']+=unknown()['choices'][0]['message']['tool_calls']
    raw['choices'][0]['message']['tool_calls'][1]['function']['name']='view_image'
    answers=iter([raw,response({'content':'Finished without executing the invalid batch.'})])
    payloads=[]
    def transport(payload):
        payloads.append(payload)
        return next(answers)
    g=gateway(tmp_path,transport)
    result=g.complete(body())
    assert all(x['type']=='message' for x in result['output'])
    errors=[x['content'] for x in payloads[1]['messages'] if x['role']=='tool']
    assert len(errors)==2 and all('No action was executed' in x for x in errors)
    g=gateway(tmp_path,lambda _:response({'content':'Finished','reasoning':'private thought'}))
    result=g.complete(body())
    assert result['output'][0]['content'][0]['text']=='Finished'
    assert g.requests==1


@pytest.mark.parametrize('message,finish',[
    ({'content':None},'stop'),
    ({'content':None,'reasoning':'thinking'},'length'),
    ({'tool_calls':[{'id':'bad','function':{'name':'read_file','arguments':'not-json'}}]},'tool_calls'),
    ({'tool_calls':[{'id':'good','function':{'name':'exec_command','arguments':'{"cmd":"ls","sandbox_permissions":"require_escalated"}'}}]},'tool_calls'),
])
def test_unrelated_invalid_outputs_are_not_recovered(tmp_path,message,finish):
    g=gateway(tmp_path,lambda _:response(message,finish))
    with pytest.raises(ModelOutputError):g.complete(body())
    assert g.requests==1


def test_rerun_preserves_ten_ids_and_model_settings():
    import yaml
    from pathlib import Path
    original=yaml.safe_load(Path('configs/qwen36_ten_task_pilot.yaml').read_text())
    corrected=yaml.safe_load(Path('configs/qwen36_gateway_recovery.yaml').read_text())
    assert corrected['model']==original['model']
    assert corrected['limits']==original['limits']
    assert corrected['pilot_selection']==original['pilot_selection']
    assert corrected['run_prefix']=='task011'
    assert corrected['serving']['recover_model_outputs'] is True
    assert corrected['serving']['max_response_recoveries']==3


def test_native_patch_grammar_is_preserved_for_function_adapter():
    from hecate.execution.model_gateway import translate_request
    request=body()
    grammar='start: "*** Begin Patch" LF hunk "*** End Patch"'
    request['tools'].append({'type':'custom','name':'apply_patch','description':'FREEFORM, do not wrap in JSON',
                             'format':{'type':'grammar','syntax':'lark','definition':grammar}})
    payload,_=translate_request(request,'fixture',{},preserve_patch_grammar=True)
    tool=next(x['function'] for x in payload['tools'] if x['function']['name']=='apply_patch')
    assert grammar in tool['description']
    assert 'Do not put another JSON object' in tool['description']
    assert 'FREEFORM, do not wrap in JSON' not in tool['description']
    assert tool['parameters']['required']==['input']


def test_progress_requires_explicit_finish_and_can_continue(tmp_path):
    answers=iter([response({'content':'Now let me look at astroid annotations:'}),valid(),
        response({'content':None,'tool_calls':[{'id':'end','function':{'name':'hecate_finish',
            'arguments':'{"response":"Finished after inspecting the file."}'}}]},'tool_calls')])
    sent=[]
    def transport(payload):sent.append(payload);return next(answers)
    g=gateway(tmp_path,transport,tool_decoding='auto_with_finish')
    action=g.complete(body())
    assert action['output'][0]['name']=='exec_command' and g.requests==2
    assert sent[1]['messages'][-1]['content'].startswith('Text alone does not end')
    assert sent[0]['tool_choice']=='auto'
    end=g.complete(body())
    assert end['output'][0]['content'][0]['text']=='Finished after inspecting the file.'
    assert g.requests==3


def test_finish_accepts_report_text_and_recovers_bad_json_without_repairing_it(tmp_path):
    bad=response({'content':'The file was read.','tool_calls':[{'id':'bad-finish','function':
        {'name':'hecate_finish','arguments':'{"response":"bad "quotes""}'}}]},'tool_calls')
    good=response({'content':'Accompanying final report.','tool_calls':[{'id':'good-finish','function':
        {'name':'hecate_finish','arguments':'{"response":"Finished after reading the file."}'}}]},'tool_calls')
    answers=iter([bad,good]);sent=[]
    def transport(payload):sent.append(payload);return next(answers)
    g=gateway(tmp_path,transport,tool_decoding='auto_with_finish')
    result=g.complete(body())
    assert g.requests==2 and 'rejected' in sent[1]['messages'][-1]['content']
    assert len(result['output'])==2
    assert result['output'][-1]['content'][0]['text']=='Finished after reading the file.'


def test_patch_call_with_extra_workdir_gets_tool_error_and_retries(tmp_path):
    request=body()
    request['tools'].append({'type':'custom','name':'apply_patch','description':'FREEFORM, do not wrap in JSON',
                             'format':{'type':'grammar','syntax':'lark','definition':'start: "*** Begin Patch"'}})
    patch='*** Begin Patch\n*** Add File: a.py\n+x = 1\n*** End Patch'
    bad=response({'content':None,'tool_calls':[{'id':'p1','type':'function','function':
        {'name':'apply_patch','arguments':json.dumps({'input':patch,'workdir':'/testbed'})}}]},'tool_calls')
    good=response({'content':None,'tool_calls':[{'id':'p2','type':'function','function':
        {'name':'apply_patch','arguments':json.dumps({'input':patch})}}]},'tool_calls')
    answers=iter([bad,good]); sent=[]
    def transport(payload):sent.append(payload);return next(answers)
    g=gateway(tmp_path,transport)
    result=g.complete(request)
    assert result['output'][0]['type']=='custom_tool_call' and result['output'][0]['input']==patch
    feedback=sent[1]['messages'][-1]
    assert feedback['role']=='tool' and feedback['tool_call_id']=='p1' and '"workdir"' in feedback['content']
    assert g.requests==2


def test_exec_command_without_cmd_gets_tool_error_and_retries(tmp_path):
    bad=response({'content':None,'tool_calls':[{'id':'c1','type':'function','function':
        {'name':'exec_command','arguments':'{"cd":"/testbed"}'}}]},'tool_calls')
    answers=iter([bad,valid()]); sent=[]
    def transport(payload):sent.append(payload);return next(answers)
    g=gateway(tmp_path,transport)
    result=g.complete(body())
    assert result['output'][0]['name']=='exec_command'
    feedback=sent[1]['messages'][-1]
    assert feedback['tool_call_id']=='c1' and '"cmd"' in feedback['content']
