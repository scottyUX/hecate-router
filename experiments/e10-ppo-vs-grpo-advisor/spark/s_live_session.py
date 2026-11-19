"""E10 check S (amendment A4): one live agent session with the local student.

The agent server (advisor-models `agent_server.py`) runs one training issue
with the student served by `serve_student.sh`, no advisor (empty advice, as
E7's student-alone arm) and no training step. It calls execute_step 5 student
steps at a time, as the training env does, until the session ends or reaches
40 steps, and checks the connection, the step loop and the six features
returned with each non-final response (spec §3.1). The reward is not computed:
S is a connection check, not a result.

Usage (on the Spark, with both servers up):
  python3 s_live_session.py <advisor-models dir> <out.json> [--server http://127.0.0.1:8081]
"""

import argparse
import json
import sys
import time

import requests

N_INPUTS = 7


def first_training_issue(advisor_models: str) -> dict:
    with open(f"{advisor_models}/data/swe_smith/train_jd__tenacity.json") as f:
        line = next(l for l in f if l.strip())
    return json.loads(json.loads(line)["reward_spec"]["ground_truth_json"])


def check_features(features: dict, advice_turn: int, steps: int) -> list:
    problems = []
    inputs = features.get("inputs") or []
    if len(inputs) != N_INPUTS:
        problems.append(f"{len(inputs)} inputs, expected {N_INPUTS}")
    if any(not (0.0 <= v <= 1.0) for v in inputs):
        problems.append(f"input outside [0, 1]: {inputs}")
    raw = features.get("raw") or {}
    if raw.get("advice_turn") != advice_turn:
        problems.append(f"advice_turn {raw.get('advice_turn')}, expected {advice_turn}")
    if raw.get("steps_used") != min(steps, 40):
        problems.append(f"steps_used {raw.get('steps_used')}, expected {min(steps, 40)}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("advisor_models")
    ap.add_argument("out")
    ap.add_argument("--server", default="http://127.0.0.1:8081")
    ap.add_argument("--model", default="hosted_vllm/student")
    args = ap.parse_args()

    instance = first_training_issue(args.advisor_models)
    report = {"instance_id": instance["instance_id"], "model": args.model, "calls": [], "problems": []}
    t0 = time.time()
    r = requests.post(f"{args.server}/agent/session/create",
                      json={"instance": instance, "model_name": args.model}, timeout=600)
    r.raise_for_status()
    session_id = r.json()["session_id"]
    report["session_id"] = session_id
    print(f"session {session_id} on {instance['instance_id']}", flush=True)

    try:
        for call in range(1, 9 + 1):
            r = requests.post(f"{args.server}/agent/session/{session_id}/step",
                              json={"advisor_feedback": "", "max_steps": 5}, timeout=3600)
            r.raise_for_status()
            res = r.json()
            entry = {"call": call, "terminated": res.get("terminated"), "total_steps": res.get("total_steps"),
                     "error": res.get("error"), "features": res.get("features"),
                     "observation_chars": len(res.get("observation") or ""), "elapsed_s": round(time.time() - t0)}
            if not res.get("terminated"):
                if res.get("features") is None:
                    report["problems"].append(f"call {call}: no features in a non-final response")
                else:
                    report["problems"] += [f"call {call}: {p}" for p in
                                           check_features(res["features"], call, res.get("total_steps", 0))]
            if res.get("error"):
                report["problems"].append(f"call {call}: error {res['error']}")
            report["calls"].append(entry)
            raw = (res.get("features") or {}).get("raw")
            print(f"call {call}: steps={res.get('total_steps')} terminated={res.get('terminated')} "
                  f"error={res.get('error')} features={raw}", flush=True)
            if res.get("terminated"):
                break
        r = requests.get(f"{args.server}/agent/session/{session_id}/patch", timeout=600)
        report["patch_chars"] = len(r.json().get("patch", "")) if r.ok else None
    finally:
        requests.delete(f"{args.server}/agent/session/{session_id}", timeout=600)

    report["elapsed_s"] = round(time.time() - t0)
    report["ok"] = not report["problems"] and bool(report["calls"])
    with open(args.out, "w") as f:
        json.dump(report, f, indent=1)
    print(f"S {'OK' if report['ok'] else 'PROBLEMS'}: {report['problems'] or 'none'}; "
          f"patch_chars={report.get('patch_chars')} elapsed={report['elapsed_s']}s", flush=True)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
