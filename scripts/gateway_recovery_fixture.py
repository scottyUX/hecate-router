"""Deterministic response injection through real sandboxed Codex, no model call."""
import json
import httpx
from run_codex_baseline import execute, init_fixture


def injected_response(message, finish='stop'):
    return {'model':'injected-fixture', 'choices':[{'finish_reason':finish,'message':message}],
            'usage':{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2}}


def recovery_fixture(run, config, tools, binary, *, live=False):
    label='live-recovery' if live else 'injected-recovery'
    workspace=run/('workspace-'+label)
    init_fixture(workspace,{'source.py':'MARKER = "recovery-heron-731"\n'})
    explicit=config['serving'].get('tool_decoding') in {'auto_with_finish','required_with_finish'}
    injections=[injected_response({'content':None,'tool_calls':[{'id':'invalid-read',
        'type':'function','function':{'name':'read_file','arguments':'{"path":"/testbed/source.py"}'}}]},'tool_calls'),
        injected_response({'content':None,'reasoning':'I should read the source file.'})]
    if explicit:
        progress=injected_response({'content':'Now let me look at the source file:'})
        injections=[progress] if live else injections+[progress]
    count=0
    def transport(payload):
        nonlocal count
        count+=1
        if count<=len(injections):return injections[count-1]
        if count==len(injections)+1:
            expected='Text alone does not end' if explicit else 'reasoning but no tool action'
            assert expected in payload['messages'][-1]['content']
        if live:
            with httpx.Client(timeout=config['limits']['request_timeout_s'],trust_env=False) as client:
                result=client.post(config['serving']['endpoint']+'/chat/completions',json=payload)
                result.raise_for_status()
                return result.json()
        if count==len(injections)+1:
            return injected_response({'content':None,'tool_calls':[{'id':'valid-read',
                'type':'function','function':{'name':'exec_command','arguments':'{"cmd":"cat source.py"}'}}]},'tool_calls')
        assert count==len(injections)+2
        assert any(m.get('role')=='tool' and 'recovery-heron-731' in m.get('content','') for m in payload['messages'])
        report='Verified recovery-heron-731 through the command result.'
        if explicit:
            return injected_response({'content':None,'tool_calls':[{'id':'finished','type':'function',
                'function':{'name':'hecate_finish','arguments':json.dumps({'response':report})}}]},'tool_calls')
        return injected_response({'content':report})
    result=execute(workspace,run/label,'Read source.py using an available tool and report MARKER.',
                   config,tools,binary,fixture=True,transport=transport)
    events=[json.loads(x) for x in (run/label/'codex_events.jsonl').read_text().splitlines()]
    commands=[x['item'] for x in events if x.get('type')=='item.completed' and x.get('item',{}).get('type')=='command_execution']
    assert result['termination_reason']=='completed' and (count>len(injections) if live else count==len(injections)+2), result
    assert any('recovery-heron-731' in c['aggregated_output'] for c in commands)
    if not live: assert len(commands)==1
    assert (workspace/'source.py').read_text()=='MARKER = "recovery-heron-731"\n'
    (run/label/'fixture-result.json').write_text(json.dumps({'passed':True,'injected_responses':len(injections) if live else count,
        'upstream_calls_after_injection':count-len(injections) if live else 0,'executed_commands':len(commands)},indent=2)+'\n')
    print(json.dumps({'fixture':label,'passed':True}),flush=True)
