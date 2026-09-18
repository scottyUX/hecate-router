# Diagnosing the Phala `BadRequestError`

Smoke run `sweep-2x300-mini-swe` (7B, 3 instances) produced:

```
BadRequestError   2   django__django-10914, sympy__sympy-20590
Submitted         1   astropy__astropy-12907
```

One instance succeeded under the same config, so the request shape is valid and
the `model.model_kwargs.timeout=300.0` we added is not the cause. Something
about the failing requests specifically is being rejected:

```
"message": "The request was rejected as invalid",
"type": "invalid_request_error", "code": null, "param": null,
"provider_name": "Phala"
```

`qwen/qwen-2.5-7b-instruct` has **exactly one provider on OpenRouter (Phala)**,
so there is no fallback to route around it.

Run both checks below from `~/hecate-mini` with the venv active.

## 1. How far did each instance get?

Failures save a trajectory, so we can see whether they died on call 1.

```bash
python3 -c "
import json, glob
for f in sorted(glob.glob('data/outputs/runs/sweep-2x300-mini-swe/qwen__qwen-2.5-7b-instruct/*/*.traj.json')):
    d = json.load(open(f))
    i = d.get('info', {}); s = i.get('model_stats') or {}
    msgs = d.get('messages', [])
    chars = sum(len(str(m.get('content') or '')) for m in msgs)
    first = len(str(msgs[1].get('content'))) if len(msgs) > 1 else 0
    print(f\"{d.get('instance_id'):28s} exit={str(i.get('exit_status')):16s} calls={s.get('api_calls')} msgs={len(msgs)} total_chars={chars} task_chars={first}\")
"
```

**Reading it:** `calls=0` or `1` with a large `task_chars` means the very first
request was already too big. The task prompt is the entire GitHub issue, and
`django-10914` / `sympy-20590` have long problem statements, while
`astropy-12907` (the one that worked) is short. 7B's context is 32,768 tokens
— roughly 130k characters.

## 2. Does Phala fail at a size threshold?

Bypasses mini-SWE entirely — just OpenRouter and increasing payload sizes.

```bash
python3 -c "
import os, json, urllib.request
from hecate.utils.env import load_env
load_env()
k = os.environ['OPENROUTER_API_KEY']
for n in (100, 5000, 20000, 50000, 100000):
    body = json.dumps({'model':'qwen/qwen-2.5-7b-instruct',
                       'messages':[{'role':'user','content':'x'*n}],
                       'max_tokens':16}).encode()
    req = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions', data=body,
        headers={'Authorization':f'Bearer {k}','Content-Type':'application/json'})
    try:
        urllib.request.urlopen(req, timeout=60); print(f'{n:7d} chars  OK')
    except Exception as e:
        print(f'{n:7d} chars  FAIL  {str(e)[:120]}')
"
```

**Reading it:**

| result | meaning |
|---|---|
| small OK, large FAIL | context ceiling surfacing as a generic 400. Structural — 7B cannot take long issues on this provider. |
| all OK | Phala is flaky/intermittent, not size-bound. Retries may get through. |
| all FAIL | provider or key problem, unrelated to payload. |

## 3. Does tool calling work at all?

The failing requests carry tool definitions; the size probe above does not. If
step 2 shows everything OK, the tools payload is the next suspect.

```bash
python3 -c "
import os, json, urllib.request
from hecate.utils.env import load_env
load_env()
k = os.environ['OPENROUTER_API_KEY']
body = json.dumps({'model':'qwen/qwen-2.5-7b-instruct',
  'messages':[{'role':'user','content':'List files in the current directory.'}],
  'tools':[{'type':'function','function':{'name':'bash','description':'Run a bash command',
     'parameters':{'type':'object','properties':{'command':{'type':'string'}},'required':['command']}}}],
  'max_tokens':64}).encode()
req = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions', data=body,
    headers={'Authorization':f'Bearer {k}','Content-Type':'application/json'})
try:
    r = json.load(urllib.request.urlopen(req, timeout=60))
    m = r['choices'][0]['message']
    print('OK  tool_calls=', json.dumps(m.get('tool_calls'))[:300])
except Exception as e:
    print('FAIL', str(e)[:300])
"
```

## What each outcome implies for the run

- **Size-bound (step 2 fails at large payloads).** The 7B arm cannot process
  long-issue instances at all. Expect a high `BadRequestError` rate across the
  300, concentrated on repos with verbose issues. Not fixable by config — it is
  the 32k ceiling we accepted when keeping this pair.
- **Intermittent.** Raise `MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT` above its
  default of 10 and accept slower runs.
- **Tool-calling rejected (step 3 fails).** Switch to upstream's
  `swebench_backticks.yaml`, which puts commands in code blocks instead of
  native tool calls. Still a stock config, so comparability holds.

## Context

- Cost so far on this smoke: **$0.01**. Diagnosis is cheap; the full 600 is not.
- `qwen-2.5-72b` has two providers (DeepInfra, Novita), so the large arm has a
  fallback the small arm lacks. Worth smoking 72B separately before concluding
  anything about the pair.
- `data/outputs/runs/fmt-pilot-editblocks/manifest.json` records both of those
  providers failing on 72B historically (Novita: "does not support endpoint:
  completions"; DeepInfra: rate-limited). Provider coverage for this pair has
  been thin for a while.
