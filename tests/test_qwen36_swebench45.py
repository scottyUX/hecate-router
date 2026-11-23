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


def fake_export(monkeypatch, tmp_path, *, version, after_line, changed='pyproject.toml'):
    from types import SimpleNamespace
    monkeypatch.syspath_prepend(str(Path('scripts').resolve()))
    import run_qwen36_swebench_pilot as pilot
    before = '[build-system]\nrequires = ["setuptools",\n  "wheel"]\n'
    after = before.replace('requires = ["setuptools",', after_line)

    def docker(*args, **kwargs):
        if args[-2:] == ('rev-parse', 'HEAD^{tree}'):
            out = 'image-tree'
        elif args[-1].endswith('^{tree}'):
            out = 'base-tree'
        elif 'diff' in args:
            out = changed + '\n'
        elif args[-1] == 'HEAD:pyproject.toml':
            out = after
        elif args[-1].endswith(':pyproject.toml'):
            out = before
        else:
            out = 'head'
        return SimpleNamespace(stdout=out, returncode=0)

    monkeypatch.setattr(pilot, 'docker', docker)
    monkeypatch.setattr(pilot.subprocess, 'check_output', lambda *a, **k: b'')
    monkeypatch.setattr(pilot, 'extract_task_archive', lambda archive, workspace: workspace.mkdir(parents=True))
    monkeypatch.setattr(pilot.subprocess, 'run', lambda *a, **k: None)
    spec = SimpleNamespace(repo='astropy/astropy', version=version, instance_image_key='img')
    return pilot.export_workspace(spec, 'base', tmp_path / 'ws')


def test_astropy_setuptools_pin_accepted_for_any_version_only_when_exact(tmp_path, monkeypatch):
    import pytest
    pinned = 'requires = ["setuptools==68.0.0",'
    for version in ('5.0', '5.1', '5.2'):
        result = fake_export(monkeypatch, tmp_path / version, version=version, after_line=pinned)
        assert result['image_setup_pin']['after'] == pinned
    with pytest.raises(ValueError):
        fake_export(monkeypatch, tmp_path / 'other-pin', version='5.1', after_line='requires = ["setuptools==69.0.0",')
    with pytest.raises(ValueError):
        fake_export(monkeypatch, tmp_path / 'extra-file', version='5.1', after_line=pinned, changed='pyproject.toml\nsetup.cfg')


def test_git_auto_gc_disabled_for_runner_git_commands(tmp_path, monkeypatch):
    import os
    import subprocess
    module = runner(monkeypatch)
    env = dict(os.environ)
    module.disable_git_auto_gc(env)
    value = subprocess.check_output(['git', 'config', 'gc.auto'], cwd=tmp_path, env=env, text=True).strip()
    assert value == '0'
