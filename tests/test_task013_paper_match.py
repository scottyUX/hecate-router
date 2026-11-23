"""TASK-013: SWE-bench-45 paper-match protocol removes our own deadlines and caps."""
import importlib.util
import sys
from pathlib import Path

import httpx
import yaml

from hecate.execution.codex_session import UNLIMITED_IDLE_MS, config_text, run_process
from hecate.execution.model_gateway import Gateway

CONFIG = Path('configs/qwen36_swebench45_paper_match.yaml')


def load_script(monkeypatch, name, path):
    monkeypatch.syspath_prepend(str(Path('scripts').resolve()))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def test_paper_match_config_drops_our_caps_and_keeps_scope():
    cfg = yaml.safe_load(CONFIG.read_text())
    old = yaml.safe_load(Path('configs/qwen36_swebench45.yaml').read_text())
    assert cfg['model']['sampling'] == {'seed': 0}
    assert cfg['limits']['task_wall_s'] is None
    assert cfg['limits']['request_timeout_s'] is None
    assert cfg['limits']['command_timeout_s'] is None
    assert cfg['excluded_ids'] == []
    assert cfg['serving']['generation_config'] == 'auto'
    assert cfg['serving']['enable_prefix_caching'] and not cfg['serving']['enforce_eager']
    assert cfg['execution_protocol'] == 'paper-match-v3'
    for key in ('selection_manifest', 'x86_ids', 'repetitions', 'codex', 'evaluator'):
        assert cfg[key] == old[key]
    assert cfg['model']['id'] == old['model']['id'] and cfg['model']['revision'] == old['model']['revision']


def test_sphinx_tasks_get_official_docutils_pin(monkeypatch):
    module = load_script(monkeypatch, 'swebench45_t13', 'scripts/run_qwen36_swebench45.py')
    for iid in ('sphinx-doc__sphinx-7590', 'sphinx-doc__sphinx-8548'):
        assert module.ENV_PINS[iid] == 'docutils==0.21.2'
    assert module.ENV_PINS['scikit-learn__scikit-learn-25102'] == 'pip==24.0 setuptools==68.0.0'


def test_codex_idle_timeout_outlasts_unbounded_requests(monkeypatch):
    module = load_script(monkeypatch, 'baseline_t13', 'scripts/run_codex_baseline.py')
    assert module.idle_timeout_ms(None) == UNLIMITED_IDLE_MS
    assert module.idle_timeout_ms(600) == 600000
    assert f'stream_idle_timeout_ms = {UNLIMITED_IDLE_MS}' in config_text('m', 262144, stream_idle_timeout_ms=UNLIMITED_IDLE_MS)
    assert 'stream_idle_timeout_ms = 600000' in config_text('m', 262144)


def test_run_process_without_wall_cap_runs_to_completion(tmp_path):
    result = run_process([sys.executable, '-c', 'import time; time.sleep(0.3)'], tmp_path, None)
    assert result['termination_reason'] != 'budget_exhausted' and result['exit_code'] == 0


def test_gateway_without_request_timeout_has_no_read_deadline(tmp_path, monkeypatch):
    seen = {}

    class Client:
        def __init__(self, *, timeout, trust_env):
            seen['timeout'] = timeout
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def post(self, url, json):
            return httpx.Response(200, json={'ok': True}, request=httpx.Request('POST', url))

    monkeypatch.setattr(httpx, 'Client', Client)
    gateway = Gateway(tmp_path / 's.sock', 'http://127.0.0.1:1/v1', 'm', tmp_path,
                      request_limit=1, sampling={}, timeout_s=None)
    assert gateway._post({}) == {'ok': True}
    assert seen['timeout'].read is None and seen['timeout'].connect == 30


def test_relay_has_no_read_deadline():
    source = Path('src/hecate/execution/codex_relay.py').read_text()
    assert 'UnixConnection("localhost", timeout=None)' in source and 'timeout=600' not in source


def test_empty_new_scratch_test_file_is_excluded_not_fatal():
    from hecate.execution.patch_evaluation import evaluation_patch
    source = ('diff --git a/django/db/models/base.py b/django/db/models/base.py\n'
              'index 1111111..2222222 100644\n--- a/django/db/models/base.py\n+++ b/django/db/models/base.py\n'
              '@@ -1 +1 @@\n-a\n+b\n')
    scratch = ('diff --git a/django/db/test_writable.py b/django/db/test_writable.py\n'
               'new file mode 100644\nindex 0000000..e69de29\n')
    derived, projection = evaluation_patch(source + scratch, ['django/db/test_writable.py'])
    assert derived == source


def test_existing_protected_file_edit_still_refused():
    import pytest
    from hecate.execution.patch_evaluation import evaluation_patch
    edit = ('diff --git a/tests/test_x.py b/tests/test_x.py\nindex 1111111..2222222 100644\n'
            '--- a/tests/test_x.py\n+++ b/tests/test_x.py\n@@ -1 +1 @@\n-a\n+b\n')
    with pytest.raises(ValueError, match='cannot be projected'):
        evaluation_patch(edit, ['tests/test_x.py'])
