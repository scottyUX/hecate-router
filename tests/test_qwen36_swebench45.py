import hashlib
import importlib.util
import json
from pathlib import Path

import yaml

from hecate.execution.swebench45_scoring import EMPTY_PATCH_SHA, aggregate, bootstrap, labels, schedule


def runner(monkeypatch):
    monkeypatch.syspath_prepend(str(Path('scripts').resolve()))
    spec = importlib.util.spec_from_file_location('swebench45', 'scripts/run_qwen36_swebench45.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def row(resolved, *, status='completed', termination='completed', patch=b'diff', tokens=1000):
    return {'status': status, 'termination_reason': termination, 'resolved': resolved,
            'evaluation': {'status': status, 'official_resolved': resolved is True if resolved is not None else False},
            'patch_projection': {'original_sha256': hashlib.sha256(patch).hexdigest()},
            'usage_records': [{'usage': {'prompt_tokens': tokens - 10, 'completion_tokens': 10}}]}


def test_exact_scope_and_frozen_task011_protocol():
    cfg = yaml.safe_load(Path('configs/qwen36_swebench45.yaml').read_text())
    previous = yaml.safe_load(Path('configs/qwen36_gateway_recovery.yaml').read_text())
    paper = json.loads(Path(cfg['selection_manifest']).read_text())
    assert len(paper['instance_ids']) == len(set(paper['instance_ids'])) == 45
    assert paper['repo_counts']['django/django'] == 22 and paper['difficulty_counts'] == {'1-4 hours': 42, '>4 hours': 3}
    assert set(cfg['x86_ids']) <= set(paper['instance_ids']) and len(cfg['x86_ids']) == 3
    assert cfg['model'] == previous['model'] and cfg['codex'] == previous['codex'] and cfg['limits'] == previous['limits']
    for key in ('image', 'parser', 'reasoning_parser', 'message_layout', 'prompt_profile', 'editing_mode',
                'recover_model_outputs', 'max_response_recoveries'):
        assert cfg['serving'][key] == previous['serving'][key]
    assert cfg['repetitions'] == 4 and cfg['concurrency'] == 3


def test_repetition_major_schedule_and_distinct_seeds(monkeypatch):
    assert schedule(['a', 'b'], 2) == [('a', 0), ('b', 0), ('a', 1), ('b', 1)]
    module = runner(monkeypatch)
    cfg = yaml.safe_load(Path('configs/qwen36_swebench45.yaml').read_text())
    seeds = [module.attempt_config(cfg, r, 'sha256:x')['model']['sampling']['seed'] for r in range(4)]
    assert seeds == [0, 1, 2, 3]
    assert cfg['model']['sampling']['seed'] == 0  # caller's config is not mutated
    assert module.attempt_config(cfg, 2, 'sha256:x')['sandbox'] == {'image': 'sha256:x'}


def test_seed_reaches_the_request_payload(tmp_path):
    from hecate.execution.model_gateway import Gateway
    sent = []

    def transport(payload):
        sent.append(payload)
        return {'model': 'fixture', 'choices': [{'message': {'content': 'done'}, 'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2}}

    gateway = Gateway(tmp_path / 's', 'http://127.0.0.1:8136/v1', 'fixture', tmp_path, request_limit=2,
                      sampling={'temperature': 0.6, 'seed': 3}, transport=transport)
    gateway.complete({'input': [{'role': 'user', 'content': 'hi'}], 'tools': []})
    assert sent and all(p['seed'] == 3 for p in sent)


def test_paper_and_strict_labels():
    good = labels(row(True))
    assert good['paper_resolved'] and good['strict_resolved'] is True and good['valid_completion'] and good['tokens'] == 1000
    # Official verifier says unresolved while our strict grader keeps it unknown.
    unknown = labels({**row(None, status='evaluator_failure'), 'evaluation': {'status': 'evaluator_failure', 'official_resolved': False}})
    assert unknown['paper_resolved'] is False and unknown['strict_resolved'] is None
    assert not labels(row(False, patch=b''))['valid_completion']
    assert hashlib.sha256(b'').hexdigest() == EMPTY_PATCH_SHA
    assert not labels(row(False, termination='model_output_failure'))['valid_completion']
    assert not labels(row(False, status='patch_application_failure'))['valid_completion']


def test_aggregate_counts_every_scheduled_attempt():
    rows = {('a', 0): row(True), ('a', 1): row(False), ('b', 0): row(False)}
    result = aggregate(rows, ['a', 'b'], 2)
    assert result['scheduled_attempts'] == 4 and result['recorded_attempts'] == 3
    assert result['mean_paper'] == 25.0 and result['best_paper'] == 50.0
    assert result['vcr'] == 75.0 and result['tokens_per_success_m'] == 3000 / 1e6
    assert result['token_coverage'] == 75.0


def test_bootstrap_is_deterministic_and_brackets_estimate():
    rows = {(t, r): row(t in {'a', 'b'} and r == 0) for t in 'abcdefgh' for r in range(4)}
    first = bootstrap(rows, list('abcdefgh'), 4, replicates=500, seed=1)
    assert first == bootstrap(rows, list('abcdefgh'), 4, replicates=500, seed=1)
    low, high = first['best_paper_ci95']
    assert low <= 25.0 <= high


def test_halting_counts_only_infrastructure(monkeypatch):
    module = runner(monkeypatch)
    assert module.halting_failure({'status': 'infrastructure_failure'})
    assert module.halting_failure({'status': 'interrupted'})
    assert module.halting_failure({'status': 'evaluator_failure', 'evaluation': {'official_resolved': None}})
    assert not module.halting_failure({'status': 'evaluator_failure', 'evaluation': {'official_resolved': False}})
    assert not module.halting_failure({'status': 'completed', 'resolved': False})


def test_serving_concurrency_defaults_to_one():
    source = Path('scripts/serve_codex_qwen7b.py').read_text()
    assert 'cfg["serving"].get("max_num_seqs", 1)' in source


def test_control_retry_supersedes_without_overwriting(tmp_path, monkeypatch):
    module = runner(monkeypatch)
    (tmp_path / 'runs').mkdir()
    assert module.current_control(tmp_path, 'x') == (tmp_path / 'runs/task012-control-x', 0)
    (tmp_path / 'runs/task012-control-x').mkdir()
    (tmp_path / 'runs/task012-control-x-retry-01').mkdir()
    assert module.current_control(tmp_path, 'x') == (tmp_path / 'runs/task012-control-x-retry-01', 1)
    assert module.control_name('x', 2) == 'task012-control-x-retry-02'


def fake_export(monkeypatch, tmp_path, *, repo, version, replay_tree='image-tree', failing=None):
    from types import SimpleNamespace
    monkeypatch.syspath_prepend(str(Path('scripts').resolve()))
    import run_qwen36_swebench_pilot as pilot
    calls = []

    def docker(*args, check=True, **kwargs):
        calls.append(args)
        code, out = 0, 'head'
        if args[-2:] == ('rev-parse', 'HEAD^{tree}'):
            out = 'image-tree'
        elif args[-1].endswith('^{tree}'):
            out = 'base-tree'
        elif args[-1] == 'write-tree':
            out = replay_tree
        elif 'diff' in args:
            out = 'setup.py\ntox.ini\n'
        elif failing and args[-1] == failing:
            code = 1
        return SimpleNamespace(stdout=out, returncode=code)

    monkeypatch.setattr(pilot, 'docker', docker)
    monkeypatch.setattr(pilot.subprocess, 'check_output', lambda *a, **k: b'')
    monkeypatch.setattr(pilot, 'extract_task_archive', lambda archive, workspace: workspace.mkdir(parents=True))
    monkeypatch.setattr(pilot.subprocess, 'run', lambda *a, **k: None)
    spec = SimpleNamespace(repo=repo, version=version, instance_image_key='img')
    return pilot.export_workspace(spec, 'base', tmp_path / 'ws'), calls


def test_official_recipe_replay_must_reproduce_image_tree(tmp_path, monkeypatch):
    import pytest
    for repo, version in (('astropy/astropy', '5.0'), ('astropy/astropy', '5.1'), ('sphinx-doc/sphinx', '3.1'),
                          ('sphinx-doc/sphinx', '4.1'), ('sphinx-doc/sphinx', '7.2')):
        result, calls = fake_export(monkeypatch, tmp_path / f'{repo}-{version}'.replace('/', '_'), repo=repo, version=version)
        recipe = result['image_setup_pin']['recipe']
        assert recipe and all(c.startswith(('sed ', 'grep ')) for c in recipe)
        assert not any('apt-get' in ' '.join(c) for c in calls)
    with pytest.raises(ValueError):  # replayed recipe differs from the image
        fake_export(monkeypatch, tmp_path / 'differs', repo='sphinx-doc/sphinx', version='3.1', replay_tree='other-tree')
    with pytest.raises(ValueError):  # no official source-editing recipe for this repo/version
        fake_export(monkeypatch, tmp_path / 'none', repo='django/django', version='3.0')
    with pytest.raises(ValueError):  # a recipe command failed
        fake_export(monkeypatch, tmp_path / 'fails', repo='sphinx-doc/sphinx', version='3.1',
                    failing="sed -i 's/pytest/pytest -rA/' tox.ini")


def test_git_auto_gc_disabled_for_runner_git_commands(tmp_path, monkeypatch):
    import os
    import subprocess
    module = runner(monkeypatch)
    env = dict(os.environ)
    module.disable_git_auto_gc(env)
    value = subprocess.check_output(['git', 'config', 'gc.auto'], cwd=tmp_path, env=env, text=True).strip()
    assert value == '0'


def test_controls_follow_official_verifier(monkeypatch):
    module = runner(monkeypatch)
    gold = {'status': 'completed', 'resolved': True, 'official_resolved': True}
    failed = {'status': 'completed', 'resolved': False, 'official_resolved': False}
    # django-10554: the bug crashes the test runner, so the target tests never report.
    crashed = {'status': 'evaluator_failure', 'resolved': None, 'official_resolved': False, 'test_markers_found': True,
               'timed_out': False, 'error': None, 'missing_required_tests': ['test_union_with_values_list_and_order']}
    assert module.controls_pass(failed, gold) and module.controls_pass(crashed, gold)
    assert not module.controls_pass(crashed, {**gold, 'official_resolved': False})
    assert not module.controls_pass(crashed, {**gold, 'resolved': None, 'status': 'evaluator_failure'})
    assert not module.controls_pass({**crashed, 'official_resolved': None}, gold)
    assert not module.controls_pass({**crashed, 'timed_out': True}, gold)
    assert not module.controls_pass({**crashed, 'error': 'Offline setup step failed; inspect test_output.txt'}, gold)
    assert not module.controls_pass({**crashed, 'test_markers_found': False}, gold)
    assert not module.controls_pass({**failed, 'official_resolved': True, 'resolved': True}, gold)


def test_excluded_tasks_are_never_scheduled_but_stay_in_all_45(monkeypatch):
    module = runner(monkeypatch)
    cfg = yaml.safe_load(Path('configs/qwen36_swebench45.yaml').read_text())
    ids = json.loads(Path(cfg['selection_manifest']).read_text())['instance_ids']
    runnable = module.runnable(cfg, ids)
    assert len(runnable) == 40
    assert not set(runnable) & {'sphinx-doc__sphinx-7590', 'sphinx-doc__sphinx-8548', 'pydata__xarray-3993'}
    rows = {(iid, r): row(True) for iid in runnable for r in range(4)}
    assert aggregate(rows, ids, 4)['best_paper'] == 100 * 40 / 45


def test_saved_records_survive_scheduling_scope_changes(tmp_path, monkeypatch):
    import pytest
    from hecate.execution.codex_artifacts import create_run, finish_run
    module = runner(monkeypatch)
    cfg = yaml.safe_load(Path('configs/qwen36_swebench45.yaml').read_text())
    before = {k: v for k, v in cfg.items() if k != 'excluded_ids'}
    p = create_run(tmp_path, 'control', before, {'git_commit': 'x'})
    finish_run(p, {'status': 'control_passed'})
    assert module.valid_saved(p, cfg)['status'] == 'control_passed'
    changed = {**cfg, 'model': {**cfg['model'], 'context_tokens': 32768}}
    with pytest.raises(ValueError):
        module.valid_saved(p, changed)
