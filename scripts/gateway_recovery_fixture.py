"""Deterministic response injection through real sandboxed Codex, no model call."""
import json
from run_codex_baseline import execute, init_fixture


def injected_response(message, finish='stop'):
    return {'model':'injected-fixture', 'choices':[{'finish_reason':finish,'message':message}],
            'usage':{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2}}


def recovery_fixture(run, config, tools, binary):
    workspace=run/'workspace-recovery'
    init_fixture(workspace,{'source.py':'MARKER = "recovery-heron-731"\n'})
    count=0
    def transport(payload):
        nonlocal count
        count+=1
        if count==1:
            return injected_response({'content':None,'tool_calls':[{'id':'invalid-read',
                'type':'function','function':{'name':'read_file','arguments':'{"path":"/testbed/source.py"}'}}]},'tool_calls')
        if count==2:
            assert any(m.get('role')=='tool' and 'Unknown or unavailable' in m.get('content','') for m in payload['messages'])
            return injected_response({'content':None,'reasoning':'I should read the source file.'})
        if count==3:
            assert 'reasoning but no tool action' in payload['messages'][-1]['content']
            return injected_response({'content':None,'tool_calls':[{'id':'valid-read',
                'type':'function','function':{'name':'exec_command','arguments':'{"cmd":"cat source.py"}'}}]},'tool_calls')
        assert count==4
        assert any(m.get('role')=='tool' and 'recovery-heron-731' in m.get('content','') for m in payload['messages'])
        return injected_response({'content':'Verified recovery-heron-731 through the command result.'})
    result=execute(workspace,run/'injected-recovery','Read source.py using an available tool and report MARKER.',
                   config,tools,binary,fixture=True,transport=transport)
    events=[json.loads(x) for x in (run/'injected-recovery/codex_events.jsonl').read_text().splitlines()]
    commands=[x['item'] for x in events if x.get('type')=='item.completed' and x.get('item',{}).get('type')=='command_execution']
    assert result['termination_reason']=='completed' and count==4, result
    assert len(commands)==1 and 'recovery-heron-731' in commands[0]['aggregated_output']
    assert (workspace/'source.py').read_text()=='MARKER = "recovery-heron-731"\n'
    (run/'injected-recovery/fixture-result.json').write_text(json.dumps({'passed':True,'injected_responses':count,
        'real_model_calls':0,'executed_commands':len(commands)},indent=2)+'\n')
    print(json.dumps({'fixture':'injected_gateway_recovery','passed':True}),flush=True)
