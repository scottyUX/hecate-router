import json
from pathlib import Path
import yaml
import importlib.util
from types import SimpleNamespace
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


def test_control_collection_exception_is_narrow_and_resume_preserves_attempts(monkeypatch):
    monkeypatch.syspath_prepend(str(Path('scripts').resolve()))
    spec=importlib.util.spec_from_file_location('ten_pilot', 'scripts/run_qwen36_ten_task.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    bug={'status':'evaluator_failure','resolved':None,'official_resolved':False,
         'test_markers_found':True,'timed_out':False,'missing_required_tests':['new_test']}
    gold={'status':'completed','resolved':True}
    log="ERROR collecting tests/unittest_pyreverse_writer.py\nImportError: cannot import name 'get_annotation' from 'pylint.pyreverse.utils'"
    task=SimpleNamespace(instance_id='pylint-dev__pylint-4551')
    assert module.controls_pass(task,bug,gold,log)
    assert not module.controls_pass(SimpleNamespace(instance_id='other'),bug,gold,log)
    assert not module.controls_pass(task,bug,{**gold,'resolved':False},log)
    assert not module.controls_pass(task,{**bug,'timed_out':True},gold,log)
    assert not module.controls_pass(task,bug,gold,'unrelated collection failure')
    assert module.case_name(1)=='task010-case-01-attempt-01'
    assert module.case_name(2)=='task010-case-02-attempt-02'
    assert module.case_name(3)=='task010-case-03-attempt-02'
    assert module.case_name(4)=='task010-case-04-attempt-01'
    assert module.case_name(2,'task011')=='task011-case-02-attempt-01'


def test_nonisolated_official_build_uses_existing_image_dependencies(tmp_path,monkeypatch):
    monkeypatch.syspath_prepend(str(Path('scripts').resolve()))
    spec=importlib.util.spec_from_file_location('ten_pilot', 'scripts/run_qwen36_ten_task.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    def no_docker(*args,**kwargs):raise AssertionError('No isolated build dependency download needed')
    monkeypatch.setattr(module,'docker',no_docker)
    module.prepare_wheels(SimpleNamespace(eval_script_list=['python -m pip install --no-build-isolation -e .']),tmp_path/'wheels')
    assert json.loads((tmp_path/'wheels/requirements.json').read_text())==[]
