import json
from pathlib import Path
import yaml
from hecate.execution.codex_session import config_text


def test_ten_task_scope_and_native_settings():
    cfg=yaml.safe_load(Path('configs/qwen36_ten_task_pilot.yaml').read_text())
    s=json.loads(Path(cfg['pilot_selection']).read_text())
    paper=json.loads(Path(cfg['selection_manifest']).read_text())
    assert len(s['instance_ids'])==len(set(s['instance_ids']))==10
    assert set(s['instance_ids'])<=set(paper['instance_ids'])
    assert not set(s['instance_ids'])&set(s['excluded_x86_ids'])
    assert s['instance_ids'][0]=='django__django-16560'
    assert cfg['model']['context_tokens']==262144
    assert cfg['serving']['prompt_profile']=='native'
    assert cfg['serving']['editing_mode']=='patch'
    assert cfg['limits']['task_model_requests']==200


def test_native_prompt_does_not_replace_codex_instructions():
    assert 'model_instructions_file' in config_text('local',32768)
    native=config_text('local',262144,native_instructions=True)
    assert 'model_instructions_file' not in native
    assert 'model_context_window = 262144' in native
