#!/usr/bin/env python3
"""TASK-012: Qwen3.6 + Codex on all of SWE-bench-45, four attempts per task.

Modes (Spark): preflight -> gate -> schedule (spawns one `attempt` process per
task/repetition) -> score. Each attempt runs in its own process because the
official SWE-bench builders and grader write relative to the working directory.
"""
from __future__ import annotations
import argparse
import ast
import copy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import yaml
from hecate.execution.codex_artifacts import create_run, finish_run, checksums
from hecate.execution.patch_evaluation import evaluation_patch, outcome_axes
from hecate.execution.swebench45_scoring import aggregate, bootstrap, schedule, labels
from run_codex_baseline import execute, fixtures, init_fixture
from run_qwen36_swebench_pilot import grade, export_workspace
from run_qwen36_ten_task import prepare_wheels

SOURCE = Path(__file__).resolve().parents[1]
GATE = 'task012-native-gate-run-01'


SCHEDULING_KEYS = {'excluded_ids', 'concurrency', 'checkpoint_attempts'}


def protocol(cfg):
    """Settings that define an attempt or control; scheduling scope may change between checkpoints."""
    return {k: v for k, v in cfg.items() if k not in SCHEDULING_KEYS}


def valid_saved(path, cfg):
    if checksums(path) != json.loads((path / 'checksums.json').read_text()):
        raise ValueError('Saved artifact checksum mismatch')
    if protocol(json.loads((path / 'manifest.json').read_text())['config']) != protocol(cfg):
        raise ValueError('Saved protocol configuration differs')
    return json.loads((path / 'results.json').read_text())


def runnable(cfg, ids):
    """ARM tasks with usable controls; excluded tasks still count as unresolved in all_45."""
    return [x for x in ids if x not in cfg['x86_ids'] and x not in cfg['excluded_ids']]


def control_name(iid, retry=0):
    return f'task012-control-{iid}' + (f'-retry-{retry:02d}' if retry else '')


def current_control(root, iid):
    """Latest control record; failed records stay in place and are superseded, never rerun."""
    retry = 0
    while (root / 'runs' / control_name(iid, retry + 1)).exists():
        retry += 1
    return root / 'runs' / control_name(iid, retry), retry


def attempt_name(iid, rep):
    return f'task012-{iid}-rep{rep}'


def attempt_config(cfg, rep, image_id):
    """Distinct seed per repetition; a shared seed would replay one trajectory."""
    effective = copy.deepcopy(cfg)
    effective['model']['sampling']['seed'] = rep
    effective['sandbox'] = {'image': image_id}
    return effective


def controls_pass(bug, gold):
    """Amendment 2: the paper's official verifier decides the negative control.

    The reference patch must pass under both the strict and official graders. The
    unpatched run must be officially unresolved without timeout or setup error;
    required tests left without a status (the bug crashed collection or the test
    runner, e.g. pylint-4551, django-10554) count as not passing, as officially."""
    if gold.get('status') != 'completed' or gold.get('resolved') is not True or gold.get('official_resolved') is not True:
        return False
    if bug.get('official_resolved') is not False or bug.get('timed_out') or bug.get('error'):
        return False
    if bug.get('status') == 'completed':
        return bug.get('resolved') is False
    return (bug.get('status') == 'evaluator_failure' and bug.get('test_markers_found') is True
            and bool(bug.get('missing_required_tests')))


def halting_failure(row):
    """Infrastructure only. A patch the official verifier scores is not one."""
    if row.get('status') in {'infrastructure_failure', 'interrupted'} or row.get('execution_infrastructure_failure'):
        return True
    return row.get('status') == 'evaluator_failure' and (row.get('evaluation') or {}).get('official_resolved') is None


def load(args):
    cfg = yaml.safe_load(args.config.read_text())
    if cfg.get('run_prefix') != 'task012' or cfg['model']['id'] != 'Qwen/Qwen3.6-35B-A3B':
        raise ValueError('Unexpected TASK-012 configuration')
    parent = json.loads((SOURCE / cfg['selection_manifest']).read_text())
    ids = parent['instance_ids']
    if len(ids) != 45 or len(set(ids)) != 45 or not set(cfg['x86_ids']) | set(cfg['excluded_ids']) <= set(ids):
        raise ValueError('Requires the exact frozen SWE-bench-45 manifest')
    if importlib.metadata.version('swebench') != cfg['evaluator']['version']:
        raise ValueError('Evaluator version mismatch')
    root = args.root.resolve()
    dataset = root / 'verified.parquet'
    if hashlib.sha256(dataset.read_bytes()).hexdigest() != parent['parquet_sha256']:
        raise ValueError('Dataset changed')
    import pyarrow.parquet as pq
    tasks = {x['instance_id']: x for x in pq.read_table(dataset).to_pylist()}
    return cfg, parent, ids, root, tasks


def codex_binary(root, cfg):
    binary = root / cfg['codex']['binary']
    if subprocess.check_output([str(binary), '--version'], text=True).strip() != 'codex-cli ' + cfg['codex']['version']:
        raise ValueError('Codex version differs')
    return binary


def new_run(root, run_id, cfg, args, purpose, parent, extra=None):
    binary = root / cfg['codex']['binary']
    p = create_run(root / 'runs', run_id, cfg, {
        'git_commit': os.environ['HECATE_CODE_SHA'], 'purpose': purpose, 'argv': sys.argv,
        'dataset_sha256': parent['parquet_sha256'], 'provider_api_cost_usd': 0,
        'codex_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(), **(extra or {})})
    snap = p / 'source_snapshot'; snap.mkdir()
    for f in [Path(__file__), args.config.resolve(), SOURCE / cfg['selection_manifest'],
              *[SOURCE / 'scripts' / n for n in ('run_codex_baseline.py', 'gateway_recovery_fixture.py',
                                                 'run_qwen36_swebench_pilot.py', 'run_qwen36_ten_task.py')],
              *sorted((SOURCE / 'src/hecate/execution').glob('*.py'))]:
        shutil.copy2(f, snap / f.name)
    (p / 'dependencies.txt').write_text(subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True))
    return p


def test_spec(cfg, task):
    from swebench.harness.test_spec.test_spec import make_test_spec
    tag = cfg['evaluator']['image_tag']
    spec = make_test_spec(task, arch=cfg['evaluator']['arch'], base_image_tag=tag, env_image_tag=tag, instance_image_tag=tag)
    if task['instance_id'] == 'scikit-learn__scikit-learn-25102':
        # TASK-011: retain the official legacy --no-use-pep517 recipe with compatible tools.
        spec.env_script_list.append('python -m pip install pip==24.0 setuptools==68.0.0')
    return spec


def resources_ok(min_disk_gib=100, min_available_gib=8):
    free = shutil.disk_usage('/').free / 1024**3
    available = next(int(x.split()[1]) for x in Path('/proc/meminfo').read_text().splitlines()
                     if x.startswith('MemAvailable:')) / 1024**2
    return free >= min_disk_gib and available >= min_available_gib, {'disk_free_gib': free, 'mem_available_gib': available}


def preflight(args):
    """Phase A: official image build, export check and clean controls. No model calls."""
    cfg, parent, ids, root, tasks = load(args)
    import docker as docker_sdk
    from swebench.harness.docker_build import build_env_images, build_instance_image
    summary = []
    for iid in [x for x in ids if x not in cfg['x86_ids']]:
        if args.only and iid not in args.only:
            continue
        p, retry = current_control(root, iid)
        supersedes = None
        if p.exists():
            if not (p / 'checksums.json').exists():
                finish_run(p, {'instance_id': iid, 'status': 'interrupted', 'error': 'Preflight interrupted; review before retry'})
            saved = valid_saved(p, cfg)
            if iid not in (args.retry or []) or saved.get('status') == 'control_passed':
                summary.append(saved); continue
            supersedes, retry = p.name, retry + 1
        for _ in range(60):
            ok, usage = resources_ok()
            if ok: break
            print(json.dumps({'waiting_for_resources': usage}), flush=True); time.sleep(60)
        else:
            raise SystemExit(f'Insufficient disk or memory for preflight: {usage}')
        p = new_run(root, control_name(iid, retry), cfg, args, 'Official image build, export check and clean controls; no model calls',
                    parent, {'supersedes': supersedes} if supersedes else None)
        old = Path.cwd(); os.chdir(p)
        try:
            spec = test_spec(cfg, tasks[iid])
            (p / 'test-spec.json').write_text(json.dumps(spec.__dict__, indent=2) + '\n')
            client = docker_sdk.from_env(); _, failed = build_env_images(client, [spec], max_workers=1)
            if failed: raise RuntimeError('Official task environment build failed')
            build_instance_image(spec, client, logger=None, nocache=False)
            image = client.images.get(spec.instance_image_key)
            (p / 'image.json').write_text(json.dumps(image.attrs, indent=2) + '\n')
            provenance = export_workspace(spec, tasks[iid]['base_commit'], p / 'export-check')
            shutil.rmtree(p / 'export-check')
            prepare_wheels(spec, p / 'wheels')
            bug = grade(spec, '', p / 'unpatched', cfg['evaluator']['timeout_s'], wheelhouse=p / 'wheels')
            gold = grade(spec, tasks[iid]['patch'], p / 'gold', cfg['evaluator']['timeout_s'], wheelhouse=p / 'wheels')
            passed = controls_pass(bug, gold)
            row = {'instance_id': iid, 'status': 'control_passed' if passed else 'control_failure',
                   'image_id': image.id, 'image_key': spec.instance_image_key, 'export': provenance,
                   'unpatched': {k: bug.get(k) for k in ('status', 'resolved', 'official_resolved', 'error')},
                   'gold': {k: gold.get(k) for k in ('status', 'resolved', 'official_resolved', 'error')}}
        except Exception as exc:
            row = {'instance_id': iid, 'status': 'control_failure', 'error': str(exc)}
        finally:
            os.chdir(old)
        finish_run(p, row); summary.append(row)
        print(json.dumps({k: row.get(k) for k in ('instance_id', 'status', 'error')}), flush=True)
    (root / 'preflight-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    failed = [r['instance_id'] for r in summary if r.get('status') != 'control_passed']
    print(json.dumps({'controls': len(summary), 'failed': failed}), flush=True)


def gate(args):
    """TASK-011 native gate unchanged: recovery, read/edit/repair and apply_patch."""
    cfg, parent, ids, root, tasks = load(args)
    binary = codex_binary(root, cfg); tools = binary.parent.parent
    p = root / 'runs' / GATE
    if p.exists():
        if not valid_saved(p, cfg).get('passed'): raise ValueError('Prior gate failed; no silent rerun')
        return
    p = new_run(root, GATE, cfg, args, 'Native prompt, recovery, read/edit/repair and patch-tool gate', parent)
    try:
        from gateway_recovery_fixture import recovery_fixture
        recovery_fixture(p, cfg, tools, binary)
        recovery_fixture(p, cfg, tools, binary, live=True)
        rows = fixtures(p, cfg, tools, binary)
        if len(rows) != 3 or not all(x['passed'] for x in rows): raise RuntimeError('Native capability gate failed')
        workspace = p / 'workspace-patch'
        init_fixture(workspace, {'source.py': 'def add(a, b):\n    return a - b\n'})
        result = execute(workspace, p / 'patch-tool', 'Inspect source.py with exec_command. Use apply_patch to change add so it returns a + b. Use the actual apply_patch tool, then finish.', cfg, tools, binary, fixture=True)
        events = [json.loads(x) for x in (p / 'patch-tool/codex_events.jsonl').read_text().splitlines()]
        changed = any(x.get('type') == 'item.completed' and x.get('item', {}).get('type') == 'file_change' and x['item'].get('status') == 'completed' for x in events)
        correct = ast.dump(ast.parse((workspace / 'source.py').read_text())) == ast.dump(ast.parse('def add(a, b):\n    return a + b\n'))
        if not changed or not correct or result['termination_reason'] != 'completed': raise RuntimeError('Native apply_patch gate failed; no shell-only fallback')
        finish_run(p, {'passed': True, 'fixtures': rows, 'patch_tool': result, 'provider_api_cost_usd': 0})
    except BaseException as exc:
        finish_run(p, {'passed': False, 'error': str(exc), 'provider_api_cost_usd': 0}); raise


def attempt(args):
    """One task, one repetition, fresh workspace. Never reruns a saved attempt."""
    cfg, parent, ids, root, tasks = load(args)
    iid, rep = args.instance, args.rep
    if iid not in runnable(cfg, ids) or not 0 <= rep < cfg['repetitions']:
        raise ValueError('Attempt outside the ARM SWE-bench-45 schedule')
    binary = codex_binary(root, cfg); tools = binary.parent.parent
    if not valid_saved(root / 'runs' / GATE, cfg).get('passed'): raise ValueError('Passing native gate required')
    control_dir, _ = current_control(root, iid)
    control = valid_saved(control_dir, cfg)
    if control.get('status') != 'control_passed': raise ValueError('Clean controls required before inference')
    p = new_run(root, attempt_name(iid, rep), cfg, args, 'SWE-bench-45 attempt; no training instrumentation', parent,
                {'instance_id': iid, 'repetition': rep, 'seed': rep, 'control_run': control_dir.name})
    os.chdir(p)
    try:
        import docker as docker_sdk
        spec = test_spec(cfg, tasks[iid])
        if docker_sdk.from_env().images.get(spec.instance_image_key).id != control['image_id']:
            raise RuntimeError('Task image changed since its controls passed')
        (p / 'test-spec.json').write_text(json.dumps(spec.__dict__, indent=2) + '\n')
        wheels = control_dir / 'wheels'
        provenance = export_workspace(spec, tasks[iid]['base_commit'], p / 'workspace')
        (p / 'public-task-provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
        effective = attempt_config(cfg, rep, control['image_id'])
        result = execute(p / 'workspace', p / 'agent', tasks[iid]['problem_statement'], effective, tools, binary, fixture=False)
        patch = (p / 'agent/patch.diff').read_text(); projected, projection = evaluation_patch(patch, result['test_modifications'])
        (p / 'evaluation.diff').write_text(projected)
        evaluated = grade(spec, projected, p / 'evaluation', cfg['evaluator']['timeout_s'], wheelhouse=wheels)
        row = {**result, 'instance_id': iid, 'repetition': rep, 'seed': rep, 'status': evaluated['status'],
               'resolved': evaluated['resolved'], 'evaluation': evaluated, 'patch_projection': projection}
        row.update(outcome_axes(row))
    except Exception as exc:
        row = {'instance_id': iid, 'repetition': rep, 'seed': rep, 'status': 'infrastructure_failure', 'resolved': None, 'error': str(exc)}
    finish_run(p, row)
    print(json.dumps({'instance_id': iid, 'repetition': rep, 'status': row['status'], 'official_resolved': (row.get('evaluation') or {}).get('official_resolved')}), flush=True)


def schedule_mode(args):
    """Run at most one checkpoint of new attempts, `concurrency` at a time."""
    cfg, parent, ids, root, tasks = load(args)
    if not valid_saved(root / 'runs' / GATE, cfg).get('passed'): raise ValueError('Passing native gate required')
    arm = runnable(cfg, ids)
    for iid in arm:
        if valid_saved(current_control(root, iid)[0], cfg).get('status') != 'control_passed':
            raise ValueError(f'Controls not passed for {iid}; resolve preflight first')
    pending, finished = [], []
    for iid, rep in schedule(arm, cfg['repetitions']):
        p = root / 'runs' / attempt_name(iid, rep)
        if not p.exists():
            pending.append((iid, rep)); continue
        if not (p / 'checksums.json').exists():
            finish_run(p, {'instance_id': iid, 'repetition': rep, 'status': 'interrupted', 'resolved': None,
                           'error': 'Attempt interrupted; never regenerated'})
        finished.append(p)
    unsynced = [p.name for p in finished if not (p / 'sync_receipt.json').exists()]
    if unsynced:
        raise ValueError(f'{len(unsynced)} attempts lack a verified off-Spark copy, e.g. {unsynced[0]}')
    batch = pending[:args.limit or cfg['checkpoint_attempts']]
    running, completed = {}, []
    env = {**os.environ, 'PYTHONPATH': os.environ.get('PYTHONPATH', 'src')}
    logs = root / 'logs'; logs.mkdir(exist_ok=True)
    halt = False
    while batch or running:
        while batch and not halt and len(running) < cfg['concurrency']:
            iid, rep = batch.pop(0)
            log = (logs / f'{attempt_name(iid, rep)}.log').open('w')
            proc = subprocess.Popen([sys.executable, '-u', str(Path(__file__)), 'attempt', '--root', str(root),
                                     '--config', str(args.config.resolve()), '--instance', iid, '--rep', str(rep)],
                                    cwd=SOURCE, env=env, stdout=log, stderr=subprocess.STDOUT)
            running[proc] = (iid, rep, log)
        if halt and not running: break
        time.sleep(10)
        for proc in [x for x in running if x.poll() is not None]:
            iid, rep, log = running.pop(proc); log.close()
            p = root / 'runs' / attempt_name(iid, rep)
            if not p.exists():
                # Failed before creating its run, so before any model call; see its log.
                row = {'instance_id': iid, 'repetition': rep, 'status': 'infrastructure_failure',
                       'error': f'Attempt process exited {proc.returncode} before creating its run'}
            else:
                if not (p / 'checksums.json').exists():
                    finish_run(p, {'instance_id': iid, 'repetition': rep, 'status': 'interrupted', 'resolved': None,
                                   'error': f'Attempt process exited {proc.returncode} before finishing'})
                row = json.loads((p / 'results.json').read_text())
            completed.append(row)
            print(json.dumps({'instance_id': iid, 'repetition': rep, 'status': row.get('status'),
                              'official_resolved': (row.get('evaluation') or {}).get('official_resolved')}), flush=True)
            if len(completed) >= 3 and all(halting_failure(r) for r in completed[-3:]):
                halt = True
        if halt: batch = []
    left = len(pending) - len(completed)
    print(json.dumps({'completed_this_checkpoint': len(completed), 'remaining': left, 'halted': halt}), flush=True)
    if halt: raise SystemExit('Halted after 3 consecutive infrastructure failures')


def score(args):
    cfg, parent, ids, root, tasks = load(args)
    rows = {}
    for iid in ids:
        for rep in range(cfg['repetitions']):
            p = root / 'runs' / attempt_name(iid, rep)
            if (p / 'checksums.json').exists():
                rows[(iid, rep)] = json.loads((p / 'results.json').read_text())
    arm = [x for x in ids if x not in cfg['x86_ids']]
    by_repo = {}
    for iid in ids:
        by_repo.setdefault(tasks[iid]['repo'], []).append(iid)
    report = {
        'paper': {'mean': 26.67, 'best': 44.44, 'vcr': 98.33, 'token_load_m': 4.770, 'tokens_per_success_m': 17.889},
        'all_45': {**aggregate(rows, ids, cfg['repetitions']), **bootstrap(rows, ids, cfg['repetitions'])},
        'arm_42': {**aggregate(rows, arm, cfg['repetitions']), **bootstrap(rows, arm, cfg['repetitions'])},
        'runnable_40': {**aggregate(rows, runnable(cfg, ids), cfg['repetitions']),
                        **bootstrap(rows, runnable(cfg, ids), cfg['repetitions'])},
        'excluded': {'x86_pending': cfg['x86_ids'], 'controls_unusable': cfg['excluded_ids']},
        'by_repo': {repo: aggregate(rows, members, cfg['repetitions']) for repo, members in sorted(by_repo.items())},
        'per_attempt': [{'instance_id': i, 'repetition': r, 'status': rows[(i, r)].get('status'),
                         'termination_reason': rows[(i, r)].get('termination_reason'), **labels(rows[(i, r)])}
                        for i, r in sorted(rows)],
    }
    (root / 'task012-score.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('paper', 'all_45', 'arm_42', 'runnable_40')}, indent=2))


def disable_git_auto_gc(env=os.environ):
    """Workspace export commits large repos; a detached `git gc --auto` then races
    deletion and checksumming (django-10554 preflight). Inherited by attempt processes."""
    env.update(GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='gc.auto', GIT_CONFIG_VALUE_0='0')


def main():
    disable_git_auto_gc()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('mode', choices=['preflight', 'gate', 'attempt', 'schedule', 'score'])
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--config', type=Path, default=SOURCE / 'configs/qwen36_swebench45.yaml')
    ap.add_argument('--only', nargs='*', help='preflight: restrict to these instance IDs')
    ap.add_argument('--retry', nargs='*', help='preflight: supersede these failed control records after an approved fix')
    ap.add_argument('--instance'); ap.add_argument('--rep', type=int)
    ap.add_argument('--limit', type=int, help='schedule: new attempts this checkpoint (default from config)')
    args = ap.parse_args()
    {'preflight': preflight, 'gate': gate, 'attempt': attempt, 'schedule': schedule_mode, 'score': score}[args.mode](args)


if __name__ == '__main__':
    main()
