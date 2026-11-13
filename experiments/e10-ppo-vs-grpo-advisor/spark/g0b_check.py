"""E10 G0b: check the ARM Tenacity image grades each SWE-smith instance as expected.

For each instance, in a fresh container: check out the bug branch and run the
suite (FAIL_TO_PASS must fail, PASS_TO_PASS must pass); then reverse the bug
patch (the gold fix) and run again (all listed tests must pass).
"""
import json, re, subprocess, sys, concurrent.futures as cf

IMAGE = sys.argv[1]
INSTANCES = sys.argv[2]
OUT = sys.argv[3]
TEST_CMD = "pytest --disable-warnings --color=no --tb=no --verbose"
LINE = re.compile(r"^(\S+::\S+)\s+(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)")


def sh(container, cmd, stdin=None):
    p = subprocess.run(["docker", "exec", "-i", container, "bash", "-c", cmd],
                       input=stdin, capture_output=True, text=True, timeout=900)
    return p.returncode, p.stdout + p.stderr


def run_tests(container):
    _, out = sh(container, f"source /opt/miniconda3/etc/profile.d/conda.sh && conda activate testbed && {TEST_CMD}")
    status = {}
    for line in out.splitlines():
        m = LINE.match(line.strip())
        if m:
            status[m.group(1)] = m.group(2)
    return status


def check(inst):
    name = "g0b-" + inst["instance_id"].split(".")[-1]
    subprocess.run(["docker", "rm", "-f", name], capture_output=True)
    subprocess.run(["docker", "run", "-d", "--name", name, "--network", "none", IMAGE, "sleep", "2h"],
                   check=True, capture_output=True)
    try:
        rc, out = sh(name, f"git checkout -q {inst['instance_id']}")
        if rc:
            return {**base(inst), "ok": False, "why": "checkout failed: " + out[-200:]}
        # The branch's last commit ("Remove F2P Tests") hides the grading tests;
        # restore them from the "Bug Patch" commit before running, as grading does.
        rc, out = sh(name, "git checkout HEAD~1 -- $(git diff --name-only HEAD HEAD~1)")
        if rc:
            return {**base(inst), "ok": False, "why": "test restore failed: " + out[-200:]}
        bug = run_tests(name)
        rc, out = sh(name, "git apply -R -", stdin=inst["patch"])
        if rc:
            return {**base(inst), "ok": False, "why": "reverse patch failed: " + out[-200:]}
        gold = run_tests(name)
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)
    f2p, p2p = inst["f2p"], inst["p2p"]
    bug_f2p_not_failing = [t for t in f2p if bug.get(t) == "PASSED"]
    bug_p2p_not_passing = [t for t in p2p if bug.get(t) != "PASSED"]
    gold_not_passing = [t for t in f2p + p2p if gold.get(t) != "PASSED"]
    ok = not (bug_f2p_not_failing or bug_p2p_not_passing or gold_not_passing)
    return {**base(inst), "ok": ok, "n_f2p": len(f2p), "n_p2p": len(p2p),
            "bug_f2p_not_failing": bug_f2p_not_failing, "bug_p2p_not_passing": bug_p2p_not_passing,
            "gold_not_passing": gold_not_passing}


def base(inst):
    return {"split": inst["split"], "instance_id": inst["instance_id"]}


rows = [json.loads(l) for l in open(INSTANCES)]
with cf.ThreadPoolExecutor(8) as ex, open(OUT, "w") as f:
    for r in ex.map(check, rows):
        f.write(json.dumps(r) + "\n"); f.flush()
        print(("OK  " if r["ok"] else "BAD ") + r["split"] + " " + r["instance_id"], flush=True)
