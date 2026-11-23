#!/usr/bin/env python3
"""TASK-010: fixed ten-task pilot, native prompt gate and five-task checkpoints."""
from __future__ import annotations
import argparse
import ast
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import fcntl
import tomllib
import yaml
from hecate.execution.codex_artifacts import create_run, finish_run, checksums
from hecate.execution.patch_evaluation import evaluation_patch, outcome_axes
from hecate.execution.codex_pilot import should_halt
from run_codex_baseline import execute, fixtures, init_fixture
from run_qwen36_swebench_pilot import grade, export_workspace
from hecate.execution.task_environment import docker


def valid_saved(path, config):
    if checksums(path) != json.loads((path/'checksums.json').read_text()):
        raise ValueError('Saved artifact checksum mismatch')
    if json.loads((path/'manifest.json').read_text())['config'] != config:
        raise ValueError('Saved configuration differs')
    return json.loads((path/'results.json').read_text())


def case_name(index):
    # Only these two setup-only records are superseded. Neither called the model.
    return f'task010-case-{index:02d}-attempt-{2 if index in (2,3) else 1:02d}'


def controls_pass(spec, bug, gold, unpatched_log):
    if gold.get('status') != 'completed' or gold.get('resolved') is not True:
        return False
    if bug.get('status') == 'completed' and bug.get('resolved') is False:
        return True
    # This task's test patch imports a newly introduced API at collection time.
    # Accept this known negative baseline only; candidate grading stays strict.
    return (spec.instance_id == 'pylint-dev__pylint-4551'
            and bug.get('status') == 'evaluator_failure'
            and bug.get('official_resolved') is False
            and bug.get('test_markers_found') is True
            and not bug.get('timed_out')
            and bool(bug.get('missing_required_tests'))
            and 'ERROR collecting tests/unittest_pyreverse_writer.py' in unpatched_log
            and "ImportError: cannot import name 'get_annotation' from 'pylint.pyreverse.utils'" in unpatched_log)


def prepare_wheels(spec, directory):
    """Prepare public build dependencies with the task's own Python version."""
    directory.mkdir()
    result=docker('run','--rm','--network','none','--entrypoint','git',spec.instance_image_key,
                  '-C','/testbed','show','HEAD:pyproject.toml',check=False)
    requirements=['setuptools>=40.8.0','wheel']
    if result.returncode==0:
        requirements=tomllib.loads(result.stdout).get('build-system',{}).get('requires',requirements)
    (directory/'requirements.json').write_text(json.dumps(requirements,indent=2)+'\n')
    # Network is available only to this preparation container, never the agent
    # or evaluator. Download wheels without executing source build hooks.
    fetched=docker('run','--rm','-v',str(directory.resolve())+':/wheelhouse',
                  '--entrypoint','/opt/miniconda3/envs/testbed/bin/python',spec.instance_image_key,
                  '-m','pip','download','--only-binary=:all:','--dest','/wheelhouse',*requirements,
                  timeout=900,check=False)
    (directory/'download.log').write_text(fetched.stdout+fetched.stderr)
    if fetched.returncode:raise RuntimeError('Offline build-dependency preparation failed')
    (directory/'wheel-sha256.json').write_text(json.dumps({f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in directory.glob('*.whl')},indent=2)+'\n')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('mode',choices=['gate','batch'])
    ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--config',type=Path,default=Path('configs/qwen36_ten_task_pilot.yaml'))
    ap.add_argument('--batch',type=int,choices=[1,2],default=1)
    args=ap.parse_args()
    root=args.root.resolve(); source=Path(__file__).resolve().parents[1]
    cfg=yaml.safe_load(args.config.read_text())
    selection=json.loads((source/cfg['pilot_selection']).read_text())
    parent=json.loads((source/cfg['selection_manifest']).read_text())
    ids=selection['instance_ids']
    if len(ids)!=len(set(ids)) or len(ids)!=10 or not set(ids)<=set(parent['instance_ids']):
        raise ValueError('Requires exactly ten distinct frozen paper tasks')
    if cfg['model']['id']!='Qwen/Qwen3.6-35B-A3B' or cfg['model']['context_tokens']!=262144 or cfg['serving']['prompt_profile']!='native' or cfg['serving']['editing_mode']!='patch':
        raise ValueError('Unexpected pilot configuration')
    if importlib.metadata.version('swebench')!='4.1.0': raise ValueError('Evaluator version mismatch')
    dataset=root/'verified.parquet'
    if hashlib.sha256(dataset.read_bytes()).hexdigest()!=parent['parquet_sha256']:
        raise ValueError('Dataset changed')
    import pyarrow.parquet as pq
    tasks={x['instance_id']:x for x in pq.read_table(dataset).to_pylist()}
    binary=root/cfg['codex']['binary']; tools=binary.parent.parent
    if subprocess.check_output([str(binary),'--version'],text=True).strip()!='codex-cli 0.164.0':
        raise ValueError('Codex version differs')
    lock=(root/'controller.lock').open('w'); fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    def new(run_id, purpose):
        p=create_run(root/'runs',run_id,cfg,{'git_commit':os.environ['HECATE_CODE_SHA'],'purpose':purpose,'argv':sys.argv,'selection':selection,'dataset_sha256':parent['parquet_sha256'],'provider_api_cost_usd':0,'codex_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()})
        snap=p/'source_snapshot';snap.mkdir()
        for f in [Path(__file__), args.config.resolve(), source/cfg['pilot_selection'], source/cfg['selection_manifest'], source/'scripts/run_codex_baseline.py',source/'scripts/run_qwen36_swebench_pilot.py',*sorted((source/'src/hecate/execution').glob('*.py'))]:
            shutil.copy2(f,snap/f.name)
        (p/'dependencies.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True))
        return p
    gate=root/'runs/task010-native-gate-run-02'
    if args.mode=='gate':
        if gate.exists():
            if not valid_saved(gate,cfg).get('passed'):raise ValueError('Prior gate failed; no silent rerun')
            return
        p=new(gate.name,'Native prompt, read/edit/repair/isolation and patch-tool gate')
        try:
            rows=fixtures(p,cfg,tools,binary)
            if len(rows)!=3 or not all(x['passed'] for x in rows):raise RuntimeError('Native capability gate failed')
            workspace=p/'workspace-patch'
            init_fixture(workspace,{'source.py':'def add(a, b):\n    return a - b\n'})
            result=execute(workspace,p/'patch-tool','Inspect source.py with exec_command. Use apply_patch to change add so it returns a + b. Use the actual apply_patch tool, then finish.',cfg,tools,binary,fixture=True)
            events=[json.loads(x) for x in (p/'patch-tool/codex_events.jsonl').read_text().splitlines()]
            changed=any(x.get('type')=='item.completed' and x.get('item',{}).get('type')=='file_change' and x['item'].get('status')=='completed' for x in events)
            code=(workspace/'source.py').read_text()
            correct=ast.dump(ast.parse(code))==ast.dump(ast.parse('def add(a, b):\n    return a + b\n'))
            if not changed or not correct or result['termination_reason']!='completed':raise RuntimeError('Native apply_patch gate failed; no shell-only fallback')
            finish_run(p,{'passed':True,'fixtures':rows,'patch_tool':result,'provider_api_cost_usd':0})
        except BaseException as exc:
            finish_run(p,{'passed':False,'error':str(exc),'provider_api_cost_usd':0});raise
        return
    if not valid_saved(gate,cfg).get('passed'): raise ValueError('Passing native gate required')
    if args.batch==2:
        for n in range(1,6):
            p=root/'runs'/case_name(n);valid_saved(p,cfg)
            if json.loads((p/'sync_receipt.json').read_text()).get('status')!='verified_off_spark':
                raise ValueError('Five-attempt review/off-Spark checkpoint incomplete')
    rows=[]
    for index in range((args.batch-1)*5,args.batch*5):
        iid=ids[index];name=case_name(index+1);p=root/'runs'/name
        if p.exists():
            if not (p/'checksums.json').exists():
                finish_run(p,{'instance_id':iid,'status':'interrupted','resolved':None,'error':'Prior attempt interrupted; never regenerated automatically'})
            row=valid_saved(p,cfg);rows.append(row)
            if row.get('status') in {'control_failure','interrupted'}:break
            continue
        p=new(name,'One fixed SWE-bench-45 task; one attempt; no training instrumentation')
        if index+1 in (2,3):
            previous=root/f'runs/task010-case-{index+1:02d}-attempt-01'
            prior=valid_saved(previous,cfg)
            if prior.get('resolved') is not None or (previous/'agent').exists():
                raise ValueError('Setup resume may not regenerate model attempts')
            (p/'supersedes-setup.json').write_text(json.dumps({'run_id':previous.name,'reason':'Authorized Astropy/Pylint harness correction; no prior model call'},indent=2)+'\n')
        old=Path.cwd();os.chdir(p)
        try:
            import docker as docker_sdk
            from swebench.harness.test_spec.test_spec import make_test_spec
            from swebench.harness.docker_build import build_env_images,build_instance_image
            tag='task009' if iid=='django__django-16560' else 'task010'
            spec=make_test_spec(tasks[iid],arch='arm64',base_image_tag=tag,env_image_tag=tag,instance_image_tag=tag)
            (p/'test-spec.json').write_text(json.dumps(spec.__dict__,indent=2)+'\n')
            client=docker_sdk.from_env();_,failed=build_env_images(client,[spec],max_workers=1)
            if failed:raise RuntimeError('Official task environment build failed')
            build_instance_image(spec,client,logger=None,nocache=False)
            image=client.images.get(spec.instance_image_key)
            (p/'image.json').write_text(json.dumps(image.attrs,indent=2)+'\n')
            prepare_wheels(spec,p/'wheels')
            bug=grade(spec,'',p/'unpatched',900,wheelhouse=p/'wheels')
            gold=grade(spec,tasks[iid]['patch'],p/'gold',900,wheelhouse=p/'wheels')
            if not controls_pass(spec,bug,gold,(p/'unpatched/test_output.txt').read_text()):
                raise RuntimeError('Official clean offline controls did not pass')
        except Exception as exc:
            row={'instance_id':iid,'status':'control_failure','resolved':None,'error':str(exc)}
            finish_run(p,row);rows.append(row);os.chdir(old);break
        try:
            provenance=export_workspace(spec,tasks[iid]['base_commit'],p/'workspace')
            (p/'public-task-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
            effective={**cfg,'sandbox':{'image':image.id}}
            result=execute(p/'workspace',p/'agent',tasks[iid]['problem_statement'],effective,tools,binary,fixture=False)
            patch=(p/'agent/patch.diff').read_text();projected,projection=evaluation_patch(patch,result['test_modifications'])
            (p/'evaluation.diff').write_text(projected)
            evaluated=grade(spec,projected,p/'evaluation',900,wheelhouse=p/'wheels')
            row={**result,'instance_id':iid,'status':evaluated['status'],'resolved':evaluated['resolved'],'evaluation':evaluated,'patch_projection':projection}
            row.update(outcome_axes(row))
        except Exception as exc:
            row={'instance_id':iid,'status':'infrastructure_failure','resolved':None,'error':str(exc)}
        finally: os.chdir(old)
        finish_run(p,row);rows.append(row)
        print(json.dumps({'index':index+1,'instance_id':iid,'status':row['status'],'resolved':row.get('resolved')}),flush=True)
        if should_halt(rows,continue_on_error=True,consecutive_limit=3):break
    (root/f'batch-{args.batch}-progress.json').write_text(json.dumps({'rows':rows,'records':len(rows),'review_boundary':True,'provider_api_cost_usd':0},indent=2)+'\n')
    if len(rows)!=5 or any(r.get('status') in {'control_failure','interrupted'} for r in rows):raise SystemExit(1)


if __name__=='__main__':main()
