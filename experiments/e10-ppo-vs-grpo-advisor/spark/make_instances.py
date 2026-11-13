"""Build the 105 Tenacity instances (56 train, 49 test) for g0b_check.py.

Usage: python3 make_instances.py <advisor-models dir> <out.jsonl>
"""
import ast
import json
import sys

SPLITS = [("train", "train_jd__tenacity.json"), ("test", "validation_jd__tenacity.json")]

root, out_path = sys.argv[1], sys.argv[2]
with open(out_path, "w") as out:
    for split, name in SPLITS:
        for line in open(f"{root}/data/swe_smith/{name}"):
            if not line.strip():
                continue
            gt = json.loads(json.loads(line)["reward_spec"]["ground_truth_json"])
            tests = {k: ast.literal_eval(gt[k]) if isinstance(gt[k], str) else gt[k]
                     for k in ("FAIL_TO_PASS", "PASS_TO_PASS")}
            out.write(json.dumps({"split": split, "instance_id": gt["instance_id"], "patch": gt["patch"],
                                  "f2p": tests["FAIL_TO_PASS"], "p2p": tests["PASS_TO_PASS"]}) + "\n")
